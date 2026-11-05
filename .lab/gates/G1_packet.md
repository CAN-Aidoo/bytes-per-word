# G1 Protocol frozen: Bytes per Word (technical note)
Date: 2026-11-05   Class: note (2 scored CPU hosts)   Budget used: 7/12 (+1 charter check)   Author of packet: research-director
Decision requested: **freeze `PROTOCOL.md`** (append-only after approval) so scored runs may begin in P2/P3.
Read first: `PROTOCOL.md` (§1 question, §3.3 benchmarks, §3.5 models, §4.3 calibration cell, §4.5 drop rule, §5 analysis, §6 validation, §10 review status,
Appendix H held-out set), `analysis/POWER.md` (statistician sign-off), `.lab/gates/P1_feasibility.md`, `lit/na2024_check.md`, `hardware/HOSTS.md`, this file.
Charter steward verdict: **APPROVE-FOR-HUMAN with conditions** (`.lab/gates/G1_charter.md`). Director's responses, 2026-11-05 (author's standing delegation to the team for decisions):
- V7 vs §5.4 contradiction: resolved after a statistician vs red-team debate; B1/F1 alone decides Q3; V7 failure labels the Q3 outcome "benchmark-dependent" (PROTOCOL §6 V7, §5.4); `analysis/POWER.md:131` edited, statistician re-confirmation pending (AMBER).
- Na et al.: accepted at moderate confidence (summary reads); limit recorded in PROTOCOL §10; author full read recommended before G3.
- Pilot wording (PROTOCOL §4.5), held-out wording (Appendix H and `heldout/README.md`, kept identical), stale header and licence text: fixed.
- `experiments/requirements.txt`: created (numpy 2.5.4, psutil 7.2.2, the versions measured on Host A).
- Still for the human: approve G1 and record the freeze commit by hand (no `/lab-gate` here).

## G0 condition check (verbatim list from `.lab/GATE_LOG.md`, G0 note item 4)
> G1 must fix MAPE threshold, excluded calibration cell, rule for dropping the cross-host test, two bandwidth benchmarks, heldout set, model licences and SHA-256.

| Item | Where fixed | Status |
|---|---|---|
| MAPE threshold (20%) | PROTOCOL §1 / §5.2 | fixed |
| Excluded calibration cell | PROTOCOL §4.3; never scored (Glossary) | fixed |
| Rule for dropping the cross-host test | PROTOCOL §4.5: kept iff \|ln ρ\| ≥ ln 1.5, ρ from post-G1 validation constants B1, F1 | fixed; **pilot ρ ≈ 0.47-0.64 (kept side, thin margin), not binding** |
| Two bandwidth benchmarks | PROTOCOL §3.3 (B1, B2) | fixed |
| Held-out set | PROTOCOL Appendix H; `heldout/README.md` identical copy; closed until G2 | fixed |
| Model licences | PROTOCOL §3.5/§3.6: Qwen3-0.6B and SmolLM2-360M apache-2.0, read in browser 2026-11-05; llama.cpp MIT (LICENSE at pinned commit) | fixed (Qwen3-1.7B and 4B rows sourced earlier, PROTOCOL §3.5 lines 151-152) |
| SHA-256 | PROTOCOL §3.5: hash on download, `experiments/MODELS.csv`; V3 checks; STREAM `stream.c` hash pinned | fixed as a procedure; per-file hashes recorded at download (none downloaded yet) |
| G0 condition 1 (Na et al., LIMINAL) | `lit/na2024_check.md`: DOES NOT ANSWER (Director confirmed) | done |
| G0 condition 3 (class) | 2 scored hosts, technical note | done |

## Review status
- Statistician: signed sections 4-5 (`analysis/POWER.md`, edits E1-E13 applied).
- Director feasibility: PASS for §3, §6, §8; all five human items closed (`.lab/gates/P1_feasibility.md` table needs its OPEN rows updated; see Open issues).
- Remote repository: `github.com/CAN-Aidoo/bytes-per-word`; last push b6a6fa2 contains the protocol as it stands (public timestamp before any scored result).
- Host A (native Windows, WSL excluded): pilot probe, 5 runs (run 1 cold-start outlier excluded from the median, judgement made after seeing it); spread of runs 2-5:
  copy ~7%, triad ~5%, matmul ~29% (Host B under 1%). Pilot only.

## Risks the human should weigh
1. Host A noise: the binding constants are measured in P2 under protocol V8/V9 rules; if Host A cannot meet the CV limits, the Q3 test or Host A is reported as failed, not tuned.
2. ρ margin: the cross-host test may be dropped by the §4.5 rule once the binding constants exist; the paper then reports a one-test result.
3. Power plan: Host A ran on Balanced; PROTOCOL §3.8 asks for the highest-performance mode; the human sets it for scored sessions.
4. Two hosts only; Host B is a labelled virtualised cloud VM.

## Open issues for the human before approving
1. Update `.lab/gates/P1_feasibility.md`: its OPEN rows (OS, disk, probe, licences, repository) are now resolved (see `PROTOCOL.md` §10, `hardware/HOSTS.md`).
2. `PROTOCOL.md` header says "Frozen at commit: <filled by gate.py>"; the gate tooling (`/lab-gate`) is not installed in this workspace. Record the commit hash in `.lab/GATE_LOG.md` by hand when approving.
3. Charter steward verdict is pending; do not approve before it is written.

## Decisions for the human
1. Approve G1 (freeze), or list edits.
2. Confirm that scored sessions on Host A use mains power, WSL shut down, and the highest-performance power mode.
3. Accept the technical-note class and plan of record (IEEE CAL or SEC 2027) unchanged from G0.
