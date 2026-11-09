"""V10 on Host A (PROTOCOL 6): residency of the development model with `-lm none`.

Runs the development model once with the full 3.7 flags (3 reps instead of 5 is NOT used: -r 5) and samples the llama-bench process
every 0.25 s: working set (psutil rss = WorkingSetSize), system available memory, mains power, and \\Memory\\Pages Input/sec
(typeperf, every 1 s). Checks:
  (a) peak working set after load >= 0.95 x file size;
  (b) paging check (Host A fallback, PROTOCOL 3.8 entry 2026-11-08): available memory >= 1.0 GiB at every 1 s sample and mains
      power throughout (Pages Input is stored, not gated, because it is non-zero at idle on this laptop).
Also stores the idle Pages Input before the run for the record. Writes JSON; never writes to results/ by itself.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time

import psutil

BENCH = r"C:\Users\Clement Nana Aidoo\llama.cpp-b12129\build-x64-windows-llvm-release\bin\llama-bench.exe"
FLAGS = ["-p", "0", "-n", "128", "-d", "0", "-r", "5", "-t", "6", "-C", "0x555", "--cpu-strict", "1", "-ngl", "0", "-fa", "off",
         "-ctk", "f16", "-ctv", "f16", "-lm", "none", "--repack", "1", "--prio", "0", "-o", "jsonl"]


def typeperf_samples(seconds):
    out = subprocess.run(["typeperf", r"\Memory\Pages Input/sec", "-sc", str(seconds)], capture_output=True, text=True).stdout
    vals = []
    for ln in out.splitlines():
        p = ln.split(",")
        if len(p) == 2:
            try:
                vals.append(float(p[1].strip('"')))
            except ValueError:
                pass
    return vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    b = psutil.sensors_battery()
    if not (b and b.power_plugged):
        print("refusing: on battery")
        return 2
    size = os.path.getsize(a.model)
    idle_pi = typeperf_samples(10)
    tp = subprocess.Popen(["typeperf", r"\Memory\Pages Input/sec", "-si", "1"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    pages = []

    def rd():
        for ln in tp.stdout:
            p = ln.strip().split(",")
            if len(p) == 2:
                try:
                    pages.append(float(p[1].strip('"')))
                except ValueError:
                    pass
    threading.Thread(target=rd, daemon=True).start()
    proc = subprocess.Popen([BENCH, "-m", a.model] + FLAGS, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    ps = psutil.Process(proc.pid)
    ws, avail, plugged, t = [], [], [], []
    t0 = time.time()
    while proc.poll() is None:
        try:
            ws.append(ps.memory_info().rss)
        except psutil.Error:
            break
        avail.append(psutil.virtual_memory().available)
        bb = psutil.sensors_battery()
        plugged.append(bool(bb.power_plugged) if bb else None)
        t.append(time.time() - t0)
        time.sleep(0.25)
    tp.terminate()
    out = proc.communicate()[0]
    peak = max(ws) if ws else 0
    res = {"model": os.path.basename(a.model), "file_bytes": size, "peak_working_set_bytes": peak,
           "peak_over_file": peak / size, "V10_residency_pass": peak >= 0.95 * size,
           "min_avail_gib": round(min(avail) / 2**30, 2), "all_plugged": all(plugged),
           "V10_paging_fallback_pass": min(avail) >= 2**30 and all(plugged),
           "pages_input_idle_samples": idle_pi, "pages_input_run_samples": pages,
           "pages_input_run_max": max(pages, default=None), "duration_s": round(time.time() - t0, 1),
           "n_samples": len(ws), "returncode": proc.returncode, "flags": FLAGS,
           "bench_json": [json.loads(x) for x in out.splitlines() if x.startswith("{")][-1:]}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("file_bytes", "peak_working_set_bytes", "peak_over_file", "V10_residency_pass",
                                          "min_avail_gib", "all_plugged", "V10_paging_fallback_pass", "pages_input_run_max")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
