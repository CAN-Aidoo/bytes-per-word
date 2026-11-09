# Decisions needed before the first scored grid run (Host A), 2026-11-09

Written by the research director while building `experiments/grid_hostA.py`. None of these looks at any tok/s value: no grid cell
has run. Each approved item is appended to PROTOCOL.md `## Deviations` as a dated entry (the protocol is append-only after G1).

## D1. Cool-down before each Host A round
- Protocol text: §3.8 (no temperature sensor) says "a fixed 120 s idle wait before each round"; §4.6 also gates on CPU < 5% over 5 s.
- What the scored calibration cell actually used (`experiments/cal_hostA.py`, 2026-11-09): the CPU < 5% gate only, no 120 s wait.
- Why it matters: η, η′ were frozen from that cell. Grid rounds measured under a different cool-down would differ systematically from
  the calibration conditions, which biases every Host A prediction.
- **Recommended:** the grid uses exactly the calibration procedure (CPU-quiet gate, max 300 s, then start and flag), and the 120 s wait
  is recorded as not applied to any Host A scored round, calibration included. The batch is built this way.
- Proposed entry: "- 2026-11-09 (Host A cool-down, P3; approved by the author in chat, transcribed by Claude): the §3.8 fixed 120 s
  idle wait was not applied in the scored calibration session; for consistency with the frozen η, η′, η′₂ every Host A grid round
  uses the same gate as the calibration cell (system CPU < 5% over 5 s, max 300 s, then start and flag). No result exists yet."

## D2. Does a RAM-fit DNF count against the 75% completeness rule?
- §3.5 lists RAM fit as eligibility rule 2 ("recorded as DNF, reported, and not scored"); §5.7 says Q1 is not evaluable if fewer than
  75% of a host's "planned eligible evaluation cells" complete. It does not say whether a DNF cell is "eligible".
- Forecast from the calibration session's own memory readings (max 4.06 GiB available, Claude app closed): Qwen3-1.7B F16 needs
  4.84 GiB and Qwen3-4B Q8_0 needs 5.03 GiB, so both are likely DNF unless a fresh restart frees more memory.
  If DNFs count as incomplete: 5 of 7 = 71% < 75%, so Host A Q1 becomes "not evaluable" and the positive claim is unreachable.
  If DNFs count as ineligible (rule 2 is an eligibility rule): 5 of 5 can complete.
- Q2 pair count either way (expected): Host A 3 pairs, Host B up to 3, total ≥ 5, so Q2 stays testable.
- **Recommended:** DNF cells are ineligible under rule 2 (they never produce a measurement, so they cannot bias Q1), every DNF is
  listed in every table, and the paper states that the largest files did not fit Host A's 8 GB. Decided now, before any data.
- Proposed entry: "- 2026-11-09 (completeness rule, P3; approved by the author in chat, transcribed by Claude): a cell recorded as DNF
  under §3.5 rule 2 after a fresh restart is not an eligible evaluation cell for §5.7's 75% completeness rule; DNF cells are reported in
  every table. Decided before any grid cell ran; forecast from calibration-session memory readings: 1.7B F16 and 4B Q8_0 likely DNF."

## D3. Exact Host A file order
- §4.6: "file order is a random permutation (seed 20261105)". The list being permuted was not written down.
- Implemented: `numpy.random.default_rng(20261105).permutation(8)` applied to the 8 grid files in the §3.5 canonical order
  (0.6B, 1.7B, 4B × Q4_K_M, Q8_0, F16, minus 4B F16), then the calibration file removed. Resulting order:
  4B Q8_0, 0.6B Q8_0, 0.6B Q4_K_M, 0.6B F16, 4B Q4_K_M, 1.7B Q4_K_M, 1.7B F16.
- Proposed entry: "- 2026-11-09 (Host A file order, P3; clarification, no result exists): the §4.6 permutation is applied to the 8 grid
  files in §3.5 canonical order with the calibration file removed afterwards; order recorded in every session file."

## D4. Excluded-round repeats when disk is short
- §5.7 repeats excluded rounds "at the end of the session". Host A's 13.4 GB disk cannot always keep every file with an excluded round
  until then. Implemented: files are kept for the end-of-session repeat; only if the next download would not fit are the pending repeats
  run early (logged); a repeat whose file was deleted in an earlier session is run at the start of the next session after re-download
  and a hash check.

## D5. Statistician note (2026-11-09 re-confirmation of POWER.md:131), needed before V7 is evaluated, not before the Host A grid
The statistician's section at the end of `analysis/POWER.md` contains a proposed dated deviation tying V7's "no cross-machine claim in
either direction" to the §9 claim templates. To be appended before any Q3 analysis.
