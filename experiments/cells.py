"""Planned grid cells and their static eligibility, from GGUF metadata only (PROTOCOL 3.5, 5.4; no tok/s is ever read).

Usage:
    GGUF_PY=<llama.cpp>/gguf-py python cells.py --gguf-dir <dir with Qwen3-<size>-<quant>.gguf files> [--out experiments/CELLS_plan.csv]
    python cells.py --use-recorded [--gguf-dir <dir>]      # no GGUF files needed for the files already measured on Host A

--use-recorded takes W_read, KV, D and P_active that were already computed from a real GGUF tensor table on Host A: the rows of
experiments/CELLS.csv (written by grid_hostA.py) and the calibration inputs of results/frozen_constants.json. W_read is a property of
the file, not of the host, so it applies to both hosts. A GGUF file in --gguf-dir, when present, takes precedence.

For each of the 8 grid files (3 sizes x 3 quants minus Qwen3-4B F16, rule 3) and each host it computes W_read, KV, D, P_active
with analysis/bytes_per_token.py (PROTOCOL 4.2), then applies
  rule 1  W_read >= multiple x LLC_h   (Host A: 4 x 8 MiB = 32 MiB; Host B: 8 x 260 MiB = 2080 MiB, 2026-11-09 Deviations entry)
  rule 3  Qwen3-4B F16 is excluded a priori
and reports rule 2 (RAM fit: available >= file + KV + 1.0 GiB) only as the number of bytes needed, because rule 2 is decided at
block start from psutil's available memory and a cell that fails it is recorded DNF at run time, not here.
It then reports the PROTOCOL 5.4 drop condition (fewer than 5 files eligible on both hosts) and the Q2 pair count per host.

A file with neither a GGUF nor a recorded row is listed with status "no_gguf" and nothing is estimated for it. Its eligibility is
unknown; the summary then gives the smallest and largest number each count can take, and says "undetermined" only when the
PROTOCOL threshold lies between them. Deterministic. Reads files; writes only --out. Never edits PROTOCOL.

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
COLS = ["cell", "host", "model", "quant", "file", "status", "source", "file_bytes", "W_read_bytes", "KV_bytes", "D_bytes", "P_active",
        "llc_bytes", "multiple", "rule1_threshold_bytes", "rule1_eligible", "rule3_excluded", "rule2_need_bytes", "computed_utc"]


def gguf_path(d, model, quant):
    return os.path.join(d, f"{model}-{quant}.gguf")


def split_name(fname):
    """'Qwen3-0.6B-Q4_K_M.gguf' -> ('Qwen3-0.6B', 'Q4_K_M'); quant names contain no '-'."""
    model, _, quant = fname[:-len(".gguf")].rpartition("-")
    return model, quant


def load_recorded(cells_csv, frozen_json):
    """W_read etc. already computed on Host A from real tensor tables: CELLS.csv rows and the frozen calibration inputs."""
    out = {}

    def put(key, facts, source):
        old = out.get(key)
        if old and old["W_read_bytes"] != facts["W_read_bytes"]:
            raise SystemExit(f"{key}: conflicting recorded W_read ({old['W_read_bytes']} from {old['source']}, "
                             f"{facts['W_read_bytes']} from {source})")
        out[key] = dict(facts, source=source)

    if cells_csv and os.path.isfile(cells_csv):
        with open(cells_csv, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("file", "").endswith(".gguf") and r.get("W_read_bytes"):
                    put(split_name(r["file"]), {"W_read_bytes": int(float(r["W_read_bytes"])), "KV_bytes": float(r["KV_bytes"]),
                                                "D_bytes": float(r["D_bytes"]), "P_active": int(float(r["P_active"]))},
                        "recorded:" + os.path.basename(cells_csv))
    if frozen_json and os.path.isfile(frozen_json):
        inp = json.load(open(frozen_json)).get("inputs", {})
        if inp.get("model_file", "").endswith(".gguf") and "W_read_bytes" in inp:
            put(split_name(inp["model_file"]), {"W_read_bytes": int(inp["W_read_bytes"]), "KV_bytes": float(inp["KV_bytes"]),
                                                "D_bytes": float(inp["D_cal_bytes"]), "P_active": int(inp["P_active_cal"])},
                "recorded:" + os.path.basename(frozen_json))
    return out


def plan(gguf_dir, compute=None, recorded=None):
    recorded = recorded or {}
    facts = {}
    for m, q in GRID:
        p = gguf_path(gguf_dir, m, q) if gguf_dir else None
        if p and os.path.isfile(p):
            if compute is None:
                import bytes_per_token

                compute = bytes_per_token.compute
            facts[(m, q)] = dict(compute(p), file_bytes=os.path.getsize(p), source="gguf")
        else:
            facts[(m, q)] = recorded.get((m, q))
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
                row.update(status="no_gguf", source="none", rule1_eligible="")
            else:
                row.update(status="computed", source=f["source"], W_read_bytes=f["W_read_bytes"], KV_bytes=f["KV_bytes"],
                           D_bytes=f["D_bytes"], P_active=f["P_active"], rule1_eligible=f["W_read_bytes"] >= thr)
                if f.get("file_bytes") is not None:  # rule 2 needs the file size, which a recorded row does not carry
                    row.update(file_bytes=f["file_bytes"], rule2_need_bytes=int(f["file_bytes"] + f["KV_bytes"] + MARGIN_BYTES))
            rows.append(row)
    return rows


def summarise(rows):
    """Eligibility is True, False or unknown (a file with no GGUF and no recorded row). Counts are reported as a certain minimum and
    a possible maximum; a PROTOCOL condition is decided only when its threshold is on one side of the whole range."""
    by = {(r["host"], r["model"], r["quant"]): r for r in rows}
    e = lambda host, m, q: {True: True, False: False}.get(by[(host, m, q)]["rule1_eligible"])  # None = unknown
    missing = sorted({(r["model"], r["quant"]) for r in rows if r["status"] == "no_gguf"})
    out = {"unknown_files": [f"{m}-{q}" for m, q in missing]}
    for host in HOSTS:
        out[f"eligible_rule1_host{host}"] = [f"{m}-{q}" for m, q in GRID if e(host, m, q) is True]
    both = [(m, q) for m, q in GRID if e("A", m, q) is True and e("B", m, q) is True]
    both_max = [(m, q) for m, q in GRID if e("A", m, q) is not False and e("B", m, q) is not False]
    out["eligible_rule1_both_hosts"] = [f"{m}-{q}" for m, q in both]
    out["both_hosts_count_range"] = [len(both), len(both_max)]
    # Q2 pairs: same size and host, lower-bit vs higher-bit (Q4_K_M:Q8_0 and Q8_0:F16), both cells eligible. 4B F16 never exists.
    total_min = total_max = 0
    for host in HOSTS:
        sure, possible = [], []
        for size in ("Qwen3-0.6B", "Qwen3-1.7B", "Qwen3-4B"):
            for a, b in (("Q4_K_M", "Q8_0"), ("Q8_0", "F16")):
                if (host, size, a) not in by or (host, size, b) not in by:
                    continue
                ea, eb = e(host, size, a), e(host, size, b)
                if ea is True and eb is True:
                    sure.append(f"{size} {a}:{b}")
                if ea is not False and eb is not False:
                    possible.append(f"{size} {a}:{b}")
        out[f"Q2_pairs_host{host}"] = sure
        out[f"Q2_pairs_host{host}_possible"] = [x for x in possible if x not in sure]
        total_min += len(sure)
        total_max += len(possible)
    out["Q2_pairs_total_range"] = [total_min, total_max]

    def decide(rng, need):
        return "yes" if rng[1] < need else "no" if rng[0] >= need else "undetermined"

    out["Q3_dropped_by_5.4_fewer_than_5_files_eligible_on_both_hosts"] = decide(out["both_hosts_count_range"], 5)
    q2 = decide(out["Q2_pairs_total_range"], 5)
    out["Q2_fewer_than_5_pairs_5.4"] = q2
    out["note"] = ("Rule 1 only. Rule 2 (RAM fit) is decided at block start and DNF cells are not eligible evaluation cells "
                   "(2026-11-09 completeness entry), so the cells that actually count can be fewer than listed here.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf-dir", help="folder with Qwen3-<size>-<quant>.gguf files (optional with --use-recorded)")
    ap.add_argument("--use-recorded", action="store_true",
                    help="also use W_read already recorded on Host A in experiments/CELLS.csv and results/frozen_constants.json")
    ap.add_argument("--cells-csv", default=os.path.join(HERE, "CELLS.csv"))
    ap.add_argument("--frozen", default=os.path.join(HERE, "..", "results", "frozen_constants.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "CELLS_plan.csv"))
    a = ap.parse_args(argv)
    if not (a.gguf_dir or a.use_recorded):
        ap.error("give --gguf-dir, --use-recorded, or both")
    rows = plan(a.gguf_dir, recorded=load_recorded(a.cells_csv, a.frozen) if a.use_recorded else None)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(summarise(rows), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
