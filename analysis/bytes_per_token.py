"""Bytes per token D and active parameters P_active from a GGUF tensor table (PROTOCOL 4.2).

W_read  = sum over tensors of n_bytes(t) = n_elements / block_size * type_size (gguf-py GGML_QUANT_SIZES), except token_embd.weight:
          if a separate output.weight exists (untied) it contributes one row (n_bytes / n_vocab); otherwise its full n_bytes.
          1-D norm tensors count in full.
KV(d)   = n_layer * 2 * n_head_kv * head_dim * d * s_kv, s_kv = 2 bytes (f16 cache), d = depth + n_gen / 2 (64 for depth 0, tg128).
D       = W_read + KV(d).
P_active = sum of n_elements of every 2-D weight tensor multiplied per token (all blk.* matrices and the output matrix);
          an untied token_embd (a gather) and all 1-D tensors are excluded.

gguf-py is read from the pinned llama.cpp tree (commit 3259ab6e5dd86fad1931962d784702cb53c7877b): set GGUF_PY to its gguf-py folder,
default is the Host A checkout. Deterministic, no randomness.

  python bytes_per_token.py <file.gguf> [--depth 0] [--n-gen 128]
"""
import argparse
import json
import os
import sys

GGUF_PY = os.environ.get("GGUF_PY", r"C:\Users\Clement Nana Aidoo\llama.cpp-b12129\gguf-py")
S_KV = 2


def _field(reader, name):
    f = reader.fields[name]
    return f.contents() if hasattr(f, "contents") else f.parts[f.data[0]].tolist()[0]


def compute(path, depth=0, n_gen=128):
    sys.path.insert(0, GGUF_PY)
    from gguf import GGUFReader
    from gguf.constants import GGML_QUANT_SIZES

    r = GGUFReader(path)
    arch = _field(r, "general.architecture")
    n_layer = int(_field(r, f"{arch}.block_count"))
    n_head_kv = int(_field(r, f"{arch}.attention.head_count_kv"))
    try:
        head_dim = int(_field(r, f"{arch}.attention.key_length"))
    except KeyError:
        head_dim = int(_field(r, f"{arch}.embedding_length")) // int(_field(r, f"{arch}.attention.head_count"))

    untied = any(t.name == "output.weight" for t in r.tensors)
    w_read = 0
    p_active = 0
    for t in r.tensors:
        n_el = int(t.n_elements)
        block, size = GGML_QUANT_SIZES[t.tensor_type]
        nbytes = n_el // block * size
        if t.name == "token_embd.weight":
            if untied:
                nbytes = nbytes // int(t.shape[1])  # one row: n_bytes / n_vocab
        w_read += nbytes
        if len(t.shape) == 2:
            if t.name == "token_embd.weight" and untied:
                continue
            p_active += n_el
    dbar = depth + n_gen / 2
    kv = n_layer * 2 * n_head_kv * head_dim * dbar * S_KV
    return {"file": os.path.basename(path), "arch": arch, "n_layer": n_layer, "n_head_kv": n_head_kv, "head_dim": head_dim,
            "untied_output": untied, "d_bar": dbar, "W_read_bytes": w_read, "KV_bytes": kv, "D_bytes": w_read + kv,
            "P_active": p_active}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--depth", type=int, default=0)
    ap.add_argument("--n-gen", type=int, default=128)
    a = ap.parse_args()
    print(json.dumps(compute(a.file, a.depth, a.n_gen), indent=1))
