"""Experiment 4: Stability across peak-side boundary tolerances.

Tests whether Proposed-Med's event-level F1 is sensitive to the temporal tolerance used when matching detected blink intervals to ground-truth intervals. A detector whose F1 varies greatly with tolerance is fragile: its apparent performance depends on an arbitrary methodological choice rather than on true detection quality.

Design
------
Proposed-Med (Strategy F, median estimator, for example, 60-second epochs) is evaluated under
five boundary tolerances: {0, 50, 100, 150, 200} milliseconds, applied
symmetrically to both onset and offset.

Primary outcome: macro-averaged F1 at each tolerance level.
Secondary outcome: range of macro F1 across the five levels.  A range < 1
percentage point indicates the evaluation is insensitive to reasonable tolerance
choices.

Datasets
--------
Drowsy Driving Raja corpus and Cao2018 sustained-attention driving corpus.
"""

from __future__ import annotations

import argparse
import csv
import json
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

from blink_evaluation import evaluate_channels
from src.common.epoch_input import prepare_epoch_detection_input
from experiment_script.channel_group_config import apply_stage_a_channel_group
from src.strategy_dbo_drop.runner import channel_results_strategy_dbo_drop
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs, discover_raja_pairs,
    load_gt_annotations_for_pair, make_dataset_loaders, setup_tutorial_logging,
    valid_epoch_indices_for_pair,
)

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp4_boundary_tolerance.yaml")
_RAJA    = get_raja_paths()
_CAO     = get_cao_paths()

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAJA_REGION_YAML     = _RAJA["brain_region_yaml"]
CAO_REGION_YAML      = _CAO["brain_region_yaml"]
RAJA_ANNOTATION_BASE = _RAJA["annotation_base"]
RAJA_PROCESSED_BASE  = _RAJA["processed_base"]
CAO_DATASET_ROOT     = _CAO["dataset_root"]

# ---------------------------------------------------------------------------
# Experiment parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S        = float(_EXP_CFG.get("epoch_duration_s", 60.0))
# IoU thresholds for event matching (0 = any overlap, 0.5 = strict ≥50% overlap)
IOU_THRESHOLDS          = [0.0, 0.1, 0.2, 0.3, 0.5]
REFERENCE_IOU           = 0.1   # default IoU threshold used elsewhere
FILTER_LOW              = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH             = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE           = 100
N_EPOCHS: int | None    = None

# Strategy dbo_drop (Proposed-Med) parameters
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD           = float(_EXP_CFG.get("std_threshold", 3.5))
CENTER_METHOD           = _EXP_CFG.get("center_method", "median")
MIN_FLAGGED_EPOCHS      = int(_EXP_CFG.get("min_flagged_epochs", 1))




# ---------------------------------------------------------------------------
# Single evaluation unit: one session × one tolerance
# ---------------------------------------------------------------------------

def _run_session(pair: dict) -> dict:
    """Load session and run Proposed-Med once; cache channel_results for reuse."""
    dataset_loaders = make_dataset_loaders(
        raja_region_yaml=RAJA_REGION_YAML, cao_region_yaml=CAO_REGION_YAML
    )
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
    prepared = apply_stage_a_channel_group(prepared, pair["dataset"])
    valid_epoch_indices = valid_epoch_indices_for_pair(pair, epochs, EPOCH_DURATION_S)

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":      STD_THRESHOLD,
        "center_method":      CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":            VERBOSE,
    }
    channel_results = channel_results_strategy_dbo_drop(prepared, valid_epoch_indices, setting=setting)

    gt_annotations = load_gt_annotations_for_pair(pair, EPOCH_DURATION_S, valid_epoch_indices)
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
    print(f"EXP 4 - PER-SESSION - {dataset_name.upper()}")
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
    print(f"EXP 4 - IoU THRESHOLD SUMMARY - {dataset_name.upper()}")
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
        ref_marker = " <-ref" if iou_thr == REFERENCE_IOU else ""
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


def _tolerance_summary_rows(results: list[dict], dataset_name: str) -> list[dict]:
    """Return macro metrics per IoU threshold for *dataset_name* (or 'all')."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return []

    buckets: dict[float, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["iou_threshold"]].append(r)

    out: list[dict] = []
    for iou_thr in sorted(buckets):
        bucket = buckets[iou_thr]
        out.append({
            "dataset": dataset_name,
            "epoch_duration_s": float(EPOCH_DURATION_S),
            "iou_threshold": float(iou_thr),
            "n_sessions": int(len(bucket)),
            "macro_precision": float(np.mean([r["precision"] for r in bucket])),
            "macro_recall": float(np.mean([r["recall"] for r in bucket])),
            "macro_f1": float(np.mean([r["f1"] for r in bucket])),
        })
    if out:
        f1_values = [r["macro_f1"] for r in out]
        f1_range = float(max(f1_values) - min(f1_values))
        for r in out:
            r["macro_f1_range_all_thresholds"] = f1_range
    return out


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Experiment 4: stability across event-matching tolerances (IoU thresholds).",
    )
    p.add_argument(
        "--epoch-duration-s",
        type=float,
        default=EPOCH_DURATION_S,
        help="Epoch duration in seconds (should be set to the best duration from Experiment 1).",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="If set, write CSV/JSON artifacts into this directory.",
    )
    p.add_argument(
        "--no-multithread",
        action="store_true",
        help="Disable internal ThreadPoolExecutor.",
    )
    p.add_argument(
        "--n-epochs",
        type=int,
        default=None,
        help="Limit epochs per session for quick runs (None = all).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce strategy verbosity.",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    global USE_MULTITHREAD, VERBOSE, EPOCH_DURATION_S, N_EPOCHS
    USE_MULTITHREAD = not args.no_multithread
    VERBOSE = not args.quiet
    EPOCH_DURATION_S = float(args.epoch_duration_s)
    N_EPOCHS = args.n_epochs

    setup_tutorial_logging()
    raja_pairs = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    cao_pairs  = discover_cao_pairs(CAO_DATASET_ROOT)
    all_pairs  = raja_pairs + cao_pairs

    logger.info("Raja sessions   : %d", len(raja_pairs))
    logger.info("Cao2018 sessions: %d", len(cao_pairs))
    logger.info("IoU thresholds  : %s", IOU_THRESHOLDS)

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

    for ds in ("raja", "cao2018"):
        _print_per_session_table(results, ds)

    for ds in ("raja", "cao2018", "all"):
        _print_tolerance_summary(results, ds)

    if args.out_dir is not None:
        out_dir: Path = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_csv(out_dir / "exp42_boundary_tolerance_results.csv", results)
        _write_csv(
            out_dir / "exp42_boundary_tolerance_summary.csv",
            _tolerance_summary_rows(results, "raja")
            + _tolerance_summary_rows(results, "cao2018")
            + _tolerance_summary_rows(results, "all"),
        )
        payload = {
            "experiment": "exp42_boundary_tolerance",
            "epoch_duration_s": float(EPOCH_DURATION_S),
            "metric_primary": "macro_f1 (dataset=all) across IOU_THRESHOLDS",
            "iou_thresholds": [float(x) for x in IOU_THRESHOLDS],
            "n_rows": int(len(results)),
        }
        (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
