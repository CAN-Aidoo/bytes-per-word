# G0 condition 1 check: Na et al. (IISWC 2024) and LIMINAL
Scout run 2026-11-05 (P1). Question text is verbatim in `.lab/gates/G0_novelty.md`.

## Verdicts
- Na et al. 2024 [na2024cpu]: **DOES NOT ANSWER** (confidence moderate: read via WebFetch summaries of the author manuscript and slides, not a verbatim full read; see caveats).
- LIMINAL [davies2025liminal]: **DOES NOT ANSWER** (GPU-only; it does overlap in spirit, see below).
- Fresh search found no CPU-only, frozen-constant, bytes-vs-FLOPs predictor. One anecdotal threat to the quantisation-ratio test (llama.cpp issue 25976).

## Na et al., "Understanding Performance Implications of LLM Inference on CPUs"
Routes tried: alphaXiv (P0, failed, per G0 note); WebSearch by title (success: found NSF PAR author manuscript https://par.nsf.gov/servlets/purl/10576248, IEEE Xplore link https://ieeexplore.ieee.org/document/10763564, computer.org link, author slides); WebFetch NSF PAR manuscript (success, via summariser); WebFetch author slides (success); WebFetch IEEE Xplore and computer.org (returned no article text); NSF PAR landing page (blocked by robots); Crossref API (blocked, permission unanswered). No arXiv version found.
Venue caveat: the NSF page states no venue. IISWC 2024 comes from the computer.org URL path (`/iiswc/2024/`) in search results and from the brief; the DOI and pages were not seen. A human should confirm.
- Hardware: Xeon 8352Y (Ice Lake, DDR4, no AMX, 2x32 cores) and Xeon Max 9468 (Sapphire Rapids, DDR5 plus HBM, AMX, 2x48 cores) versus A100-40GB and H100-80GB with FlexGen offloading. Server class, not our hosts.
- Models: OPT-1.3B to 66B, LLaMA-2 7B/13B/70B, BF16. Metrics: latency, TTFT, TPOT, tok/s, LLC MPKI, core and UPI utilisation. Not llama.cpp, not GGUF.
- Throughput predictor? No. Quote [na2024cpu]: "Despite processing only one token per step, the decode phase demands substantial I/O operations making it memory-bound."
- Bytes vs FLOPs comparison? No predictor of either kind. Slides classify decode as "Memory bound" and prefill as "Compute bound" and give measured 233.8 GB/s (DDR5) and 588 GB/s (HBM) per socket; the only formula is KV-cache sizing, not performance.
- Quantisation sweep? No (BF16 only; INT8 appears only as an AMX data type).
- Cross-machine transfer with a frozen constant? No; machines are compared by measurement only. Key finding quote: "AMX-enabled CPUs can achieve lower latency and higher throughput for larger models requiring offloading."
- Quotes above came through a summariser; verify wording against the PDF before putting any in the paper.

## LIMINAL (Davies, Crago, Sankaralingam, Kozyrakis; arXiv:2507.14397 v2, 13 Nov 2025, "preliminary work, under review")
Routes: WebSearch (success); WebFetch arxiv.org abs, pdf and html v2 (success, summariser). alphaXiv tools were not available in this run. No peer-reviewed venue seen.
- Setting: analytical decode model, batch latency = max(compute time, memory time) plus exposed collective latency; hypothetical xPU with HBM3/HBM4/3D-DRAM/SRAM; validation on 8xH100 with vLLM BF16; Llama 3/4, DeepSeek V3, Qwen 3, Kimi K2, GPT-OSS.
- Predictor? Yes, analytical, but GPU. Quote: "We find LIMINAL is accurate when comparing to LLMs executing on existing hardware, achieving a mean absolute error of 7.6%."
- Bytes vs FLOPs? The model includes both terms and concludes bytes dominate: "This low arithmetic intensity quantifies that LLM serving will be memory bandwidth constrained." It does not score a FLOPs-only competitor.
- CPU, llama.cpp, GGUF, quantisation? None of these terms appear in the content retrieved.
- Frozen constant across machines? No: a per-layer exposed-latency constant is least-squares fitted to H100 data (about 114 microseconds per summariser; number unverified). No transfer to other machines.
- Overlap: supports the premise (bytes-bound decode, MAPE-style validation) but narrows nothing in our CPU-only, frozen-eta, cross-machine design. Cite as GPU analogue.

## Fresh search, Sept-Nov 2026 (CPU-only decode predictors)
Queries in landscape P1 section. Nothing new answers the question. Items:
- [anon2026armgemv] llama.cpp issue 25976: Neoverse-N2, 754B MoE; quantised decode at roughly 30-63% of STREAM depending on quant. Quote: "so decode here is compute-bound, not memory-bound". Anecdotal, MoE and server Arm, but it supports the risk that tok/s ratios across quants do not follow byte ratios on ARM. Our Pi host may show this; pre-register how it is reported.
- [malakhov2025cpuonly] measurement only, no predictor.
- Already known: Qiu 2609.14864 stays the near neighbour (AMBER already raised).

## Unreached or unconfirmed
- Na et al. venue/DOI/pages: https://ieeexplore.ieee.org/document/10763564 (human, IEEE Xplore access, to confirm IISWC 2024 and read PDF figures on decode scaling).
