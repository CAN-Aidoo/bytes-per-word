# G0 Novelty gate: bytes-per-word
Author: novelty-analyst · Date: 2026-11-05 · Inputs: `.lab/QUESTION.md`, `lit/landscape.md`, `lit/sources.csv`, `.lab/gates/venue.md`, plus 5 sources I opened myself via alphaXiv (listed at the end).
Convention: every claim about a paper is from a page I or the scout opened. Numbers quoted from papers are theirs; no number below is a result of ours.

## Verdict: **REVISE** · Class: **standard (conditional)**, otherwise technical note

The question as written ("is tok/s predicted by bytes/bandwidth rather than FLOPs?") is answered "yes, roughly" by a crowded literature at the level of premise, and the formula is an instance of Qiu et al. Its open, publishable core is narrower: a **pre-registered, transfer test on CPU-only hosts** in which bandwidth is *not* allowed to cancel out by per-host fitting, against an equally constrained FLOPs competitor. That is worth doing, but only if the question is rewritten so it can fail.

## Sharper question (one sentence)

> On CPU-only llama.cpp decode (batch 1, DRAM-resident dense GGUF models, no GPU/iGPU offload), does a predictor with no per-host and no per-quantisation fitting, tok/s = η · B_meas / D (D = bytes read per generated token from GGUF metadata plus KV cache, B_meas = sustained read bandwidth measured by a pre-registered STREAM-type benchmark, η one constant frozen on a single calibration cell of one machine), predict held-out tok/s on every other machine, model size and quantisation level within a pre-registered MAPE of 20%, and beat an equally constrained FLOPs predictor (tok/s = η′ · F_meas / 2P_active) on both the quantisation-ratio and the cross-machine-ratio tests; it is refuted if held-out MAPE exceeds 20% on any host, or if the FLOPs predictor is not worse on either ratio test.

The 20% threshold is a proposal for the protocol-architect to fix at G1, not a measured value. Basis: Qiu et al. report 11.6–36.0% leave-one-host-out MAPE on GPU/Metal with per-quant fitting [qiu2026gguf]; Li and Lu find the best CPU runtimes reach 72–78% of one NUMA node's read bandwidth [li2026weightplacement], so a single η near that range is physically plausible; 20% sits between "fitted GPU result" and "uselessly loose".

Why the two ratio tests are the real discriminators (design note for G1): for dense models at a fixed quantisation, bytes and nominal FLOPs per token both scale with P, so across model sizes the two predictors are collinear up to a constant and cannot be told apart. They separate only (a) **across quantisation levels** (bytes shrink, nominal FLOPs do not; dequantisation adds compute), and (b) **across machines**, if and only if the hosts' bandwidth ratio and FLOP/s ratio differ. The hardware-lead must measure B and F on each host before G1 and confirm (b) is discriminating; if the two ratios are close, test (b) is uninformative and must be dropped from the claim.

## Criterion scores

### 1. Is it new? — **3/5**
- Closest work: **Qiu et al. 2026** [qiu2026gguf, arXiv:2609.14864]. I opened it. Decode model is T̂ = η_{h,q} · B_h / D with η fitted per host and quantisation; scored hosts are two M4 Max machines (Metal, with BLAS) and an RTX 5080 (CUDA), per their host/backend table. They state the bandwidth scale "cancels algebraically after fitting on this same host". Their only unfitted baseline (B0, total parameters, η=1) gave 41.7–58.0% held-out MAPE. They did measure CPU STREAM triad and CPU FP32 GEMM on each host but used them for nothing scored. They do not test a FLOPs predictor for decode (their FLOPs model is for prefill only).
- Precise difference available to us: CPU-only backend; x86 laptop DDR4 + ARM SBC; η not refitted per host or quantisation, so B_meas does real predictive work; explicit bytes-vs-FLOPs comparison on quantisation and cross-host ratios; pre-registered refutation criterion.
- Search trail: scout's 17 sources plus my alphaXiv searches for (i) Na et al. IISWC 2024 by title and by keywords "LLM inference on CPUs, Sapphire Rapids, AMX, memory bandwidth" (not found in alphaXiv; see Open issues); (ii) RooflineBench (found, arXiv:2602.11506, opened); (iii) "CPU-only decode throughput, memory bandwidth, llama.cpp, tok/s prediction" (returned Qiu, Poperszky, Token-Energy Law 2610.28576, Li and Lu 2610.28620; the latter two opened); (iv) Tu et al. 2607.21602 (opened).
- RooflineBench [arXiv:2602.11506]: roofline characterisation and a "Relative Inference Potential" metric on M1 Pro, RTX 3070 Ti Laptop, Jetson Orin Nano and Raspberry Pi 5 (Pi runs Q8_0 only, models ≤0.5B). It measures peak bandwidth with PyTorch (Pi: 17.10 theoretical vs 3.98 GB/s measured, their Table 1) and reports tok/s tables, but does not predict tok/s or compare a bytes predictor against a FLOPs predictor. Not a threat to the sharpened question; it is a methodological warning that bandwidth measurement method matters.
- Tu et al. [arXiv:2607.21602]: learned, calibrated latency predictor on Pixel phones (MLC-LLM); black-box, needs target-device calibration. Contrast, not competitor.
- Score reason: the law and even the formula are prior art; the novelty is a narrower falsification on a hardware class nobody has scored. Incremental but real.

### 2. Does it matter? — **3/5**
- Who changes behaviour: (a) people choosing a model/quant for a CPU-only device (offline-first deployments) could size it from a one-minute bandwidth test instead of benchmarking every GGUF; Qiu et al. state this exact motivation for GPU/Apple hosts. (b) The Token-Energy Law authors say their energy law needs "a separately validated duration model" [niu2026tokenenergy]; a validated CPU duration model is a direct input. (c) If refuted, runtime authors and the many papers that *assume* CPU decode is bandwidth-bound (Poperszky, FairyFuse, Prieto and Abad) learn where that assumption fails; Li and Lu already show synchronisation, not bandwidth, limits multi-node CPU decode.
- Limits: the bandwidth-bound premise is widely believed, so a positive result mostly confirms; impact rests on the transfer test and the failure map.

### 3. Is it answerable here? — **3/5**
Stated honestly:
- Hosts usable for scored runs: **AMD Ryzen 5 5500U laptop, 8 GB DDR4-3200 dual channel** (x86); **Raspberry Pi, borrowed, model and RAM not yet known** (ARM). That is two CPU machines, the minimum the sharper question needs. The **iPhone** is a weak third host: CPU-only llama.cpp on iOS is possible (Zhang and Huang ran it [zhang2025cpugpu]) but thread placement, thermal throttling and bandwidth measurement are poorly controllable; treat as exploratory only. The **2-vCPU cloud Xeon (7 GB)** is development-only per the brief; if the Director allows it as a labelled third host, it adds a server-class x86 data point but is virtualised and shared, so it must be flagged.
- **No GPU** is not a limitation here: the question is CPU-only by design. Make sure the laptop build has no Vulkan/ROCm iGPU offload.
- Constraints: 8 GB RAM caps the largest model×quant cell on the laptop, and the Pi likely tighter; **disk mostly full** means models must be downloaded, hashed (SHA-256), run and deleted one at a time. Three sizes from one dense family at small scale (sub-1B to ~3B class) × three quantisation levels is feasible; the largest size at F16 may not fit on either device, in which case use three integer quantisation levels.
- Time: a few weeks is enough for ~2 hosts × 9 cells × thread sweep × 5 repetitions with llama-bench; the bottleneck is borrowing the Pi and disk juggling, not compute.
- Real data on real hardware; nothing is simulated.

### 4. What would a negative result mean? — **4/5**
- If the frozen-η bytes predictor misses 20% on a held-out host: CPU decode is not portable from a bandwidth number alone; the cause (thread synchronisation [li2026weightplacement], dequantisation compute on a weak ARM core, cache residency of small models, launch-like overheads as in [chen2026membound]) becomes the finding. ISPASS explicitly welcomes "confirmations or refutations of prior results" (venue.md).
- If FLOPs is not worse on the quantisation-ratio test: dequantisation compute, not bytes, governs CPU decode at low bit-widths, which contradicts the premise used by FairyFuse, bitnet.cpp-style work and Poperszky. Publishable either way.
- One caution: a negative caused by a bad bandwidth benchmark is not a result. Pre-register two bandwidth measurements (STREAM triad and a read-only kernel) and report both.

### 5. Paper class — **3/5 confidence in "standard"**
- **Standard** if the study reaches ≥3 CPU hosts (laptop + Pi + one more: the cloud Xeon as a labelled host, or a second borrowed machine), ≥3 sizes, ≥3 quantisation levels, a thread sweep and the failure-regime analysis. That supports a 10–12 page ISPASS/SEC paper.
- **Technical note** (IEEE CAL 4-page letter, or EuroMLSys 6 pages) if only the laptop and the Pi are scored. Two hosts give exactly one cross-machine ratio, which is thin for a full conference paper.
- Not flagship: single author, small models, commodity hardware, incremental over Qiu et al.

## Minimum experiment that answers the sharper question
1. **Hosts:** Ryzen 5 5500U laptop (calibration host) and Raspberry Pi (held-out host); third host optional as above. Record CPU, DRAM type/channels, kernel, governor, llama.cpp commit, build flags (CPU-only).
2. **Host constants (before any model run):** B_meas by STREAM triad and a read-only kernel; F_meas by an int8 and an FP32 GEMM micro-benchmark at the same thread count; 5 repetitions each. Check the B and F ratios between hosts differ enough to discriminate.
3. **Models:** one dense family, ≥3 sizes; ≥3 quantisation levels (e.g. Q4_K_M, Q8_0, F16 where it fits, else another integer level). D from GGUF metadata + KV bytes at the tested depth; P_active from tensor shapes.
4. **Measurement:** llama-bench tg128 at depth 0 (primary) and one longer depth (scope test); threads swept 1..physical cores, primary = pre-registered thread count; 5 repetitions; settle time; fresh process per cell; record decode CV.
5. **Fitting rule:** η and η′ each fitted once, on one pre-registered calibration cell of the laptop, then frozen. Everything else is held out.
6. **Tests:** (i) held-out MAPE per host vs 20%; (ii) quantisation ratio: measured tok/s(Qa)/tok/s(Qb) vs D_b/D_a (bytes) vs ≈1 (FLOPs); (iii) cross-host ratio for identical files vs B ratio vs F ratio. Report every cell, including failures (thread-scaling cliffs, cache-resident tiny models).

## Open issues
- **Na et al., IISWC 2024, "Understanding Performance Implications of LLM Inference on CPUs": NOT FOUND in alphaXiv** (exact-title lookup failed; keyword search returned other CPU papers). It is the most likely peer-reviewed CPU characterisation and is still unread. A human with IEEE Xplore access must read it before G1; if it already fits bytes/bandwidth to CPU tok/s across quant levels, this gate must be re-run.
- Not opened by me: LIMINAL, MoE-CAP (arXiv:2412.07067), Benazir and Lin. MoE-CAP is MoE-focused and the sharper question is dense-only, so low risk; LIMINAL is cited by Qiu as hardware-aware LLM analysis and should be checked by the literature-scout.
- Raspberry Pi model and RAM unknown; affects which cells fit.
- Whether the cloud Xeon may be used as a labelled scored host is the Director's call.

## New sources I opened (not added to `lit/`; for the literature-scout)
| Proposed key | arXiv | Verbatim quote (<25 words) |
|---|---|---|
| bi2026rooflinebench | 2602.11506 | "a systematic framework based on the Roofline model that unifies architectural primitives and hardware constraints" |
| tu2026transferable | 2607.21602 | "Heterogeneous profiling further shows that latency is highly device- and runtime-dependent" |
| niu2026tokenenergy | 2610.28576 | "Our evaluation uses observed decode duration; prospective deployment estimates can combine the law with a separately validated duration model." |
| li2026weightplacement | 2610.28620 | "the best runtimes use 72–78 % of the node's bandwidth" |
| qiu2026gguf (re-checked; already in sources.csv) | 2609.14864 | "For the fitted B1/B2 and P1/P2 models, the measured bandwidth or FLOP/s scale cancels algebraically after fitting on this same host." |

Searched, not found in alphaXiv: Na et al., IISWC 2024 (title above).
