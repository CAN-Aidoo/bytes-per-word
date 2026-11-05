# Research question
On commodity CPUs without a GPU, is the token-generation rate of small open language models predicted by the bytes that must be moved per generated token divided by measured memory bandwidth (a "bytes per word" law), rather than by arithmetic FLOPs, across model sizes, quantisation levels and machines?

Author (accountable): Clement Aidoo, CANLABS · Recorded: 2026-11-05 · Class: standard
Context: Follows the CANLABS frugal-AI thesis and the GPU-less AI direction (memory wall as the scaling law for edge AI, narrowed to
"bytes per word"). Hardware available to the author: laptop with AMD Ryzen 5 5500U, 8 GB DDR4-3200 dual channel; iPhone; a Raspberry
Pi to be borrowed. Cloud workspace CPU (2-vCPU Xeon, 7 GB) usable for development runs only.

- 2026-11-05: Author confirms no Raspberry Pi is available. Scored CPU hosts so far: Ryzen 5 5500U laptop; cloud 2-vCPU Xeon (labelled, virtualised). Per G0 condition 3, fewer than 3 hosts means technical-note class unless a third host is found.
- 2026-11-05: Author chose technical-note class (2 CPU hosts; G0 condition 3). Target: IEEE CAL 4-page letter (plan of record).
- 2026-11-05: Author: Host A has Windows and Ubuntu installed (boot mode, dual boot or WSL, to be confirmed); free disk reported 13.4 GB (partition to be confirmed). Project remote: github.com/CAN-Aidoo/bytes-per-word.
- 2026-11-05: Author ran `systemd-detect-virt` in the laptop's Ubuntu: output "wsl" (Ubuntu runs under WSL, not bare metal). WSL reports a 1007G virtual disk; real free space on the Windows drive is 13.4 GB (author-stated). Probe not yet run (the pasted commands stopped after apt installed python3-numpy). Note: Ubuntu's python3-numpy links the reference BLAS (libblas3), not OpenBLAS, so it must not be used for F1 (PROTOCOL §3.4 pins NumPy via pip in experiments/requirements.txt).
