"""Create annotation CSVs for Strategy F false negatives on one Raja segment.

This script is intentionally scoped to:

    S1/S01_20170519_043933

It writes an annotation-compatible CSV next to the manual annotation file:

    blink_fail_f.csv

Every row in that file is a manual blink missed by Strategy F, with
``description`` set to ``blink_fail_f`` so the failures can be opened as a
separate annotation layer.  A second diagnostics CSV preserves the original
manual blink label and nearest-prediction information for later analysis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mne
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.analysis.false_negative_analysis import collect_false_negatives
from pyblinker.analysis.lane_evaluation import evaluate_channel_lanes
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from pyblinker.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference
from pyblinker.strategy_a.kleifges_blinker_2017 import kleifges_strategy_a
from pyblinker.strategy_f.runner import channel_results_strategy_f


SEGMENT_RELATIVE_PATH = Path("S1") / "S01_20170519_043933_3"
ANNOTATION_DIR = (
    Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
    / SEGMENT_RELATIVE_PATH
)
CSV_PATH = ANNOTATION_DIR / "ear_eog.csv"
FIF_PATH = (
    Path(r"D:\dataset\drowsy_driving_raja_processed")
    / SEGMENT_RELATIVE_PATH
    / "seg_data_raw"
    / "eeg_eog_raw.fif"
)
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"

OUTPUT_ANNOTATION_CSV = ANNOTATION_DIR / "blink_fail_f.csv"
OUTPUT_DETAILS_CSV = ANNOTATION_DIR / "blink_fail_f_details.csv"

EPOCH_DURATION_S = 3.0
PEAK_SIDE_TOLERANCE_S = 0.01
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Match tutorial/20_strategy_comparison_raja_dataset.py Strategy F settings.
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD = 3.5
CENTER_METHOD = "median"
MIN_FLAGGED_EPOCHS = 1
VERBOSE = False


def _run_strategy_f(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose": VERBOSE,
    }
    return channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)


def _score_strategy(
    strategy_name: str,
    channel_results: list[dict],
    ground_truth: pd.DataFrame,
    *,
    n_epochs: int,
    sfreq: float,
) -> tuple[object, pd.DataFrame]:
    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=n_epochs,
        sfreq=sfreq,
        epoch_duration=EPOCH_DURATION_S,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )
    false_negatives = collect_false_negatives(
        scored.best_predicted,
        ground_truth,
        signal_by_epoch=scored.best_result["signal_by_epoch"],
        sfreq=sfreq,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    ).sort_values(["absolute_onset_s", "epoch_index", "blink_onset"], ignore_index=True)

    metrics = scored.best_metrics
    print(
        f"{strategy_name}: channel={scored.best_result['channel']} "
        f"TP={metrics.true_positives} FP={metrics.false_positives} "
        f"FN={metrics.false_negatives} recall={metrics.recall:.4f} "
        f"f1={metrics.f1:.4f}"
    )
    return scored, false_negatives


def _manual_annotations_with_epoch_columns(csv_path: Path) -> pd.DataFrame:
    manual = pd.read_csv(csv_path).dropna(subset=["onset", "duration"]).copy()
    manual["source_index"] = np.arange(len(manual), dtype=int)
    manual["epoch_index"] = (manual["onset"].astype(float) // EPOCH_DURATION_S).astype(int)
    manual["blink_onset"] = manual["onset"].astype(float) - (
        manual["epoch_index"].astype(float) * EPOCH_DURATION_S
    )
    manual["blink_duration"] = manual["duration"].astype(float)
    return manual


def _attach_original_manual_labels(
    false_negatives: pd.DataFrame,
    manual: pd.DataFrame,
) -> pd.DataFrame:
    if false_negatives.empty:
        return false_negatives.copy()

    rows: list[dict] = []
    for _, fn_row in false_negatives.iterrows():
        same_epoch = manual[manual["epoch_index"] == int(fn_row["epoch_index"])].copy()
        if same_epoch.empty:
            source = None
        else:
            same_epoch["match_distance"] = (
                (same_epoch["blink_onset"] - float(fn_row["blink_onset"])).abs()
                + (same_epoch["blink_duration"] - float(fn_row["blink_duration"])).abs()
            )
            source = same_epoch.sort_values("match_distance", kind="mergesort").iloc[0]

        row = fn_row.to_dict()
        if source is None:
            row.update(
                {
                    "source_index": np.nan,
                    "source_description": "",
                    "source_onset": np.nan,
                    "source_duration": np.nan,
                }
            )
        else:
            row.update(
                {
                    "source_index": int(source["source_index"]),
                    "source_description": str(source.get("description", "")),
                    "source_onset": float(source["onset"]),
                    "source_duration": float(source["duration"]),
                }
            )
        rows.append(row)

    return pd.DataFrame(rows)


def _mark_strategy_a_recovery(
    f_false_negatives: pd.DataFrame,
    a_false_negatives: pd.DataFrame,
) -> pd.DataFrame:
    details = f_false_negatives.copy()
    if details.empty:
        details["detected_by_strategy_a"] = pd.Series(dtype=bool)
        return details

    a_fn_keys = {
        (int(row.epoch_index), round(float(row.blink_onset), 6), round(float(row.blink_duration), 6))
        for row in a_false_negatives.itertuples(index=False)
    }
    details["detected_by_strategy_a"] = [
        (
            int(row.epoch_index),
            round(float(row.blink_onset), 6),
            round(float(row.blink_duration), 6),
        )
        not in a_fn_keys
        for row in details.itertuples(index=False)
    ]
    return details


def _write_annotation_csv(false_negatives: pd.DataFrame, output_path: Path) -> None:
    if false_negatives.empty:
        annotation = pd.DataFrame(columns=["onset", "duration", "description"])
    else:
        annotation = pd.DataFrame(
            {
                "onset": false_negatives["absolute_onset_s"].astype(float),
                "duration": false_negatives["blink_duration"].astype(float),
                "description": "blink_fail_f",
            }
        )
    annotation.to_csv(output_path, index=False)


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Manual annotation CSV not found: {CSV_PATH}")
    if not FIF_PATH.exists():
        raise FileNotFoundError(f"Processed FIF not found: {FIF_PATH}")

    print(f"Segment: {SEGMENT_RELATIVE_PATH.as_posix()}")
    print(f"Manual annotations: {CSV_PATH}")
    print(f"Processed FIF: {FIF_PATH}")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
    epochs = mne.make_fixed_length_epochs(
        raw,
        duration=EPOCH_DURATION_S,
        preload=True,
        verbose="ERROR",
    )
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(CSV_PATH, EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )

    f_scored, f_false_negatives = _score_strategy(
        "Strategy F",
        _run_strategy_f(prepared, valid_epoch_indices),
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
    )
    _, a_false_negatives = _score_strategy(
        "Strategy A",
        kleifges_strategy_a(prepared, valid_epoch_indices),
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
    )

    manual = _manual_annotations_with_epoch_columns(CSV_PATH)
    details = _attach_original_manual_labels(f_false_negatives, manual)
    details = _mark_strategy_a_recovery(details, a_false_negatives)
    details.insert(0, "strategy_f_best_channel", f_scored.best_result["channel"])
    details.to_csv(OUTPUT_DETAILS_CSV, index=False)

    _write_annotation_csv(f_false_negatives, OUTPUT_ANNOTATION_CSV)

    type_counts = (
        details["source_description"].value_counts(dropna=False).sort_index()
        if "source_description" in details
        else pd.Series(dtype=int)
    )
    print(f"Wrote annotation CSV: {OUTPUT_ANNOTATION_CSV}")
    print(f"Wrote details CSV: {OUTPUT_DETAILS_CSV}")
    print(f"Strategy F missed blink count: {len(f_false_negatives)}")
    if not type_counts.empty:
        print("Missed blink types:")
        for label, count in type_counts.items():
            print(f"  {label}: {count}")


if __name__ == "__main__":
    main()
