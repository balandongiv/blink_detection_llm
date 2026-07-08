"""Strategy comparison — kleifges, nathanael_mne, dbo, dbo_drop across multiple file pairs.

Runs all four strategies on each dataset pair and prints a unified comparison
table showing best-channel metrics (precision, recall, F1) per strategy/pair.

Pairs are discovered automatically from VideoFrameViewers.yaml files under
ANNOTATION_BASE_DIR; only sessions with ``status: complete_eeg`` are included.

Toggle ``USE_MULTITHREAD = False`` for sequential debugging.
Toggle ``VERBOSE = True/False`` to control diagnostic output from strategy dbo_drop.
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from pyblinker.strategies import kleifges_strategy
from src.strategy_nathanael_mne.runner import blink_position_strategy_nathanael
from src.strategy_dbo.runner import blink_position_strategy_dbo
from pyblinker.double_thresholding import blink_position_strategy_dbo
from src.utils.dataset_discovery import discover_raja_pairs
from src.utils.experiment_utils import setup_tutorial_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True   # False → sequential (easier to debug)
VERBOSE: bool = True           # diagnostic output from strategy dbo_drop

# ---------------------------------------------------------------------------
# Dataset root paths
# ---------------------------------------------------------------------------
ANNOTATION_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
PROCESSED_BASE_DIR  = Path(r"D:\dataset\drowsy_driving_raja_processed")

# ---------------------------------------------------------------------------
# Shared parameters
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Set to a positive integer to process only the first N epochs (quick inspection).
N_EPOCHS: int | None = None

# ---------------------------------------------------------------------------
# Strategy nathanael_mne parameters
# ---------------------------------------------------------------------------
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None

# ---------------------------------------------------------------------------
# Strategy dbo parameters
# ---------------------------------------------------------------------------
STAGE1_THRESHOLD_SCOPE = "per_channel"
AUTOREJECT_METHOD = "bayesian_optimization"
STAGE1_SCAN_SCALE = 0.12
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT = False

# ---------------------------------------------------------------------------
# Strategy dbo_drop parameters
# ---------------------------------------------------------------------------
MIN_FLAGGED_EPOCHS = 1
STD_THRESHOLD = 3.5
CENTER_METHOD = "median"

STRATEGIES = ["kleifges", "nathanael_mne", "dbo", "dbo_drop"]


# ---------------------------------------------------------------------------
# Per-strategy runners
# ---------------------------------------------------------------------------

def _run_strategy_kleifges(prepared, valid_epoch_indices):
    return kleifges_strategy(prepared, valid_epoch_indices)


def _run_strategy_nathanael_mne(prepared, valid_epoch_indices):
    return blink_position_strategy_nathanael(
        prepared,
        valid_epoch_indices,
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )


def _run_strategy_dbo(prepared, valid_epoch_indices):
    setting = {
        "threshold_scope": STAGE1_THRESHOLD_SCOPE,
        "scan_scale": STAGE1_SCAN_SCALE,
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "autoreject_method": AUTOREJECT_METHOD,
        "autoreject_augment": AUTOREJECT_AUGMENT,
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


def _run_strategy_dbo_drop(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose": VERBOSE,
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


_STRATEGY_RUNNERS = {
    "kleifges": _run_strategy_kleifges,
    "nathanael_mne": _run_strategy_nathanael_mne,
    "dbo": _run_strategy_dbo,
    "dbo_drop": _run_strategy_dbo_drop,
}


# ---------------------------------------------------------------------------
# Single task: one strategy × one pair
# ---------------------------------------------------------------------------

def run_one(pair_name: str, fif_path: Path, csv_path: Path, strategy: str) -> dict:
    """Load data, run *strategy*, evaluate, return metrics dict."""
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(fif_path, brain_channels)
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

    channel_results = _STRATEGY_RUNNERS[strategy](prepared, valid_epoch_indices)

    gt_annotations = load_ground_truth_annotations(csv_path, EPOCH_DURATION_S)

    scored = evaluate_channels(
        channel_results,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
    )

    em = scored.best_eval_result.event_metrics
    return {
        "pair": pair_name,
        "strategy": strategy,
        "best_channel": scored.best_channel,
        "tp": em.tp,
        "fp": em.fp,
        "fn": em.fn,
        "precision": em.precision,
        "recall": em.recall,
        "f1": em.f1,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _print_results(results: list[dict]) -> None:
    results.sort(key=lambda r: (r["pair"], r["strategy"]))

    col_w = {"pair": 8, "strategy": 10, "best_channel": 14,
              "tp": 5, "fp": 5, "fn": 5,
              "precision": 10, "recall": 8, "f1": 8}

    header = (
        f"{'pair':<{col_w['pair']}}  "
        f"{'strategy':<{col_w['strategy']}}  "
        f"{'best_channel':<{col_w['best_channel']}}  "
        f"{'tp':>{col_w['tp']}}  "
        f"{'fp':>{col_w['fp']}}  "
        f"{'fn':>{col_w['fn']}}  "
        f"{'precision':>{col_w['precision']}}  "
        f"{'recall':>{col_w['recall']}}  "
        f"{'f1':>{col_w['f1']}}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print("STRATEGY COMPARISON RESULTS  —  drowsy_driving_raja")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_pair = None
    for r in results:
        if prev_pair and r["pair"] != prev_pair:
            print(sep)
        prev_pair = r["pair"]
        print(
            f"{r['pair']:<{col_w['pair']}}  "
            f"{r['strategy']:<{col_w['strategy']}}  "
            f"{str(r['best_channel']):<{col_w['best_channel']}}  "
            f"{r['tp']:>{col_w['tp']}}  "
            f"{r['fp']:>{col_w['fp']}}  "
            f"{r['fn']:>{col_w['fn']}}  "
            f"{r['precision']:>{col_w['precision']}.4f}  "
            f"{r['recall']:>{col_w['recall']}.4f}  "
            f"{r['f1']:>{col_w['f1']}.4f}"
        )
    print(f"{'=' * len(header)}\n")

    _print_overall_summary(results)


def _print_overall_summary(results: list[dict]) -> None:
    """Print per-strategy aggregate metrics (micro + macro) across all pairs."""
    from collections import defaultdict

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        buckets[r["strategy"]].append(r)

    col_w = {"strategy": 10, "n_pairs": 8,
              "tp": 7, "fp": 7, "fn": 7,
              "micro_p": 10, "micro_r": 9, "micro_f1": 9,
              "macro_p": 10, "macro_r": 9, "macro_f1": 9}

    header = (
        f"{'strategy':<{col_w['strategy']}}  "
        f"{'n_pairs':>{col_w['n_pairs']}}  "
        f"{'TP(sum)':>{col_w['tp']}}  "
        f"{'FP(sum)':>{col_w['fp']}}  "
        f"{'FN(sum)':>{col_w['fn']}}  "
        f"{'micro_P':>{col_w['micro_p']}}  "
        f"{'micro_R':>{col_w['micro_r']}}  "
        f"{'micro_F1':>{col_w['micro_f1']}}  "
        f"{'macro_P':>{col_w['macro_p']}}  "
        f"{'macro_R':>{col_w['macro_r']}}  "
        f"{'macro_F1':>{col_w['macro_f1']}}"
    )
    sep = "-" * len(header)

    print(f"{'=' * len(header)}")
    print("OVERALL SUMMARY  (aggregated across all pairs)  —  drowsy_driving_raja")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for strategy in sorted(buckets):
        rows = buckets[strategy]
        total_tp = sum(r["tp"] for r in rows)
        total_fp = sum(r["fp"] for r in rows)
        total_fn = sum(r["fn"] for r in rows)

        micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                    if (micro_p + micro_r) > 0 else 0.0)

        macro_p = sum(r["precision"] for r in rows) / len(rows)
        macro_r = sum(r["recall"] for r in rows) / len(rows)
        macro_f1 = sum(r["f1"] for r in rows) / len(rows)

        print(
            f"{strategy:<{col_w['strategy']}}  "
            f"{len(rows):>{col_w['n_pairs']}}  "
            f"{total_tp:>{col_w['tp']}}  "
            f"{total_fp:>{col_w['fp']}}  "
            f"{total_fn:>{col_w['fn']}}  "
            f"{micro_p:>{col_w['micro_p']}.4f}  "
            f"{micro_r:>{col_w['micro_r']}.4f}  "
            f"{micro_f1:>{col_w['micro_f1']}.4f}  "
            f"{macro_p:>{col_w['macro_p']}.4f}  "
            f"{macro_r:>{col_w['macro_r']}.4f}  "
            f"{macro_f1:>{col_w['macro_f1']}.4f}"
        )
    print(f"{'=' * len(header)}\n")


def main() -> None:
    setup_tutorial_logging()
    logger.info("Scanning %s", ANNOTATION_BASE_DIR)
    pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    if not pairs:
        logger.warning("No complete pairs found under %s. Exiting.", ANNOTATION_BASE_DIR)
        return

    logger.info("Discovered %d complete pair(s):", len(pairs))
    for p in pairs:
        logger.info("  %s", p["name"])

    tasks = [
        (pair["name"], pair["fif"], pair["csv"], strategy)
        for pair in pairs
        for strategy in STRATEGIES
    ]

    results: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        logger.info("Running %d tasks with ThreadPoolExecutor …", len(tasks))
        with ThreadPoolExecutor() as executor:
            future_to_task = {
                executor.submit(run_one, name, fif, csv, strat): (name, strat)
                for name, fif, csv, strat in tasks
            }
            for future in as_completed(future_to_task):
                pair_name, strategy = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info("done  pair=%s  strategy=%s  f1=%.4f", pair_name, strategy, result["f1"])
                except Exception as exc:
                    logger.error("pair=%s  strategy=%s: %s", pair_name, strategy, exc)
                    errors.append(f"ERROR pair={pair_name}  strategy={strategy}: {exc}")
    else:
        logger.info("Running %d tasks sequentially …", len(tasks))
        for name, fif, csv, strat in tasks:
            logger.info("running  pair=%s  strategy=%s …", name, strat)
            try:
                result = run_one(name, fif, csv, strat)
                results.append(result)
                logger.info("done     pair=%s  strategy=%s  f1=%.4f", name, strat, result["f1"])
            except Exception as exc:
                logger.error("pair=%s  strategy=%s: %s", name, strat, exc)
                errors.append(f"ERROR pair={name}  strategy={strat}: {exc}")

    if results:
        _print_results(results)

    if errors:
        print("Errors encountered:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
