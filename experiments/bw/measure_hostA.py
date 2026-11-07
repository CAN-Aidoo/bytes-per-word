"""Host A bandwidth constants B1_A, B2_A and checks V5, V6, V9, V11, V13 (PROTOCOL 3.3, section 6).

Usage (idle machine, mains power, highest-performance mode, other programs closed):
    python measure_hostA.py --bin <dir with stream_read.exe and stream_b2.exe> --out results/hosts/hostA_bw.json --confirm-conditions
Without --confirm-conditions, or if the laptop is on battery, the script refuses (use --dev to run anyway; the output is then
marked "development": true and must not be used as a constant). Runs via launch.py so affinity is mask_A (V11).
Deterministic apart from the measurement itself. Reports; never edits PROTOCOL.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys

import psutil

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.join(HERE, "..", "launch.py")
RUNS = 5
PEAK_A = 51.2  # GB/s, 2 x 8 B x 3200 MT/s (HOSTS.md)


def launch(cmd):
    p = subprocess.run([sys.executable, LAUNCH, "--"] + cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"command failed: {cmd}\n{p.stderr}")
    meta = json.loads(p.stderr.strip().splitlines()[-1])
    return p.stdout, meta


def b1(exe, mib):
    out, meta = launch([exe, str(mib)])
    r = json.loads(out.strip().splitlines()[-1])
    return {"gbps": r["median_gbps_iters_2_20"], "min_ticks": r["min_ticks"], "checksum_ok": r["checksum_ok"],
            "affinity_ok": meta["affinity_matches_mask"]}


def b2(exe):
    out, meta = launch([exe])
    triad = re.search(r"^Triad:\s+([0-9.]+)", out, re.M)
    ticks = re.search(r"\(= (\d+) clock ticks\)", out)
    valid = "Solution Validates" in out
    if not (triad and ticks):
        sys.exit("could not parse STREAM output:\n" + out)
    return {"gbps": float(triad.group(1)) / 1000.0, "min_ticks": float(ticks.group(1)), "checksum_ok": valid,
            "affinity_ok": meta["affinity_matches_mask"]}


def cv(xs):
    return 100.0 * statistics.pstdev(xs) / statistics.mean(xs) if len(xs) > 1 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--confirm-conditions", action="store_true",
                    help="human confirms: mains power, highest-performance mode, other programs closed")
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--runs", type=int, default=RUNS)
    a = ap.parse_args()

    bat = psutil.sensors_battery()
    plugged = None if bat is None else bat.power_plugged
    ok_cond = a.confirm_conditions and plugged is not False
    if not ok_cond and not a.dev:
        sys.exit(f"refusing: conditions not confirmed or on battery (plugged={plugged}); use --dev for a non-scored run")

    e1, e2 = os.path.join(a.bin, "stream_read.exe"), os.path.join(a.bin, "stream_b2.exe")
    res = {"B1_32MiB": [b1(e1, 32) for _ in range(a.runs)],
           "B1_64MiB": [b1(e1, 64) for _ in range(a.runs)],
           "B2": [b2(e2) for _ in range(a.runs)]}
    med = {k: statistics.median(r["gbps"] for r in v) for k, v in res.items()}
    # Second amendment 2026-11-07: V9 CV over the middle runs (2 lowest and 2 highest removed when >= 15 runs).
    def trimmed(v):
        xs = sorted(r["gbps"] for r in v)
        return xs[2:-2] if len(xs) >= 15 else xs
    cvs = {k: cv(trimmed(v)) for k, v in res.items()}
    allr = [r for v in res.values() for r in v]
    checks = {
        "V5_plateau_diff_pct": 100.0 * abs(med["B1_32MiB"] - med["B1_64MiB"]) / med["B1_64MiB"],
        "V5_pass": 100.0 * abs(med["B1_32MiB"] - med["B1_64MiB"]) / med["B1_64MiB"] <= 5.0,
        # PROTOCOL amendment 2026-11-07 (Host A): V6 lower bound reported, not gated; upper bound gates.
        # Third amendment: B1_A is the 64 MiB median; V6 upper and V9 B1 use the 64 MiB series.
        "V6_reported_in_range": 0.5 * PEAK_A <= med["B1_64MiB"] <= PEAK_A,
        "V6_pass": med["B1_64MiB"] <= PEAK_A,
        "V9_B1_cv_pct": cvs["B1_64MiB"], "V9_B2_cv_pct": cvs["B2"],
        "V9_pass": cvs["B1_64MiB"] <= 2.0 and cvs["B2"] <= 6.0,
        "V11_pass": all(r["affinity_ok"] for r in allr),
        "V13_min_ticks": min(r["min_ticks"] for r in allr),
        "V13_pass": min(r["min_ticks"] for r in allr) >= 20,
        "checksums_ok": all(r["checksum_ok"] for r in allr),
    }
    checks["gating_pass"] = all(checks[k] for k in ("V5_pass", "V6_pass", "V9_pass", "V11_pass", "V13_pass", "checksums_ok"))
    out = {"development": not ok_cond, "power_plugged": plugged, "runs_per_item": a.runs,
           "powercfg": subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True).stdout.strip(),
           "B1_A_gbps": med["B1_64MiB"], "B2_A_gbps": med["B2"], "medians": med, "cv_pct": cvs, "checks": checks,
           "runs": res}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"development": out["development"], "B1_A_gbps": out["B1_A_gbps"], "B2_A_gbps": out["B2_A_gbps"],
                      "checks": checks}, indent=1))


if __name__ == "__main__":
    main()
