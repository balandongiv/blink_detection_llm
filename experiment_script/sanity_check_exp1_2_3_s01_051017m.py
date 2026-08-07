"""Sanity check: exp1/exp2/exp3 (Cao2018) agree on session S01/051017m at 30s epoch.

exp1 (channel selection), exp2 (strategy comparison), and exp3 (epoch duration
sweep) each independently run the same Stage A->B->C pipeline on session
S01__051017m for the ``all_channel`` selection. At the 30s epoch duration they
should all pick channel FP1 as the best channel and report identical
tp/fp/fn/precision/recall/f1 for both the ``median`` and ``mean`` Stage-B
centre methods, since exp2/exp3 are supersets/variants of exp1's sweep.

This script re-derives that comparison from the cached per-session CSVs and
hard-asserts agreement, so a future re-run of exp1/exp2/exp3 can be checked
for a wiring/regression bug with one command.

Usage::

    python experiment_script/sanity_check_exp1_2_3_s01_051017m.py

Exits non-zero (via AssertionError) if any session/experiment disagrees.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.project_paths import EXP_SETUP_DIR, load_exp_config

SESSION_CSV_NAME = "S01__051017m.csv"
EPOCH_DURATION_S = 30.0
FLOAT_ATOL = 1e-6

# Expected values, pinned from the reference run (2026-07-23). If exp1/exp2/exp3
# are re-run and legitimately change (e.g. new data, algorithm change), update
# these together with the git commit that caused the change -- do not silently
# relax the assertions below.
EXPECTED = {
    "median": {"channel": "FP1", "tp": 331, "fp": 335, "fn": 77,
               "precision": 0.496996996996997, "recall": 0.8112745098039216,
               "f1": 0.6163873370577281},
    "mean": {"channel": "FP1", "tp": 326, "fp": 320, "fn": 82,
             "precision": 0.5046439628482973, "recall": 0.7990196078431373,
             "f1": 0.618595825426945},
}


def _out_dir(exp_key: str) -> Path:
    path_cfg = load_exp_config(EXP_SETUP_DIR / "exp_path.yaml")
    return REPO_ROOT / Path(path_cfg["out_dirs"][exp_key]["cao2018"])


def _best_row_per_center(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Return the top-f1 row for each Stage-B center method, within the
    ``all_channel`` selection group.

    exp1/exp3 sweep several channel-selection groups (all_channel, frontal,
    frontal_left, fp1_only, ...). The same physical channel (e.g. FP1) gets
    slightly different tp/fp/fn across groups because Stage-B's robust
    threshold is computed from the group's channel subset, not just from FP1
    itself. exp2's "Proposed" conditions are always the all_channel result,
    so we must restrict to that group before comparing -- otherwise a
    same-channel-different-group row (e.g. frontal_left) can outrank it by a
    hair on f1 and produce a false mismatch.
    """
    df = df[df["selection"] == "all_channel"]
    best = {}
    for center_method, group in df.groupby("center_method"):
        best[center_method] = group.sort_values("f1", ascending=False).iloc[0]
    return best


def _check_row(source: str, center_method: str, row: pd.Series) -> None:
    expected = EXPECTED[center_method]
    assert row["channel"] == expected["channel"], (
        f"{source}/{center_method}: best channel {row['channel']!r} != expected {expected['channel']!r}"
    )
    for key in ("tp", "fp", "fn"):
        assert int(row[key]) == expected[key], (
            f"{source}/{center_method}: {key}={row[key]} != expected {expected[key]}"
        )
    for key in ("precision", "recall", "f1"):
        assert abs(float(row[key]) - expected[key]) < FLOAT_ATOL, (
            f"{source}/{center_method}: {key}={row[key]} != expected {expected[key]} (atol={FLOAT_ATOL})"
        )


def main() -> None:
    exp1_csv = _out_dir("exp1") / "sessions" / SESSION_CSV_NAME
    exp2_csv = _out_dir("exp2") / "sessions" / SESSION_CSV_NAME
    exp3_csv = _out_dir("exp3") / "sessions" / SESSION_CSV_NAME

    for label, csv_path in (("exp1", exp1_csv), ("exp2", exp2_csv), ("exp3", exp3_csv)):
        assert csv_path.exists(), f"{label} session CSV not found: {csv_path}. Run the experiment first."

    exp1 = pd.read_csv(exp1_csv)
    exp2 = pd.read_csv(exp2_csv)
    exp3 = pd.read_csv(exp3_csv)

    exp1_best = _best_row_per_center(exp1)

    exp3_30 = exp3[exp3["epoch_duration_s"] == EPOCH_DURATION_S]
    assert not exp3_30.empty, f"exp3 has no rows at epoch_duration_s={EPOCH_DURATION_S}"
    exp3_best = _best_row_per_center(exp3_30)

    exp2_by_condition = {
        "Proposed-Mean": exp2.loc[exp2["condition"] == "Proposed-Mean"].iloc[0],
        "Proposed-Med": exp2.loc[exp2["condition"] == "Proposed-Med"].iloc[0],
    }
    exp2_best = {
        "mean": exp2_by_condition["Proposed-Mean"].rename({"best_channel": "channel"}),
        "median": exp2_by_condition["Proposed-Med"].rename({"best_channel": "channel"}),
    }

    rows = []
    for center_method in ("median", "mean"):
        for source, best in (("exp1", exp1_best), ("exp2", exp2_best), ("exp3", exp3_best)):
            row = best[center_method]
            _check_row(source, center_method, row)
            rows.append({
                "center_method": center_method,
                "source": source,
                "channel": row["channel"],
                "tp": int(row["tp"]),
                "fp": int(row["fp"]),
                "fn": int(row["fn"]),
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "f1": float(row["f1"]),
            })

    report = pd.DataFrame(rows)
    print(report.to_string(index=False))
    print()
    print("PASS: exp1, exp2, exp3 agree on channel/f1 for S01/051017m at 30s epoch.")


if __name__ == "__main__":
    main()
