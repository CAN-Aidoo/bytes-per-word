"""V8 / sentinel rounds on Host A (PROTOCOL 4.6): one round = one fresh llama-bench process (warm-up + 5 reps of tg128).

Round value = mean of the 5 repetitions. Before each round: wait (max 300 s, then start and flag) until system CPU utilisation over
5 s is below 5%. State (CPU %, available memory, power source) recorded before and after each round. Runs under launch.py
(T_A = 6, mask_A). Writes a JSON file; never writes to results/ by itself.

  python v8_hostA.py --model <gguf> --rounds 5 --out <json>
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

import psutil

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = r"C:\Users\Clement Nana Aidoo\llama.cpp-b12129\build-x64-windows-llvm-release\bin\llama-bench.exe"


def state():
    b = psutil.sensors_battery()
    return {"cpu_pct_5s": psutil.cpu_percent(interval=5), "avail_gib": round(psutil.virtual_memory().available / 2**30, 2),
            "plugged": b.power_plugged if b else None}


def wait_quiet(limit_s=300):
    t0 = time.time()
    while True:
        s = state()
        if s["cpu_pct_5s"] < 5.0:
            return s, False
        if time.time() - t0 > limit_s:
            return s, True  # started anyway, flagged


def one_round(model):
    pre, flagged = wait_quiet()
    p = subprocess.run([sys.executable, os.path.join(HERE, "launch.py"), "--threads", "6", "--", BENCH, "-m", model,
                        "-p", "0", "-n", "128", "-t", "6", "-r", "5", "-o", "json"], capture_output=True, text=True)
    post = state()
    r = json.loads(p.stdout)[0]
    meta = json.loads([ln for ln in p.stderr.splitlines() if ln.startswith("{")][-1])
    return {"value_toks": r["avg_ts"], "samples": r["samples_ts"], "pre": pre, "post": post, "start_flagged_not_quiet": flagged,
            "affinity_ok": meta["affinity_matches_mask"], "returncode": meta["returncode"], "backends": r.get("backends"),
            "build_commit": r.get("build_commit")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if not (psutil.sensors_battery() and psutil.sensors_battery().power_plugged) and not a.dev:
        print("refusing: on battery")
        return 2
    rounds = [one_round(a.model) for _ in range(a.rounds)]
    vals = [r["value_toks"] for r in rounds]
    res = {"model": os.path.basename(a.model), "rounds": rounds, "values": vals, "mean_toks": statistics.mean(vals),
           "between_round_cv_pct": 100.0 * statistics.stdev(vals) / statistics.mean(vals) if len(vals) > 1 else 0.0,
           "V8_pass": (100.0 * statistics.stdev(vals) / statistics.mean(vals) <= 1.5) if len(vals) > 1 else None,
           "V11_pass": all(r["affinity_ok"] for r in rounds), "all_plugged": all(r["pre"]["plugged"] and r["post"]["plugged"] for r in rounds),
           "n_flagged_not_quiet": sum(r["start_flagged_not_quiet"] for r in rounds), "development": a.dev}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("values", "mean_toks", "between_round_cv_pct", "V8_pass", "V11_pass", "all_plugged", "n_flagged_not_quiet")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
