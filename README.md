# Bytes per word

**A preregistered CPU-only study of whether memory traffic predicts language-model decode speed better than arithmetic throughput.**

This repository contains the protocol, benchmark harness, analysis code, raw measurements, and paper sources for a CANLABS technical note. The central question is:

> On CPU-only `llama.cpp` decode, does a model's bytes moved per generated token, divided by measured sustained read bandwidth, predict tokens per second across model sizes, quantisation levels, and machines better than a FLOPs-based predictor?

The study deliberately uses **two CPU hosts**, **one model family**, and a frozen analysis plan. It does not claim that the resulting law applies to all CPUs, runtimes, model architectures, or GPU systems.

> **Project status:** the protocol is frozen at G1. Host A grid collection is in progress. The repository contains real pilot, calibration, validation, and grid-session data, but the end-to-end analysis and paper are not yet final. Do not treat the current intermediate results as the final scientific conclusion.

## Research design

### Predictors

For each eligible model file, the primary bytes predictor is:

```text
predicted tok/s = η × B_measured / D
```

where:

- `D` is the bytes read per generated token: GGUF tensor bytes plus the expected KV-cache traffic;
- `B_measured` is the host's sustained read bandwidth from the preregistered B1 benchmark;
- `η` is one efficiency constant, frozen once on the calibration cell and not refit per host or quantisation.

The competing FLOPs predictor uses the same one-constant constraint:

```text
predicted tok/s = η' × F_measured / (2 × P_active)
```

`P_active` is the active two-dimensional model parameter count derived from the GGUF tensor table. The protocol also defines a stronger runtime-based FLOPs competitor using `llama-bench` (`F2`).

### Questions and decision rules

| Question | Primary measure | Preregistered decision |
|---|---|---|
| Does the bytes predictor transfer? | Per-host MAPE on evaluation cells, then the held-out confirmation set | Pass if MAPE is at most 20% on each host |
| Do bytes or FLOPs explain quantisation ratios better? | Paired log-ratio error across quantisation pairs | Bytes wins only with the preregistered sign-flip test and bootstrap interval |
| Do bytes or FLOPs explain cross-machine ratios better? | Paired log-ratio error for identical files across hosts | Same statistical rule, unless the preregistered discrimination check drops the test |
| Where does the predictor fail? | Per-format efficiency, depth, cache regime, and thread-scaling diagnostics | Exploratory; no confirmatory claim |

Negative and inconclusive results are valid outcomes. The protocol defines them before the confirmatory runs.

## Experimental matrix

### Hosts

- **Host A:** AMD Ryzen 5 5500U laptop, 6 cores / 12 threads, Zen 2, 8 MiB L3, AVX2, 8 GB DDR4-3200 dual-channel memory. Scored measurements use native Windows; WSL is excluded.
- **Host B:** shared, virtualised KVM Intel Xeon environment with the host facts recorded in `hardware/HOSTS.md` and per-session rechecked. Results remain labelled virtualised/shared and are never silently pooled with a changed VM configuration.

Host constants include sustained bandwidth (`B1`, `B2`) and compute throughput (`F1`, `F2`). The exact measured values and session metadata belong under `results/hosts/` and `results/raw/`; the paper's generated numbers must come from the analysis pipeline.

### Models

The confirmatory family is Qwen3 GGUF:

| Size | Quantisations |
|---|---|
| 0.6B | `Q4_K_M`, `Q8_0`, `F16` |
| 1.7B | `Q4_K_M`, `Q8_0`, `F16` |
| 4B | `Q4_K_M`, `Q8_0` |

Qwen3-4B `F16` is excluded a priori because it does not fit the 8 GB Host A memory constraint. Qwen3-0.6B `Q4_K_M` is produced locally with the pinned `llama-quantize` build because it is not listed in the source repository. Every downloaded or generated model is SHA-256 hashed and recorded in `experiments/MODELS.csv`.

The development model is SmolLM2-360M Q8_0. Development cells are for rig validation and debugging only; they are not confirmatory evidence.

## Repository map

| Path | Purpose |
|---|---|
| `PROTOCOL.md` | Authoritative preregistered protocol. It is frozen at G1 and is append-only; post-G1 changes go in `Deviations`. |
| `.lab/` | CANLABS project state, tasks, alerts, gate packets, and decision records. |
| `experiments/` | Validation, host benchmarks, model-cell generation, launch/affinity helpers, calibration, and grid runners. |
| `analysis/` | Bytes-per-token calculation, frozen constants, statistical analysis, power documentation, and figure generation. |
| `hardware/` | Host descriptions, hardware probing, and hardware-test documentation. |
| `results/` | Frozen constants, host measurements, run logs, session state, and raw benchmark outputs. |
| `heldout/` | Definition-only confirmation-set specification. It must remain closed until G2 approval. |
| `paper/` | LaTeX manuscript, generated `numbers.tex`, and bibliography. |
| `lit/` | Literature landscape, source inventory, and novelty checks. |
| `CITATION.cff` | Citation metadata, to be completed for release. |
| `LICENSE` | MIT licence for code; paper, figures, and data are CC BY 4.0. |

## Reproducibility

### Requirements

The analysis utilities require Python 3 and the pinned packages:

```text
numpy==2.5.4
psutil==7.2.2
```

Install them in an environment appropriate to the host:

```bash
python3 -m pip install -r experiments/requirements.txt
```

The full protocol also requires a pinned CPU-only `llama.cpp` checkout at commit `3259ab6e5dd86fad1931962d784702cb53c7877b` (tag `b12129`), its `gguf-py` package, a C/C++ toolchain, OpenMP, CMake, and a LaTeX installation with `latexmk`. Build options and benchmark details are specified in `PROTOCOL.md`; do not substitute a different runtime or silently change compiler/build flags for scored runs.

### Canonical pipeline

The intended reproducibility entry point is:

```bash
make all
```

The Makefile stages are:

```bash
make validate      # protocol and rig validation
make experiments   # benchmark collection
make analysis      # analysis and paper/numbers.tex
make figures       # generated figures
make paper         # paper/main.pdf via latexmk
make clean         # remove LaTeX build artefacts
```

**Current implementation note:** the top-level orchestration is still being completed. In the current checkout, `experiments/validate.py` and `experiments/run.py` are placeholders, and `analysis/analyse.py` currently implements the `freeze` stage rather than the complete MAPE/ratio analysis. Use the committed Host A runner and supporting scripts for the collection work already implemented, and do not describe `make all` as a completed end-to-end reproduction until those stages are finished.

### Host A grid

The Host A runner is designed for native Windows Command Prompt, with the laptop plugged into mains power, WSL stopped, and the Claude desktop application and other interfering programs closed:

```bat
py experiments\grid_hostA.py --dry-run
py experiments\grid_hostA.py --max-hours 3
```

The dry run performs pre-flight checks without downloading models or running `llama-bench`. A real session records host/session state, uses the frozen cell order, applies RAM and residency rules, hashes model files, stores raw blocks and sentinels, resumes from `results/raw/A/state.json`, and deletes large model files when no longer needed. Read `experiments/grid_hostA.py` and `experiments/hostA/SESSION_A_GRID.md` before running it.

For a single GGUF file, the bytes-per-token calculation can be inspected directly:

```bash
python analysis/bytes_per_token.py path/to/model.gguf --depth 0 --n-gen 128
```

The calculator reads the pinned `gguf-py` implementation. Set `GGUF_PY` if that checkout is not at the default path used by the script.

## Data and analysis rules

- `results/` contains measurements and derived artefacts; raw session files are not edited by hand.
- `experiments/CELLS.csv` is generated from GGUF metadata before model runs and records eligibility.
- A cell must satisfy the preregistered DRAM-residency and RAM-fit rules to be scored.
- The calibration cell is excluded from all evaluation MAPE and ratio statistics.
- Frozen constants in `results/frozen_constants.json` must not be refit or overwritten without explicit author approval.
- Every number in the paper must be generated into `paper/numbers.tex` by `analysis/`; do not type measured values directly into `paper/main.tex`.
- The held-out confirmation set is definition-only before G2. Do not download, open, run, or analyse its files early.
- Protocol deviations must be dated and recorded in `PROTOCOL.md`; project problems belong in `.lab/ALERTS.md` using the repository's alert format.

For the complete definitions of cells, eligibility, bandwidth benchmarks, model metadata, statistical tests, exclusions, and held-out confirmation, use `PROTOCOL.md` as the source of truth. This README is an orientation and execution guide, not a replacement for the protocol.

## Current artefacts

Useful starting points for inspecting the current project state:

```text
results/RUNLOG.md                 # Host A session chronology
results/hosts/                    # Host constants and calibration inputs
results/raw/                      # Immutable session/block JSON outputs
experiments/MODELS.csv            # Model provenance and SHA-256 records
experiments/CELLS.csv             # Eligibility and derived cell metadata
.lab/STATE.md                     # Research phase and next gate
.lab/ALERTS.md                    # Open and resolved protocol/data concerns
```

Do not infer a final result from the run log alone. Read the protocol, check validation flags, and use the analysis outputs when they are available.

## Citing

Citation metadata is maintained in [`CITATION.cff`](CITATION.cff). The title, author, release date, repository URL, and DOI fields are still release placeholders and must be completed before publication or archival release.

## Licence

Code is released under the [MIT License](LICENSE). Paper text, figures, and data are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
