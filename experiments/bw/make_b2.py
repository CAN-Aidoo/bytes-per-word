"""Make B2's source from STREAM v5.10 stream.c with the ONLY change of PROTOCOL 3.3: mysecond() uses omp_get_wtime().

Usage: python make_b2.py <path to downloaded stream.c> <output stream_b2.c>
Refuses to run unless the input's SHA-256 is the pinned value. Deterministic.
"""
import hashlib
import sys

PINNED = "c388924eb140fda95f534cdb808ae7f1f8ebb18da41d8aec1b512a3c8d303c9b"

OLD_INCLUDE = "# include <sys/time.h>\n"
OLD_TIMER = """#include <sys/time.h>

double mysecond()
{
        struct timeval tp;
        struct timezone tzp;
        int i;

        i = gettimeofday(&tp,&tzp);
        return ( (double) tp.tv_sec + (double) tp.tv_usec * 1.e-6 );
}
"""
NEW_TIMER = """/* Based on a variant of the STREAM benchmark code: timer changed from gettimeofday to omp_get_wtime (PROTOCOL 3.3). */
#include <omp.h>

double mysecond()
{
        return omp_get_wtime();
}
"""


def main(src, dst):
    text = open(src, "rb").read()
    h = hashlib.sha256(text).hexdigest()
    if h != PINNED:
        sys.exit(f"stream.c hash {h} != pinned {PINNED}")
    text = text.decode("utf-8").replace("\r\n", "\n")
    if text.count(OLD_INCLUDE) != 1 or text.count(OLD_TIMER) != 1:
        sys.exit("stream.c does not contain the expected timer block exactly once")
    text = text.replace(OLD_INCLUDE, "# include <omp.h>\n").replace(OLD_TIMER, NEW_TIMER)
    open(dst, "w", newline="\n").write(text)
    print(f"wrote {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
