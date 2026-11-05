# Protocol: Bytes per word: a pre-registered transfer test of a bandwidth predictor for CPU-only llama.cpp decode

Status: DRAFT until gate G1 is approved. After G1 this file is append-only: changes go in `## Deviations` with a date and reason.
Author (accountable): Clement Aidoo · Project class: note (technical note, two CPU hosts; G0 condition 3; `.lab/QUESTION.md` 2026-11-05) · Frozen at commit: <filled by gate.py>
Drafted by: protocol-architect, 2026-11-05. Review status: sections 4-5 **await the statistician's sign-off in `analysis/POWER.md`**
(not yet written; see §10); sections 3, 6, 8 await hardware-lead / experiment-lead feasibility sign-off. G1 must not be requested
until both sign-offs exist.

Evidence tags used below: **SOURCED** (opened in this task or in a cited lab file, with location), **MEASURED** (lab file),
**UNVERIFIED** (could not be opened; must be checked by the named person before G1), **JUDGEMENT** (a choice we make, with reason).

### Glossary (fixed meanings; the question's words map onto these)
- **Cell**: one (host, model file, depth, thread count) combination. Unit of analysis for MAPE.
- **Calibration cell**: the single cell on which η and η′ are computed (§4.3). It is never scored.
- **Evaluation cells** (= the question's "held-out tok/s ... on every other machine, model size and quantisation level"): every
  confirmatory grid cell except the calibration cell, scored at G2.
- **Confirmation set** (`heldout/`): additional cells defined in `heldout/README.md`, run and opened only after G2 approval.
- **Development cells**: runs on the development model only (§3.6), used for rig validation and debugging, never scored.
- **Eligible**: passes the DRAM-residency and RAM-fit rules of §3.5 on that host.

---

## 1. Question and claims

**Research question (verbatim, source `.lab/gates/G0_novelty.md` line 11, approved at G0 per `.lab/GATE_LOG.md` 2026-11-05T16:11:24Z):**

> On CPU-only llama.cpp decode (batch 1, DRAM-resident dense GGUF models, no GPU/iGPU offload), does a predictor with no per-host and no per-quantisation fitting, tok/s = η · B_meas / D (D = bytes read per generated token from GGUF metadata plus KV cache, B_meas = sustained read bandwidth measured by a pre-registered STREAM-type benchmark, η one constant frozen on a single calibration cell of one machine), predict held-out tok/s on every other machine, model size and quantisation level within a pre-registered MAPE of 20%, and beat an equally constrained FLOPs predictor (tok/s = η′ · F_meas / 2P_active) on both the quantisation-ratio and the cross-machine-ratio tests; it is refuted if held-out MAPE exceeds 20% on any host, or if the FLOPs predictor is not worse on either ratio test.

Context (summary, not decision-critical): G0 condition 1 is met. Na et al. (IISWC 2024) and LIMINAL do not answer the question
(`lit/na2024_check.md`; Director confirmation 2026-11-05). The nearest neighbour is Qiu et al. (arXiv:2609.14864), which fits η per
host and quantisation on Metal/CUDA (`lit/landscape.md` §1). Only this section would change if a later novelty check narrows the claim.

**Positive result.** All of: (i) per-host MAPE of the bytes predictor ≤ 20% on the evaluation cells of Host A and of Host B;
(ii) the same on the confirmation set of each host after G2; (iii) the bytes predictor beats the FLOPs predictor on the
quantisation-ratio test (§5.3); (iv) the bytes predictor beats the FLOPs predictor on the cross-machine-ratio test (§5.4), provided
that test was not dropped by the pre-registered rule of §4.5. Meaning: on these two CPU hosts, one efficiency constant and one
read-bandwidth number transfer across machine, model size and quantisation level, and bytes explain decode speed better than FLOPs.
It does not mean the law holds on other CPUs, runtimes or model families (two hosts only; §7).

**Negative result (refutation).** Any of: per-host MAPE > 20% on Host A or Host B (evaluation or confirmation cells); or the
FLOPs predictor is not worse on the quantisation-ratio test; or (if not dropped) the FLOPs predictor is not worse on the
cross-machine-ratio test. Meaning: a single frozen η with measured read bandwidth does not transfer on commodity CPUs; per-host
or per-format calibration is required, and the paper reports which regime breaks it (§5.6). A negative is publishable and will be
reported with the same prominence.

**Null / partial result.** Any of: the cross-machine test is dropped by the §4.5 rule (the two hosts' bandwidth and FLOP/s ratios
are too similar to discriminate); a ratio test is inconclusive (point estimate favours bytes but the 95% interval of the paired
difference includes 0); fewer than 75% of a host's planned eligible evaluation cells complete (§5.7). Meaning: the data do not
decide that part of the question; the paper states which part is untested and makes no claim on it.

---

## 2. Questions, hypotheses and outcomes

| ID | Question | Hypothesis or "descriptive" | Primary outcome | Unit | Direction / decision rule | Refutation criterion | Competing hypothesis |
|---|---|---|---|---|---|---|---|
| Q1 | Does the frozen-η bytes predictor transfer within 20%? | H1: per-host MAPE of tok/s = η·B1/D is ≤ 20% on every host | Per-host MAPE of the bytes predictor over evaluation cells (and, after G2, over confirmation cells) | % | Lower is better; pass iff point MAPE ≤ 20.0% on Host A **and** Host B (§5.2) | Point MAPE > 20.0% on either host, in evaluation or confirmation cells | H0-transfer: η is host- or format-specific (per-host fitting needed, as in Qiu et al.) so MAPE > 20% off the calibration host |
| Q2 | Across quantisation levels, do bytes or FLOPs predict the speed ratio? | H2: bytes predictor has lower log-ratio error than FLOPs predictor | Mean paired difference Δq = e_F − e_B of absolute log-ratio errors over quantisation pairs (§5.3) | dimensionless (natural log) | Bytes wins iff mean Δq > 0 and the one-sided 95% bootstrap lower bound > 0 | Mean Δq ≤ 0, or lower bound ≤ 0 with mean Δq ≤ 0 (inconclusive if mean > 0 but bound ≤ 0: null, §1) | HF-q: decode is compute-bound (dequantisation/arithmetic), so tok/s is ~independent of format at fixed P (ratio ≈ 1); also HDQ: partially compute-bound for high-dequant formats only |
| Q3 | Across the two machines, do bytes or FLOPs predict the speed ratio of identical files? | H3: bytes predictor has lower log-ratio error than FLOPs predictor | Mean paired difference Δh = e_F − e_B over files eligible on both hosts (§5.4) | dimensionless (natural log) | As Q2; only run if the §4.5 drop rule keeps the test | As Q2 | HF-h: tok/s scales with measured FLOP/s across hosts (F_B/F_A), not with read bandwidth (B_B/B_A) |
| Q4 | Where does the predictor fail? | descriptive (exploratory) | Per-format η_q = tok/s·D/B1 ratios; thread-scaling curve; depth-1024 error; cache-regime cells | dimensionless; tok/s | None (no test; labelled exploratory) | n/a | n/a |

---

## 3. System, data and materials

### 3.1 Hosts (facts from `hardware/HOSTS.md`, owned by the Director; restated, not re-measured)
- **Host A (calibration host; bare metal).** AMD Ryzen 5 5500U, 6 cores / 12 threads, Zen 2, L3 8 MiB, AVX2, no AVX-512
  [SOURCED in HOSTS.md: WikiChip]; 8 GB DDR4-3200 dual channel, both slots [author-stated]; theoretical peak 51.2 GB/s [derived in
  HOSTS.md]. Runs done by the human with our scripts.
- **Host B (evaluation host; virtualised, shared, labelled as such in every table and figure).** KVM Intel Xeon family 6 model 207
  (Emerald Rapids class), 2 vCPUs, 1 thread/core, L2 4 MiB, L3 260 MiB visible, AVX-512 (VNNI, BF16, FP16), AMX (bf16, int8), ~8 GB
  RAM, no frequency governor exposed [MEASURED: lscpu, HOSTS.md].
- **Recorded per host before the first scored run** (script `experiments/host_facts.py`, output `results/hosts/<host>.json`): CPU
  model string, microcode, BIOS/firmware version (Host A: `dmidecode -s bios-version`; Host B: as visible), kernel, OS release,
  compiler versions, LLC size per `lscpu`, memory size, DIMM count/speed (Host A: `dmidecode -t memory`), SMT state, governor and
  boost state, THP setting, and (Host A) power source. Serial numbers are not recorded (personal data rule).
- **OS requirement (UNVERIFIED for Host A).** All scripts assume Linux (sysfs topology, `/proc/vmstat`, `taskset`). Host A's OS is
  not recorded in any lab file. **Blocking for G1:** the Director confirms Host A runs Linux for scored runs, or this section is
  amended before G1 with Windows equivalents.

### 3.2 Software, pinned
- **llama.cpp**: tag `b12129`, commit `3259ab6e5dd86fad1931962d784702cb53c7877b` [SOURCED: `git ls-remote --tags
  https://github.com/ggml-org/llama.cpp.git`, 2026-11-05, newest numbered tag]. Same commit on both hosts.
- **Build (CPU-only, identical command on both hosts)**:
  `cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=ON -DGGML_BLAS=OFF -DGGML_OPENMP=ON
  -DGGML_CPU_REPACK=ON -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_HIP=OFF -DGGML_SYCL=OFF -DGGML_OPENCL=OFF -DGGML_ZENDNN=OFF
  -DGGML_BACKEND_DL=OFF && cmake --build build --config Release -j`.
  Option names and defaults SOURCED from `ggml/CMakeLists.txt` at the pinned commit (e.g. line 224 `option(GGML_VULKAN ... OFF)`,
  line 248 `option(GGML_OPENMP ... ON)`, line 152 `option(GGML_CPU_REPACK ... ON)`). BLAS is OFF (JUDGEMENT: BLAS only serves
  batched matmul, and turning it on changes F2 in §3.4 between hosts for reasons unrelated to the question). GGML_NATIVE=ON
  (JUDGEMENT: each host gets its own ISA, as a deployer would; the resulting ISA flags, including any AMX use on Host B, are
  recorded from llama.cpp's system-info line). No GPU/iGPU backend is compiled, so no offload is possible (V2).
- **gguf-py** from the same commit (`gguf-py/`), used to read tensor tables (§4.2).
- **STREAM** v5.10, `stream.c` with SHA-256 `c388924eb140fda95f534cdb808ae7f1f8ebb18da41d8aec1b512a3c8d303c9b`, obtained from
  `https://raw.githubusercontent.com/jeffhammond/STREAM/master/stream.c` (repo HEAD `6703f7504a38a8da96b353cadafa64d3c2d7a2d3`)
  [SOURCED 2026-11-05; the canonical cs.virginia.edu URL was blocked by the proxy]. Compiled `gcc -O3 -march=native -fopenmp`.
- **NumPy** for F1: version pinned in `experiments/requirements.txt` at G1 (same version both hosts); `numpy.show_config()` output
  stored with each F1 measurement.
- Python 3 version, gcc version and cmake version recorded per host in `results/hosts/<host>.json`.

### 3.3 Bandwidth benchmarks (G0 condition 4: two benchmarks)
Both run at the host's scored thread count T_h (§3.7), with `OMP_NUM_THREADS=T_h OMP_PROC_BIND=close OMP_PLACES=cores`.
- **B1, primary ("sustained read bandwidth")**: `experiments/bw/stream_read.c`, a variant of STREAM v5.10 that adds a read-only
  `Sum` kernel (s += a[j] over a double array, OpenMP reduction), keeping STREAM's timing loop (NTIMES = 20) and array sizing. Labelled
  "based on a variant of the STREAM benchmark code", as STREAM's licence item 3b requires [SOURCED: stream.c lines 29-34]. Reported
  value per process run: the median of iterations 2-20 of the Sum kernel in GB/s (bytes = 8 × N). Host value B1_h: median of 5 process
  runs. Rationale (JUDGEMENT): decode reads weights and KV; a read-only kernel measures the quantity the question names.
- **B2, secondary**: unmodified STREAM v5.10 Triad "Best Rate" (STREAM's own counting, 24 bytes per iteration). Host value B2_h:
  median of 5 process runs.
- **Array size**: each array ≥ 4 × LLC of the host, per STREAM rule (a): "Each array must be at least 4 times the size of the
  available cache memory" [SOURCED: stream.c lines 58-59]. Host A: ≥ 32 MiB; Host B: ≥ 1040 MiB. Additionally B1 is measured at
  8 × LLC to check the DRAM plateau (V5). Host B at 8 × LLC needs 2080 MiB for the single Sum array, which fits 8 GB.
- The NumPy probe of `hardware/host_probe.py` (pilot, `results/pilot/`) is advisory only and never enters any predictor.

### 3.4 FLOP/s benchmarks (for the FLOPs predictor)
- **F1, primary**: FP32 GEMM, NumPy `float32` matmul, n = m = k = 4096, `OPENBLAS_NUM_THREADS=T_h` (and `OMP_NUM_THREADS=T_h`),
  1 warm-up then 5 timed products per process; process value = median; host value F1_h = median of 5 process runs; FLOPs = 2n³.
  Rationale (JUDGEMENT): a model-independent, vendor-BLAS compute ceiling, measured the same way on both hosts, mirrors B1's role.
- **F2, robustness competitor**: llama.cpp's own compute-bound rate on the calibration file: F2_h = 2 · P_active(cal) · pp512_h,
  where pp512_h is `llama-bench -p 512 -n 0` tok/s of the calibration file on host h at T_h (5 repetitions, one process). Rationale
  (JUDGEMENT): gives the FLOPs predictor the runtime's achievable FLOP/s, its strongest fair form, while staying one constant per
  host and the same file on both hosts (no per-quantisation information).

### 3.5 Models, licences, SHA-256, eligibility
One open dense family, three sizes, three quantisation levels: **Qwen3 0.6B, 1.7B, 4B × {Q4_K_M, Q8_0, F16}**, GGUF files from the
`ggml-org` Hugging Face organisation.

| Model | Source repo | Licence | Quants (file size on repo page) | Evidence |
|---|---|---|---|---|
| Qwen3-1.7B | `huggingface.co/ggml-org/Qwen3-1.7B-GGUF` | Apache-2.0 | Q4_K_M 1.28 GB, Q8_0 2.17 GB, F16 4.07 GB | SOURCED (WebFetch 2026-11-05: "License: apache-2.0") |
| Qwen3-4B | `huggingface.co/ggml-org/Qwen3-4B-GGUF` | Apache-2.0 | Q4_K_M 2.5 GB, Q8_0 4.28 GB, F16 8.05 GB (F16 excluded: exceeds RAM) | SOURCED (WebFetch 2026-11-05: "License: apache-2.0") |
| Qwen3-0.6B | `huggingface.co/ggml-org/Qwen3-0.6B-GGUF` | Apache-2.0 expected | Q4_K_M, Q8_0, F16 expected | **UNVERIFIED** (page fetch not permitted in this task). Data-curator/Director must confirm licence and available quants before G1. Rule fixed now: any listed quant missing from that repo is produced with `llama-quantize <F16 file> <out> <TYPE>` at the pinned commit, no imatrix, and hashed. |

Quantisation format sizes (SOURCED, `gguf-py/gguf/constants.py` lines 6960-6971 at the pinned commit): F16 2 bytes/weight; Q8_0 34
bytes per 32 weights (8.5 bits/weight); Q4_K 144 bytes per 256 weights (4.5 bits/weight); Q6_K 210 bytes per 256 weights. Q4_K_M
files mix tensor types, which is why D is computed per tensor from metadata, never from a nominal bit width.

Dequantisation cost (required by the Director's 2026-11-05 note; JUDGEMENT from the format structure above, not measured): Q4_K_M is
the **high-dequant** format (256-weight super-blocks with packed 6-bit sub-block scales and mins, 4-bit unpacking); Q8_0 is the
**low-dequant** format (one fp16 scale per 32 int8 weights); F16 needs only a half-to-single conversion. The quantisation-ratio
test therefore contains a high-vs-low pair (Q4_K_M:Q8_0) and a low-vs-none pair (Q8_0:F16).

**SHA-256.** Each file is hashed with `sha256sum` immediately after download, before first use, and recorded in
`experiments/MODELS.csv` (columns: `model,quant,repo,revision_commit,filename,bytes,sha256,licence,downloaded_utc,host`). The
repo's revision commit is recorded so the file is re-downloadable. The same file must have the same hash on both hosts (V3).
Files are deleted after use on Host A (disk); the hash and revision make them re-obtainable.

**Eligibility rules (fixed now; computed by `experiments/cells.py` from metadata only, before any model run; output
`experiments/CELLS.csv`):**
1. **DRAM residency**: W_read (§4.2) ≥ 4 × LLC_h. Justification: the same multiple STREAM uses for "out of cache" (rule (a) above).
   If V5 shows that B1 at 4 × LLC exceeds B1 at 8 × LLC by more than 5% on a host, the multiple for that host becomes 8 (decided by
   the validation run, before any model run). Thresholds: Host A ≥ 32 MiB (all files pass); Host B ≥ 1040 MiB (or 2080 MiB).
   Ineligible cells are not scored; they may be run as exploratory "cache-regime" cells (Q4).
2. **RAM fit**: at block start, `MemAvailable` ≥ file bytes + KV bytes at the tested depth + 1.0 GiB (JUDGEMENT: margin for the
   process, compute buffers and the OS; prevents swap). A cell that fails this check after a fresh reboot with no other user
   programs is recorded as DNF ("did not fit"), reported, and not scored. This check never looks at tok/s.
3. Qwen3-4B F16 is excluded a priori (8.05 GB file > 8 GB RAM).

Planned confirmatory grid: 8 files (3 sizes × 3 quants minus 4B-F16) × 2 hosts = 16 cells, minus ineligible cells. By the file
sizes above, the 0.6B files at Q4_K_M and Q8_0 are expected to fail rule 1 on Host B (UNVERIFIED until computed by `cells.py`).

### 3.6 Data splits
- **Development**: `HuggingFaceTB/SmolLM2-360M-Instruct` GGUF at Q8_0 (Apache-2.0 expected; **UNVERIFIED**, data-curator confirms;
  fallback rule: the smallest Apache-2.0 or MIT dense GGUF ≥ 300 MB not in the grid or the confirmation set, chosen and hashed before
  first use). Used for V8, sentinel runs (§4.4) and script debugging only. Never scored. No grid or confirmation file may be run
  before G1 (G0 condition 3), and no pilot runs on any model are part of this draft.
- **Test (evaluation cells)**: the grid of §3.5 minus the calibration cell, at depth 0, T_h. Run after G1, scored at G2.
- **Held-out confirmation set**: defined in Appendix H of this file (authoritative; `heldout/README.md` is a copy, see §10).
  Generator: fixed cell list + `llama-quantize` recipe; order seed 20261106. Files are not downloaded, produced or hashed before G2
  approval; cells are run once, after G2, with this frozen protocol and the analysis code as committed at G2.

### 3.7 Run parameters (identical for every confirmatory cell)
- `llama-bench -m <file> -p 0 -n 128 -d 0 -r 5 -t <T_h> -C <mask_h> --cpu-strict 1 -ngl 0 -fa off -ctk f16 -ctv f16 -lm none
  --repack 1 --prio 0 -o jsonl` (flags SOURCED from `tools/llama-bench/README.md` at the pinned commit; `--no-warmup` is NOT given,
  so llama-bench's warm-up runs). If `-lm none` fails to load a file, `-lm mmap` is used for that cell and logged as a deviation.
- **Generation length** n_gen = 128 tokens, **prompt** 0 tokens, **depth** 0 (primary). llama-bench excludes tokenisation and sampling
  from its timing [SOURCED, README note].
- **Thread count** T_A = 6, T_B = 2 (one thread per physical core; JUDGEMENT: the standard deployment choice, fixed before data).
  `mask_h` selects the first logical CPU of each physical core, built from `/sys/devices/system/cpu/*/topology`. B1, B2, F1 and F2 use
  the same T_h and placement.
- **Seeds**: run order seed 20261105 (confirmatory), 20261106 (confirmation set), 20261107 (exploratory Q4); bootstrap seed 20261108.
  llama-bench uses no sampling seed for timing.

---

## 4. Design and sample size

### 4.1 Factors and levels
| Factor | Levels | Role |
|---|---|---|
| Host | A (Ryzen 5 5500U, bare metal), B (Xeon VM, shared) | cross-machine contrast |
| Model size | Qwen3 0.6B, 1.7B, 4B | size contrast (not discriminating, see 4.3) |
| Quantisation | Q4_K_M (high dequant), Q8_0 (low dequant), F16 (none) | quantisation contrast |
| Depth | 0 (confirmatory); 1024 (exploratory, Q4) | KV term scope |
| Threads | T_h (confirmatory); sweep (exploratory, Q4) | — |

### 4.2 Predictors and how their inputs are computed (worked example)
**Bytes per token D** (computed by `analysis/bytes_per_token.py` from the GGUF tensor table via gguf-py at the pinned commit):
- W_read = Σ over tensors t of n_bytes(t), where n_bytes(t) = n_elements(t) / block_size(type) × type_size(type) (gguf-py
  `GGML_QUANT_SIZES`), except `token_embd.weight`: if a separate `output.weight` exists (untied), token_embd contributes one row
  (n_bytes / n_vocab); if not (tied embeddings, output uses token_embd), it contributes its full n_bytes. 1-D norm tensors count in full.
- KV(d̄) = n_layer × 2 × n_head_kv × head_dim × d̄ × s_kv, with s_kv = 2 bytes (f16 cache, `-ctk/-ctv f16`), and d̄ = depth + n_gen/2
  = 64 for the confirmatory runs (mean context length over a 128-token generation; JUDGEMENT, standard averaging). n_layer, n_head_kv
  and head_dim are read from the GGUF keys `<arch>.block_count`, `<arch>.attention.head_count_kv`, and `<arch>.attention.key_length`
  (or embedding_length / head_count when absent).
- **D = W_read + KV(d̄).**
- **Worked example (illustrative numbers, NOT Qwen3's; real values come from metadata):** a model with n_layer = 28, n_head_kv = 8,
  head_dim = 128 and W_read = 1.000 × 10⁹ bytes at d̄ = 64: KV = 28 × 2 × 8 × 128 × 64 × 2 = 7,340,032 bytes, so D = 1.00734 × 10⁹
  bytes; with B1 = 40 × 10⁹ B/s and η = 0.7 the predicted rate is 0.7 × 40 × 10⁹ / 1.00734 × 10⁹ = 27.8 tok/s. At depth 1024 the KV
  term becomes 28 × 2 × 8 × 128 × 1088 × 2 = 124.8 × 10⁶ bytes (12.5% of W_read), which is why depth 1024 is a useful scope probe.

**Active parameters P_active** (same script): Σ n_elements of every 2-D weight tensor multiplied per token: all `blk.*` attention and
FFN projection matrices plus the output matrix (`output.weight`, or `token_embd.weight` when tied). Excluded: an untied token_embd
(a gather, no multiply-adds) and 1-D tensors. P_active is identical across quantisations of one model. FLOPs per token = 2·P_active,
exactly as the question defines; attention-score FLOPs are excluded from the predictor (reported in Q4 only).

**Predictors**: bytes ŷ_B = η · B1_h / D; FLOPs ŷ_F = η′ · F1_h / (2 P_active) (primary), and ŷ_F2 with F2_h (robustness).

### 4.3 Calibration cell (G0 condition 4: "excluded calibration cell")
**Host A, Qwen3-1.7B Q8_0, depth 0, T_A = 6.** η = tok/s_cal × D_cal / B1_A; η′ = tok/s_cal × 2 P_active,cal / F1_A; η′₂ likewise with
F2_A. Computed once by `analysis/analyse.py` from that cell only, written to `results/frozen_constants.json`, and excluded from
every scored error, MAPE, ratio test and figure statistic. Justification (JUDGEMENT): middle size and middle (low-dequant) format,
so neither extreme of the grid sets the constant; Host A is the bare-metal host with the lower noise. No other cell may influence
η or η′; refitting is forbidden (a quant- or host-dependent η is reported as a finding, §9).

### 4.4 Discriminating design
| Contrast (cells that test it) | Bytes predictor predicts | FLOPs predictor predicts | Discriminates? |
|---|---|---|---|
| C1. Quant pair Q4_K_M vs Q8_0, same model, same host (each size × host with both cells eligible; up to 6 pairs) | tok/s ratio = D_Q8_0 / D_Q4_K_M (at most 8.5/4.5 ≈ 1.9 from bits per weight; lower because Q4_K_M mixes in higher-bit tensors; exact value from metadata) | ratio = 1 (same P_active, same F) | **Yes**: predictions differ by well over the factor 1.5 that separates two ±20% bands (§4.5), unless Q4_K_M's mixed types push D_Q8_0/D_Q4_K_M below 1.5, which `cells.py` reports before any run. Also tests HDQ: a high-dequant format falling short of its byte ratio |
| C2. Quant pair Q8_0 vs F16, same model, same host (0.6B and 1.7B per host when eligible; up to 4 pairs) | ratio = D_F16 / D_Q8_0 (≈ 16/8.5 ≈ 1.9) | ratio = 1 | **Yes**, low-dequant vs no-dequant |
| C3. Same file on Host B vs Host A (files eligible on both hosts; expected 1.7B × 3, 4B × 2, 0.6B F16 if eligible: up to 6) | ratio = B1_B / B1_A | ratio = F_B / F_A | **Yes iff** the ratio of ratios ρ = (F_A/F_B)/(B_A/B_B) satisfies \|ln ρ\| ≥ ln 1.5 (§4.5); otherwise dropped |
| C4. Different sizes, same quant, same host | ∝ 1/D ≈ ∝ 1/P | ∝ 1/P | **No** (collinear up to a constant, per `.lab/gates/G0_novelty.md` design note). Used only inside MAPE, not as evidence for bytes over FLOPs |

Pair counts are upper bounds; actual pairs are fixed by `cells.py` from metadata before any run. Bits-per-weight values are from
gguf-py constants (§3.5); Q4_K_M's mixed tensor types make its exact D file-specific.

### 4.5 Rule for dropping the cross-machine test (G0 condition 4)
Compute, from the validation-phase host constants (B1, F1 measured after G1 and before any model run), **ρ = (F1_A / F1_B) / (B1_A /
B1_B)**. **The cross-machine-ratio test (Q3) is kept iff |ln ρ| ≥ ln 1.5, i.e. ρ ≥ 1.5 or ρ ≤ 1/1.5 = 0.667.** Otherwise it is
dropped: Q3 becomes descriptive, the paper states that the hosts cannot discriminate, and no cross-machine claim (for or against
bytes) is made.

Justification from the 20% threshold: both predictors are judged with a ±20% tolerance. A measured ratio can lie inside the band of
both predictions only if they are closer than (1 + 0.20)/(1 − 0.20) = 1.5. At ρ ≥ 1.5 no measured value can be "within 20%" of both, so
the test can separate them; below it the outcome could support both. The rule is fixed before any Host A host constant exists (Host
A's pilot probe is pending per `hardware/HOSTS.md`; Host B's pilot is known and is irrelevant to a threshold on a ratio). The same
rule is applied to F2 separately: if ρ₂ fails, the F2 comparison in Q3 is dropped and this is reported. B2 (Triad) enters only V7.

### 4.6 Repetitions, randomisation and blocking (provisional until `analysis/POWER.md` signs)
- **Unit**: cell. **Round**: one fresh `llama-bench` process for the cell (warm-up + 5 timed repetitions of tg128); round value = mean
  of the 5 repetitions. **Rounds per cell: 5.** Cell value = mean of round values.
- **Precision target** (JUDGEMENT, pending statistician): 95% CI half-width of the cell mean ≤ 2% of the cell mean (one tenth of the
  20% threshold, so measurement noise moves a cell's APE by at most about 2 percentage points). If after 5 rounds a cell misses it,
  up to 3 more rounds are added (max 8), a rule that uses only the cell's variance, never the predictor error; a cell still missing
  it is flagged "imprecise" and reported.
- **Host B (all files fit its 28 GB free disk)**: rounds are interleaved: round r runs every eligible cell once in a random order
  (permutation from `numpy.random.default_rng(20261105 + r)`), so drift and neighbour load are spread over cells.
- **Host A (disk forces one file at a time)**: blocked by file; file order is a random permutation (seed 20261105); within a file
  the 5 rounds run consecutively. A **sentinel** (development model, kept on disk throughout, 1 round) runs at session start and after
  every file; if a sentinel deviates by > 5% from the session's first sentinel, the preceding file's block is flagged and re-run at the
  end of the session (JUDGEMENT: 5% is a quarter of the MAPE threshold).
- **Thermal and load state** recorded before and after every round: CPU temperatures (`/sys/class/hwmon`), per-core MHz, 1-min load
  average, MemAvailable, `pswpin` and steal time from `/proc/stat` and `/proc/vmstat`. Host A: mains power, lid open, no user programs,
  performance governor if exposed. Rounds start only when the hottest sensor is within 5 °C of the idle baseline taken at session start
  (max wait 300 s, then start and flag). Host B: rounds start only when 1-min load average < 0.3.
- **Exploratory Q4 runs** (thread sweep T ∈ {1, 2, 4, 6} on Host A and {1, 2} on Host B for Qwen3-1.7B Q4_K_M and Q8_0; depth 1024
  for the Qwen3-1.7B files on both hosts; ineligible cache-regime cells on Host B) run only after all confirmatory rounds of the
  session, 3 rounds each, order seed 20261107.

---

## 5. Analysis plan (provisional until `analysis/POWER.md` signs)

### 5.1 Common
- APE per cell c: |ŷ_c − y_c| / y_c, with y_c the cell value (§4.6). All computations in `analysis/analyse.py`, deterministic.
- Bootstrap: 10,000 resamples, percentile intervals, seed 20261108, resampling the stated unit with replacement.

### 5.2 Q1 (MAPE)
- Per host h: MAPE_h = mean APE over that host's completed eligible evaluation cells (Host A excludes the calibration cell).
  Decision on the point estimate vs 20.0% (the question's wording). Reported with a 95% bootstrap CI over cells.
- Threshold justification (20%): Qiu et al. report 11.6–36.0% held-out MAPE with η fitted per host and quantisation on GPU/Metal, and
  41.7–58.0% for their unfitted baseline [SOURCED via `.lab/gates/G0_novelty.md` lines 13, 20]; Li and Lu report the best CPU runtimes
  use 72–78% of node bandwidth [same file, line 69], so one constant is physically plausible. 20% is stricter than half of Qiu's
  fitted range and is the G0-approved number.
- Secondary (reported, not decisive): FLOPs-predictor MAPE per host (F1 and F2); MAPE with B2 in place of B1.
- Confirmation set (after G2): the same statistic per host over confirmation cells; same 20.0% rule.

### 5.3 Q2 (quantisation-ratio test)
- Units: quantisation pairs (C1, C2) per (host, size) with both cells completed and eligible. For a pair (lower-bit a, higher-bit b):
  R = y_a / y_b; R_B = D_b / D_a; R_F = 1. Errors e_B = |ln(R / R_B)|, e_F = |ln R|; Δq = e_F − e_B.
- Decision: bytes beats FLOPs iff mean Δq > 0 and the one-sided 95% percentile-bootstrap lower bound (resampling pairs) > 0.
  Paired by construction. η cancels.

### 5.4 Q3 (cross-machine-ratio test; only if kept by §4.5)
- Units: files completed and eligible on both hosts. R = y_B / y_A; R_B = B1_B / B1_A; R_F = F1_B / F1_A. e_B, e_F, Δh as in 5.3,
  same decision rule. Robustness: repeated with F2 (if ρ₂ passes) and with B2; if bytes loses against F2 or with B2 the paper must say
  so (claim template T-narrow, §9), though only the F1/B1 comparison is the refutation test.

### 5.5 Multiplicity
The positive claim requires Q1 on both hosts **and** Q2 **and** Q3 (when kept): an intersection-union test, so each component is
tested at its own one-sided 5% level without correction and the family-wise false-positive rate for the joint claim stays ≤ 5%.
Robustness variants (F2, B2) are not separate confirmatory tests. Q4 has no tests.

### 5.6 Exploratory (labelled exploratory in the paper)
Per-format efficiency η_q = y·D/B1 by format and host (the Director's dequantisation risk: llama.cpp issue 25976, `lit/na2024_check.md`
line 31); thread-scaling curves; depth-1024 APE (tests the KV term); cache-regime cells on Host B; attention-FLOP share; FLOPs
predictor with attention FLOPs included. None of these can change a Q1-Q3 verdict.

### 5.7 Exclusions, failures, crashes, timeouts (decided now)
- A round is **excluded and repeated once** (at the end of the session) if: `pswpin` increased during it (swap: not DRAM-resident);
  Host B steal time > 5% of the round's CPU time (JUDGEMENT: caps stolen-time bias at a quarter of the MAPE threshold); Host A
  on battery; or a sentinel flag (§4.6). A repeated round failing again is kept and flagged; the cell is reported with the flag.
- A **crash** (non-zero exit, OOM kill) or **timeout** (a round exceeding 30 min, then killed) is logged and the round retried once.
  Two failures make the cell **failed**: reported in every table as failed, excluded from MAPE and ratio pairs.
- **Completeness rule**: if fewer than 75% of a host's planned eligible evaluation cells complete, Q1 for that host is "not
  evaluable" and the outcome is null/partial, never positive. Failures can therefore never help the positive claim.
- No other exclusions. Outliers are not removed. Every planned cell appears in `results/` and the supplementary table.

---

## 6. Validation plan (all must pass before any scored run; results in `results/validation/`)
| ID | Check | Tolerance (fixed now) | Justification |
|---|---|---|---|
| V1 | `git rev-parse HEAD` of the llama.cpp tree equals `3259ab6e…` on both hosts | exact | pinning |
| V2 | CPU-only: `llama-bench --list-devices` lists only CPU; system-info line shows no CUDA/Vulkan/HIP/SYCL/OpenCL/BLAS | exact | question requires no GPU/iGPU offload |
| V3 | SHA-256 of every model file equals the value in `experiments/MODELS.csv`; identical file ⇒ identical hash on both hosts | exact | G0 condition 4 |
| V4 | D computation: on the development model, script n_bytes per tensor equals gguf-py's tensor `n_bytes` for every tensor; and file size − Σ all tensor bytes ≤ 1% of file size | exact; ≤ 1% | tensor table vs file (remaining bytes are header, metadata, alignment) |
| V5 | DRAM plateau: B1 at 4 × LLC vs 8 × LLC per host | ≤ 5% difference, else LLC multiple → 8 (§3.5) | detects cache retention of a streaming pattern (relevant to Host B's 260 MiB L3) |
| V6 | B1 plausibility, Host A | 0.50 × 51.2 ≤ B1_A ≤ 51.2 GB/s | upper: theoretical peak (physical bound); lower: JUDGEMENT, below half of dual-channel peak indicates a misconfiguration (thread placement, single-channel memory) |
| V7 | Two bandwidth benchmarks agree on the host ratio: (B1_A/B1_B) vs (B2_A/B2_B) | within 15% | if they disagree more, Q3 must be won with both B1 and B2 (pre-registered consequence) |
| V8 | Repeatability, development model, tg128, 5 rounds per host | between-round CV ≤ 3% | needed to meet the 2% CI target with 5 rounds (§4.6); otherwise find the noise source first |
| V9 | Host constants stable: B1, B2, F1 over 5 process runs | CV ≤ 3% each | constants enter every prediction |
| V10 | Residency: RSS after load ≥ 0.95 × file size with `-lm none` on the development model; `pswpin` delta = 0 during a round | as stated | DRAM-resident and no swap |
| V11 | Thread placement: `taskset -p` of the llama-bench process during a run matches `mask_h` | exact | T_h is a fixed factor |

A failed check blocks scored runs on that host until fixed; the fix is logged as a deviation if it changes anything in §3.

---

## 7. Threats to validity
**Internal.**
- *Quantisation-dependent efficiency* (Director note 2026-11-05; llama.cpp issue 25976 reports Arm quantised decode at about 30–63%
  of STREAM, "compute-bound, not memory-bound", `lit/na2024_check.md` line 31). On x86, Q4_K_M dequantisation may make η lower for
  Q4_K_M than Q8_0. Mitigation: C1 contains a high- and a low-dequant format; η_q reported per format (Q4); no refit. Limitation
  sentence if seen: "a single η does not hold across formats on host h; the bytes law is format-conditional there."
- *Cache residency on Host B* (260 MiB L3). Mitigation: 4 × LLC eligibility, V5 plateau check; residual risk that adaptive LLC
  replacement retains a fraction of weights (at 4 × LLC at most a quarter of W_read). Limitation stated if Host B errors are positive
  and largest for the smallest eligible files.
- *Virtualisation noise and shared tenancy on Host B*: steal-time exclusion, interleaving, load gate; residual: undisclosed host
  frequency and memory configuration (UNVERIFIED); labelled "shared virtualised host" everywhere.
- *Drift and thermal throttling on Host A (15 W laptop)*: sentinel runs, cool-down gate, temperature logging.
- *Order effects*: randomised order (Host B interleaved; Host A file-blocked with sentinel).
- *Measurement error in D*: V4; KV averaging over d̄ is an approximation (KV ≈ 0.7% of D in the worked example at depth 0).
- *F1 as FLOPs ceiling*: NumPy/OpenBLAS may not represent llama.cpp's kernels; mitigated by F2 (runtime-native).
**External.** Two hosts, one x86 laptop and one virtualised server slice; one model family (Qwen3); one runtime commit; batch 1.
Limitation sentence: "Results are for two x86 CPU hosts and one dense model family; they do not establish the law for ARM, other
runtimes, MoE models, or batched serving."
**Construct.** tok/s from llama-bench excludes tokenisation and sampling (SOURCED); "decode speed" here means llama-bench tg128.
B1 measures read bandwidth with a simple reduction, which may exceed what a mixed GEMV access pattern can reach; η absorbs a
constant gap, but not a host-dependent one (that is exactly what Q1 tests).
**Conclusion.** Few units: up to ~10 quant pairs and ~6 cross-host files; bootstrap intervals over so few units are coarse
(statistician to quantify in `analysis/POWER.md`). Multiplicity handled by intersection-union (§5.5). The 20% decision uses the point
MAPE as the question states; its CI is always reported.
**What we will not be able to claim**: generality beyond two hosts; any causal mechanism for a failure (only the regime); anything
about prefill, long context beyond depth 1024, or energy.

---

## 8. Stopping rules, budget and safety
- **Compute/time budget**: Host B: ≤ 12 h wall time for validation + confirmatory + exploratory runs (JUDGEMENT; cells are seconds to
  minutes each). Host A: ≤ 3 human sessions of ≤ 3 h each, including downloads (one file at a time). Money: 0 (no paid compute).
  Agents in P1: 2 instances (protocol-architect, statistician) of the class limit 12 (`.lab/BUDGET.md`). Overrun > 20% raises AMBER.
- **Downloads**: grid ≈ 14.3 GB for the 1.7B and 4B files (repo page sizes above) plus the 0.6B files (sizes UNVERIFIED); held-out files only after G2.
- **On crash**: §5.7 rules; a host-level failure (machine unusable) stops that host; the remaining data are analysed under the
  completeness rule; nothing is re-planned without a dated deviation.
- **Early stopping**: only for safety, budget exhaustion, a failed validation check, or a RED alert. Never for good (or bad) results.
  No analysis of evaluation cells before all confirmatory rounds on both hosts are complete (the analysis script refuses to compute
  MAPE or ratio tests until `CELLS.csv` shows every planned cell as done, failed or DNF).
- **Hardware safety**: laptop on a hard surface with vents clear, mains power; stop the session if any CPU sensor reports ≥ 90 °C or
  the OS logs thermal throttling (JUDGEMENT; normal operation, no electrical modification).
- **Dual use**: none identified (performance measurement of public open-weight models). **Licences**: models Apache-2.0 (0.6B and
  development model UNVERIFIED until checked); llama.cpp MIT (UNVERIFIED in this task, licence file to be read at the pinned commit);
  STREAM under its own licence: B1 is labelled a STREAM variant, B2 results follow STREAM run rules or are labelled. No model
  weights are redistributed; `experiments/MODELS.csv` gives repo, revision and hash.
- **No secrets or personal data** in any file (no serial numbers, no user names in logs).

---

## 9. Reporting
- **Validation level for the abstract**: "bench measurement on real hardware (two CPU hosts, one virtualised)". No simulation.
- **To `paper/numbers.tex`** (generated by `analysis/`, never typed): B1, B2, F1, F2 per host; ρ and ρ₂ and the drop decision; η, η′;
  per-host MAPE (bytes, FLOPs F1, F2) with CIs; mean Δq and Δh with CIs; cell counts (planned, eligible, completed, failed, DNF);
  confirmation-set MAPE per host; llama.cpp commit; number of rounds.
- **Figures (CAL 4-page budget)**: Fig. 1: predicted vs measured tok/s (log-log), both predictors, both hosts, ±20% band, calibration
  cell marked. Fig. 2: ratio tests: measured vs predicted ratios for C1/C2 (left) and C3 (right). Table 1: host constants and drop
  decision. Per-cell table in the supplementary repository.
- **Claim templates** (the paper may use only the one matching the outcome; numbers are macros):
  - **T-pos**: "On two CPU hosts, a bandwidth predictor with one constant frozen on one laptop cell predicted CPU-only llama.cpp decode
    speed within \MapeA\ and \MapeB\ MAPE (threshold 20%) and explained quantisation and cross-machine speed ratios better than an
    equally constrained FLOPs predictor."
  - **T-pos-noQ3** (test dropped): as T-pos without the cross-machine clause, plus: "The two hosts' bandwidth and FLOP/s ratios differed
    by less than the pre-registered factor 1.5, so the cross-machine comparison was uninformative and no claim is made about it."
  - **T-neg-MAPE**: "A single frozen efficiency constant did not transfer: MAPE on host \HostX\ was \MapeX\ (threshold 20%)." followed by
    the regime analysis, labelled exploratory.
  - **T-neg-ratio**: "The FLOPs predictor was not worse than the bytes predictor on the \TestName\ test (mean difference \Delta, 95% CI
    \CI); the bytes-per-token law is refuted for this test on these hosts."
  - **T-narrow (quantisation-dependent η)**: "Efficiency depended on the quantisation format (η for Q4_K_M was \EtaRatio\ of Q8_0's on
    host \HostX\); the bytes law holds only conditional on format there." A format-dependent η is reported as this narrowed claim and is
    never silently refitted; any per-format refit appears only as a labelled exploratory analysis.
  - **T-null**: "The test of \TestName\ was inconclusive (point estimate favours bytes, CI includes zero)."
  - **T-imprecise**: if a MAPE CI crosses 20% while the point passes: "within the pre-registered threshold on the point estimate; the
    interval includes values above it."
- AI-use disclosure in every version (G0 condition 5).

---

## 10. Review status (to be resolved before G1)
- Statistician: **not yet spawned**. This agent's runtime had no agent-spawning tool; the brief is ready for the Director. Sections 4.6
  and 5 are provisional until `analysis/POWER.md` signs them; any change goes into this draft before G1, not as a deviation.
- Feasibility of §§3, 6, 8: hardware-lead/experiment-lead sign-off pending.
- `heldout/README.md` could not be written: the plugin guard blocks every write under `heldout/` before G2, README included. The
  definition is therefore Appendix H here; a copy for `heldout/README.md` is staged for the Director, who decides whether the guard
  should allow the README (human/Director decision, not worked around).
- Blocking facts for G1: Host A OS (Linux assumed, §3.1); Qwen3-0.6B and development-model licences and quants (§3.5, §3.6);
  llama.cpp licence file at the pinned commit; Host A probe is NOT needed for the protocol (the drop rule is fixed above).

---

## Appendix H. Held-out confirmation set (definition only; authoritative copy)
Purpose: one-shot confirmation of Q1 (per-host bytes-predictor MAPE ≤ 20%) on cells nobody has downloaded, run or analysed during
development. η and η′ are NOT recomputed (constants from the calibration cell, `results/frozen_constants.json`). Two kinds of novelty:
a quantisation level never used in the grid (Q6_K) and a model never used (different architecture: SmolLM2, Llama-type).

| ID | Host | Model file | How obtained (after G2 only) | Condition |
|---|---|---|---|---|
| HA1 | A | Qwen3-1.7B Q6_K | `llama-quantize <ggml-org Qwen3-1.7B F16 GGUF> <out> Q6_K` at commit `3259ab6e5dd86fad1931962d784702cb53c7877b`, no imatrix, default options | always |
| HA2 | A | Qwen3-0.6B Q6_K | same recipe from the ggml-org Qwen3-0.6B F16 GGUF | always (Host A LLC rule passes) |
| HA3 | A | SmolLM2-1.7B-Instruct `smollm2-1.7b-instruct-q4_k_m.gguf` | `huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF` (SOURCED 2026-11-05: "License: apache-2.0", 1.06 GB) | always |
| HA4 | A | Qwen3-4B Q6_K | same recipe from the ggml-org Qwen3-4B F16 GGUF (8.05 GB download) | only if Host A free disk ≥ 12 GB, recorded before the session (resource rule, never an outcome rule) |
| HB1 | B | Qwen3-1.7B Q6_K | as HA1 | always |
| HB2 | B | Qwen3-4B Q6_K | as HA4 | always (~28 GB free on Host B) |
| HB3 | B | Qwen3-0.6B Q6_K | as HA2 | only if eligible under §3.5; else exploratory |
| HB4 | B | SmolLM2-1.7B-Instruct q4_k_m | as HA3 | only if eligible under §3.5 (1.06 GB file is expected to fall just below Host B's 1040 MiB threshold; UNVERIFIED until computed); else exploratory |

- Run parameters exactly §3.7; rounds and precision rule §4.6; exclusions §5.7. Same host constants as the evaluation runs; if a host's
  hardware or OS changed in between, that host's confirmation is invalid and reported as such (no re-measurement to rescue it).
- Order: permutation of the applicable IDs per host from `numpy.random.default_rng(20261106)`; Host B interleaved by round; Host A
  blocked by file with sentinels.
- Hashes: SHA-256 in `heldout/MODELS.csv` (schema of `experiments/MODELS.csv`) at production/download time, after G2. Q6_K files made on
  both hosts from the same F16 input are expected to be byte-identical; a mismatch is reported and each host uses its own file.
- Decision: per-host MAPE over completed eligible confirmation cells ≤ 20.0% (point estimate) with the §5.7 completeness rule; a host
  with fewer than 2 completed eligible confirmation cells is "confirmation not evaluable", and the paper makes no confirmed-transfer
  claim for that host.
- Access: nothing produced, downloaded or opened before G2 approval; run once; retries only per §5.7, logged; analysed with
  `analysis/analyse.py` as committed at G2, unchanged.

## Deviations
<!-- YYYY-MM-DD: what changed, why, which results it affects. Append only. -->
