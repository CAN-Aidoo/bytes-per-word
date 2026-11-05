# P2 plan: build and validate (research-director, 2026-11-05, after G1)
Source of truth: PROTOCOL.md §3.2, §3.8 (Host A native Windows), §6 (V1-V14). Nothing below changes a threshold. No scored run before every V check passes.

## State on Host A (this laptop), measured 2026-11-05
- Present: git, Python 3.13.14 (Microsoft Store, via `python3.13.exe`; no `py` launcher), numpy 2.5.4 and psutil 7.2.2 (installed; OpenBLAS bundled).
- Missing: cmake, clang, gcc, MSVC (`cl`), ninja, make. PROTOCOL §3.8 needs Visual Studio 2022 "Desktop development with C++" with the CMake Tools, Clang compiler and MSBuild-for-LLVM components, and clang 20.x for `GGML_OPENMP_FETCH`.
- Free disk 14.1 GB (C:). A VS 2022 C++ install is several GB and competes with the 4.28 GB largest model file; check free space before installing.
- Host B (Linux cloud container) is not reachable from this Windows session; its steps run in that workspace.
- `experiments/run.py` and `validate.py` are placeholders; `experiments/cells.py`, `MODELS.csv`, `launch.py`, `topology_win.py` do not exist yet.

## Needs the author's explicit yes (downloads and installs; per file: name, source, size)
| # | Item | Source | Size (approx.) | Why |
|---|---|---|---|---|
| D1 | Visual Studio 2022 Build Tools with the three components in §3.8 (or full VS 2022) | visualstudio.microsoft.com | several GB | only toolchain allowed by §3.8 |
| D2 | llama.cpp source at tag `b12129` / commit `3259ab6e5dd86fad1931962d784702cb53c7877b` | `git clone` from github.com/ggml-org/llama.cpp | ~100 MB | pinned build |
| D3 | STREAM v5.10 `stream.c` (SHA-256 `c388924eb140fda95f534cdb808ae7f1f8ebb18da41d8aec1b512a3c8d303c9b`) | source named in PROTOCOL §3.3 | <1 MB | B1/B2 |
| D4 | SmolLM2-360M-Instruct Q8_0 (development model) | huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF | 386 MB | V8 and sentinel runs |
| D5 | Grid files, one at a time on Host A, deleted after use | huggingface.co/ggml-org/Qwen3-{0.6B,1.7B,4B}-GGUF | 1.28 / 2.17 / 4.07 GB (1.7B), 2.5 / 4.28 GB (4B), 0.6B per §3.5 | scored cells, only after V1-V14 pass |

## Work I can do without those downloads (scripts, no results)
1. `experiments/cells.py` (eligibility from GGUF metadata, writes `CELLS.csv`), `experiments/MODELS.csv` header, `topology_win.py`, `launch.py`, a real `validate.py` skeleton for V1-V14, and stubs that fail loudly instead of printing "not implemented".
2. Tests of those scripts on synthetic inputs only (no invented measurements).

## Order after yes
D1 -> D2 build with the §3.8 preset -> V1, V2, V12, V14 -> D3 and B1/B2/F1/F2 -> V5-V7, V9-V11, V13 -> D4 and V8, sentinel -> binding constants (rho decided under §4.5) -> D5 grid, calibration cell first -> analysis -> G2 packet.
Each step logs deviations in PROTOCOL `## Deviations`. Agent budget: 10/12 used; P2-P3 work is done by the Director in the main session unless a task is truly independent.
