# Hosts (P1, written by research-director for task T7; 2026-11-05)

Two CPU hosts (technical-note class, G0 condition 3; no Raspberry Pi available). Scored runs only after G1.

| | Host A: author's laptop | Host B: cloud workspace VM |
|---|---|---|
| CPU | AMD Ryzen 5 5500U: 6 cores / 12 threads, Zen 2, 2.1 GHz base / 4.0 GHz boost, L2 3 MiB, L3 8 MiB, AVX2 (no AVX-512), 15 W TDP [SOURCED: WikiChip, en.wikichip.org/wiki/amd/ryzen_5/5500u, accessed 2026-11-05] | Intel Xeon, family 6 model 207 (Emerald Rapids class), 2 vCPUs, 1 thread/core, L2 4 MiB, L3 260 MiB, AVX-512 (VNNI, BF16, FP16), AMX (bf16, int8) [MEASURED: lscpu, /proc/cpuinfo] |
| Memory | 8 GB DDR4-3200, dual channel, both slots used [author-stated]. Theoretical peak 2 ch x 8 B x 3200 MT/s = 51.2 GB/s [derived] | ~8 GB visible to the VM; memory type and channels not visible to the guest [UNVERIFIED] |
| Virtualisation | none (bare metal) | KVM, full virtualisation, shared host [MEASURED: lscpu]; no frequency governor exposed |
| Storage | 238 GB, mostly full [author-stated]: one model file at a time | 252 GB disk, ~28 GB free [MEASURED: df] |
| Who runs | the human, with scripts we supply | agents (after G1 only for models) |

## Pilot probe (development only; not scored) — `hardware/host_probe.py`
NumPy, single process, arrays of 1040 MiB (= 4 x LLC for Host B), 5 timed repetitions after 1 warm-up, two independent runs:

| Host | Copy GB/s (median) | Triad GB/s (median) | FP32 matmul GFLOP/s (median) | FLOP/byte (matmul / copy) | Files |
|---|---|---|---|---|---|
| B (Xeon VM) run 1 | 16.7 | 11.5 | 146.6 | 8.76 | `results/pilot/host_xeon_run1.json` |
| B (Xeon VM) run 2 | 16.8 | 11.9 | 147.1 | 8.77 | `results/pilot/host_xeon_run2.json` |
| A (laptop, native Windows) | **pending: human runs the probe** | | | | |

Run-to-run spread on Host B is under 1% for all three quantities.

## Discrimination check (G0 condition 4, "rule for dropping the cross-host test")
The cross-machine ratio test separates the bytes predictor from the FLOPs predictor only if the hosts' bandwidth ratio and FLOP/s
ratio differ: if B_A/B_B ≈ F_A/F_B, both predictors predict the same cross-host speed ratio and the test is uninformative.
- Host B's FLOP/s come from AVX-512/AMX on 2 vCPUs; Host A has 6 Zen 2 cores with AVX2 only and bare-metal DDR4. Whether the ratios
  differ enough cannot be decided until Host A is probed. **Blocking item for G1.**
- The numeric drop rule itself (threshold on the ratio of ratios) is set in PROTOCOL.md by the protocol architect and statistician,
  before Host A's numbers are seen by anyone writing the protocol, so the rule is not tuned to the data.

## DRAM-residency rule input
Host B's L3 is 260 MiB. Any model whose weights are not several times larger than 260 MiB may be partly cache-resident on Host B,
which would violate the approved question's "DRAM-resident" condition. PROTOCOL.md sets the minimum multiple.

## Probe instructions for the human (Host A, native Windows; decided 2026-11-05, WSL excluded)
Host A's Ubuntu is WSL (`systemd-detect-virt` = wsl), which is virtualised, so all Host A measurements run in **native Windows**.
1. Get the repository onto the Windows drive (WSL already has git; it asks for your GitHub login, use a personal access token):
   in the WSL Ubuntu terminal: `git clone https://github.com/CAN-Aidoo/bytes-per-word "/mnt/c/Users/Clement Nana Aidoo/bytes-per-word"`
2. Close WSL (`wsl --shutdown` in Windows Command Prompt), plug into mains, close other programs.
3. In Windows Command Prompt:
```
cd "C:\Users\Clement Nana Aidoo\bytes-per-word"
py -m pip install numpy psutil
py hardware\host_probe.py --out results\pilot\host_laptop_run1.json --llc-mib 8
py hardware\host_probe.py --out results\pilot\host_laptop_run2.json --llc-mib 8
```
4. Commit and push from WSL (`cd "/mnt/c/Users/Clement Nana Aidoo/bytes-per-word" && git add results/pilot && git commit -m "Pilot: laptop host probe (Windows)" && git push`), or paste the two JSON outputs.
pip NumPy wheels bundle OpenBLAS; do not use WSL's apt NumPy (reference BLAS) for anything.
