"""Experiment 4: Stability across peak-side boundary tolerances.

Tests whether Proposed-Med's event-level F1 is sensitive to the temporal
tolerance used when matching detected blink intervals to ground-truth intervals.
A detector whose F1 varies greatly with tolerance is fragile: its apparent
performance depends on an arbitrary methodological choice rather than on true
detection quality.

Design
------
Proposed-Med (Strategy F, median estimator, 60-second epochs) is evaluated under
five boundary tolerances: {0, 50, 100, 150, 200} milliseconds, applied
symmetrically to both onset and offset.

Primary outcome: macro-averaged F1 at each tolerance level.
Secondary outcome: range of macro F1 across the five levels.  A range < 1
percentage point indicates the evaluation is insensitive to reasonable tolerance
choices.

Datasets
--------
Drowsy Driving Raja corpus and murat_2018.
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.strategy_dbo_drop.runner import channel_results_strategy_dbo_drop
from tutorial.tutorial_utils import (
    discover_raja_pairs, discover_murat_pairs, make_dataset_loaders, setup_tutorial_logging,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML    = REPO_ROOT / "brain_region.yaml"
RAJA_ANNOTATION_BASE = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
RAJA_PROCESSED_BASE  = Path(r"D:\dataset\drowsy_driving_raja_processed")
MURAT_DATASET_ROOT   = Path(r"D:\dataset\murat_2018")

# ---------------------------------------------------------------------------
# Experiment parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S        = 60.0
# IoU thresholds for event matching (0 = any overlap, 0.5 = strict ≥50% overlap)
IOU_THRESHOLDS          = [0.0, 0.1, 0.2, 0.3, 0.5]
REFERENCE_IOU           = 0.1   # default IoU threshold used elsewhere
FILTER_LOW              = 1.0
FILTER_HIGH             = 20.0
RESAMPLE_RATE           = None
N_EPOCHS: int | None    = None

# Strategy dbo_drop (Proposed-Med) parameters
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD           = 3.5
CENTER_METHOD           = "median"
MIN_FLAGGED_EPOCHS      = 1




# ---------------------------------------------------------------------------
# Single evaluation unit: one session × one tolerance
# ---------------------------------------------------------------------------

def _run_session(pair: dict) -> dict:
    """Load session and run Proposed-Med once; cache channel_results for reuse."""
    dataset_loaders = make_dataset_loaders(BRAIN_REGION_YAML)
    load_fn = dataset_loaders[pair["dataset"]]
    raw = load_fn(pair["fif"])
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":      STD_THRESHOLD,
        "center_method":      CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":            VERBOSE,
    }
    channel_results = channel_results_strategy_dbo_drop(prepared, valid_epoch_indices, setting=setting)

    gt_annotations = load_ground_truth_annotations(pair["csv"], EPOCH_DURATION_S)
    return {
        "pair":            pair,
        "channel_results": channel_results,
        "gt_annotations":  gt_annotations,
    }


def run_one_session_all_tolerances(pair: dict) -> list[dict]:
    """Run the pipeline once and evaluate across all boundary tolerances.

    This avoids repeating Stage A/B computation for each tolerance level.

    Returns
    -------
    List of metric dicts, one per tolerance value.
    """
    session_data    = _run_session(pair)
    channel_results = session_data["channel_results"]
    gt_annotations  = session_data["gt_annotations"]

    records: list[dict] = []
    for iou_thr in IOU_THRESHOLDS:
        scored = evaluate_channels(
            channel_results,
            gt_annotations,
            epoch_duration=EPOCH_DURATION_S,
            iou_threshold=iou_thr,
        )
        em = scored.best_eval_result.event_metrics
        records.append({
            "dataset":       pair["dataset"],
            "session":       pair["name"],
            "iou_threshold": iou_thr,
            "tp":            em.tp,
            "fp":            em.fp,
            "fn":            em.fn,
            "precision":     em.precision,
            "recall":        em.recall,
            "f1":            em.f1,
        })
    return records


# ---------------------------------------------------------------------------
# Result printing
# ---------------------------------------------------------------------------

def _print_per_session_table(results: list[dict], dataset_name: str) -> None:
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: (r["session"], r["iou_threshold"]))

    W_sess = max(len(r["session"]) for r in rows)
    W_sess = max(W_sess, 8)
    header = (
        f"{'session':<{W_sess}}  {'iou_thr':>7}  "
        f"{'tp':>5}  {'fp':>5}  {'fn':>5}  "
        f"{'precision':>10}  {'recall':>8}  {'f1':>8}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 4 — PER-SESSION  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_session = None
    for r in rows:
        if prev_session and r["session"] != prev_session:
            print(sep)
        prev_session = r["session"]
        print(
            f"{r['session']:<{W_sess}}  {r['iou_threshold']:>7.2f}  "
            f"{r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  "
            f"{r['precision']:>10.4f}  {r['recall']:>8.4f}  {r['f1']:>8.4f}"
        )
    print(f"{'=' * len(header)}\n")


def _print_tolerance_summary(results: list[dict], dataset_name: str) -> None:
    """Print macro-averaged P/R/F1 per IoU threshold and report the F1 range."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return

    buckets: dict[float, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["iou_threshold"]].append(r)

    header = (
        f"{'iou_thr':>7}  {'N':>5}  "
        f"{'macro_P':>9}  {'macro_R':>9}  {'macro_F1':>9}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 4 — IoU THRESHOLD SUMMARY  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    f1_values: list[float] = []
    for iou_thr in sorted(buckets):
        bucket = buckets[iou_thr]
        macro_p  = float(np.mean([r["precision"] for r in bucket]))
        macro_r  = float(np.mean([r["recall"]    for r in bucket]))
        macro_f1 = float(np.mean([r["f1"]        for r in bucket]))
        f1_values.append(macro_f1)
        ref_marker = " ←ref" if iou_thr == REFERENCE_IOU else ""
        print(
            f"{iou_thr:>7.2f}  {len(bucket):>5}  "
            f"{macro_p:>9.4f}  {macro_r:>9.4f}  {macro_f1:>9.4f}{ref_marker}"
        )

    if f1_values:
        f1_range = max(f1_values) - min(f1_values)
        stable = "YES" if f1_range < 0.01 else "NO"
        print(sep)
        print(f"  macro-F1 range = {f1_range:.4f}  stable (<1 pp) = {stable}")
    print(f"{'=' * len(header)}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    raja_pairs  = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    murat_pairs = discover_murat_pairs(MURAT_DATASET_ROOT)
    all_pairs   = raja_pairs + murat_pairs

    logger.info("Raja sessions  : %d", len(raja_pairs))
    logger.info("Murat subjects : %d", len(murat_pairs))
    logger.info("IoU thresholds : %s", IOU_THRESHOLDS)

    results: list[dict] = []
    errors:  list[str]  = []

    if USE_MULTITHREAD:
        logger.info("Running %d sessions with ThreadPoolExecutor …", len(all_pairs))
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one_session_all_tolerances, pair): pair["name"]
                for pair in all_pairs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    records = future.result()
                    results.extend(records)
                    logger.info("done  %s  (%d tolerances)", name, len(records))
                except Exception as exc:
                    logger.error("%s: %s", name, exc)
                    errors.append(f"ERROR  {name}: {exc}")
    else:
        logger.info("Running %d sessions sequentially …", len(all_pairs))
        for pair in all_pairs:
            logger.info("running  %s …", pair["name"])
            try:
                records = run_one_session_all_tolerances(pair)
                results.extend(records)
                logger.info("done     %s  (%d tolerances)", pair["name"], len(records))
            except Exception as exc:
                logger.error("%s: %s", pair["name"], exc)
                errors.append(f"ERROR  {pair['name']}: {exc}")

    if not results:
        print("No results collected.")
        return

    for ds in ("raja", "murat2018"):
        _print_per_session_table(results, ds)

    for ds in ("raja", "murat2018", "all"):
        _print_tolerance_summary(results, ds)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
