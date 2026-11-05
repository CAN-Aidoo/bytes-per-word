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
| Host A operating system | **OPEN (human)** | scripts assume Linux (§3.1). If Host A runs Windows: options are a Linux live USB/dual boot (preferred: bare metal kept) or a Windows-port amendment before G1. WSL2 is not acceptable for scored runs (virtualised memory path would remove Host A's bare-metal role). |
| Host A disk | **OPEN (human)** | needs ≥ 7 GB free for grid runs (largest file 4.28 GB + build ~1 GB + margin); ≥ 12 GB for held-out cell HA4 (resource rule already in Appendix H) |
| Host A RAM fit (Qwen3-4B Q8_0 needs ~5.3 GiB available) | PASS (conditional) | §3.5 rule 2 (fresh boot, DNF if it does not fit, never scored) handles it honestly |
| Host A probe (cross-host discrimination input) | **OPEN (human)** | `hardware/host_probe.py` twice; ρ rule fixed in §4.5 before the numbers exist |
| Model licences Qwen3-0.6B, SmolLM2-360M | **OPEN** | Hugging Face pages not reachable from this workspace (fetch needs approval; API blocked). Human to open the two links in §3.5/§3.6 and confirm "apache-2.0" and the available quants |
| Validation checks V1-V11 runnable | PASS | all on Linux with standard tools; V6 uses the derived 51.2 GB/s peak |
| Time and money (§8) | PASS | Host A ≤ 3 sessions of ≤ 3 h; no paid compute |
| Safety (§8) | PASS | laptop thermal stop rule at 90 °C; no electrical modification |
| Remote repository for the project | **OPEN (human)** | the project lives only in an ephemeral workspace; a GitHub repo (`CAN-Aidoo/bytes-per-word`) is needed before any scored run |

Verdict: **feasible for G1 once the five OPEN items are closed.** No section needs redesign.
Signed: research-director, 2026-11-05.
