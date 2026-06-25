"""Sanity check: exp1 'all|any|median' must match tutorial/10d on the same session.

Runs both pipelines on S01_20170519_043933 with identical parameters and prints
a side-by-side comparison.  A mismatch indicates a regression in channel_ablation_utils.

Usage::

    python experiment_script/check_exp1_vs_10d.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import mne

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.project_paths import get_raja_paths
from src.strategy_dbo_drop.core import blink_position_strategy_dbo_drop
from experiment_script.channel_ablation_utils import run_one_session
from tutorial.tutorial_utils import setup_tutorial_logging

# ── shared session paths (derived from paths.yaml) ─────────────────────────
_RAJA = get_raja_paths()
_SESSION = "S1/S01_20170519_043933"
FIF_PATH = _RAJA["processed_base"] / _SESSION / "seg_data_raw" / "eeg_eog_raw.fif"
CSV_PATH = _RAJA["annotation_base"] / _SESSION / "ear_eog.csv"
# Intentionally the combined brain_region.yaml to match tutorial/10d exactly.
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"

# ── shared parameters (must match tutorial/10d exactly) ────────────────────
EPOCH_DURATION_S = 30.0
STD_THRESHOLD    = 3.5
CENTER_METHOD    = "median"
FILTER_LOW       = 1.0
FILTER_HIGH      = 20.0
RESAMPLE_RATE    = 100
AUTOREJECT_RS    = 42


def run_10d() -> dict:
    """Replicate tutorial/10d and return event metrics."""
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
    epochs = mne.make_fixed_length_epochs(raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR")
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    setting = {
        "autoreject_random_state": AUTOREJECT_RS,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": 1,
        "verbose": False,
    }
    channel_results = blink_position_strategy_dbo_drop(prepared, valid_epoch_indices, setting=setting)
    gt_annotations = load_ground_truth_annotations(CSV_PATH, EPOCH_DURATION_S)
    scored = evaluate_channels(channel_results, gt_annotations, epoch_duration=EPOCH_DURATION_S)
    em = scored.best_eval_result.event_metrics
    return {
        "best_channel": scored.best_channel,
        "tp": em.tp, "fp": em.fp, "fn": em.fn,
        "precision": em.precision, "recall": em.recall, "f1": em.f1,
    }


def run_exp1_all_median() -> dict:
    """Run exp1 channel ablation for 'all|any|median' and return its metrics."""
    pair = {
        "dataset": "raja",
        "name": "S01_20170519_043933",
        "fif": FIF_PATH,
        "csv": CSV_PATH,
    }
    records = run_one_session(
        pair,
        raja_region_yaml=BRAIN_REGION_YAML,
        cao_region_yaml=BRAIN_REGION_YAML,
        epoch_duration_s=EPOCH_DURATION_S,
        std_threshold=STD_THRESHOLD,
        center_methods=(CENTER_METHOD,),
        rules=("any",),
        autoreject_random_state=AUTOREJECT_RS,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        include_single_frontal=False,
        use_epoch_health=True,
        groups_filter={"all"},
        verbose=False,
    )
    # find the 'all|any|median' row
    row = next((r for r in records if r["selection"] == "all"), None)
    if row is None:
        raise RuntimeError("'all' group not found in exp1 records")
    return {
        "best_channel": row["best_channel"],
        "tp": row["det_tp"], "fp": row["det_fp"], "fn": row["det_fn"],
        "precision": row["det_precision"], "recall": row["det_recall"], "f1": row["det_f1"],
    }


def main() -> None:
    setup_tutorial_logging()
    logger = logging.getLogger(__name__)



    logger.info("Running exp1 'all|any|median' …")
    rexp = run_exp1_all_median()

    logger.info("Running tutorial/10d pipeline …")
    r10d = run_10d()

    print("\n" + "=" * 60)
    print(f"{'Metric':<14}  {'tutorial/10d':>12}  {'exp1 all|any|med':>16}  {'match':>5}")
    print("-" * 60)
    for key in ("tp", "fp", "fn", "precision", "recall", "f1"):
        v10 = r10d[key]
        vex = rexp[key]
        if isinstance(v10, int):
            match = "OK" if v10 == vex else "DIFF"
            print(f"{key:<14}  {v10:>12d}  {vex:>16d}  {match:>5}")
        else:
            match = "OK" if abs(v10 - vex) < 1e-6 else "DIFF"
            print(f"{key:<14}  {v10:>12.4f}  {vex:>16.4f}  {match:>5}")
    print(f"{'best_channel':<14}  {r10d['best_channel']:>12}  {rexp['best_channel']:>16}")
    print("=" * 60)

    diffs = [k for k in ("tp", "fp", "fn", "precision", "recall", "f1")
             if (r10d[k] != rexp[k] if isinstance(r10d[k], int) else abs(r10d[k] - rexp[k]) >= 1e-6)]
    if diffs:
        print(f"\nFAIL — differences in: {diffs}")
        sys.exit(1)
    else:
        print("\nPASS — outputs are identical.")


if __name__ == "__main__":
    main()
