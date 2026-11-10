"""Host A confirmatory grid, unattended (PROTOCOL 3.5-3.7, 4.6, 5.7; Host A rules of the 2026-11-08 fifth deviation entry).

What one session does, in order:
  0. Pre-flight: refuses to start on battery, with the Claude desktop app or WSL running, or with too little free disk.
     Records the session facts (power plan, free disk, available memory, CPU, mask, build commit).
  1. Opening sentinel (development model, 1 round). It is the reference for this session's 5% sentinel rule.
  2. For each Host A evaluation file in the frozen order (permutation seed 20261105, calibration file excluded), until the time
     budget is spent: obtain the file (download at a pinned revision, or llama-quantize for Qwen3-0.6B Q4_K_M), SHA-256 it and
     append it to experiments/MODELS.csv, compute D / P_active and V4 from the tensor table (experiments/CELLS.csv), apply the RAM
     fit rule (rule 2: available >= file + KV + 1.0 GiB, else DNF), then run the block: 5 rounds, one look at the precision rule
     (h <= 2.0% of the mean, else 3 more rounds, max 8), then a sentinel. Each round is one fresh llama-bench with exactly the
     calibration flags (imported from cal_hostA.py). The file is deleted after its block (disk), except when still needed.
  3. End of session: rounds excluded under 5.7 (left mains, available memory < 1.0 GiB) are repeated once; blocks whose closing
     sentinel is > 5% from the opening sentinel are re-run once (re-obtaining the file if needed); a closing sentinel is taken.
State is kept in results/raw/A/state.json, so a later session resumes where this one stopped. Nothing is ever overwritten:
every block, sentinel and session is its own file. The script never reads tok/s to decide anything except the 5.7 rules,
the precision rule (variance only) and the sentinel rule, exactly as pre-registered.

Run (plain Command Prompt, Claude app closed, charger in):   py experiments\\grid_hostA.py --max-hours 3
Dry run (no downloads, no llama-bench, writes only to a temporary folder):   py experiments\\grid_hostA.py --dry-run
"""
import argparse
import csv
import datetime as dt
import hashlib
import http.client
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))

HOST = "A"
T_A = 6
SEED_ORDER = 20261105
ROUNDS = 5
EXTRA_ROUNDS = 3
PRECISION = 0.02
SENTINEL_LIMIT = 0.05
MARGIN_BYTES = 2**30  # 1.0 GiB, PROTOCOL 3.5 rule 2
LLC_A_BYTES = 8 * 2**20
RESIDENCY_MULTIPLE = 4  # rule 1 (Host A: every file passes; checked anyway)
ROUND_TIMEOUT_S = 30 * 60  # 5.7
DEV_FILE = "smollm2-360m-instruct-q8_0.gguf"
CAL = ("Qwen3-1.7B", "Q8_0")
# The confirmatory grid of PROTOCOL 3.5 in canonical order (size, then quant); 4B F16 is excluded a priori (rule 3).
GRID = [("Qwen3-0.6B", "Q4_K_M"), ("Qwen3-0.6B", "Q8_0"), ("Qwen3-0.6B", "F16"),
        ("Qwen3-1.7B", "Q4_K_M"), ("Qwen3-1.7B", "Q8_0"), ("Qwen3-1.7B", "F16"),
        ("Qwen3-4B", "Q4_K_M"), ("Qwen3-4B", "Q8_0")]
REPO = {"Qwen3-0.6B": "ggml-org/Qwen3-0.6B-GGUF", "Qwen3-1.7B": "ggml-org/Qwen3-1.7B-GGUF", "Qwen3-4B": "ggml-org/Qwen3-4B-GGUF"}
QUANTIZE_LOCAL = {("Qwen3-0.6B", "Q4_K_M")}  # not in the repo: made with llama-quantize from the F16 file (PROTOCOL 3.5)
T975 = {4: 2.776445105, 7: 2.364624252}  # t(0.975, n-1) for n = 5 and n = 8


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cell_id(model, quant):
    return f"A_{model}_{quant}_d0"


def frozen_order():
    """Evaluation files for Host A in the pre-registered order: permutation (seed 20261105) of GRID, calibration file removed."""
    import numpy as np

    perm = np.random.default_rng(SEED_ORDER).permutation(len(GRID))
    return [GRID[i] for i in perm if GRID[i] != CAL]


def precision_ok(values):
    n = len(values)
    if n < 2:
        return False, None
    m = statistics.mean(values)
    h = T975[n - 1] * statistics.stdev(values) / math.sqrt(n) if (n - 1) in T975 else None
    return (h is not None and h <= PRECISION * m), (None if h is None else h / m)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- files
class HF:
    """Pinned-revision access to Hugging Face. The revision of a repo is resolved once (or taken from MODELS.csv) and reused."""

    def __init__(self, state, models_csv):
        self.state = state
        self.pins = state.setdefault("revisions", {})
        if os.path.exists(models_csv):
            with open(models_csv, newline="") as f:
                for row in csv.DictReader(f):
                    if row["repo"].startswith("ggml-org/") and row.get("revision_commit"):
                        self.pins.setdefault(row["repo"], row["revision_commit"])

    def _get(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "canlabs-bytes-per-word/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def revision(self, repo):
        if repo not in self.pins:
            self.pins[repo] = self._get(f"https://huggingface.co/api/models/{repo}/revision/main")["sha"]
        return self.pins[repo]

    def listing(self, repo):
        rev = self.revision(repo)
        tree = self._get(f"https://huggingface.co/api/models/{repo}/tree/{rev}")
        return rev, {e["path"]: e for e in tree if e.get("type") == "file"}

    def find(self, repo, quant):
        rev, files = self.listing(repo)
        want = f"-{quant}.gguf".lower()
        hits = [p for p in files if p.lower().endswith(want) and not p.lower().endswith(f"-b{quant}.gguf".lower())]
        if len(hits) != 1:
            raise RuntimeError(f"{repo}@{rev}: expected one file ending {want}, found {hits}")
        e = files[hits[0]]
        return rev, hits[0], (e.get("lfs") or {}).get("oid"), e.get("size")

    base = "https://huggingface.co"

    def download(self, repo, rev, fname, dest, expected_sha=None, size=None, attempts=8):
        """Download to dest + '.part', resuming with an HTTP Range request after a network error, then check the SHA-256 against
        the Hugging Face LFS hash (V3). A stalled or dropped connection used to abort the whole session on the first error."""
        url = f"{self.base}/{repo}/resolve/{rev}/{fname}"
        part = dest + ".part"
        last = None
        for attempt in range(1, attempts + 1):
            have = os.path.getsize(part) if os.path.exists(part) else 0
            if size and have == size:
                break
            headers = {"User-Agent": "canlabs-bytes-per-word/1.0"}
            if have:
                headers["Range"] = f"bytes={have}-"
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
                    mode = "ab"
                    if have and r.status != 206:  # server ignored the Range header: start again from zero
                        mode = "wb"
                    with open(part, mode) as f:
                        for chunk in iter(lambda: r.read(1 << 22), b""):
                            f.write(chunk)
                if not size or os.path.getsize(part) == size:
                    break
                last = RuntimeError(f"got {os.path.getsize(part)} of {size} bytes")
            except (OSError, http.client.HTTPException) as e:  # TimeoutError, URLError and ConnectionError are OSError
                last = e
            if attempt < attempts:
                time.sleep(min(60, 5 * attempt))
        else:
            raise RuntimeError(f"download of {fname} failed after {attempts} attempts: {last!r}")
        digest = sha256(part)
        if expected_sha and digest != expected_sha:
            os.remove(part)
            raise RuntimeError(f"SHA-256 mismatch for {fname}: got {digest}, Hugging Face LFS says {expected_sha} (V3)")
        os.replace(part, dest)
        return digest


def tensor_facts(path):
    """D, P_active (PROTOCOL 4.2, via analysis/bytes_per_token.py) and V4's second clause (file size - all tensor bytes <= 1%)."""
    import bytes_per_token

    d = bytes_per_token.compute(path, depth=0, n_gen=128)
    sys.path.insert(0, bytes_per_token.GGUF_PY)
    from gguf import GGUFReader

    total = sum(int(t.n_bytes) for t in GGUFReader(path).tensors)
    size = os.path.getsize(path)
    d.update({"file_bytes": size, "all_tensor_bytes": total, "V4_outside_pct": 100.0 * (size - total) / size,
              "V4_pass": (size - total) / size <= 0.01})
    return d


# ---------------------------------------------------------------- rounds (identical measurement to cal_hostA.py)
def real_round(model_path):
    import cal_hostA

    pre, not_quiet = cal_hostA.wait_quiet()
    s = cal_hostA.Sampler()
    try:
        p = subprocess.run([cal_hostA.BENCH, "-m", model_path] + cal_hostA.FLAGS, capture_output=True, text=True,
                           timeout=ROUND_TIMEOUT_S)
        rc, out, err, timed_out = p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired as e:
        rc, out, err, timed_out = None, e.stdout or "", e.stderr or "", True
    mon = s.stop()
    post = cal_hostA.state()
    lines = [ln for ln in (out or "").splitlines() if ln.startswith("{")]
    if timed_out or rc != 0 or not lines:
        return {"failed": True, "timed_out": timed_out, "returncode": rc, "stderr_tail": (err or "")[-2000:], "pre": pre,
                "post": post, "monitor": mon}
    r = json.loads(lines[-1])
    flags = []
    if not mon["all_plugged"]:
        flags.append("left_mains")
    if mon["min_avail_gib"] is not None and mon["min_avail_gib"] < 1.0:
        flags.append("avail_below_1GiB")
    return {"failed": False, "value_toks": r["avg_ts"], "samples": r["samples_ts"], "pre": pre, "post": post, "monitor": mon,
            "start_flagged_not_quiet": not_quiet, "round_flags": flags, "returncode": rc, "backends": r.get("backends"),
            "build_commit": r.get("build_commit"), "cpu_mask": r.get("cpu_mask"), "cpu_strict": r.get("cpu_strict"),
            "n_threads": r.get("n_threads"), "time_utc": now()}


def run_round(runner, model_path, log):
    """One scored round with the 5.7 crash/timeout rule: retried once; two failures return None (cell failed)."""
    for attempt in (1, 2):
        r = runner(model_path)
        r["attempt"] = attempt
        if not r["failed"]:
            return r, None
        log(f"round failure (attempt {attempt}) on {os.path.basename(model_path)}: rc={r.get('returncode')} "
            f"timeout={r.get('timed_out')}")
        last = r
    return None, last


# ---------------------------------------------------------------- session
class Session:
    def __init__(self, a, runner, hf, hostfacts):
        self.a, self.runner, self.hf = a, runner, hf
        self.raw = os.path.join(a.results_dir, "raw", HOST)
        os.makedirs(os.path.join(self.raw, "sessions"), exist_ok=True)
        self.state_path = os.path.join(self.raw, "state.json")
        self.state = json.load(open(self.state_path)) if os.path.exists(self.state_path) else {"cells": {}, "sessions": []}
        if hf is not None:
            hf.state = self.state
            hf.pins = self.state.setdefault("revisions", hf.pins)
        self.sid = dt.datetime.now(dt.timezone.utc).strftime("S%Y%m%dT%H%M%SZ")
        self.t0 = time.time()
        self.facts = hostfacts
        self.events = []
        self.sentinels = []
        self.redo_rounds = []  # (cell_id, block_file, round_index)
        self.redo_blocks = []

    # -- bookkeeping
    def log(self, msg):
        line = f"{now()} {self.sid} {msg}"
        print(line, flush=True)
        self.events.append(line)
        with open(os.path.join(self.a.results_dir, "RUNLOG.md"), "a", encoding="utf-8") as f:
            f.write(f"- {line}\n")

    def save_state(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=1)
        os.replace(tmp, self.state_path)

    def write_json(self, rel, obj):
        path = os.path.join(self.raw, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            raise RuntimeError(f"refusing to overwrite {path}")
        with open(path, "w") as f:
            json.dump(obj, f, indent=1)
        return path

    def hours_left(self):
        return self.a.max_hours - (time.time() - self.t0) / 3600.0

    # -- sentinel
    def sentinel(self, tag):
        dev = os.path.join(self.a.models_dir, DEV_FILE)
        r, fail = run_round(self.runner, dev, self.log)
        rec = {"tag": tag, "session": self.sid, "round": r, "failure": fail}
        self.write_json(f"sentinels/{self.sid}_{len(self.sentinels):02d}_{tag}.json", rec)
        v = None if r is None else r["value_toks"]
        self.sentinels.append(v)
        ref = self.sentinels[0]
        dev_pct = None if (v is None or ref is None) else 100.0 * abs(v - ref) / ref
        self.log(f"sentinel {tag}: {v} tok/s (deviation from opening sentinel: {dev_pct})")
        return v, dev_pct

    # -- files
    def obtain(self, model, quant):
        """Return (path, models_csv_row). Reuses a file already on disk only if its SHA-256 still equals the recorded one (V3);
        otherwise downloads at the pinned revision, or quantizes locally (Qwen3-0.6B Q4_K_M, PROTOCOL 3.5). Each new file is
        appended to MODELS.csv exactly once."""
        dest = os.path.join(self.a.models_dir, f"{model}-{quant}.gguf")
        known = self.state.setdefault("files", {}).get(dest)
        if known and os.path.exists(dest):
            if sha256(dest) == known["sha256"]:
                return dest, known
            self.log(f"{os.path.basename(dest)}: on-disk hash differs from the recorded one; obtaining it again")
        if (model, quant) in QUANTIZE_LOCAL:
            src, src_row = self.obtain(model, "F16")
            out_tmp = dest + ".part"
            q = os.path.join(os.path.dirname(BENCH()), "llama-quantize.exe")
            self.log(f"llama-quantize {os.path.basename(src)} -> {os.path.basename(dest)} ({quant}, no imatrix)")
            p = subprocess.run([q, src, out_tmp, quant], capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"llama-quantize failed: {p.stderr[-1000:]}")
            os.replace(out_tmp, dest)
            row = {"model": model, "quant": quant, "repo": f"local: llama-quantize {quant} (no imatrix) of {src_row['filename']}",
                   "revision_commit": f"llama.cpp 3259ab6e; source sha256 {src_row['sha256']}", "filename": os.path.basename(dest),
                   "bytes": os.path.getsize(dest), "sha256": sha256(dest), "licence": "Apache-2.0", "downloaded_utc": now(),
                   "host": HOST}
        else:
            repo = REPO[model]
            rev, fname, lfs_sha, size = self.hf.find(repo, quant)
            self.check_disk(size or 0)
            self.log(f"download {repo}@{rev[:12]}/{fname} ({size} bytes)")
            digest = self.hf.download(repo, rev, fname, dest, expected_sha=lfs_sha, size=size)
            row = {"model": model, "quant": quant, "repo": repo, "revision_commit": rev, "filename": fname,
                   "bytes": os.path.getsize(dest), "sha256": digest, "licence": "Apache-2.0", "downloaded_utc": now(), "host": HOST}
            if lfs_sha is None:
                self.log(f"{fname}: Hugging Face listing gave no LFS hash; own SHA-256 recorded, cross-host check (V3) still applies")
        self.state["files"][dest] = row
        self.record_model(row)
        self.save_state()
        return dest, row

    def needed_later(self, path):
        """A file stays on disk while an unfinished cell in this session still needs it (Qwen3-0.6B F16 is the source of Q4_K_M)."""
        name = os.path.basename(path)
        for (m, q) in QUANTIZE_LOCAL:
            if name == f"{m}-F16.gguf" and self.state["cells"].get(cell_id(m, q), {}).get("status") not in ("complete", "failed", "DNF"):
                return True
            if name == f"{m}-F16.gguf" and self.state["cells"].get(cell_id(m, "F16"), {}).get("status") not in ("complete", "failed", "DNF"):
                return True
        return False

    def check_disk(self, need):
        free = shutil.disk_usage(self.a.models_dir).free
        if free < need + 2**30 and self.redo_rounds:
            self.log("disk is short: running the pending 5.7 round repeats now instead of at session end, to free the kept files")
            self.do_round_repeats()
            free = shutil.disk_usage(self.a.models_dir).free
        if free < need + 2**30:
            raise RuntimeError(f"not enough free disk on the model drive: {free} bytes free, {need + 2**30} needed")

    def record_model(self, row):
        path = self.a.models_csv
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["model", "quant", "repo", "revision_commit", "filename", "bytes", "sha256", "licence",
                                              "downloaded_utc", "host"])
            if new:
                w.writeheader()
            w.writerow(row)

    def record_cell_facts(self, cid, facts, eligible1):
        path = self.a.cells_csv
        new = not os.path.exists(path)
        cols = ["cell", "host", "file", "W_read_bytes", "KV_bytes", "D_bytes", "P_active", "llc_bytes", "rule1_threshold_bytes",
                "rule1_eligible", "V4_outside_pct", "V4_pass", "computed_utc"]
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if new:
                w.writeheader()
            w.writerow({"cell": cid, "host": HOST, "file": facts["file"], "W_read_bytes": facts["W_read_bytes"],
                        "KV_bytes": facts["KV_bytes"], "D_bytes": facts["D_bytes"], "P_active": facts["P_active"],
                        "llc_bytes": LLC_A_BYTES, "rule1_threshold_bytes": RESIDENCY_MULTIPLE * LLC_A_BYTES,
                        "rule1_eligible": eligible1, "V4_outside_pct": round(facts["V4_outside_pct"], 4),
                        "V4_pass": facts["V4_pass"], "computed_utc": now()})

    def remove(self, path):
        if self.needed_later(path):
            self.log(f"keeping {os.path.basename(path)}: a later cell still needs it")
            return
        try:
            os.remove(path)
            self.log(f"deleted {os.path.basename(path)} (hash and revision recorded, re-obtainable)")
        except OSError as e:
            self.log(f"could not delete {path}: {e}")

    # -- blocks
    def block(self, model, quant, path, facts, kind):
        cid = cell_id(model, quant)
        import psutil

        avail = psutil.virtual_memory().available if not self.a.dry_run else 10 * 2**30
        need = facts["file_bytes"] + facts["KV_bytes"] + MARGIN_BYTES
        if avail < need:
            rec = {"cell": cid, "session": self.sid, "status": "DNF", "available_bytes": avail, "needed_bytes": need,
                   "note": "PROTOCOL 3.5 rule 2 failed at block start; DNF is final only after a fresh restart with no other "
                           "user programs (re-run this file in a session started right after a restart)"}
            self.write_json(f"{cid}/{self.sid}_DNF.json", rec)
            self.log(f"{cid}: RAM fit failed ({avail} < {need} bytes): recorded DNF for this session")
            return "DNF", None
        rounds, failure = [], None
        n_target = ROUNDS
        while len(rounds) < n_target:
            r, fail = run_round(self.runner, path, self.log)
            if r is None:
                failure = fail
                break
            rounds.append(r)
            if len(rounds) == ROUNDS and n_target == ROUNDS:
                ok, rel = precision_ok([x["value_toks"] for x in rounds])
                if not ok:
                    n_target = ROUNDS + EXTRA_ROUNDS
                    self.log(f"{cid}: precision h/mean = {rel} > 2%: 3 more rounds (one look, max 8)")
        k = len([f for f in os.listdir(os.path.join(self.raw, cid))]) if os.path.isdir(os.path.join(self.raw, cid)) else 0
        sv, sdev = self.sentinel(f"after_{cid}")
        values = [x["value_toks"] for x in rounds]
        ok, rel = precision_ok(values)
        rec = {"cell": cid, "host": HOST, "session": self.sid, "kind": kind, "file": os.path.basename(path), "tensor_facts": facts,
               "rounds": rounds, "values": values, "mean_toks": statistics.mean(values) if values else None,
               "precision_h_over_mean": rel, "precision_met": ok, "imprecise": (len(values) >= ROUNDS and not ok),
               "failure": failure, "status": "failed" if failure else "complete",
               "opening_sentinel_toks": self.sentinels[0], "closing_sentinel_toks": sv, "sentinel_deviation_pct": sdev,
               "sentinel_flag": (sdev is not None and sdev > 100 * SENTINEL_LIMIT),
               "excluded_round_indices": [i for i, x in enumerate(rounds) if x["round_flags"]], "flags_cal_hostA": True}
        bfile = self.write_json(f"{cid}/{self.sid}_block{k:02d}_{kind}.json", rec)
        self.log(f"{cid}: {rec['status']}, {len(values)} rounds, mean {rec['mean_toks']}, h/mean {rel}, sentinel dev {sdev}%")
        for i in rec["excluded_round_indices"]:
            self.redo_rounds.append((cid, bfile, i, path))
        if rec["sentinel_flag"] and kind == "primary":
            self.redo_blocks.append((model, quant))
        return rec["status"], bfile

    def do_round_repeats(self):
        """PROTOCOL 5.7: each excluded round is repeated once; the repeat replaces it (a repeat that is flagged again is kept, flagged)."""
        pending, self.redo_rounds = self.redo_rounds, []
        for cid, bfile, i, path in pending:
            m, q = next(((m, q) for m, q in GRID if cell_id(m, q) == cid), (None, None))
            if not os.path.exists(path):
                path, _ = self.obtain(m, q)
            r, fail = run_round(self.runner, path, self.log)
            self.write_json(f"{cid}/{self.sid}_repeat_of_{os.path.basename(bfile)[:-5]}_r{i}.json",
                            {"cell": cid, "replaces_round": i, "of_block": os.path.basename(bfile), "round": r, "failure": fail,
                             "flagged_again": bool(r and r["round_flags"])})
            self.log(f"{cid}: round {i} of {os.path.basename(bfile)} repeated (flagged again: {bool(r and r['round_flags'])})")
            if (m, q) not in self.redo_blocks and not any(c == cid for c, _, _, _ in self.redo_rounds):
                self.remove(path)

    def run(self, order):
        todo = [x for x in order if self.state["cells"].get(cell_id(*x), {}).get("status") not in ("complete", "failed")]
        carried = self.state.pop("pending_round_repeats", [])
        if not todo and not carried:
            print("Nothing left to run on Host A: every evaluation cell is complete or failed.")
            return 0
        for cid, bfile, i in carried:
            m, q = next((m, q) for m, q in GRID if cell_id(m, q) == cid)
            self.redo_rounds.append((cid, bfile, i, os.path.join(self.a.models_dir, f"{m}-{q}.gguf")))
        self.state["sessions"].append({"id": self.sid, "start_utc": now(), "facts": self.facts})
        self.save_state()
        self.log(f"session start; order = {[cell_id(*x) for x in order]}; budget {self.a.max_hours} h")
        v0, _ = self.sentinel("opening")
        if v0 is None:
            self.log("opening sentinel failed twice: session stopped (nothing scored)")
            return 3
        for model, quant in order:
            cid = cell_id(model, quant)
            st = self.state["cells"].get(cid, {})
            if st.get("status") in ("complete", "failed"):
                continue
            if self.hours_left() < self.a.min_block_hours:
                self.log(f"time budget reached before {cid}: stopping; next session resumes here")
                break
            path, row = self.obtain(model, quant)
            facts = tensor_facts(path) if not self.a.dry_run else self.a.fake_facts(path)
            elig1 = facts["W_read_bytes"] >= RESIDENCY_MULTIPLE * LLC_A_BYTES
            self.record_cell_facts(cid, facts, elig1)
            if not facts["V4_pass"]:
                self.log(f"{cid}: V4 failed ({facts['V4_outside_pct']:.3f}% outside the tensor table): block still run, flagged")
            if not elig1:
                self.state["cells"][cid] = {"status": "ineligible_rule1"}
            else:
                status, bfile = self.block(model, quant, path, facts, "primary")
                self.state["cells"][cid] = {"status": status, "block": bfile, "session": self.sid, "sha256": row["sha256"]}
            self.save_state()
            if (model, quant) not in self.redo_blocks and not any(c == cid for c, _, _, _ in self.redo_rounds):
                self.remove(path)
        for dest in list(self.state.get("files", {})):  # sources kept for a cell that has now finished
            if os.path.exists(dest) and not self.needed_later(dest) and os.path.basename(dest) != DEV_FILE \
                    and all((m, q) not in self.redo_blocks for m, q in GRID if dest.endswith(f"{m}-{q}.gguf")) \
                    and not any(p == dest for _, _, _, p in self.redo_rounds):
                self.remove(dest)
        # end of session: repeated rounds (5.7), then sentinel re-runs (4.6)
        self.do_round_repeats()
        for model, quant in self.redo_blocks:
            cid = cell_id(model, quant)
            path = os.path.join(self.a.models_dir, f"{model}-{quant}.gguf")
            path, row = self.obtain(model, quant)
            facts = tensor_facts(path) if not self.a.dry_run else self.a.fake_facts(path)
            self.log(f"{cid}: sentinel-flagged block re-run (PROTOCOL 4.6, 5.7)")
            self.block(model, quant, path, facts, "sentinel_rerun")
            self.remove(path)
        self.sentinel("closing")
        self.state["sessions"][-1]["end_utc"] = now()
        self.save_state()
        self.write_json(f"sessions/{self.sid}.json", {"id": self.sid, "facts": self.facts, "events": self.events,
                                                      "sentinels": self.sentinels, "order": [cell_id(*x) for x in order]})
        left = [cell_id(*x) for x in order if self.state["cells"].get(cell_id(*x), {}).get("status") not in ("complete", "failed")]
        self.log(f"session end; cells still to run: {left}")
        return 0


# ---------------------------------------------------------------- pre-flight
def preflight(a):
    import psutil

    problems, facts = [], {}
    names = {p.info["name"].lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
    if any(n.startswith("claude") for n in names):
        problems.append("the Claude desktop app is running: close it (it slows Host A; PROTOCOL deviation 2026-11-08)")
    # PROTOCOL 3.8 fallback: WSL is "not running" when there is no vmmem process. wslservice.exe is only the idle WSL Windows
    # service; it stays resident after `wsl --shutdown` with no VM and no distribution (confirmed on Host A 2026-11-09), so it is
    # not counted. A running distribution or open WSL terminal shows as wsl.exe.
    if any(n in names for n in ("vmmem", "vmmemwsl", "wsl.exe")):
        problems.append("WSL is running: run `wsl --shutdown` first (G1 condition 3)")
    b = psutil.sensors_battery()
    if not (b and b.power_plugged):
        problems.append("not on mains power: plug in the charger")
    if not os.path.exists(os.path.join(a.models_dir, DEV_FILE)):
        problems.append(f"development model {DEV_FILE} not found in {a.models_dir}")
    free = shutil.disk_usage(a.models_dir).free
    if free < 6 * 2**30:
        problems.append(f"only {free / 2**30:.1f} GiB free on the model drive (needs about 6 GiB for the largest file plus margin)")
    import cal_hostA

    if not os.path.exists(cal_hostA.BENCH):
        problems.append(f"llama-bench not found at {cal_hostA.BENCH}")
    facts.update({"time_utc": now(), "free_disk_bytes": free, "available_bytes": psutil.virtual_memory().available,
                  "total_bytes": psutil.virtual_memory().total, "plugged": bool(b and b.power_plugged),
                  "power_plan": subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True).stdout.strip(),
                  "bench": cal_hostA.BENCH, "flags": cal_hostA.FLAGS, "python": sys.version.split()[0]})
    try:
        import topology_win

        facts["mask_A"] = topology_win.mask_a()
    except Exception as e:  # recorded, not fatal: the mask in FLAGS is the frozen 0x555
        facts["mask_A_error"] = repr(e)
    return problems, facts


def BENCH():
    import cal_hostA

    return cal_hostA.BENCH


def ram_forecast(a, order):
    """Advisory only: which files the RAM fit rule is likely to refuse, from repo file sizes and current available memory."""
    import psutil

    avail = psutil.virtual_memory().available
    sizes = {"Qwen3-0.6B": {"Q4_K_M": 0.48e9, "Q8_0": 0.81e9, "F16": 1.51e9},
             "Qwen3-1.7B": {"Q4_K_M": 1.28e9, "Q8_0": 2.17e9, "F16": 4.07e9},
             "Qwen3-4B": {"Q4_K_M": 2.5e9, "Q8_0": 4.28e9}}
    out = []
    for m, q in order:
        need = sizes[m][q] + 0.05e9 + MARGIN_BYTES
        out.append((cell_id(m, q), round(need / 2**30, 2), avail >= need))
    return round(avail / 2**30, 2), out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", default=os.path.join(os.path.expanduser("~"), "hostA-downloads"))
    ap.add_argument("--results-dir", default=os.path.join(ROOT, "results"))
    ap.add_argument("--models-csv", default=os.path.join(HERE, "MODELS.csv"))
    ap.add_argument("--cells-csv", default=os.path.join(HERE, "CELLS.csv"))
    ap.add_argument("--max-hours", type=float, default=3.0, help="PROTOCOL 8: Host A sessions of at most 3 h")
    ap.add_argument("--min-block-hours", type=float, default=0.75, help="do not start a file with less time than this left")
    ap.add_argument("--check-only", action="store_true", help="pre-flight and RAM forecast only, then exit")
    ap.add_argument("--dry-run", action="store_true", help="simulated rounds and files in a temporary folder; nothing scored")
    a = ap.parse_args(argv)
    order = frozen_order()
    if a.dry_run:
        return dry_run(a, order)
    problems, facts = preflight(a)
    avail, fc = ram_forecast(a, order)
    print(f"Frozen order (seed {SEED_ORDER}, calibration file excluded): {[c for c, _, _ in fc]}")
    print(f"Available memory now: {avail} GiB. RAM-fit forecast (needed GiB, fits now?):")
    for c, need, fits in fc:
        print(f"  {c:28s} {need:5.2f}  {'yes' if fits else 'NO: likely DNF unless memory is freed (restart first)'}")
    if problems:
        print("\nNOT STARTING:\n  - " + "\n  - ".join(problems))
        return 2
    if a.check_only:
        print("\nPre-flight passed (check only; nothing run).")
        return 0
    return Session(a, real_round, HF({}, a.models_csv), facts).run(order)


# ---------------------------------------------------------------- dry run (tests the control flow; never touches results/)
def dry_run(a, order):
    import random
    import tempfile

    tmp = tempfile.mkdtemp(prefix="grid_hostA_dry_")
    a.results_dir, a.models_dir = os.path.join(tmp, "results"), os.path.join(tmp, "models")
    a.models_csv, a.cells_csv = os.path.join(tmp, "MODELS.csv"), os.path.join(tmp, "CELLS.csv")
    os.makedirs(a.models_dir)
    open(os.path.join(a.models_dir, DEV_FILE), "wb").write(b"x" * 1024)
    rnd = random.Random(1)

    def fake_runner(path):
        if rnd.random() < 0.03:
            return {"failed": True, "returncode": 1, "timed_out": False}
        base = 20.0 if DEV_FILE in path else 5.0
        return {"failed": False, "value_toks": base * (1 + rnd.gauss(0, 0.01)), "samples": [], "round_flags":
                (["avail_below_1GiB"] if rnd.random() < 0.05 else []), "start_flagged_not_quiet": False}

    class FakeHF:
        def __init__(self):
            self.state, self.pins = {}, {}

        def find(self, repo, quant):
            return "0" * 40, f"{repo.split('/')[1][:-5]}-{quant}.gguf", None, 1000

        def download(self, repo, rev, fname, dest, expected_sha=None):
            open(dest, "wb").write(os.urandom(1000))
            return sha256(dest)

    def fake_facts(path):
        return {"file": os.path.basename(path), "W_read_bytes": 10**9, "KV_bytes": 7340032, "D_bytes": 10**9 + 7340032,
                "P_active": 10**9, "file_bytes": 10**9, "V4_outside_pct": 0.3, "V4_pass": True}

    a.fake_facts = fake_facts
    global BENCH

    def BENCH():  # noqa: F811 - the dry run must not need llama-bench
        return os.path.join(tmp, "bin", "llama-bench.exe")

    os.makedirs(os.path.join(tmp, "bin"))

    def fake_quantize(*args, **kw):
        cmd = args[0]
        open(cmd[2], "wb").write(os.urandom(500))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    real_sub_run = subprocess.run
    subprocess.run = lambda cmd, *x, **k: fake_quantize(cmd) if "llama-quantize" in str(cmd[0]) else real_sub_run(cmd, *x, **k)
    try:
        rc = Session(a, fake_runner, FakeHF(), {"dry_run": True}).run(order)
        rc2 = Session(a, fake_runner, FakeHF(), {"dry_run": True}).run(order)  # resume: must run nothing new
    finally:
        subprocess.run = real_sub_run
    print(f"\nDRY RUN finished (rc {rc}, resume rc {rc2}); outputs in {tmp} (nothing written to the repository)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
