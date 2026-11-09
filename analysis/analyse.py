"""Analysis stages. Deterministic (no randomness); every number comes from files under results/ and the GGUF tensor table.

Stage implemented so far:  freeze   (PROTOCOL 4.3)
  eta   = tok/s_cal * D_cal / B1_A
  eta'  = tok/s_cal * 2 * P_active_cal / F1_A
  eta'2 = tok/s_cal * 2 * P_active_cal / F2_A,   F2_A = 2 * P_active_cal * pp512_A
Computed once from the Host A calibration cell (Qwen3-1.7B Q8_0, depth 0, T_A = 6) and written to results/frozen_constants.json.
Refitting is forbidden: the script refuses to overwrite an existing frozen_constants.json unless --force is given.
Other stages (cells, MAPE, ratios, figures) are not implemented yet.

  python analysis/analyse.py freeze --model <Qwen3-1.7B-Q8_0.gguf>
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bytes_per_token  # noqa: E402


def _load(name):
    with open(os.path.join(ROOT, "results", "hosts", name)) as f:
        return json.load(f)


def freeze(model, force=False):
    out_path = os.path.join(ROOT, "results", "frozen_constants.json")
    if os.path.exists(out_path) and not force:
        sys.exit(f"{out_path} exists; constants are frozen (refitting is forbidden). Use --force only with the author's approval.")
    bw, f1, f2, cal = _load("hostA_bw.json"), _load("hostA_f1.json"), _load("hostA_f2.json"), _load("hostA_cal.json")
    dp = bytes_per_token.compute(model, depth=0, n_gen=128)
    tok_cal = cal["tok_s_cal"]
    b1 = bw["B1_A_gbps"] * 1e9
    f1v = f1["F1_A_gflops"] * 1e9
    pp512 = f2["pp512_A_toks"]
    f2v = 2.0 * dp["P_active"] * pp512
    eta = tok_cal * dp["D_bytes"] / b1
    eta_f = tok_cal * 2.0 * dp["P_active"] / f1v
    eta_f2 = tok_cal * 2.0 * dp["P_active"] / f2v
    # sensitivity to the calibration session (values are recorded in results/hosts/hostA_cal.json notes)
    sess = {"2026-11-09 15:28 (scored)": tok_cal, "2026-11-09 14:29": 4.466, "2026-11-08 night": 5.384}
    sens = {k: {"tok_s_cal": v, "eta": v * dp["D_bytes"] / b1, "eta_prime": v * 2.0 * dp["P_active"] / f1v,
                "eta_prime2": v * 2.0 * dp["P_active"] / f2v} for k, v in sess.items()}
    res = {
        "cell": "Host A, Qwen3-1.7B Q8_0, depth 0, T_A = 6 (calibration cell; excluded from every APE, MAPE and Q1 statistic)",
        "inputs": {"tok_s_cal": tok_cal, "B1_A_Bps": b1, "B2_A_Bps": bw["B2_A_gbps"] * 1e9, "F1_A_flops": f1v, "F2_A_flops": f2v,
                   "pp512_A_toks": pp512, "D_cal_bytes": dp["D_bytes"], "W_read_bytes": dp["W_read_bytes"], "KV_bytes": dp["KV_bytes"],
                   "P_active_cal": dp["P_active"], "model_file": dp["file"]},
        "eta": eta, "eta_prime": eta_f, "eta_prime2": eta_f2,
        "calibration_flags": cal.get("flags"), "calibration_status": cal.get("status"),
        "session_sensitivity": sens,
        "notes": "Frozen once; refitting forbidden (PROTOCOL 4.3). The spread between calibration sessions (1.6% between the two 2026-11-09 sessions, about 16% to 2026-11-08) is uncertainty on eta, eta', eta'2 and must be carried into the Host A prediction intervals.",
    }
    with open(out_path, "w") as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("freeze")
    p.add_argument("--model", required=True)
    p.add_argument("--force", action="store_true")
    a = ap.parse_args()
    r = freeze(a.model, a.force)
    print(json.dumps({k: r[k] for k in ("eta", "eta_prime", "eta_prime2")}, indent=1))
