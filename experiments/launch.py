"""Launch a benchmark process pinned to mask_h (PROTOCOL 3.3, 3.7, 3.8, V11).

Usage: python launch.py [--threads T] [--cpus 0,2,4,...] -- <command> [args...]
Host A: with no --cpus, mask_A comes from topology_win.py (first logical CPU of each physical core) and T defaults to the
number of physical cores. Sets OMP_NUM_THREADS / OMP_PROC_BIND / OMP_PLACES, sets this process's CPU affinity (the child
inherits it), starts the command, samples the child's affinity once while it runs (V11), and prints one JSON line of metadata
on stderr. The command's stdout is passed through unchanged. Exit code is the command's.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import psutil


def linux_thread_affinities(pid):
    """Linux: allowed-CPU set of every thread of pid (OMP_PROC_BIND=close binds each thread to its own place, so the
    main thread alone shows only its own CPU). Returns a list of sorted CPU lists, or None if /proc is unreadable."""
    out = []
    try:
        for tid in os.listdir(f"/proc/{pid}/task"):
            with open(f"/proc/{pid}/task/{tid}/status") as f:
                for line in f:
                    if line.startswith("Cpus_allowed_list:"):
                        cpus = set()
                        for part in line.split(":")[1].strip().split(","):
                            lo, _, hi = part.partition("-")
                            cpus.update(range(int(lo), int(hi or lo) + 1))
                        out.append(sorted(cpus))
    except OSError:
        return None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int)
    ap.add_argument("--cpus", help="comma-separated logical CPU list; default mask_A from topology_win.py")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        ap.error("no command given")

    if args.cpus:
        cpus = [int(x) for x in args.cpus.split(",")]
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import topology_win

        cpus = topology_win.mask_a()["cpu_list"]
    threads = args.threads or len(cpus)

    env = dict(os.environ, OMP_NUM_THREADS=str(threads), OMP_PROC_BIND="close", OMP_PLACES="cores")
    psutil.Process().cpu_affinity(cpus)
    battery = psutil.sensors_battery()
    proc = subprocess.Popen(cmd, env=env)
    # Sample the child's affinity as early as possible (short runs such as B1 at 32 MiB finish in well under 0.3 s),
    # then once more after 0.3 s if it is still running; the last successful sample is recorded.
    thread_aff = None  # Linux only: per-thread affinities (V11 on Host B)
    sampled = None  # stays None only if the process finished before any sample: V11 cannot be evidenced for this run
    t_end = time.time() + 0.3
    while True:
        try:
            sampled = psutil.Process(proc.pid).cpu_affinity()
            if sys.platform.startswith("linux"):
                th = linux_thread_affinities(proc.pid)
                if th:
                    thread_aff = th
        except psutil.Error:
            break
        if time.time() >= t_end or proc.poll() is not None:
            break
        time.sleep(0.01)
    rc = proc.wait()
    meta = {
        "cmd": cmd,
        "threads": threads,
        "mask_cpus": cpus,
        "sampled_affinity": sampled,
        "thread_affinities": thread_aff,
        # Linux: every thread inside the mask and the threads together cover the mask; Windows: process affinity equals mask
        "affinity_matches_mask": (all(set(t) <= set(cpus) for t in thread_aff) and set().union(*map(set, thread_aff)) == set(cpus))
        if thread_aff else sampled == cpus,
        "power_plugged": None if battery is None else battery.power_plugged,
        "returncode": rc,
    }
    print(json.dumps(meta), file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
