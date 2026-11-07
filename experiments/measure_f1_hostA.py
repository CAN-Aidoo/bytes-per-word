"""F1 on Host A (PROTOCOL 3.4): 5 process runs of experiments/f1_gemm.py under experiments/launch.py (T_A = 6, mask_h).

F1_A = median of the 5 process values (GFLOP/s). Refuses to run on battery. Writes JSON to --out (never to results/ by itself).
"""
import argparse
import json
import os
import statistics
import subprocess
import sys

import psutil

HERE = os.path.dirname(os.path.abspath(__file__))


def one_run():
    env = dict(os.environ, OPENBLAS_NUM_THREADS="6", OMP_NUM_THREADS="6")
    p = subprocess.run([sys.executable, os.path.join(HERE, "launch.py"), "--threads", "6", "--",
                        sys.executable, os.path.join(HERE, "f1_gemm.py")],
                       capture_output=True, text=True, env=env)
    out = json.loads(p.stdout.strip().splitlines()[-1])
    meta = json.loads([ln for ln in p.stderr.splitlines() if ln.startswith("{")][-1])
    out["affinity_ok"] = meta["affinity_matches_mask"]
    out["returncode"] = meta["returncode"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--dev", action="store_true", help="non-scored run (allowed on battery)")
    a = ap.parse_args()
    plugged = psutil.sensors_battery().power_plugged
    if not plugged and not a.dev:
        print("refusing: on battery; use --dev for a non-scored run")
        return 2
    runs = [one_run() for _ in range(a.runs)]
    vals = [r["gflops_median"] for r in runs]
    res = {
        "development": a.dev, "power_plugged": plugged, "runs_n": a.runs,
        "F1_A_gflops": statistics.median(vals), "process_values": vals,
        "cv_pct": 100.0 * statistics.pstdev(vals) / statistics.mean(vals),
        "numpy": runs[0]["numpy"],
        "V12_openblas_named": all(r["openblas_in_config"] for r in runs),
        "V11_pass": all(r["affinity_ok"] for r in runs),
        "all_returncode_0": all(r["returncode"] == 0 for r in runs),
        "show_config": runs[0]["show_config"],
        "runs": [{k: v for k, v in r.items() if k != "show_config"} for r in runs],
    }
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("F1_A_gflops", "process_values", "cv_pct", "V12_openblas_named", "V11_pass")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
