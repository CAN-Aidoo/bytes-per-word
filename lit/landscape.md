# Literature landscape: "bytes per word" law for CPU decode

Scout run 2026-11-05. 17 sources in `lit/sources.csv`, all opened via alphaXiv (full text for 11, summary report plus abstract snippet for 6, flagged in `how_found`). Search was arXiv-centric (alphaXiv index); publisher and proceedings pages were not reachable (WebFetch and direct HTTPS were blocked), so peer-reviewed coverage is thin. See Limits at the end.

## Verdict for G0

No paper found answers the question as posed. One paper is a near neighbour and one is a serious cautionary result. The general idea ("decode is memory-bound, so tokens/s is about bandwidth / bytes per token") is NOT new and must not be claimed as ours. What appears open is a clean, preregistered, CPU-only test of that law against a FLOPs-based competitor, with measured (not peak) bandwidth, across model sizes, quantisation levels and several commodity machines. Treat "appears open" as provisional until the leads listed under Limits are read.

## The closest works

### 1. Qiu et al. 2026, GGUF-metadata prediction of llama.cpp throughput (arXiv:2609.14864) — MOST THREATENING
- Does: predicts decode tok/s as `eta(host, quant) * B_host / D`, where `D` is bytes per generated token (file size scaled by active/total parameters, plus KV and recurrent state). 318 measurements on two Apple M4 Max machines and an RTX 5080. Held-out MAPE 11.6 to 36%, versus about 50% when charging total parameters. Includes MoE and a prefill model.
- Does not: use x86 commodity CPUs with DDR4/DDR5; test bandwidth against a FLOPs predictor for decode; fit zero parameters (eta is fitted per host and quantisation, and the paper says fitted efficiencies "are not universal"); show that measured bandwidth explains cross-machine differences, because B cancels after same-host fitting (their own remark). I did not verify which backend (Metal, CUDA, CPU) each run used.
- Consequence: our formula is an instance of theirs. Our novelty must be the hypothesis test (bytes versus FLOPs, no per-host fudge factor, CPU-only, several machines), not the formula.

### 2. Chen 2026, "Memory-Bound but Not Bandwidth-Limited" (arXiv:2605.30571) — cautionary
- Does: tests step time against `(W+K)/B_peak` on four NVIDIA GPUs, 44 cells. Achieved fraction of peak bandwidth falls from about 81% (L4) to about 27% (H100); CUDA Graphs recovers 1.26x on H100, and quantised kernels often fail to deliver the expected 4x byte reduction.
- Does not: cover CPUs, and it is a measurement study, not a model. It warns that the naive law over-predicts on fast hardware and that kernel support decides whether byte savings are realised. Expect reviewers to raise it; we need a CPU-side efficiency analysis.

### 3. Poperszky 2026, Pipeline-Native Transformers (arXiv:2608.23841) and Zhang 2026, Budgeting Bytes (arXiv:2609.04238)
- Do: both state the premise outright. Poperszky: CPU decode is bandwidth-bound (about 1 TFLOP/s versus about 50 GB/s, machine balance about 20 FLOP/byte versus about 4 FLOP/byte at Q4) and builds a CPU runtime around cutting bytes. Zhang: bytes-per-token as a first-class axis with roofline `bpt <= B/R`, validated on a USB drive (predicted 5.28 versus measured about 5.2 tok/s) and eMMC boards.
- Do not: test the law across many dense models, quantisation levels and DRAM-resident machines. Poperszky assumes it; Zhang works in the storage-tier regime (mostly MoE, sub-100M models).
- Consequence: the premise has independent single-point supporting evidence; our contribution is breadth and falsification, not the premise.

### 4. Prieto and Abad 2025, SLMs on CPU/GPU/NPU (arXiv:2511.22334)
- Does: 11 small models, F16 and Q4K, on an i5-12400 (DDR, 76.7 GB/s peak), ARM, Jetson GPU and an NPU; normalises tok/s by peak bandwidth and concludes "memory bandwidth emerges as the dominant factor".
- Does not: derive or fit a bytes-per-token model, use measured bandwidth, or have more than one x86 machine. Normalisation by peak, not a prediction test.

### 5. Gholami et al. 2024, AI and Memory Wall (arXiv:2403.14123) and Yuan et al. 2024, roofline survey (arXiv:2402.16363)
- Do: establish the arithmetic-intensity argument. Gholami profiles batch-1 GPT-2 decode on an Intel Gold 6242 CPU and shows it is far slower than BERT despite equal FLOPs. Yuan gives a roofline tool (LLM-Viewer) showing decode is memory-bound.
- Do not: validate predictions of absolute tok/s across models, quantisation levels and machines. These are the correct theory citations, not competing results.

## Other relevant items (shorter)
- CPU systems: Intel Efficient LLM Inference on CPUs (2311.00502), bitnet.cpp (2502.11880), FairyFuse (2604.20913): speedups from fewer bytes and cheaper arithmetic, never framed as a predictive law.
- Edge benchmarks: Raspberry Pi/Orange Pi (2511.07425), Hydra on Jetson (2608.25053), edge continuum (2609.08307). Measurement only. Khatib et al. report that weight-file size alone does not reliably predict latency, which is evidence we must explain (backend, architecture, thread count).
- Phones: Zhang and Huang (2505.06461): CPU beats GPU on an iPhone for a 1B model; the explanation is incomplete.
- Ways around the limit: speculative decoding on a laptop (2607.17283) shows gains depend on kernel batch behaviour. Batching and speculation change bytes per useful token and should be out of scope for the main claim.
- Quantisation: GPTQ (2210.17323) and AWQ (2306.00978) are the sources of the quantisation levels; cited as inputs only.

## The gap our question addresses
Existing work (a) asserts the bandwidth-bound premise, (b) fits per-host efficiency factors on Apple or NVIDIA hardware, or (c) benchmarks without a model. We found none that:
1. runs a CPU-only study on several commodity x86 and ARM machines with DRAM-resident dense models;
2. uses independently measured sustained bandwidth, with a single efficiency constant or none, instead of host-specific fitting;
3. pits the bytes-per-token predictor against an explicit FLOPs predictor and reports where each fails (threads, cache-resident small models, prefill, long context);
4. varies model size and quantisation together and reports out-of-sample error.
Narrowest defensible claim: "a preregistered, out-of-sample test of the bytes-per-token law on commodity CPUs, with failure regimes characterised". Do not claim discovery of the law.

## Limits and open leads (not opened, so not in sources.csv)
- Qiu et al. cite RooflineBench, LIMINAL, MoE-CAP, and Benazir and Lin on Apple Silicon quantisation; any may overlap. Prieto and Abad cite Na et al., "Understanding Performance Implications of LLM Inference on CPUs", IISWC 2024; this is the most likely peer-reviewed CPU characterisation and must be read before G0.
- Also seen only as search snippets: 2610.28576 (Token-Energy Law), 2609.30854 (KV cache memory wall), 2601.05047 (LLM inference hardware, Google), 2606.21428 (MoE on consumer hardware, cited by 2609.04238), 2410.16144 (1-bit AI Infra).
- llama.cpp and ggml documentation or discussions may already contain informal bandwidth-vs-tok/s tables; blogs and repositories were not searched and would be "background" only.
- Peer-reviewed venue coverage: IEEE Micro, NeurIPS 2023, ICLR 2023 and MLSys 2024 are asserted by pages I opened (footer or reference lists); most others are preprints dated 2026 that may not be peer-reviewed.
