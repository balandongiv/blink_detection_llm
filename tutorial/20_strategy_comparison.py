"""Strategy comparison — A, B, C, F across multiple file pairs.

Runs all four strategies on each dataset pair and prints a unified comparison
table showing best-channel metrics (precision, recall, F1) per strategy/pair.

Toggle ``USE_MULTITHREAD = False`` for sequential debugging.
Toggle ``VERBOSE = True/False`` to control diagnostic output from Strategy F.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.analysis.lane_evaluation import evaluate_channel_lanes
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from pyblinker.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference
from pyblinker.strategy_a.kleifges_blinker_2017 import kleifges_strategy_a
from pyblinker.strategy_b.runner import blink_position_strategy_b
from pyblinker.strategy_c.runner import blink_position_strategy_c
from pyblinker.strategy_f.runner import channel_results_strategy_f

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True   # False → sequential (easier to debug)
VERBOSE: bool = True           # diagnostic output from Strategy F stage A/B

# ---------------------------------------------------------------------------
# Shared parameters
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
PEAK_SIDE_TOLERANCE_S = 0.01
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Set to a positive integer to process only the first N epochs (quick inspection).
N_EPOCHS: int | None = None

# ---------------------------------------------------------------------------
# Strategy B parameters
# ---------------------------------------------------------------------------
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None

# ---------------------------------------------------------------------------
# Strategy C parameters
# ---------------------------------------------------------------------------
STAGE1_THRESHOLD_SCOPE = "per_channel"
AUTOREJECT_METHOD = "bayesian_optimization"
STAGE1_SCAN_SCALE = 0.12
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT = False

# ---------------------------------------------------------------------------
# Strategy F parameters
# ---------------------------------------------------------------------------
MIN_FLAGGED_EPOCHS = 1
STD_THRESHOLD = 3.5
CENTER_METHOD = "median"

# ---------------------------------------------------------------------------
# Dataset pairs
# ---------------------------------------------------------------------------
PAIRS = [
    {
        "name": "pair_1",
        "fif": Path(r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif"),
        "csv": Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg\S1\S01_20170519_043933\ear_eog.csv"),
    },
    {
        "name": "pair_2",
        "fif": Path(r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933_2\seg_data_raw\eeg_eog_raw.fif"),
        "csv": Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg\S1\S01_20170519_043933_2\ear_eog.csv"),
    },
    {
        "name": "pair_3",
        "fif": Path(r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933_3\seg_data_raw\eeg_eog_raw.fif"),
        "csv": Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg\S1\S01_20170519_043933_3\ear_eog.csv"),
    },
]

STRATEGIES = ["A", "B", "C", "F"]


# ---------------------------------------------------------------------------
# Per-strategy runners
# ---------------------------------------------------------------------------

def _run_strategy_a(prepared, valid_epoch_indices):
    return kleifges_strategy_a(prepared, valid_epoch_indices)


def _run_strategy_b(prepared, valid_epoch_indices):
    return blink_position_strategy_b(
        prepared,
        valid_epoch_indices,
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )


def _run_strategy_c(prepared, valid_epoch_indices):
    setting = {
        "threshold_scope": STAGE1_THRESHOLD_SCOPE,
        "scan_scale": STAGE1_SCAN_SCALE,
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "autoreject_method": AUTOREJECT_METHOD,
        "autoreject_augment": AUTOREJECT_AUGMENT,
    }
    return blink_position_strategy_c(prepared, valid_epoch_indices, setting=setting)


def _run_strategy_f(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose": VERBOSE,
    }
    return channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)


_STRATEGY_RUNNERS = {
    "A": _run_strategy_a,
    "B": _run_strategy_b,
    "C": _run_strategy_c,
    "F": _run_strategy_f,
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

    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(csv_path, EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )

    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=EPOCH_DURATION_S,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )

    m = scored.best_metrics
    return {
        "pair": pair_name,
        "strategy": strategy,
        "best_channel": scored.best_result["channel"],
        "tp": m.true_positives,
        "fp": m.false_positives,
        "fn": m.false_negatives,
        "precision": m.precision,
        "recall": m.recall,
        "f1": m.f1,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _print_results(results: list[dict]) -> None:
    # Sort by pair then strategy for readable output
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
    print("STRATEGY COMPARISON RESULTS")
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


def main() -> None:
    tasks = [
        (pair["name"], pair["fif"], pair["csv"], strategy)
        for pair in PAIRS
        for strategy in STRATEGIES
    ]

    results: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        print(f"Running {len(tasks)} tasks with ThreadPoolExecutor …")
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
                    print(f"  done  pair={pair_name}  strategy={strategy}  f1={result['f1']:.4f}")
                except Exception as exc:
                    msg = f"  ERROR pair={pair_name}  strategy={strategy}: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"Running {len(tasks)} tasks sequentially …")
        for name, fif, csv, strat in tasks:
            print(f"  running  pair={name}  strategy={strat} …")
            try:
                result = run_one(name, fif, csv, strat)
                results.append(result)
                print(f"  done     pair={name}  strategy={strat}  f1={result['f1']:.4f}")
            except Exception as exc:
                msg = f"  ERROR pair={name}  strategy={strat}: {exc}"
                print(msg)
                errors.append(msg)

    if results:
        _print_results(results)

    if errors:
        print("Errors encountered:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
