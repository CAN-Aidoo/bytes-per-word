# POWER.md: precision basis and decision rules for PROTOCOL.md sections 4-5

Project: bytes-per-word · Phase: P1 · Author: statistician (CANLABS) · Date: 2026-11-05
Inputs read: `.lab/STATE.md`, `.lab/ALERTS.md` (3 AMBER, no RED), `.lab/OWNERS.md`, `.lab/QUESTION.md`, `.lab/GATE_LOG.md`,
`PROTOCOL.md` (§§1-7, 10, Appendix H), `hardware/HOSTS.md`, `results/pilot/host_xeon_run{1,2}.json` (advisory only).
Calculation: `analysis/power.py` (deterministic; simulation seed 20261109, bootstrap demonstration seed 20261108, 10,000 resamples).
Every number below is printed by `python3 analysis/power.py`; the section tag (S0-S8) says where. No tok/s data exist; all noise
levels, unit layouts and scenarios are **assumptions**, stated as such. Two runs of the script gave byte-identical output (md5 checked).

Decision-critical text used here (verbatim, source `PROTOCOL.md` line 27, = `.lab/gates/G0_novelty.md` line 11):
> "... predict held-out tok/s on every other machine, model size and quantisation level within a pre-registered MAPE of 20%, and beat an equally constrained FLOPs predictor (tok/s = η′ · F_meas / 2P_active) on both the quantisation-ratio and the cross-machine-ratio tests; it is refuted if held-out MAPE exceeds 20% on any host, or if the FLOPs predictor is not worse on either ratio test."

---

## Unit and metric

**Units (confirmed, with one change).**
- Q1: the **cell** (host × file × depth × threads). Replicate inside a cell = the **round** (one fresh `llama-bench` process); the
  5 `-r` repetitions inside a round are not independent and only form the round value. Cell value = mean of round values. Correct as
  drafted; it avoids pseudo-replication of repetitions.
- Q2: the **quantisation pair** (host, size, C1 or C2). Q3: the **file** eligible on both hosts.
- Q3 scope: the predicted ratios R_B = B1_B/B1_A and R_F = F1_B/F1_A are **one constant pair for all files**. Files replicate over
  models, not over machines; the machine comparison has n = 1 host pair. Q3 can therefore support "on these two hosts", never
  "across machines" in general (edit E7).
- **Change:** the calibration cell must **enter** the Q2/Q3 ratio units. η and η′ cancel in every ratio (R = y_a/y_b, R_B = D_b/D_a or
  B1_B/B1_A), so the calibration cell carries no fitted information into Q2/Q3. Excluding it removes 2 Q2 pairs and 1 Q3 file (S5
  layouts) and, in the 8×LLC branch, leaves Q2 with 4 pairs, a number at which no exact 5% test can pass (S4, S5). It stays excluded
  from every APE, MAPE and Q1 statistic (edit E3).

**Error metric, Q1.** APE_c = |ŷ_c − y_c| / y_c and per-host MAPE with the decision on the **point estimate** vs 20.0% are kept: the
question names MAPE and a point refutation ("held-out MAPE exceeds 20%"), and the metric must not change after G0. Note for readers:
APE is asymmetric (over-prediction by a factor 1.25 scores 25%, under-prediction by 1.25 scores 20%). A symmetric secondary,
mean |ln(ŷ/y)| per host, is **reported, not decisive** (edit E5). The 95% percentile-bootstrap CI over cells is reported next to the
point (n = 3-7 cells per host, so it is coarse and descriptive).

**Error metric, Q2/Q3.** The paired log-ratio difference Δ = e_F − e_B with e = |ln(R / R_pred)| is confirmed. It is paired by
construction, scale-free, symmetric in over/under-prediction, and η-free. Interpretation (S5): a unit favours bytes iff the measured
ratio lies on the bytes side of the **geometric midpoint** of the two predictions. For Q2 that is R > sqrt(R_B): with the assumed
R_B values, sqrt = 1.304 (C1, R_B = 1.7, illustrative) and 1.372 (C2, R_B = 16/8.5); a C1 pair is lost iff η_Q4/η_Q8 < 0.767.
For Q3 the margin from the midpoint is at least ln(1.5)/2 = 0.2027 whenever the §4.5 rule keeps the test (S6).

**Fitted parameters.** Bytes predictor: 1 (η). FLOPs predictor: 1 (η′, plus η′₂ for F2). Both fitted on the same single cell.

## Precision and rounds

**Half-width formula (to pre-register).** h = t(0.975, n−1) · s / √n, with s the SD of the n round values; target h / mean ≤ 2.0%.
Required CV for the target (S1): n = 5 needs CV ≤ 1.61%; n = 8 needs CV ≤ 2.39%; n = 10 needs CV ≤ 2.80%; n = 12 needs CV ≤ 3.15%.

**Table R (S1; normal round values, sample SD, 20,000 reps).**

| between-round CV | rounds needed | h at 5 | h at 8 | P(meet at 5) | P(meet by 8) | P(imprecise) | E[rounds] |
|---|---|---|---|---|---|---|---|
| 0.5% | 3 | 0.62% | 0.42% | 1.000 | 1.000 | 0.000 | 5.00 |
| 1.0% | 4 | 1.24% | 0.84% | 0.965 | 1.000 | 0.000 | 5.11 |
| 1.5% | 5 | 1.86% | 1.25% | 0.675 | 0.989 | 0.011 | 5.98 |
| 2.0% | 7 | 2.48% | 1.67% | 0.372 | 0.830 | 0.170 | 6.88 |
| 2.5% | 9 | 3.10% | 2.09% | 0.203 | 0.534 | 0.466 | 7.39 |
| 3.0% | 12 | 3.72% | 2.51% | 0.118 | 0.305 | 0.695 | 7.65 |
| 3.5% | 15 | 4.35% | 2.93% | 0.070 | 0.178 | 0.822 | 7.79 |
| 4.0% | 18 | 4.97% | 3.34% | 0.045 | 0.098 | 0.902 | 7.87 |
| 4.5% | 22 | 5.59% | 3.76% | 0.026 | 0.055 | 0.945 | 7.92 |
| 5.0% | 27 | 6.21% | 4.18% | 0.020 | 0.037 | 0.963 | 7.94 |

**Verdict on 5 rounds + extension to 8: sound, with three fixes.**
1. **V8 is inconsistent with §4.6.** V8 admits between-round CV ≤ 3%, "needed to meet the 2% CI target with 5 rounds"; at CV 3% the
   target needs 12 rounds and 0.695 of cells would end "imprecise" (Table R). V8 tolerance must be **CV ≤ 1.5%** (P(meet by 8) = 0.989).
   Above that, find the noise source first, as V8 already says (edit E10).
2. **Extension = one look.** After 5 rounds, if h/mean > 2.0%, add **3 rounds together** (one look), not one at a time. Bias of the
   adaptive cell mean under a skewed interference model (rounds 5% slow with probability 0.1-0.2) is at most 0.1169% of the mean
   (one-look) vs 0.1213% (sequential), against a 2% target (S2): negligible, and the rule never sees the predictor. Coverage of the
   final t-interval falls to 0.8615 in the worst skewed case (CV 1%, p_slow 0.2) because extension is triggered by slow outliers;
   acceptable for a precision flag, and reported. "Imprecise" cells are **scored and flagged**, never excluded.
3. **Calibration cell: 10 rounds, fixed.** Its noise multiplies every prediction on both hosts (common-mode). On Host A (7 cells,
   CV 2%, all errors of one sign) the SD of the observed MAPE falls from 1.15 pp (calibration 5 rounds) to 0.86 pp (10 rounds) (S3).

**Host constants matter more than rounds on Host B (S3).** On Host A, B1_A cancels (ŷ = y_cal·D_cal/D). On Host B, ŷ carries
ln(B1_B/B1_A) as a common-mode error. With B1 process-run CV 1% the Host B MAPE noise SD is 1.29 pp; with CV 3% (the current V9
limit) it is 2.98 pp, and 2.20 pp even with 10 process runs. Hence **V9 for B1: CV ≤ 1.0%** (edit E10). The pilot NumPy probe on
Host B had within-process copy CV 1.77% and 1.02% (S0; advisory, not the B1 benchmark, and B1 takes a median of 19 iterations).

**Decision reliability, Q1 (S3, "same-sign" errors, the harder case).** With the recommended design (cell CV 2%, 5 rounds,
calibration 10 rounds, B1 CV 1%), P(pass) is 0.990 (Host A) / 0.941 (Host B) at true MAPE 18%, and 0.011 / 0.060 at 22%; at 19.5% and
20.5% the outcome is noise-dominated (Host A 0.718 / 0.282). With alternating-sign errors common-mode noise largely cancels (SD
0.42-0.94 pp). Consequence: a point MAPE within about 2 pp of 20% is reported with template T-imprecise and its CI; the decision rule
itself is unchanged.

## Ratio tests

**Minimum units for any pass (S4).**
- One-sided 95% **percentile bootstrap** (lower bound > 0): passes for **any n ≥ 1** when all units favour bytes (MC demo, B = 10,000,
  seed 20261108: n = 1 lower bound 0.3000, n = 2 0.0500, n = 3 0.0733). It has no small-n error control: at the boundary null its
  rejection rate was 0.187 (Q3, n = 3), 0.120 (n = 4), 0.090 (Q2, 4 pairs) against a nominal 0.05 (S5, S6).
- **Exact sign test** and **exact sign-flip (randomisation) test**: smallest p = 0.5^n, so they can pass only for **n ≥ 5**
  (0.0312). The sign test needs 5/5, 6/6, 7/7, 7/8, 8/9, 9/10 positive units; the sign-flip test uses magnitudes and can tolerate a
  small negative unit at n ≥ 6.

**Rule adopted (edits E6, E12, E13).** For Q2 and Q3 separately, with n units:
- **Bytes wins** iff (a) mean Δ > 0, **and** (b) exact one-sided sign-flip p ≤ 0.05 (all 2^n sign vectors enumerated; p = share of
  sign-flipped means ≥ the observed mean), **and** (c) the one-sided 95% percentile-bootstrap lower bound of mean Δ > 0 (10,000
  resamples of units, seed 20261108).
- **Refuted (FLOPs not worse)** iff mean Δ ≤ 0 (the question's wording; unchanged).
- **Inconclusive (null)** otherwise, including every case with n < 5 and mean Δ > 0.
- The bootstrap interval is always reported as the effect-size interval; (b) is the binding small-n control.

**Operating characteristics (S5 Q2, S6 Q3; P(pass) for rule a∧b∧c; cell CV 2%, 5 rounds).**

| Test | layout (n) | bytes law, low heterogeneity | bytes law, high heterogeneity | boundary null | FLOPs law |
|---|---|---|---|---|---|
| Q2 | 4×LLC, cal included (8) | 1.000 | 0.955 | 0.023 / 0.019 | 0.000 |
| Q2 | 4×LLC, cal excluded (6) | 1.000 | 0.855 | 0.020 / 0.026 | 0.000 |
| Q2 | 8×LLC, cal included (6) | 1.000 | 0.851 | 0.022 / 0.024 | 0.000 |
| Q2 | 8×LLC, cal excluded (4) | 0.000 | 0.000 | 0.000 / 0.000 | 0.000 |
| Q3 | n = 5, ρ = 1.5 | 0.893 | 0.297 | 0.033 | 0.000 |
| Q3 | n = 6, ρ = 1.5 | 0.990 | 0.472 | 0.049 | 0.000 |
| Q3 | n = 6, ρ = 2.0 | 1.000 | 0.874 | 0.051 | 0.000 |
| Q3 | n = 3 or 4, any ρ | 0.000 | 0.000 | 0.000 | 0.000 |

Heterogeneity: Q2 per-cell log-efficiency SD τ = 0.05 / 0.15; Q3 per-file SD τ = 0.10 / 0.25. Q2 under a dequantisation penalty
η_Q4 × 0.75 passes with 0.158 (8 pairs): correct behaviour, since the C1 pairs then lie on the FLOPs side of the midpoint (threshold
0.767); at × 0.60 Q2 is refuted with probability 0.993. Unit layouts are JUDGEMENT estimates from the repo file sizes in §3.5 and are
UNVERIFIED until `cells.py` runs.

**Consequences, pre-registered now (edits E3, E4, E6).** (i) Calibration cell enters ratio units. (ii) If `cells.py` (after V5) gives
fewer than 5 Q3 files, Q3 is dropped by the §4.5 mechanism (metadata only, before any model run). (iii) If it gives fewer than 5 Q2
pairs, Q2 cannot pass; this is reported before any model run, the positive claim is then unreachable, and the Director decides
(deviation before runs) whether to proceed. (iv) Pairs with R_B < 1.5 from metadata are kept; a sensitivity analysis without them is
reported, not decisive.

## Multiplicity

The joint positive claim is Q1(Host A) ∧ Q1(Host B) ∧ Q2 ∧ Q3 (if kept), plus Q1 on the confirmation set after G2 (a V7 failure only labels the Q3 outcome "benchmark-dependent"; it adds no component; Director decision 2026-11-05, pending statistician re-confirmation). This is an **intersection-union** claim: a false joint claim requires at least one false component, so
P(joint pass | some component null) ≤ that component's level ≤ 0.05 (S8). No Holm or Bonferroni correction applies; one would only
cost power. Q1 components are fixed point thresholds without an α. F2 and B2 variants are robustness reports, not tests (§5.4 kept).
The **refutation** side is a union of point rules (mean Δ ≤ 0, MAPE > 20%) without α control; its rate under the bytes law is reported
in S5/S6 (up to 0.095 for Q3, n = 3, τ = 0.25), which is the price of the question's "not worse" wording and is stated in §7.

**Dependence.** Q2 pairs C1 and C2 of one (host, size) share the Q8_0 cell; the induced correlation of their Δ is negative
(−0.307 to −0.499, S7), and the sign-flip test's boundary-null rate stayed ≤ 0.026 with pair-level resampling (S5). Primary
resampling unit therefore stays the pair; a cluster bootstrap over (host, size) is reported as sensitivity. Q3 host-constant noise
is common to all files and is not captured by resampling files; its size is small against the decision margin: SE of
ln(B1_B/B1_A) 0.0079 (B1 CV 1%) to 0.0238 (CV 3%), i.e. 0.039-0.117 of the half-gap ln(1.5)/2 (S6).

## Exclusions check

§5.7 rules (swap, steal > 5%, battery, sentinel, crash, timeout) depend only on system state, never on tok/s or predictor error:
outcome-blind, accepted. Gaps to close (edit E9):
1. Sentinel re-run: state which block is scored. Rule: the re-run block replaces the flagged block if its own bracketing sentinels
   are within 5%; otherwise the block with the smaller sentinel deviation is scored and flagged (sentinel uses the development model,
   so outcome-blind).
2. An excluded-and-repeated round replaces the excluded round and counts toward the 5 (or 8) rounds; the precision check uses the
   final set.
3. Completeness threshold rounding: "fewer than ceil(0.75 × planned)" (Host B may have 3-6 cells).
4. Calibration cell failure (two failures): no substitute cell is chosen; Q1 is "not evaluable" on both hosts (null); Q2/Q3 proceed
   (η-free).
5. Imprecise cells are scored and flagged (above). Outliers are not removed (kept as drafted).

## Required edits to PROTOCOL.md (exact text)

Each edit gives the current text (verbatim) and the replacement. All are pre-G1 draft changes, not deviations.

**E1 (§4.6, line 252-255).** Replace
"- **Precision target** (JUDGEMENT, pending statistician): 95% CI half-width of the cell mean ≤ 2% of the cell mean (one tenth of the
  20% threshold, so measurement noise moves a cell's APE by at most about 2 percentage points). If after 5 rounds a cell misses it,
  up to 3 more rounds are added (max 8), a rule that uses only the cell's variance, never the predictor error; a cell still missing
  it is flagged "imprecise" and reported."
with
"- **Precision target** (signed in `analysis/POWER.md`): h = t(0.975, n−1) · s / √n over the n round values, h ≤ 2.0% of the cell
  mean. If after 5 rounds a cell misses it, 3 more rounds are added together (one look; max 8), a rule that uses only the cell's
  variance, never the predictor error; a cell still missing it is flagged "imprecise", scored, and reported.
- **Calibration cell**: 10 rounds, fixed (no extension rule), because its noise enters every prediction (`analysis/POWER.md` S3)."

**E2 (§4.6, line 249 heading).** Replace "(provisional until `analysis/POWER.md` signs)" with "(signed: `analysis/POWER.md`, 2026-11-05)";
same replacement in the §5 heading (line 272).

**E3 (§4.3, lines 221-222).** Replace "and excluded from
every scored error, MAPE, ratio test and figure statistic." with "and excluded from every APE, MAPE and Q1 statistic. It enters the
Q2 and Q3 ratio units like any other cell, because η and η′ cancel in every ratio (`analysis/POWER.md`, Unit and metric)."

**E4 (§4.5, append after line 247).** "Second drop condition (metadata only, before any model run): if `experiments/CELLS.csv` lists
fewer than 5 files eligible on both hosts, Q3 is dropped in the same way, because no exact one-sided 5% test can pass with fewer than
5 units (`analysis/POWER.md` S4). If it lists fewer than 5 Q2 pairs, this is reported before any model run: Q2 then cannot pass, the
positive claim is unreachable, and continuing requires a dated deviation."

**E5 (§5.1, append after line 276).** "- Secondary Q1 metric (reported, not decisive): per-host mean |ln(ŷ/y)|. Ratio-test p-values:
exact one-sided sign-flip test over all 2^n sign vectors of the unit Δ values. Q2 sensitivity: cluster bootstrap over (host, size);
pairs with R_B < 1.5 removed. Power and precision basis: `analysis/power.py`."

**E6 (§5.3, line 291).** Replace "- Decision: bytes beats FLOPs iff mean Δq > 0 and the one-sided 95% percentile-bootstrap lower bound
(resampling pairs) > 0." with "- Decision: bytes beats FLOPs iff mean Δq > 0, the exact one-sided sign-flip p ≤ 0.05, and the one-sided
95% percentile-bootstrap lower bound (resampling pairs) > 0. FLOPs not worse (refutation) iff mean Δq ≤ 0. Otherwise inconclusive
(null); with fewer than 5 pairs a pass is impossible."

**E7 (§5.4, append after line 297).** "Scope: R_B and R_F are one constant pair for all files; files replicate over models, not
machines, so a Q3 result is stated for these two hosts only."

**E8 (§5.5, append after line 302).** "The refutation side (mean Δ ≤ 0; MAPE > 20%) is a union of point rules without α control; its
rate under the bytes law is given in `analysis/POWER.md` (S5, S6)."

**E9 (§5.7, append after line 317).** "- A repeated round replaces the excluded round and counts toward the round total. A sentinel
re-run block replaces the flagged block if its own bracketing sentinels are within 5%; otherwise the block with the smaller sentinel
deviation is scored and flagged. Completeness threshold: ceil(0.75 × planned eligible evaluation cells). If the calibration cell
fails, no substitute is chosen: Q1 is not evaluable on either host (null); Q2 and Q3 proceed."

**E10 (§6, lines 331-332).** V8 tolerance "between-round CV ≤ 3%" → "between-round CV ≤ 1.5%" and its justification "needed to meet
the 2% CI target with 5 rounds (§4.6)" → "gives P(target met by 8 rounds) = 0.989 (`analysis/POWER.md` Table R)". V9 tolerance
"CV ≤ 3% each" → "B1: CV ≤ 1.0%; B2, F1: CV ≤ 3%" (B1 enters every Host B prediction as common-mode error, POWER.md S3).
(§6 is outside sections 4-5; owner protocol-architect / hardware-lead to confirm feasibility.)

**E11 (§1 line 47-48, §2 Q2 row line 58).** In §1 replace "a ratio test is inconclusive (point estimate favours bytes but the 95% interval
of the paired difference includes 0)" with "a ratio test is inconclusive (point estimate favours bytes but the 95% interval of the
paired difference includes 0 or the exact sign-flip p > 0.05)". In §2, Q2 row, replace "Bytes wins iff mean Δq > 0 and the one-sided
95% bootstrap lower bound > 0" with "Bytes wins iff mean Δq > 0, exact sign-flip p ≤ 0.05 and the one-sided 95% bootstrap lower bound
> 0 (§5.3)", and replace "Mean Δq ≤ 0, or lower bound ≤ 0 with mean Δq ≤ 0 (inconclusive if mean > 0 but bound ≤ 0: null, §1)" with
"Mean Δq ≤ 0 (inconclusive if mean > 0 but the bound ≤ 0 or p > 0.05: null, §1)".

**E12 (§7, line 362).** Replace "(statistician to quantify in `analysis/POWER.md`)" with "(quantified in `analysis/POWER.md`: no exact
5% test passes with fewer than 5 units; Q3 power 0.297-0.893 at 5 files and ρ = 1.5 under the assumed heterogeneity)".

**E13 (§10, line 418).** Replace the statistician bullet with "- Statistician: signed in `analysis/POWER.md` (2026-11-05), sections 4-5
approved with edits E1-E12."

## Sign-off

Sections 4-5 are statistically defensible once E1-E9 and E11-E13 are applied; E10 (§6) is needed for the precision target to be
reachable and is passed to its owners. Residual risks, stated not solved: unit counts are estimates until `cells.py` runs (8×LLC
branch could leave Q3 with 3 files and Q2 with 6 pairs); Q3 power is low (0.297) if per-file heterogeneity is high and ρ is near 1.5;
the Q1 decision is noise-dominated within about 2 pp of 20%; Host A rounds are consecutive within a file block, so the round CI
measures within-session precision only.

Signed: statistician, 2026-11-05, sections 4-5 of PROTOCOL.md approved with the edits above
