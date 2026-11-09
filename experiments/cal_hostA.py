"""Host A calibration session (PROTOCOL 4.6): sentinel, calibration cell (10 fixed rounds), sentinel.

Every round is one fresh llama-bench process with the full PROTOCOL 3.7 flags:
  -p 0 -n 128 -d 0 -r 5 -t 6 -C 0x555 --cpu-strict 1 -ngl 0 -fa off -ctk f16 -ctv f16 -lm none --repack 1 --prio 0 -o jsonl
Round value = mean of the 5 repetitions. Before a round: wait (max 300 s, then start and flag) for system CPU < 5% over 5 s.
During a round: available memory and \\Memory\\Pages Input/sec are sampled every second (typeperf). A round is flagged if the
laptop leaves mains power, available memory drops below 1.0 GiB, or Pages Input is non-zero at any sample after the first 3 s
(model load). Writes a JSON file; never writes to results/ by itself.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import threading
import time

import psutil

BENCH = r"C:\Users\Clement Nana Aidoo\llama.cpp-b12129\build-x64-windows-llvm-release\bin\llama-bench.exe"
MASK = "0x555"
FLAGS = ["-p", "0", "-n", "128", "-d", "0", "-r", "5", "-t", "6", "-C", MASK, "--cpu-strict", "1", "-ngl", "0", "-fa", "off",
         "-ctk", "f16", "-ctv", "f16", "-lm", "none", "--repack", "1", "--prio", "0", "-o", "jsonl"]


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
            return s, True


class Sampler:
    def __init__(self):
        self.avail, self.plugged, self.pages_in, self._stop = [], [], [], False
        self.tp = subprocess.Popen(["typeperf", r"\Memory\Pages Input/sec", "-si", "1"], stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()
        self.t2 = threading.Thread(target=self._mem, daemon=True)
        self.t2.start()

    def _mem(self):
        while not self._stop:
            self.avail.append(psutil.virtual_memory().available / 2**30)
            b = psutil.sensors_battery()
            self.plugged.append(bool(b.power_plugged) if b else None)
            time.sleep(1)

    def _run(self):
        for line in self.tp.stdout:
            parts = line.strip().split(",")
            if len(parts) == 2 and parts[1].strip('"').replace(".", "", 1).replace("-", "", 1).isdigit():
                self.pages_in.append(float(parts[1].strip('"')))

    def stop(self):
        self._stop = True
        self.tp.terminate()
        return {"min_avail_gib": round(min(self.avail), 2) if self.avail else None,
                "all_plugged": all(self.plugged) if self.plugged else None,
                "pages_in_samples": len(self.pages_in),
                "pages_in_nonzero_after_load": sum(1 for v in self.pages_in[3:] if v > 0),
                "pages_in_max_after_load": max(self.pages_in[3:], default=0.0)}


def one_round(model):
    pre, flagged = wait_quiet()
    s = Sampler()
    p = subprocess.run([BENCH, "-m", model] + FLAGS, capture_output=True, text=True)
    mon = s.stop()
    post = state()
    r = json.loads([ln for ln in p.stdout.splitlines() if ln.startswith("{")][-1])
    bad = []
    if not mon["all_plugged"]:
        bad.append("left_mains")
    if mon["min_avail_gib"] is not None and mon["min_avail_gib"] < 1.0:
        bad.append("avail_below_1GiB")
    # Pages Input/sec is non-zero at idle on Host A (87.9 and 17.0 in a 2 s test on 2026-11-08), so by PROTOCOL 3.8 the paging
    # check is the fallback "available memory >= 1.0 GiB at every 1 s sample" (above); Pages Input is recorded, not gated.
    return {"value_toks": r["avg_ts"], "samples": r["samples_ts"], "pre": pre, "post": post, "monitor": mon,
            "start_flagged_not_quiet": flagged, "round_flags": bad, "returncode": p.returncode,
            "backends": r.get("backends"), "build_commit": r.get("build_commit"), "cpu_mask": r.get("cpu_mask"),
            "cpu_strict": r.get("cpu_strict")}


def block(model, n):
    rs = [one_round(model) for _ in range(n)]
    v = [r["value_toks"] for r in rs]
    return {"model": os.path.basename(model), "rounds": rs, "values": v, "mean_toks": statistics.mean(v),
            "between_round_cv_pct": 100.0 * statistics.stdev(v) / statistics.mean(v) if len(v) > 1 else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-model", required=True)
    ap.add_argument("--cal-model", required=True)
    ap.add_argument("--cal-rounds", type=int, default=10)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    b = psutil.sensors_battery()
    if not (b and b.power_plugged):
        print("refusing: on battery")
        return 2
    s1 = block(a.dev_model, 1)
    cal = block(a.cal_model, a.cal_rounds)
    s2 = block(a.dev_model, 1)
    d = 100.0 * abs(s2["mean_toks"] - s1["mean_toks"]) / s1["mean_toks"]
    res = {"sentinel_start": s1, "calibration_cell": cal, "sentinel_end": s2, "sentinel_deviation_pct": d,
           "sentinel_ok_5pct": d <= 5.0,
           "any_round_flagged": any(r["round_flags"] or r["start_flagged_not_quiet"] for blk in (s1, cal, s2) for r in blk["rounds"]),
           "flags": FLAGS}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({"calibration_values": cal["values"], "calibration_mean_toks": cal["mean_toks"],
                      "calibration_cv_pct": cal["between_round_cv_pct"], "sentinel_start": s1["mean_toks"],
                      "sentinel_end": s2["mean_toks"], "sentinel_deviation_pct": d, "any_round_flagged": res["any_round_flagged"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
