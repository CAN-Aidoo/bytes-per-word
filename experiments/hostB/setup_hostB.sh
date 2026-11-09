#!/usr/bin/env bash
# Host B (Linux Xeon cloud VM) setup for P2, PROTOCOL 3.2: pinned llama.cpp build, pinned Python packages, STREAM B1/B2 binaries.
# Run from the repository root:   bash experiments/hostB/setup_hostB.sh 2>&1 | tee ~/hostB_setup.log
# It downloads: llama.cpp commit 3259ab6e (git, ~100 MB), STREAM stream.c (<1 MB, SHA-256 checked), NumPy 2.5.4 and psutil 7.2.2 (pip).
# It needs: git, cmake, gcc/g++, make, python3 with venv/pip. It installs nothing system-wide and never uses sudo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${HOSTB_WORK:-$HOME/hostB-work}"
COMMIT=3259ab6e5dd86fad1931962d784702cb53c7877b
STREAM_SHA=c388924eb140fda95f534cdb808ae7f1f8ebb18da41d8aec1b512a3c8d303c9b
mkdir -p "$WORK"; cd "$WORK"

echo "== tools =="; for t in git cmake gcc g++ make python3; do command -v "$t" >/dev/null || { echo "MISSING: $t"; exit 1; }; done
gcc --version | head -1; cmake --version | head -1; python3 --version

echo "== llama.cpp at the pinned commit =="
if [ ! -d llama.cpp/.git ]; then
  git init -q llama.cpp && git -C llama.cpp remote add origin https://github.com/ggml-org/llama.cpp.git
fi
git -C llama.cpp fetch --depth 1 origin "$COMMIT"
git -C llama.cpp checkout -q FETCH_HEAD
test "$(git -C llama.cpp rev-parse HEAD)" = "$COMMIT" && echo "V1 OK: HEAD = $COMMIT"

echo "== build (PROTOCOL 3.2 command) =="
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=ON -DGGML_BLAS=OFF -DGGML_OPENMP=ON \
  -DGGML_CPU_REPACK=ON -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_HIP=OFF -DGGML_SYCL=OFF -DGGML_OPENCL=OFF -DGGML_ZENDNN=OFF \
  -DGGML_BACKEND_DL=OFF
cmake --build build --config Release -j "$(nproc)"
cd "$WORK"
echo "V14 OpenMP in cache: $(grep -E '^GGML_OPENMP(_ENABLED)?:' llama.cpp/build/CMakeCache.txt | tr '\n' ' ')"
echo "V2 devices:"; ./llama.cpp/build/bin/llama-bench --list-devices 2>&1 | head -5 || true
echo "system info line:"; ./llama.cpp/build/bin/llama-cli --version 2>&1 | head -3 || true

echo "== Python venv with pinned packages =="
python3 -m venv venv
./venv/bin/pip install --quiet -r "$REPO_ROOT/experiments/requirements.txt"
./venv/bin/python -c "import numpy,psutil;print('numpy',numpy.__version__,'psutil',psutil.__version__)"
./venv/bin/python -c "import numpy;numpy.show_config()" 2>&1 | grep -i -E "openblas|name:" | head -4

echo "== STREAM (B2) and B1 =="
mkdir -p bw
curl -fsSL -o bw/stream.c https://raw.githubusercontent.com/jeffhammond/STREAM/master/stream.c
echo "$STREAM_SHA  bw/stream.c" | sha256sum -c -
cp "$REPO_ROOT/experiments/bw/make_b2.py" "$REPO_ROOT/experiments/bw/stream_read.c" bw/
python3 bw/make_b2.py bw/stream.c bw/stream_b2.c
gcc -O3 -march=native -fopenmp bw/stream_read.c -o bw/stream_read -lm
# B2 arrays must be >= 4 x LLC (PROTOCOL 3.3: Host B >= 1040 MiB per array); STREAM's default 10M doubles (76 MiB) sits inside
# the 260 MiB L3. 140e6 doubles = 1068 MiB per array; three static arrays exceed 2 GiB, hence -mcmodel=medium.
gcc -O3 -march=native -fopenmp -mcmodel=medium -DSTREAM_ARRAY_SIZE=140000000 bw/stream_b2.c -o bw/stream_b2 -lm
ls -l bw
echo "quick smoke test (not a measurement): B1 64 MiB, 2 threads"
OMP_NUM_THREADS=2 ./bw/stream_read 64 | head -c 400; echo
echo "Setup finished. Send me ~/hostB_setup.log (and tell me the CPU model: lscpu | grep 'Model name')."
