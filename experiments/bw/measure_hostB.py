"""Host B bandwidth constants B1_B and B2_B and checks V5, V9, V11, V13 (PROTOCOL 3.3, section 6), Linux.

Usage: ~/hostB-work/venv/bin/python measure_hostB.py --bin <dir with stream_read and stream_b2_1068> --out results/hosts/hostB_bw.json
Measures every thread configuration given by --threads (default 2,4; mask = first logical CPUs 0..T-1, one thread per vCPU,
the VM exposes 1 thread/core). PROTOCOL 3.7 fixes T_B = 2 (written when Host B had 2 vCPUs); the 4-vCPU configuration is
measured as well so the author can decide T_B. Nothing here is frozen: the output is marked "frozen": false.
B1: stream_read at 1040 MiB (4 x LLC) and 2080 MiB (8 x LLC), 5 process runs each. B2: STREAM Triad, array 140e6 doubles
(1068 MiB each, >= 1040 MiB), built with -mcmodel=medium. Runs via launch.py (affinity = mask, V11). Reports; never edits PROTOCOL.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.join(HERE, "..", "launch.py")


def steal():
    f = open("/proc/stat").readline().split()[1:]
    return int(f[7]), sum(int(x) for x in f[:8])


def launch(cpus, cmd):
    p = subprocess.run([sys.executable, LAUNCH, "--threads", str(len(cpus)), "--cpus", ",".join(map(str, cpus)), "--"] + cmd,
                       capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"command failed: {cmd}\n{p.stderr}")
    return p.stdout, json.loads(p.stderr.strip().splitlines()[-1])


def b1(exe, mib, cpus):
    out, meta = launch(cpus, [exe, str(mib)])
    r = json.loads(out.strip().splitlines()[-1])
    return {"gbps": r["median_gbps_iters_2_20"], "min_ticks": r["min_ticks"], "checksum_ok": r["checksum_ok"],
            "affinity_ok": meta["affinity_matches_mask"]}


def b2(exe, cpus):
    out, meta = launch(cpus, [exe])
    triad = re.search(r"^Triad:\s+([0-9.]+)", out, re.M)
    ticks = re.search(r"\(= (\d+) clock ticks\)", out)
    if not (triad and ticks):
        sys.exit("could not parse STREAM output:\n" + out)
    return {"gbps": float(triad.group(1)) / 1000.0, "min_ticks": float(ticks.group(1)),
            "checksum_ok": "Solution Validates" in out, "affinity_ok": meta["affinity_matches_mask"]}


def cv(xs):
    return 100.0 * statistics.pstdev(xs) / statistics.mean(xs) if len(xs) > 1 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threads", default="2,4")
    ap.add_argument("--runs", type=int, default=5)
    a = ap.parse_args()
    e1, e2 = os.path.join(a.bin, "stream_read"), os.path.join(a.bin, "stream_b2_1068")
    out = {"frozen": False, "llc_mib": 260, "runs_per_item": a.runs, "configs": {}}
    for t in [int(x) for x in a.threads.split(",")]:
        cpus = list(range(t))
        s0 = steal()
        res = {"B1_1040MiB": [b1(e1, 1040, cpus) for _ in range(a.runs)],
               "B1_2080MiB": [b1(e1, 2080, cpus) for _ in range(a.runs)],
               "B2": [b2(e2, cpus) for _ in range(a.runs)]}
        s1 = steal()
        med = {k: statistics.median(r["gbps"] for r in v) for k, v in res.items()}
        cvs = {k: cv([r["gbps"] for r in v]) for k, v in res.items()}
        allr = [r for v in res.values() for r in v]
        d5 = 100.0 * abs(med["B1_1040MiB"] - med["B1_2080MiB"]) / med["B1_2080MiB"]
        chk = {"V5_plateau_diff_pct": d5, "V5_pass": d5 <= 5.0,
               "V9_B1_cv_pct": cvs["B1_2080MiB"], "V9_B2_cv_pct": cvs["B2"],
               "V9_pass": cvs["B1_1040MiB"] <= 1.0 and cvs["B1_2080MiB"] <= 1.0 and cvs["B2"] <= 3.0,
               "V11_pass": all(r["affinity_ok"] for r in allr),
               "V13_min_ticks": min(r["min_ticks"] for r in allr), "V13_pass": min(r["min_ticks"] for r in allr) >= 20,
               "checksums_ok": all(r["checksum_ok"] for r in allr),
               "steal_pct_of_cpu_time": 100.0 * (s1[0] - s0[0]) / max(1, s1[1] - s0[1])}
        out["configs"][f"T{t}"] = {"mask_cpus": cpus, "B1_gbps_at_4xLLC": med["B1_1040MiB"],
                                   "B1_gbps_at_8xLLC": med["B1_2080MiB"], "B2_gbps": med["B2"],
                                   "medians": med, "cv_pct": cvs, "checks": chk, "runs": res}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: {x: v[x] for x in ("B1_gbps_at_4xLLC", "B1_gbps_at_8xLLC", "B2_gbps", "cv_pct", "checks")}
                      for k, v in out["configs"].items()}, indent=1))


if __name__ == "__main__":
    main()
