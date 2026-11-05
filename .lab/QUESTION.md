# Research question
On commodity CPUs without a GPU, is the token-generation rate of small open language models predicted by the bytes that must be moved per generated token divided by measured memory bandwidth (a "bytes per word" law), rather than by arithmetic FLOPs, across model sizes, quantisation levels and machines?

Author (accountable): Clement Aidoo, CANLABS · Recorded: 2026-11-05 · Class: standard
Context: Follows the CANLABS frugal-AI thesis and the GPU-less AI direction (memory wall as the scaling law for edge AI, narrowed to
"bytes per word"). Hardware available to the author: laptop with AMD Ryzen 5 5500U, 8 GB DDR4-3200 dual channel; iPhone; a Raspberry
Pi to be borrowed. Cloud workspace CPU (2-vCPU Xeon, 7 GB) usable for development runs only.
