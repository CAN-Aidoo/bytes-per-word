"""F1 (PROTOCOL 3.4): FP32 GEMM rate, NumPy float32 matmul, n = m = k = 4096.

One process: 1 warm-up product, then 5 timed products; the process value is the median GFLOP/s (FLOPs = 2 n^3).
Run it under experiments/launch.py (affinity mask_h, OPENBLAS_NUM_THREADS/OMP_NUM_THREADS = T_h).
Prints one JSON line, including numpy.show_config() text for the V12 check (OpenBLAS must be named).
"""
import io
import json
import statistics
import sys
import time
from contextlib import redirect_stdout

import numpy as np

N = 4096


def main():
    rng = np.random.default_rng(12345)
    a = rng.random((N, N), dtype=np.float32)
    b = rng.random((N, N), dtype=np.float32)
    c = a @ b  # warm-up
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        c = a @ b
        times.append(time.perf_counter() - t0)
    flops = 2.0 * N ** 3
    gflops = [flops / t / 1e9 for t in times]
    buf = io.StringIO()
    with redirect_stdout(buf):
        np.show_config()
    cfg = buf.getvalue()
    print(json.dumps({
        "n": N, "numpy": np.__version__, "dtype": str(c.dtype),
        "gflops_median": statistics.median(gflops), "gflops_all": gflops,
        "min_time_s": min(times), "openblas_in_config": "openblas" in cfg.lower(),
        "checksum": float(c[0, 0]) + float(c[-1, -1]),
        "show_config": cfg,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
