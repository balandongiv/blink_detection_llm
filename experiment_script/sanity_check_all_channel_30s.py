"""Sanity check: does exp1, exp2, and exp3 agree on the all_channel (32 ch) / 30s epoch /
median-centre Proposed result, for both datasets?

Reads the RAW *_results.csv files produced by exp1/exp2/exp3 directly (not the generated
*_summary.csv files) — using raw rows sidesteps any bug that might exist in the
summary-generation code itself, which is the whole point of this check.

Background (read before "fixing" a flagged gap)
-------------------------------------------------
exp1 and exp3 share the same per-channel engine (src/utils/channel_ablation_utils.py):
for a fixed channel, evaluate it across every session and average -> ONE macro F1 per
channel. exp2's "Proposed-Med" condition works differently: for each SESSION it picks
whichever channel scores best for THAT session (src/exp/exp2_channel_group_sweep.py's
evaluate_channels() -> best_channel), then macro-averages those per-session winners.

A fixed fixed-channel number (e.g. exp1's best-on-average channel, evaluated the same
way for every session) is NOT the same quantity as a per-session-adaptive number, even
with zero pipeline drift — "always pick the winner in hindsight, per session" is
mechanically >= "commit to one channel for the whole dataset". So this script computes
exp1's per-session-best-channel macro F1 (call it exp1_adaptive) using exp1's own raw
rows and compares THAT to exp2 — which should match almost exactly, since both are
computing the same "per-session argmax over channels" quantity, just via different code
paths. Confirmed by hand on 2026-07-22 (Cao2018): exp1_adaptive == exp2 Proposed-Med to
15 decimal places, with an identical per-session best-channel distribution.

The naive fixed-channel-vs-exp2 comparison is still printed for context (labeled
clearly) but is NOT flagged, since it is expected to differ structurally.

Usage:
    python experiment_script/sanity_check_all_channel_30s.py
    python experiment_script/sanity_check_all_channel_30s.py --tolerance 5e-4
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXPECTED_SESSIONS = {"raja": 46, "cao2018": 58}


def _out_dirs() -> dict:
    cfg = yaml.safe_load((REPO_ROOT / "experiment_script" / "setup" / "exp_path.yaml").read_text())
    return cfg["out_dirs"]


def _paths(out_dirs: dict) -> dict:
    return {
        "raja": {
            "exp1": REPO_ROOT / out_dirs["exp1"]["raja"] / "exp1_channel_selection_raja_results.csv",
            "exp2": REPO_ROOT / out_dirs["exp2"]["raja"] / "exp2_strategy_comparison_raja_results.csv",
            "exp3": REPO_ROOT / out_dirs["exp3"]["raja"] / "exp3_epoch_duration_raja_results.csv",
        },
        "cao2018": {
            "exp1": REPO_ROOT / out_dirs["exp1"]["cao2018"] / "exp1_channel_selection_cao2018_results.csv",
            "exp2": REPO_ROOT / out_dirs["exp2"]["cao2018"] / "exp2_strategy_comparison_cao2018_results.csv",
            "exp3": REPO_ROOT / out_dirs["exp3"]["cao2018"] / "exp3_epoch_duration_cao2018_results.csv",
        },
    }


def _validity(path: Path, expected_sessions: int) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing (not produced yet)"
    df = pd.read_csv(path)
    n = df["session"].nunique() if "session" in df.columns else 0
    if n < expected_sessions:
        return False, f"INCOMPLETE: only {n}/{expected_sessions} sessions in raw CSV (stale/crashed run?)"
    return True, f"OK: {n}/{expected_sessions} sessions"


def _exp1_all_channel_median(path: Path) -> pd.DataFrame:
    """Raw all_channel/median rows: one row per (session, channel)."""
    df = pd.read_csv(path)
    return df[(df.selection == "all_channel") & (df.center_method == "median")]


def _exp3_all_channel_median_30s(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df[
        (df.selection == "all_channel")
        & (df.center_method == "median")
        & (df.epoch_duration_s == 30.0)
    ]


def _exp2_all_channel_proposed_med(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df[(df.selection == "all_channel") & (df.condition == "Proposed-Med")]


def run(tolerance: float) -> bool:
    out_dirs = _out_dirs()
    paths = _paths(out_dirs)
    any_flag = False
    any_skipped = False

    for dataset in ("raja", "cao2018"):
        print(f"\n=== {dataset} ===")
        p = paths[dataset]
        exp_n = EXPECTED_SESSIONS[dataset]

        ok1, msg1 = _validity(p["exp1"], exp_n)
        ok2, msg2 = _validity(p["exp2"], exp_n)
        ok3, msg3 = _validity(p["exp3"], exp_n)
        print(f"exp1: {msg1}")
        print(f"exp2: {msg2}")
        print(f"exp3: {msg3}")

        exp1_rows = _exp1_all_channel_median(p["exp1"]) if ok1 else None
        exp3_rows = _exp3_all_channel_median_30s(p["exp3"]) if ok3 else None
        exp2_rows = _exp2_all_channel_proposed_med(p["exp2"]) if ok2 else None

        exp1_by_channel = exp1_rows.groupby("channel")["f1"].mean().sort_index() if exp1_rows is not None else None
        exp3_by_channel = exp3_rows.groupby("channel")["f1"].mean().sort_index() if exp3_rows is not None else None
        exp2_macro_f1 = float(exp2_rows["f1"].mean()) if exp2_rows is not None and not exp2_rows.empty else None

        # --- Check A: exp1 vs exp3, per fixed channel (same engine -> should match tightly) ---
        if exp1_by_channel is not None and exp3_by_channel is not None:
            common = sorted(set(exp1_by_channel.index) & set(exp3_by_channel.index))
            if not common:
                print("  [A] no common channels between exp1 and exp3 all_channel/median rows")
            else:
                max_diff = max(abs(exp1_by_channel[ch] - exp3_by_channel[ch]) for ch in common)
                mism = [ch for ch in common if abs(exp1_by_channel[ch] - exp3_by_channel[ch]) > tolerance]
                print(f"  [A] exp1 vs exp3 (per fixed channel, {len(common)} channels, same engine): "
                      f"max|diff|={max_diff:.6f}")
                if mism:
                    any_flag = True
                    print(f"      FLAG: {len(mism)} channel(s) exceed tolerance {tolerance}:")
                    for ch in mism:
                        print(f"        {ch}: exp1={exp1_by_channel[ch]:.5f}  exp3={exp3_by_channel[ch]:.5f}  "
                              f"diff={exp1_by_channel[ch]-exp3_by_channel[ch]:+.5f}")
                else:
                    print(f"      OK: all channels within tolerance {tolerance}")
        else:
            print("  [A] SKIP exp1-vs-exp3: one or both not valid/complete yet")
            any_skipped = True

        # --- Check B: exp1's per-session best-channel macro F1 vs exp2 Proposed-Med ---
        # (the apples-to-apples comparison -- both are "per-session argmax over channels")
        if exp1_rows is not None and exp2_macro_f1 is not None:
            per_session_best = exp1_rows.loc[exp1_rows.groupby("session")["f1"].idxmax()]
            exp1_adaptive_f1 = float(per_session_best["f1"].mean())
            gap = abs(exp1_adaptive_f1 - exp2_macro_f1)
            flag = " FLAG" if gap > tolerance else ""
            print(f"  [B] exp1 per-session-best-channel macro F1={exp1_adaptive_f1:.6f}  vs  "
                  f"exp2 Proposed-Med(all_channel) macro F1={exp2_macro_f1:.6f}  |diff|={gap:.6f}{flag}")
            if gap > tolerance:
                any_flag = True

            # --- FYI only: fixed-best-channel vs exp2 (expected to differ, NOT flagged) ---
            if exp1_by_channel is not None:
                fixed_best_ch = exp1_by_channel.idxmax()
                fixed_gap = abs(exp1_by_channel[fixed_best_ch] - exp2_macro_f1)
                print(f"      (context, not a check) exp1 fixed best channel ({fixed_best_ch}) "
                      f"F1={exp1_by_channel[fixed_best_ch]:.6f}  vs exp2={exp2_macro_f1:.6f}  "
                      f"|diff|={fixed_gap:.6f} -- expected to differ, per-session-adaptive vs fixed-channel")
        else:
            print("  [B] SKIP exp1-vs-exp2: one or both not valid/complete yet")
            any_skipped = True

    print()
    if any_flag:
        print("FLAGGED: yes -- review [A]/[B] lines above")
    elif any_skipped:
        print("INCOMPLETE: no drift in the checks that ran, but at least one [A]/[B] check "
              "was SKIPPED (missing/incomplete input) -- this is NOT a clean pass, rerun once "
              "all six CSVs are complete.")
    else:
        print("FLAGGED: no -- all checks ran and no drift detected beyond tolerance")
    return not any_flag and not any_skipped


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tolerance", type=float, default=1e-3)
    args = ap.parse_args()
    ok = run(args.tolerance)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
