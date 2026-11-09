"""Planned grid cells and their static eligibility, from GGUF metadata only (PROTOCOL 3.5, 5.4; no tok/s is ever read).

Usage:
    GGUF_PY=<llama.cpp>/gguf-py python cells.py --gguf-dir <dir with Qwen3-<size>-<quant>.gguf files> [--out experiments/CELLS_plan.csv]

For each of the 8 grid files (3 sizes x 3 quants minus Qwen3-4B F16, rule 3) and each host it computes W_read, KV, D, P_active
with analysis/bytes_per_token.py (PROTOCOL 4.2), then applies
  rule 1  W_read >= multiple x LLC_h   (Host A: 4 x 8 MiB = 32 MiB; Host B: 8 x 260 MiB = 2080 MiB, 2026-11-09 Deviations entry)
  rule 3  Qwen3-4B F16 is excluded a priori
and reports rule 2 (RAM fit: available >= file + KV + 1.0 GiB) only as the number of bytes needed, because rule 2 is decided at
block start from psutil's available memory and a cell that fails it is recorded DNF at run time, not here.
It then reports the PROTOCOL 5.4 drop condition (fewer than 5 files eligible on both hosts) and the Q2 pair count per host.

A file that is not in --gguf-dir is listed with status "no_gguf" and nothing is estimated for it; if any file is missing the
summary says the Q3/Q2 counts are undetermined. Deterministic. Reads files; writes only --out. Never edits PROTOCOL.

Output is experiments/CELLS_plan.csv by default, not CELLS.csv: grid_hostA.py appends one row per executed cell to CELLS.csv, and
the two must not be mixed.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "analysis"))

if "GGUF_PY" not in os.environ:
    for cand in (os.path.expanduser("~/hostB-work/llama.cpp/gguf-py"),):
        if os.path.isdir(cand):
            os.environ["GGUF_PY"] = cand

MIB = 2**20
MARGIN_BYTES = 2**30  # rule 2 margin, 1.0 GiB
# Host constants. Host B multiple is 8 after the 2026-11-09 V5 entry (B1 at 4 x LLC exceeded 8 x LLC by 5.04%).
HOSTS = {"A": {"llc_bytes": 8 * MIB, "multiple": 4}, "B": {"llc_bytes": 260 * MIB, "multiple": 8}}
GRID = [("Qwen3-0.6B", "Q4_K_M"), ("Qwen3-0.6B", "Q8_0"), ("Qwen3-0.6B", "F16"),
        ("Qwen3-1.7B", "Q4_K_M"), ("Qwen3-1.7B", "Q8_0"), ("Qwen3-1.7B", "F16"),
        ("Qwen3-4B", "Q4_K_M"), ("Qwen3-4B", "Q8_0")]  # 4B F16 excluded a priori (rule 3), not listed
EXCLUDED_RULE3 = [("Qwen3-4B", "F16")]
COLS = ["cell", "host", "model", "quant", "file", "status", "file_bytes", "W_read_bytes", "KV_bytes", "D_bytes", "P_active",
        "llc_bytes", "multiple", "rule1_threshold_bytes", "rule1_eligible", "rule3_excluded", "rule2_need_bytes", "computed_utc"]


def gguf_path(d, model, quant):
    return os.path.join(d, f"{model}-{quant}.gguf")


def plan(gguf_dir, compute=None):
    if compute is None:
        import bytes_per_token

        compute = bytes_per_token.compute
    facts = {}
    for m, q in GRID:
        p = gguf_path(gguf_dir, m, q)
        facts[(m, q)] = dict(compute(p), file_bytes=os.path.getsize(p)) if os.path.isfile(p) else None
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for host, h in HOSTS.items():
        thr = h["multiple"] * h["llc_bytes"]
        for m, q in GRID + EXCLUDED_RULE3:
            row = {"cell": f"{host}_{m}_{q}_d0", "host": host, "model": m, "quant": q, "file": f"{m}-{q}.gguf",
                   "llc_bytes": h["llc_bytes"], "multiple": h["multiple"], "rule1_threshold_bytes": thr,
                   "rule3_excluded": (m, q) in EXCLUDED_RULE3, "computed_utc": now}
            f = facts.get((m, q))
            if (m, q) in EXCLUDED_RULE3:
                row.update(status="excluded_rule3", rule1_eligible=False)
            elif f is None:
                row.update(status="no_gguf", rule1_eligible="")
            else:
                row.update(status="computed", file_bytes=f["file_bytes"], W_read_bytes=f["W_read_bytes"], KV_bytes=f["KV_bytes"],
                           D_bytes=f["D_bytes"], P_active=f["P_active"], rule1_eligible=f["W_read_bytes"] >= thr,
                           rule2_need_bytes=int(f["file_bytes"] + f["KV_bytes"] + MARGIN_BYTES))
            rows.append(row)
    return rows


def summarise(rows):
    by = {(r["host"], r["model"], r["quant"]): r for r in rows}
    missing = sorted({(r["model"], r["quant"]) for r in rows if r["status"] == "no_gguf"})
    out = {"missing_gguf": [f"{m}-{q}" for m, q in missing]}
    for host in HOSTS:
        out[f"eligible_rule1_host{host}"] = [f"{m}-{q}" for m, q in GRID if by[(host, m, q)]["rule1_eligible"] is True]
    both = [f"{m}-{q}" for m, q in GRID if by[("A", m, q)]["rule1_eligible"] is True and by[("B", m, q)]["rule1_eligible"] is True]
    out["eligible_rule1_both_hosts"] = both
    # Q2 pairs: same size and host, lower-bit vs higher-bit (Q4_K_M:Q8_0 and Q8_0:F16), both cells eligible. 4B F16 never exists.
    for host in HOSTS:
        pairs = []
        for size in ("Qwen3-0.6B", "Qwen3-1.7B", "Qwen3-4B"):
            for a, b in (("Q4_K_M", "Q8_0"), ("Q8_0", "F16")):
                ra, rb = by.get((host, size, a)), by.get((host, size, b))
                if ra and rb and ra["rule1_eligible"] is True and rb["rule1_eligible"] is True:
                    pairs.append(f"{size} {a}:{b}")
        out[f"Q2_pairs_host{host}"] = pairs
    if missing:
        out["verdict"] = (f"UNDETERMINED: {len(missing)} of {len(GRID)} grid files not supplied, so the 5.4 'fewer than 5 files eligible on "
                          "both hosts' condition and the Q2 pair counts cannot be decided; nothing was estimated.")
    else:
        out["Q3_drop_by_5.4_metadata_condition"] = len(both) < 5
        out["note"] = ("Rule 1 only. Rule 2 (RAM fit) is decided at block start and DNF cells are not eligible evaluation cells "
                       "(2026-11-09 completeness entry), so the cells that actually count can be fewer than listed here.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf-dir", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "CELLS_plan.csv"))
    a = ap.parse_args(argv)
    rows = plan(a.gguf_dir)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(summarise(rows), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
