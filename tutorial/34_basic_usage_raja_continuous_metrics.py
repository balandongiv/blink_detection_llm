"""Run basic BlinkDetector usage on the Raja dataset as continuous signals.

This script mirrors the detection approach in ``tutorial/01a_basic_usage.py``:
load raw FIF, keep EEG brain-region channels, run ``BlinkDetector`` on the long
continuous signal, and use its selected representative channel.

Metrics are printed in the same TP/FP/FN, precision, recall, and F1 style used
by ``tutorial/20_strategy_comparison_raja_dataset.py``.  No fixed-length epochs
are created for detection; the whole recording is scored as one continuous lane.
"""

from __future__ import annotations

import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter

import mne
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.blinker import BlinkDetector
from src.common.validation import match_blink_tables
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.matching.blink_matching import load_annotation_as_reference

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = False
N_PAIRS: int | None = None

# ---------------------------------------------------------------------------
# Dataset root paths
# ---------------------------------------------------------------------------
ANNOTATION_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
PROCESSED_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja_processed")

# ---------------------------------------------------------------------------
# Shared parameters
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
CONTINUOUS_LANE_DURATION_S = 24 * 60 * 60.0
PEAK_SIDE_TOLERANCE_S = 0.01
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = 30
N_JOBS = 2

BASIC_USAGE_BLINKER_PARAMS = {
    "std_threshold": 1.50,
    "min_event_len": 0.05,
    "min_event_sep": 0.05,
    "base_fraction": 0.1,
    "correlation_threshold_top": 0.980,
    "correlation_threshold_bottom": 0.90,
    "correlation_threshold_middle": 0.95,
    "shut_amp_fraction": 0.9,
    "blink_amp_range_1": 3,
    "blink_amp_range_2": 50,
    "good_ratio_threshold": 0.7,
    "min_good_blinks": 10,
    "keep_signals": 0,
    "correlation_threshold": 0.98,
    "p_avr_threshold": 3,
    "z_thresholds": np.array([[0.9, 0.98], [2.0, 5.0]]),
}

STRATEGY_NAME = "BlinkDetector"


def _discover_pairs() -> list[dict]:
    """Return complete Raja FIF/CSV pairs discovered from VideoFrameViewers.yaml."""
    pairs = []
    for yaml_path in sorted(ANNOTATION_BASE_DIR.rglob("VideoFrameViewers.yaml")):
        with yaml_path.open("r", encoding="utf-8") as fh:
            info = yaml.safe_load(fh)
        if (info or {}).get("status") != "complete_eeg":
            continue

        session_dir = yaml_path.parent
        rel = session_dir.relative_to(ANNOTATION_BASE_DIR)
        csv_path = session_dir / "ear_eog.csv"
        fif_path = PROCESSED_BASE_DIR / rel / "seg_data_raw" / "eeg_eog_raw.fif"

        if not csv_path.exists():
            print(f"  [skip] CSV not found: {csv_path}")
            continue
        if not fif_path.exists():
            print(f"  [skip] FIF not found: {fif_path}")
            continue

        pairs.append(
            {
                "name": str(rel).replace("\\", "/"),
                "fif": fif_path,
                "csv": csv_path,
            }
        )

    return pairs[:N_PAIRS] if N_PAIRS is not None else pairs


def _annotations_to_continuous_prediction(annotations: mne.Annotations) -> pd.DataFrame:
    """Convert detector annotations into one continuous, unepoched prediction table."""
    if len(annotations) == 0:
        return pd.DataFrame(columns=["epoch_index", "blink_onset", "blink_duration"])
    return pd.DataFrame(
        {
            "epoch_index": np.zeros(len(annotations), dtype=int),
            "blink_onset": np.asarray(annotations.onset, dtype=float),
            "blink_duration": np.asarray(annotations.duration, dtype=float),
        }
    )


def _reference_to_continuous_lane(csv_path: Path) -> pd.DataFrame:
    """Load absolute Raja labels and place all events in one continuous lane."""
    reference = load_annotation_as_reference(csv_path, CONTINUOUS_LANE_DURATION_S)
    if reference.empty:
        return reference
    reference = reference.copy()
    reference["epoch_index"] = 0
    return reference


def run_one(pair_name: str, fif_path: Path, csv_path: Path) -> dict:
    """Run continuous BlinkDetector detection on one Raja pair and score it."""
    started = perf_counter()
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(fif_path, brain_channels)

    detector = BlinkDetector(
        raw,
        visualize=False,
        annot_label=None,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        n_jobs=N_JOBS,
        use_multiprocessing=True,
        blink_params=BASIC_USAGE_BLINKER_PARAMS,
    )
    annotations, channel, n_good_blinks, df_positions, _fig_data, _selected = detector.get_blink()

    predicted = _annotations_to_continuous_prediction(annotations)
    reference = _reference_to_continuous_lane(csv_path)
    signal = detector.raw_data.get_data(picks=channel)[0]

    metrics = match_blink_tables(
        predicted,
        reference,
        n_epochs=1,
        signal_by_epoch={0: signal},
        sfreq=float(detector.sfreq),
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )

    return {
        "pair": pair_name,
        "strategy": STRATEGY_NAME,
        "best_channel": channel,
        "tp": metrics.true_positives,
        "fp": metrics.false_positives,
        "fn": metrics.false_negatives,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "detected": int(len(predicted)),
        "good_blinks": int(n_good_blinks),
        "raw_candidates": int(len(df_positions)),
        "elapsed_s": perf_counter() - started,
    }


def _print_results(results: list[dict]) -> None:
    results.sort(key=lambda r: (r["pair"], r["strategy"]))

    col_w = {
        "pair": 8,
        "strategy": 14,
        "best_channel": 14,
        "tp": 5,
        "fp": 5,
        "fn": 5,
        "precision": 10,
        "recall": 8,
        "f1": 8,
    }

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
    print("CONTINUOUS BASIC USAGE RESULTS")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for r in results:
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
    col_w = {
        "strategy": 14,
        "n_pairs": 8,
        "tp": 7,
        "fp": 7,
        "fn": 7,
        "micro_p": 10,
        "micro_r": 9,
        "micro_f1": 9,
        "macro_p": 10,
        "macro_r": 9,
        "macro_f1": 9,
    }
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
    print("OVERALL SUMMARY  (aggregated across all pairs)")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for strategy in sorted({r["strategy"] for r in results}):
        rows = [r for r in results if r["strategy"] == strategy]
        total_tp = sum(r["tp"] for r in rows)
        total_fp = sum(r["fp"] for r in rows)
        total_fn = sum(r["fn"] for r in rows)

        micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
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
    pairs = _discover_pairs()
    if not pairs:
        print("No Raja dataset pairs found.")
        return

    results: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        print(f"Running {len(pairs)} continuous BlinkDetector tasks with ThreadPoolExecutor ...")
        with ThreadPoolExecutor() as executor:
            future_to_pair = {
                executor.submit(run_one, pair["name"], pair["fif"], pair["csv"]): pair
                for pair in pairs
            }
            for future in as_completed(future_to_pair):
                pair = future_to_pair[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  done  pair={pair['name']}  f1={result['f1']:.4f}")
                except Exception:  # noqa: BLE001
                    msg = f"  ERROR pair={pair['name']}:\n{traceback.format_exc()}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"Running {len(pairs)} continuous BlinkDetector tasks sequentially ...")
        for pair in pairs:
            print(f"  running  pair={pair['name']} ...")
            try:
                result = run_one(pair["name"], pair["fif"], pair["csv"])
                results.append(result)
                print(f"  done     pair={pair['name']}  f1={result['f1']:.4f}")
            except Exception:  # noqa: BLE001
                msg = f"  ERROR pair={pair['name']}:\n{traceback.format_exc()}"
                print(msg)
                errors.append(msg)

    if results:
        _print_results(results)

    if errors:
        print("Errors encountered:")
        for error in errors:
            print(error)


if __name__ == "__main__":
    main()
