# Held-out confirmation set: definition only (no data before G2)

Authoritative definition: PROTOCOL.md, Appendix H (frozen at G1). This README is a verbatim copy of that appendix.
Nothing else may exist in this directory before gate G2 is approved.

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
