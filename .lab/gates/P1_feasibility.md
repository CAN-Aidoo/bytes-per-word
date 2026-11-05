# Feasibility sign-off: PROTOCOL.md sections 3, 6, 8 (research-director, technical-note class, 2026-11-05)

In a technical note the Director gives the lead feasibility review (no separate experiment-lead or hardware-lead instance; budget
12 instances, 7 used). Reviewed against `hardware/HOSTS.md` and the facts verified this phase.

| Item | Verdict | Evidence or condition |
|---|---|---|
| llama.cpp pin `b12129` / `3259ab6e…` | PASS | `git ls-remote` and a sparse clone at the tag (Director, 2026-11-05) |
| llama.cpp licence | PASS | `LICENSE` at the pinned commit: "MIT License" (PROTOCOL §8 updated) |
| CPU-only build, both hosts | PASS | CMake options sourced from the pinned `ggml/CMakeLists.txt`; V1-V2 verify |
| Host B capacity (8 GB RAM, ~28 GB disk) | PASS | largest grid file 4.28 GB (Qwen3-4B Q8_0); Q6_K 4B held-out file fits |
| Host B stability across sessions | PASS with amendment | ephemeral container: per-session host-facts re-check added to §3.1; push after every session |
| Host A operating system | PASS (resolved 2026-11-05) | native Windows for all Host A scored, host-constant and validation measurements; WSL excluded (PROTOCOL §3.1, §3.8, §10 item 2). |
| Host A disk | PASS (author-stated, 2026-11-05) | 13.4 GB free: enough for the grid (≥ 7 GB needed); HA4 (≥ 12 GB rule) runs only if free space measured at session start is ≥ 12 GB (PROTOCOL §10 item 2). |
| Host A RAM fit (Qwen3-4B Q8_0 needs ~5.3 GiB available) | PASS (conditional) | §3.5 rule 2 (fresh boot, DNF if it does not fit, never scored) handles it honestly |
| Host A probe (cross-host discrimination input) | PASS with caveat (2026-11-05) | 5 runs, native Windows, mains (`results/pilot/host_laptop_run1..5.json`, `hardware/HOSTS.md`); pilot spread is large (matmul ~29%), binding constants come after G1; indicative ρ ≈ 0.47-0.64 |
| Model licences Qwen3-0.6B, SmolLM2-360M | PASS (2026-11-05) | read in the browser: both "apache-2.0"; Qwen3-0.6B repo has no Q4_K_M (made with `llama-quantize`, PROTOCOL §3.5); SmolLM2-360M GGUF repo lists Q8_0 386 MB |
| Validation checks V1-V11 runnable | PASS | all on Linux with standard tools; V6 uses the derived 51.2 GB/s peak |
| Time and money (§8) | PASS | Host A ≤ 3 sessions of ≤ 3 h; no paid compute |
| Safety (§8) | PASS | laptop thermal stop rule at 90 °C; no electrical modification |
| Remote repository for the project | PASS (2026-11-05) | `github.com/CAN-Aidoo/bytes-per-word` exists and holds the protocol (push b6a6fa2) |

Verdict: **feasible for G1; the five former OPEN items are closed (2026-11-05).** No section needs redesign.
Signed: research-director, 2026-11-05.
