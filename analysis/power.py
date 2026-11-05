#!/usr/bin/env python3
"""Precision and decision-rule simulation for PROTOCOL.md sections 4.6 and 5 (bytes-per-word, P1).

Deterministic: every random draw comes from numpy.random.default_rng with a seed printed below.
No model runs, no tok/s data: all inputs are stated assumptions (noise levels, layouts, scenarios) or
read from results/pilot/ (advisory context only, never a predictor input).

Run:  python3 analysis/power.py      (about 1-2 minutes on the 2-vCPU workspace)
Every number quoted in analysis/POWER.md is printed by this script, in sections S1-S8.
"""
import itertools
import json
import math
import os

import numpy as np
from scipy import stats

SIM_SEED = 20261109      # power-simulation noise only (not a protocol seed)
BOOT_SEED = 20261108     # PROTOCOL.md 3.7 bootstrap seed, used for the Monte Carlo bootstrap demonstration
B_MC = 10_000            # PROTOCOL.md 5.1 resamples
TARGET_HW = 0.02         # PROTOCOL.md 4.6: 95% CI half-width <= 2% of the cell mean
ALPHA = 0.05
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def hdr(t):
    print("\n" + "=" * 100 + "\n" + t + "\n" + "=" * 100)


# ---------------------------------------------------------------------------------------------
# S0. Pilot context (advisory; NumPy probe on Host B, not the pre-registered B1/F1 benchmarks)
# ---------------------------------------------------------------------------------------------
def s0_pilot():
    hdr("S0. Pilot context: within-process CV of the Host B NumPy probe (results/pilot/, advisory only)")
    for fn in ("host_xeon_run1.json", "host_xeon_run2.json"):
        p = os.path.join(REPO, "results", "pilot", fn)
        if not os.path.exists(p):
            print(f"{fn}: missing")
            continue
        d = json.load(open(p))
        row = []
        for k in ("copy_GBps", "triad_GBps", "fp32_matmul_GFLOPs"):
            x = np.asarray(d[k], float)
            row.append(f"{k}: CV={100 * x.std(ddof=1) / x.mean():.2f}% min/median={x.min() / np.median(x):.3f}")
        print(f"{fn}: " + " | ".join(row))


# ---------------------------------------------------------------------------------------------
# S1. Rounds per cell for the 2% half-width target (t interval on round values)
# ---------------------------------------------------------------------------------------------
def halfwidth(cv, n):
    return stats.t.ppf(0.975, n - 1) * cv / math.sqrt(n)


def s1_rounds(rng):
    hdr("S1. Rounds per cell: half-width = t(0.975, n-1) * CV / sqrt(n); target <= 2.0% of the cell mean")
    print("Max between-round CV that meets the target with certainty-equivalent s = CV:")
    for n in (3, 5, 6, 8, 10, 12, 15):
        cvmax = TARGET_HW * math.sqrt(n) / stats.t.ppf(0.975, n - 1)
        print(f"  n={n:2d}: t={stats.t.ppf(0.975, n - 1):.3f}  CV_max={100 * cvmax:.2f}%")
    reps = 20000
    print("\nTable R (normal round values; P columns simulated with sample SD, %d reps, seed %d):" % (reps, SIM_SEED))
    print(f"{'CV%':>5} {'n_req':>6} {'hw@5%':>7} {'hw@8%':>7} {'hw@10%':>7} {'P(meet@5)':>10} {'P(meet<=8)':>11} "
          f"{'P(imprecise)':>13} {'E[rounds]':>10}")
    for cv in (0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05):
        n_req = next(n for n in range(2, 1000) if halfwidth(cv, n) <= TARGET_HW)
        x = 1.0 + cv * rng.standard_normal((reps, 8))
        m5, s5 = x[:, :5].mean(1), x[:, :5].std(1, ddof=1)
        ok5 = stats.t.ppf(0.975, 4) * s5 / math.sqrt(5) / m5 <= TARGET_HW
        m8, s8 = x.mean(1), x.std(1, ddof=1)
        ok8 = stats.t.ppf(0.975, 7) * s8 / math.sqrt(8) / m8 <= TARGET_HW
        meet = ok5 | (~ok5 & ok8)
        e_rounds = np.where(ok5, 5, 8).mean()
        print(f"{100 * cv:5.1f} {n_req:6d} {100 * halfwidth(cv, 5):7.2f} {100 * halfwidth(cv, 8):7.2f} "
              f"{100 * halfwidth(cv, 10):7.2f} {ok5.mean():10.3f} {meet.mean():11.3f} {1 - meet.mean():13.3f} {e_rounds:10.2f}")


# ---------------------------------------------------------------------------------------------
# S2. Variance-only extension: bias and coverage under a skewed (interference) noise model
# ---------------------------------------------------------------------------------------------
def s2_extension(rng):
    hdr("S2. Extension 5 -> 8 rounds (one look, 3 rounds added together) vs fixed designs; skewed noise model")
    print("Round value = exp(N(0, cv)) * (0.95 with prob p_slow else 1). Bias of cell mean vs true E[round], % of mean.")
    reps = 200000
    print(f"{'cv%':>4} {'p_slow':>6} {'bias_fixed5%':>13} {'bias_fixed8%':>13} {'bias_adapt%':>12} {'bias_seq%':>10} "
          f"{'cover_adapt':>12} {'P(ext)':>7}")
    for cv in (0.01, 0.02, 0.03):
        for p_slow in (0.0, 0.1, 0.2):
            ln = cv * rng.standard_normal((reps, 8))
            slow = rng.random((reps, 8)) < p_slow
            x = np.exp(ln) * np.where(slow, 0.95, 1.0)
            true = math.exp(cv ** 2 / 2) * (1 - 0.05 * p_slow)
            f5, f8 = x[:, :5].mean(1), x.mean(1)
            hw5 = stats.t.ppf(0.975, 4) * x[:, :5].std(1, ddof=1) / math.sqrt(5)
            ext = hw5 / f5 > TARGET_HW
            adapt = np.where(ext, f8, f5)
            hw8 = stats.t.ppf(0.975, 7) * x.std(1, ddof=1) / math.sqrt(8)
            hw = np.where(ext, hw8, hw5)
            cover = (np.abs(adapt - true) <= hw).mean()
            # sequential alternative: add one round at a time, re-check after each (looks at 5,6,7,8)
            seq = f5.copy()
            done = ~ext
            for n in (6, 7, 8):
                mn = x[:, :n].mean(1)
                hn = stats.t.ppf(0.975, n - 1) * x[:, :n].std(1, ddof=1) / math.sqrt(n)
                newly = (~done) & ((hn / mn <= TARGET_HW) | (n == 8))
                seq = np.where(newly, mn, seq)
                done |= newly
            print(f"{100 * cv:4.0f} {p_slow:6.2f} {100 * (f5.mean() / true - 1):13.4f} {100 * (f8.mean() / true - 1):13.4f} "
                  f"{100 * (adapt.mean() / true - 1):12.4f} {100 * (seq.mean() / true - 1):10.4f} {cover:12.4f} {ext.mean():7.3f}")


# ---------------------------------------------------------------------------------------------
# S3. Q1: reliability of the point-MAPE decision under measurement noise
# ---------------------------------------------------------------------------------------------
def true_ratios(n, mape, pattern):
    """Deterministic true ratios r_c = yhat_c / y_c with sum |r_c - 1| / n == mape."""
    z = stats.norm.ppf((np.arange(n) + 0.5) / n)
    sgn = np.where(np.arange(n) % 2 == 0, 1.0, -1.0) if pattern == "mixed" else np.ones(n)

    def f(a):
        return np.mean(np.abs(np.exp(sgn * a + 0.03 * z) - 1)) - mape

    lo, hi = 0.0, 2.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return np.exp(sgn * lo + 0.03 * z)


def s3_mape(rng):
    hdr("S3. Q1 point-MAPE decision (pass iff MAPE <= 20.0%): P(pass) vs true MAPE, measurement noise only")
    print("Noise in ln y per cell ~ N(0, CV/sqrt(k)); common-mode on every prediction of a host: calibration cell")
    print("N(0, CV/sqrt(k_cal)); Host B also B1_A and B1_B (median of r process runs, SE = 1.2533*CV_B1/sqrt(r) each);")
    print("Host A: B1_A cancels (yhat = y_cal*D_cal/D). Patterns: 'same' = all errors one sign, 'mixed' = alternating signs.")
    reps = 40000
    configs = [  # (label, n cells, cell CV, rounds k, calibration rounds, B1 CV per process run, B1 process runs)
        ("A n=7 CV2 k5 kcal5", 7, 0.02, 5, 5, None, 5),
        ("A n=7 CV2 k5 kcal10", 7, 0.02, 5, 10, None, 5),
        ("B n=6 CV2 k5 kcal10 B1cv1 r5", 6, 0.02, 5, 10, 0.01, 5),
        ("B n=6 CV2 k5 kcal10 B1cv3 r5", 6, 0.02, 5, 10, 0.03, 5),
        ("B n=6 CV2 k5 kcal10 B1cv3 r10", 6, 0.02, 5, 10, 0.03, 10),
        ("B n=6 CV3 k8 kcal10 B1cv1 r5", 6, 0.03, 8, 10, 0.01, 5),
        ("B n=3 CV3 k8 kcal10 B1cv1 r5", 3, 0.03, 8, 10, 0.01, 5),
    ]
    mapes = (0.15, 0.17, 0.18, 0.19, 0.195, 0.205, 0.21, 0.22, 0.23, 0.25)
    for pattern in ("same", "mixed"):
        print(f"\npattern={pattern}")
        print(f"{'config':<32}" + "".join(f"{100 * m:>7.1f}" for m in mapes) + f"{'SD(pp)':>8}")
        for name, n, cv, k, kcal, b1cv, b1r in configs:
            row, sds = [], []
            for m in mapes:
                r = true_ratios(n, m, pattern)
                e_cell = rng.standard_normal((reps, n)) * cv / math.sqrt(k)
                common = rng.standard_normal(reps) * cv / math.sqrt(kcal)
                if b1cv is not None:
                    common = common + rng.standard_normal(reps) * math.sqrt(2) * 1.2533 * b1cv / math.sqrt(b1r)
                r_obs = r[None, :] * np.exp(common[:, None] - e_cell)
                mape_obs = np.abs(r_obs - 1).mean(1)
                row.append((mape_obs <= 0.20).mean())
                sds.append(mape_obs.std())
            print(f"{name:<32}" + "".join(f"{p:7.3f}" for p in row) + f"{100 * np.mean(sds):8.2f}")


# ---------------------------------------------------------------------------------------------
# Ratio-test machinery
# ---------------------------------------------------------------------------------------------
_EXACT = {}


def exact_boot_support(n):
    """All bootstrap resample count vectors for n units with multinomial probabilities (ideal bootstrap, B -> inf)."""
    if n not in _EXACT:
        rows = []
        for comb in itertools.combinations_with_replacement(range(n), n):
            rows.append(np.bincount(comb, minlength=n))
        c = np.array(rows, float)
        logp = math.lgamma(n + 1) - np.sum([np.vectorize(math.lgamma)(c[:, i] + 1) for i in range(n)], axis=0) \
            - n * math.log(n)
        _EXACT[n] = (c / n, np.exp(logp))
    return _EXACT[n]


_FLIPS = {}


def flips(n):
    if n not in _FLIPS:
        _FLIPS[n] = np.array(list(itertools.product((1.0, -1.0), repeat=n)))
    return _FLIPS[n]


def rules(delta):
    """delta: (reps, n). Returns dict of boolean pass vectors and the refute vector (mean <= 0)."""
    reps, n = delta.shape
    mean = delta.mean(1)
    w, p = exact_boot_support(n)
    mass_le0 = ((w @ delta.T) <= 0).T @ p           # bootstrap P(mean* <= 0)
    boot = (mean > 0) & (mass_le0 < ALPHA)          # percentile one-sided 95% lower bound > 0
    fl = flips(n)
    perm = (fl @ np.abs(delta).T).T / n             # (reps, 2^n) sign-flipped means
    p_flip = (perm >= mean[:, None] - 1e-12).mean(1)
    signflip = (mean > 0) & (p_flip <= ALPHA)
    k = (delta > 0).sum(1)
    p_sign = stats.binom.sf(k - 1, n, 0.5)
    sign = (mean > 0) & (p_sign <= ALPHA)
    return {"boot": boot, "signflip": signflip, "sign": sign, "boot&flip": boot & signflip, "refute": mean <= 0}


def s4_min_units():
    hdr("S4. Minimum number of units for which each one-sided 5% rule can ever pass")
    for n in range(1, 9):
        print(f"  n={n}: smallest attainable sign-test / sign-flip p = 0.5^n = {0.5 ** n:.4f} -> "
              f"{'can pass' if 0.5 ** n <= ALPHA else 'can never pass'}")
    print("Sign test: number of positive units needed to pass at alpha = 0.05:")
    for n in range(5, 11):
        need = next(k for k in range(n + 1) if stats.binom.sf(k - 1, n, 0.5) <= ALPHA)
        print(f"  n={n:2d}: need >= {need} of {n} positive (p = {stats.binom.sf(need - 1, n, 0.5):.4f})")
    rng = np.random.default_rng(BOOT_SEED)
    print(f"Percentile bootstrap (Monte Carlo, B={B_MC}, seed {BOOT_SEED}) on all-positive toy vectors:")
    for d in ([0.3], [0.3, 0.05], [0.3, 0.2, 0.01]):
        d = np.asarray(d)
        idx = rng.integers(0, len(d), size=(B_MC, len(d)))
        lb = np.quantile(d[idx].mean(1), 0.05)
        print(f"  n={len(d)} delta={d.tolist()}: one-sided 95% lower bound = {lb:.4f} (> 0: passes)")
    print("=> the percentile bootstrap passes for ANY n >= 1 when every unit favours bytes; it carries no small-n error control.")


# Unit layouts (JUDGEMENT/UNVERIFIED: estimated from repo file sizes in PROTOCOL 3.5; real counts come from cells.py)
# Q2 units are (host, size, type) with cells (lower-bit, higher-bit); cells are shared within (host, size).
Q2_LAYOUTS = {
    "4xLLC incl-cal (8)": [("A", "0.6", "C1"), ("A", "0.6", "C2"), ("A", "1.7", "C1"), ("A", "1.7", "C2"), ("A", "4", "C1"),
                           ("B", "1.7", "C1"), ("B", "1.7", "C2"), ("B", "4", "C1")],
    "4xLLC excl-cal (6)": [("A", "0.6", "C1"), ("A", "0.6", "C2"), ("A", "4", "C1"),
                           ("B", "1.7", "C1"), ("B", "1.7", "C2"), ("B", "4", "C1")],
    "8xLLC incl-cal (6)": [("A", "0.6", "C1"), ("A", "0.6", "C2"), ("A", "1.7", "C1"), ("A", "1.7", "C2"), ("A", "4", "C1"),
                           ("B", "4", "C1")],
    "8xLLC excl-cal (4)": [("A", "0.6", "C1"), ("A", "0.6", "C2"), ("A", "4", "C1"), ("B", "4", "C1")],
}
LN_RB = {"C1": math.log(1.7), "C2": math.log(16 / 8.5)}   # C1 illustrative (Q4_K_M mixes types); C2 from bits/weight


def sim_q2(rng, layout, lam, tau, hdq, cv, k, reps):
    """lam: 1 bytes law, 0 FLOPs law (ratio 1), 0.5 geometric midpoint (boundary null).
    tau: SD of per-cell log efficiency (format x host x size heterogeneity). hdq: log efficiency penalty of Q4_K_M cells."""
    cells = {}
    for h, s, _ in layout:
        for q in ("Q4", "Q8", "F16"):
            if (h, s, q) not in cells:
                cells[(h, s, q)] = tau * rng.standard_normal(reps) + cv / math.sqrt(k) * rng.standard_normal(reps) \
                    + (hdq if q == "Q4" else 0.0)
    d = np.empty((reps, len(layout)))
    for j, (h, s, t) in enumerate(layout):
        a, b = ("Q4", "Q8") if t == "C1" else ("Q8", "F16")
        lnR = lam * LN_RB[t] + cells[(h, s, a)] - cells[(h, s, b)]
        d[:, j] = np.abs(lnR) - np.abs(lnR - LN_RB[t])
    return d


def s5_q2(rng):
    hdr("S5. Q2 quantisation-ratio test: P(pass) per rule and P(refute: mean delta <= 0); exact bootstrap (B->inf)")
    print("Assumed ln R_B: C1 = ln 1.7 (illustrative; Q4_K_M mixes types, UNVERIFIED), C2 = ln(16/8.5) (bits/weight).")
    print("A unit favours bytes iff ln R > ln(R_B)/2, i.e. measured ratio > sqrt(R_B):",
          f"C1 sqrt={math.exp(LN_RB['C1'] / 2):.3f}, C2 sqrt={math.exp(LN_RB['C2'] / 2):.3f};",
          f"so a C1 pair is lost iff eta_Q4/eta_Q8 < {math.exp(-LN_RB['C1'] / 2):.3f}.")
    reps = 4000
    scen = [("bytes law, tau=0.05", 1.0, 0.05, 0.0), ("bytes law, tau=0.15", 1.0, 0.15, 0.0),
            ("bytes + HDQ eta_Q4 x0.75", 1.0, 0.05, math.log(0.75)), ("bytes + HDQ eta_Q4 x0.60", 1.0, 0.05, math.log(0.60)),
            ("boundary null lam=0.5, tau=0.05", 0.5, 0.05, 0.0), ("boundary null lam=0.5, tau=0.15", 0.5, 0.15, 0.0),
            ("FLOPs law lam=0, tau=0.05", 0.0, 0.05, 0.0)]
    print(f"cell noise: CV=2%, k=5 rounds; reps={reps}, seed {SIM_SEED}")
    print(f"{'layout':<20} {'scenario':<34} {'boot':>6} {'flip':>6} {'sign':>6} {'b&f':>6} {'refute':>7}")
    for lname, lay in Q2_LAYOUTS.items():
        for sname, lam, tau, hdq in scen:
            d = sim_q2(rng, lay, lam, tau, hdq, 0.02, 5, reps)
            r = rules(d)
            print(f"{lname:<20} {sname:<34} {r['boot'].mean():6.3f} {r['signflip'].mean():6.3f} {r['sign'].mean():6.3f} "
                  f"{r['boot&flip'].mean():6.3f} {r['refute'].mean():7.3f}")


def s6_q3(rng):
    hdr("S6. Q3 cross-machine-ratio test: P(pass) per rule; predictions R_B, R_F are constants shared by every file")
    print("ln R = lam*ln R_B + (1-lam)*ln R_F + u_file, u_file ~ N(0, tau) + cell noise; |ln(R_F/R_B)| = ln rho.")
    print(f"Half-gap at the drop threshold rho=1.5: ln(1.5)/2 = {math.log(1.5) / 2:.4f}")
    for b1cv in (0.01, 0.03):
        se_lnratio = math.sqrt(2) * 1.2533 * b1cv / math.sqrt(5)
        print(f"  host-constant noise: B1 CV={100 * b1cv:.0f}% -> SE of ln(B1_B/B1_A) ~ {se_lnratio:.4f} "
              f"(= {se_lnratio / (math.log(1.5) / 2):.3f} of the half-gap); same order for F1")
    reps = 4000
    print(f"cell noise: CV=2%, k=5; reps={reps}, seed {SIM_SEED}")
    print(f"{'n files':>7} {'rho':>5} {'scenario':<24} {'boot':>6} {'flip':>6} {'sign':>6} {'b&f':>6} {'refute':>7}")
    for n in (3, 4, 5, 6):
        for rho in (1.5, 2.0):
            lnRB, lnRF = math.log(0.5), math.log(0.5 * rho)
            for sname, lam, tau in (("bytes law, tau=0.10", 1.0, 0.10), ("bytes law, tau=0.25", 1.0, 0.25),
                                    ("boundary lam=0.5,tau=0.10", 0.5, 0.10), ("FLOPs law, tau=0.10", 0.0, 0.10)):
                u = tau * rng.standard_normal((reps, n)) + math.sqrt(2) * 0.02 / math.sqrt(5) * rng.standard_normal((reps, n))
                lnR = lam * lnRB + (1 - lam) * lnRF + u
                d = np.abs(lnR - lnRF) - np.abs(lnR - lnRB)
                r = rules(d)
                print(f"{n:7d} {rho:5.1f} {sname:<24} {r['boot'].mean():6.3f} {r['signflip'].mean():6.3f} {r['sign'].mean():6.3f} "
                      f"{r['boot&flip'].mean():6.3f} {r['refute'].mean():7.3f}")


def s7_dependence(rng):
    hdr("S7. Dependence in Q2: correlation of delta between the C1 and C2 pairs that share one Q8_0 cell")
    reps = 40000
    lay = [("A", "1.7", "C1"), ("A", "1.7", "C2")]
    for lam, tau in ((1.0, 0.05), (0.5, 0.05), (0.5, 0.15)):
        d = sim_q2(rng, lay, lam, tau, 0.0, 0.02, 5, reps)
        print(f"  lam={lam}, tau={tau}: corr(delta_C1, delta_C2) = {np.corrcoef(d.T)[0, 1]:+.3f}")
    print("  (negative or near-zero: sharing the middle cell does not inflate the sign-flip test's size; see S5 boundary rows)")


def s8_iut():
    hdr("S8. Intersection-union: joint claim = Q1A and Q1B and Q2 and Q3 (when kept)")
    print("Any false joint claim needs at least one false component: P(joint pass | some H0_i) <= P(pass_i | H0_i) <= alpha.")
    print(f"Inferential components at one-sided alpha = {ALPHA}: Q2, Q3; Q1 is a fixed point threshold (no alpha).")
    print("No Holm/Bonferroni correction is needed for the conjunction; a correction would only lower power.")


if __name__ == "__main__":
    print(f"power.py  SIM_SEED={SIM_SEED}  BOOT_SEED={BOOT_SEED}  B_MC={B_MC}  numpy {np.__version__}")
    rng = np.random.default_rng(SIM_SEED)
    s0_pilot()
    s1_rounds(rng)
    s2_extension(rng)
    s3_mape(rng)
    s4_min_units()
    s5_q2(rng)
    s6_q3(rng)
    s7_dependence(rng)
    s8_iut()
