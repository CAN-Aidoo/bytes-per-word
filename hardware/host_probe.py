"""Host probe for bytes-per-word (pilot / host characterisation; NOT a scored measurement).

Measures, with NumPy only:
  - sustained memory bandwidth: copy (2 arrays) and triad (3 arrays), arrays sized >= 4x the last-level cache
  - FP32 matrix-multiply throughput (GFLOP/s) as a rough compute ceiling
and records host facts. The pre-registered benchmarks for scored runs are named in PROTOCOL.md; this probe only checks
that the hosts differ in their FLOP/s-to-bandwidth ratio (the cross-machine discrimination condition).

Usage:  python3 hardware/host_probe.py [--out results/pilot/host_<name>.json] [--llc-mib N] [--reps 7]
On the laptop (native Windows): plug in to mains power, close other programs, then run it twice and send both JSON files:
    py -m pip install numpy psutil
    py hardware\\host_probe.py --out results\\pilot\\host_laptop_run1.json --llc-mib 8
"""
import argparse, json, os, platform, statistics, subprocess, sys, time

import numpy as np


def loadavg():
    """Unix load average; on Windows, the system-wide CPU percent over 1 s (psutil if installed), else None."""
    if hasattr(os, "getloadavg"):
        return os.getloadavg()
    try:
        import psutil
        return {"cpu_percent_1s": psutil.cpu_percent(interval=1.0)}
    except Exception:
        return None


def win_cpu():
    if platform.system() != "Windows":
        return ""
    return sh('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).Name"')


def win_l3_mib():
    if platform.system() != "Windows":
        return None
    out = sh('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).L3CacheSize"')
    try:
        return float(out.split()[0]) / 1024  # KiB -> MiB
    except Exception:
        return None


def power_source():
    try:
        import psutil
        b = psutil.sensors_battery()
        return None if b is None else ("mains" if b.power_plugged else "battery")
    except Exception:
        return None


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def llc_mib_guess():
    w = win_l3_mib()
    if w:
        return w
    out = sh("lscpu | grep 'L3 cache'")
    try:
        num = float(out.split(":")[1].split()[0])
        unit = out.split(":")[1].split()[1]
        return num * (1024 if unit.lower().startswith("g") else 1 if unit.lower().startswith("m") else 1 / 1024)
    except Exception:
        return 32.0


def bandwidth(n_bytes_per_array, reps):
    n = n_bytes_per_array // 8
    a = np.ones(n, dtype=np.float64)
    b = np.full(n, 2.0)
    c = np.zeros(n)
    copy, triad = [], []
    for _ in range(reps + 1):  # first rep is warm-up, discarded
        t = time.perf_counter(); np.copyto(c, a); dt = time.perf_counter() - t
        copy.append(2 * n * 8 / dt / 1e9)
        t = time.perf_counter(); np.multiply(b, 3.0, out=c); np.add(c, a, out=c); dt = time.perf_counter() - t
        triad.append(4 * n * 8 / dt / 1e9)  # multiply pass (read b, write c) + add pass (read c, a, write c) ~ 5 streams; report 4 conservatively
    return copy[1:], triad[1:]


def gflops(reps, size=2048):
    x = np.random.default_rng(0).standard_normal((size, size), dtype=np.float32)
    y = np.random.default_rng(1).standard_normal((size, size), dtype=np.float32)
    out = []
    for _ in range(reps + 1):
        t = time.perf_counter(); x @ y; dt = time.perf_counter() - t
        out.append(2 * size ** 3 / dt / 1e9)
    return out[1:]


def blas_info():
    import io, contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            np.show_config()
    except Exception:
        return "unknown"
    lines = [l.strip() for l in buf.getvalue().splitlines() if any(k in l.lower() for k in ("openblas", "mkl", "accelerate", "name:"))]
    return " | ".join(lines[:4])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--llc-mib", type=float, default=None)
    ap.add_argument("--reps", type=int, default=7)
    args = ap.parse_args()
    llc = args.llc_mib or llc_mib_guess()
    array_bytes = int(max(4 * llc * 2**20, 256 * 2**20))
    copy, triad = bandwidth(array_bytes, args.reps)
    gf = gflops(args.reps)
    res = {
        "kind": "PILOT host probe (not a scored measurement)",
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": platform.node(), "os": platform.platform(), "python": sys.version.split()[0], "numpy": np.__version__,
        "cpu": win_cpu() or sh("lscpu | grep 'Model name' | cut -d: -f2").strip() or platform.processor(),
        "logical_cpus": os.cpu_count(), "llc_mib_used": llc, "array_mib": array_bytes / 2**20,
        "hypervisor": sh("lscpu | grep -i 'Hypervisor vendor' | cut -d: -f2").strip() or "none reported",
        "governor": sh("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") if platform.system() != "Windows" else sh("powercfg /getactivescheme"),
        "loadavg": loadavg(), "power_source": power_source(),
        "blas": blas_info(),
        "copy_GBps": copy, "triad_GBps": triad, "fp32_matmul_GFLOPs": gf,
        "copy_GBps_median": statistics.median(copy), "triad_GBps_median": statistics.median(triad),
        "fp32_GFLOPs_median": statistics.median(gf),
    }
    res["flops_per_byte_ratio"] = res["fp32_GFLOPs_median"] / res["copy_GBps_median"]
    text = json.dumps(res, indent=1)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
