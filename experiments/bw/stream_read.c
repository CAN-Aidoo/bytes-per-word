/*
 * B1: sustained read bandwidth (PROTOCOL 3.3).
 *
 * This program is based on a variant of the STREAM benchmark code (STREAM v5.10, John D. McCalpin,
 * https://www.cs.virginia.edu/stream/; source file stream.c, SHA-256 c388924eb140fda95f534cdb808ae7f1f8ebb18da41d8aec1b512a3c8d303c9b).
 * It is NOT an official STREAM result. Changes: a read-only "Sum" kernel (s += a[j], OpenMP reduction) replaces the
 * four STREAM kernels; the timer is omp_get_wtime() (same as B2); NTIMES = 20.
 *
 * Usage: stream_read <array_MiB>        (Host A: 32 = 4 x LLC for the V5 plateau uses 64 = 8 x LLC)
 * Output: one JSON line. Reported value (PROTOCOL 3.3): median of iterations 2-20 in GB/s (bytes = 8 * N, GB = 1e9 B).
 * V13 inputs: clock quantum (microseconds, STREAM's checktick method) and minimum ticks per timed iteration.
 */
#include <math.h>
#include <omp.h>
#ifdef __AVX2__
#include <immintrin.h>
#endif
#include <stdio.h>
#include <stdlib.h>

#ifdef _WIN32
#include <malloc.h>
#define ALLOC(n) _aligned_malloc((n), 64)
#define FREE(p) _aligned_free(p)
#else
#define ALLOC(n) aligned_alloc(64, (n))
#define FREE(p) free(p)
#endif

#define NTIMES 20

static int cmp_double(const void *x, const void *y) {
    double a = *(const double *)x, b = *(const double *)y;
    return (a > b) - (a < b);
}

/* STREAM's checktick: smallest observable positive step of the timer, in microseconds (>= 1). */
static int checktick(void) {
    enum { M = 20 };
    double t1, t2, found[M];
    int i, minDelta = 1000000, delta;
    for (i = 0; i < M; i++) {
        t1 = omp_get_wtime();
        while (((t2 = omp_get_wtime()) - t1) < 1.0e-6) {
        }
        found[i] = t2;
    }
    for (i = 1; i < M; i++) {
        delta = (int)(1.0e6 * (found[i] - found[i - 1]));
        if (delta < 0) delta = 0;
        if (delta < minDelta) minDelta = delta;
    }
    return minDelta < 1 ? 1 : minDelta;
}

int main(int argc, char **argv) {
    size_t mib = argc > 1 ? (size_t)atoll(argv[1]) : 32;
    size_t n = mib * 1024 * 1024 / sizeof(double);
    double *a = (double *)ALLOC(n * sizeof(double));
    double times[NTIMES], gbps[NTIMES - 1], sink = 0.0, tmin = 1e30;
    int k, quantum, threads;
    size_t j;

    if (!a) {
        fprintf(stderr, "allocation of %zu MiB failed\n", mib);
        return 2;
    }
#pragma omp parallel
    {
#pragma omp single
        threads = omp_get_num_threads();
    }
#pragma omp parallel for schedule(static)
    for (j = 0; j < n; j++) a[j] = 1.0; /* first touch with the same static schedule as the kernel */

    quantum = checktick();
    for (k = 0; k < NTIMES; k++) {
        double s = 0.0, t0 = omp_get_wtime();
        /* Strict FP semantics make "s += a[j]" one serial add chain (latency-bound, not memory-bound; measured ~1 GB/s per
           thread on Host A). Eight independent partial sums per thread break the chain without -ffast-math. */
#pragma omp parallel reduction(+ : s)
        {
            int nt = omp_get_num_threads(), id = omp_get_thread_num();
            size_t chunk = (n / nt) & ~(size_t)7, lo = (size_t)id * chunk, hi = (id == nt - 1) ? n : lo + chunk;
            double s0 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, s5 = 0, s6 = 0, s7 = 0;
            size_t i = lo;
#ifdef __AVX2__
            /* clang keeps the eight scalar sums scalar (vaddsd); use AVX2 explicitly: 4 independent 256-bit sums. */
            {
                __m256d v0 = _mm256_setzero_pd(), v1 = v0, v2 = v0, v3 = v0;
                for (; i + 16 <= hi; i += 16) {
                    v0 = _mm256_add_pd(v0, _mm256_loadu_pd(a + i));
                    v1 = _mm256_add_pd(v1, _mm256_loadu_pd(a + i + 4));
                    v2 = _mm256_add_pd(v2, _mm256_loadu_pd(a + i + 8));
                    v3 = _mm256_add_pd(v3, _mm256_loadu_pd(a + i + 12));
                }
                {
                    double t[4];
                    _mm256_storeu_pd(t, _mm256_add_pd(_mm256_add_pd(v0, v1), _mm256_add_pd(v2, v3)));
                    s0 = t[0]; s1 = t[1]; s2 = t[2]; s3 = t[3];
                }
            }
#endif
            for (; i + 8 <= hi; i += 8) {
                s0 += a[i];     s1 += a[i + 1]; s2 += a[i + 2]; s3 += a[i + 3];
                s4 += a[i + 4]; s5 += a[i + 5]; s6 += a[i + 6]; s7 += a[i + 7];
            }
            for (; i < hi; i++) s0 += a[i];
            s += ((s0 + s1) + (s2 + s3)) + ((s4 + s5) + (s6 + s7));
        }
        times[k] = omp_get_wtime() - t0;
        sink += s;
    }
    for (k = 0; k < NTIMES; k++)
        if (times[k] < tmin) tmin = times[k];
    for (k = 1; k < NTIMES; k++) gbps[k - 1] = 1.0e-9 * (double)(8 * n) / times[k];

    {
        double sorted[NTIMES - 1], median;
        int m = NTIMES - 1;
        for (k = 0; k < m; k++) sorted[k] = gbps[k];
        qsort(sorted, (size_t)m, sizeof(double), cmp_double);
        median = sorted[m / 2]; /* m = 19 -> the 10th of 19: the exact median */
        printf("{\"kernel\":\"sum\",\"array_mib\":%zu,\"n\":%zu,\"threads\":%d,\"ntimes\":%d,"
               "\"checksum_ok\":%s,\"clock_quantum_us\":%d,\"min_iter_us\":%.1f,\"min_ticks\":%.1f,"
               "\"median_gbps_iters_2_20\":%.4f,\"gbps_iters_2_20\":[",
               mib, n, threads, NTIMES, (fabs(sink - (double)n * NTIMES) < 0.5) ? "true" : "false", quantum,
               1.0e6 * tmin, 1.0e6 * tmin / quantum, median);
        for (k = 0; k < m; k++) printf("%s%.4f", k ? "," : "", gbps[k]);
        printf("]}\n");
    }
    FREE(a);
    return 0;
}
