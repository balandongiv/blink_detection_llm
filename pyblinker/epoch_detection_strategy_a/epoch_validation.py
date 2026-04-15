"""Validation helpers for the epoch-aware blink pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import mne
import numpy as np
import pandas as pd

from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.utils.peak_overlap_metric import (
    calculate_interval_overlap_ratio,
    is_peak_overlap_match,
)

from .bad_epoch_utils import get_valid_epoch_indices, simulate_bad_epochs
from .epoch_blink_pipeline import (
    PreparedEpochDetectionInput,
    prepare_epoch_detection_input,
    run_epoch_blink_pipeline,
)


@dataclass
class BlinkValidationMetrics:
    """Event-level and epoch-level agreement metrics."""

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    epoch_blink_agreement: float
    blink_count_agreement: float


def load_reference_blink_table(path: str | Path) -> pd.DataFrame:
    """Load the long-form ground_truth blink CSV used for validation."""

    reference = pd.read_csv(path)
    reference = reference.dropna(subset=["epoch_id", "epoch_onset_sec", "epoch_duration_sec"])
    reference = reference.rename(
        columns={
            "epoch_id": "epoch_index",
            "epoch_onset_sec": "blink_onset",
            "epoch_duration_sec": "blink_duration",
        }
    )
    columns = ["epoch_index", "blink_onset", "blink_duration"]
    return reference.loc[:, columns].reset_index(drop=True)


def filter_reference_to_valid_epochs(
    reference: pd.DataFrame,
    valid_epoch_indices: Sequence[int],
) -> pd.DataFrame:
    """Restrict the ground_truth table to the retained valid epochs."""

    if reference.empty:
        return reference.copy().reset_index(drop=True)
    filtered = reference[reference["epoch_index"].isin(valid_epoch_indices)].copy()
    return filtered.reset_index(drop=True)


def match_blink_tables(
    predicted: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    n_epochs: int,
    signal_by_epoch: Mapping[int, np.ndarray],
    sfreq: float,
    peak_side_tolerance_s: float = 0.01,
) -> BlinkValidationMetrics:
    """Greedily match predicted and ground_truth blink tables using peak-overlap."""

    predicted = predicted.copy().reset_index(drop=True)
    reference = reference.copy().reset_index(drop=True)

    tp = 0
    fp = 0
    fn = 0

    epoch_indices = sorted(
        set(predicted.get("epoch_index", pd.Series(dtype=int)).tolist())
        | set(reference.get("epoch_index", pd.Series(dtype=int)).tolist())
    )

    for epoch_index in epoch_indices:
        pred_group = predicted[predicted["epoch_index"] == epoch_index].copy()
        ref_group = reference[reference["epoch_index"] == epoch_index].copy()
        unmatched_ref = set(ref_group.index.tolist())
        epoch_signal = np.asarray(
            signal_by_epoch.get(int(epoch_index), np.array([], dtype=float)),
            dtype=float,
        )

        for _, pred_row in pred_group.sort_values("blink_onset").iterrows():
            best_key = None
            best_ref_index = None
            for ref_index in list(unmatched_ref):
                ref_row = ref_group.loc[ref_index]
                is_match = is_peak_overlap_match(
                    pred_row,
                    ref_row,
                    epoch_signal=epoch_signal,
                    sfreq=float(sfreq),
                    peak_side_tolerance_s=peak_side_tolerance_s,
                )
                key = (
                    -calculate_interval_overlap_ratio(
                        float(pred_row["blink_onset"]),
                        float(pred_row["blink_duration"]),
                        float(ref_row["blink_onset"]),
                        float(ref_row["blink_duration"]),
                    ),
                    abs(float(pred_row["blink_onset"]) - float(ref_row["blink_onset"])),
                    ref_index,
                )
                if not is_match:
                    continue
                if best_key is None or key < best_key:
                    best_key = key
                    best_ref_index = ref_index

            if best_ref_index is None:
                fp += 1
                continue

            unmatched_ref.remove(best_ref_index)
            tp += 1

        fn += len(unmatched_ref)

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (
        float(2.0 * precision * recall / (precision + recall))
        if (precision + recall) > 0.0
        else 0.0
    )

    pred_epoch_counts = (
        predicted.groupby("epoch_index").size().reindex(range(n_epochs), fill_value=0)
    )
    ref_epoch_counts = (
        reference.groupby("epoch_index").size().reindex(range(n_epochs), fill_value=0)
    )
    epoch_blink_agreement = float(
        (pred_epoch_counts.gt(0) == ref_epoch_counts.gt(0)).mean()
    )
    blink_count_agreement = float((pred_epoch_counts == ref_epoch_counts).mean())

    return BlinkValidationMetrics(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        epoch_blink_agreement=epoch_blink_agreement,
        blink_count_agreement=blink_count_agreement,
    )


def run_random_drop_validation(
    epochs: mne.Epochs,
    reference_table: pd.DataFrame,
    *,
    drop_ratios: Sequence[float],
    random_states: Sequence[int],
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    n_jobs: int = 2,
    use_multiprocessing: bool = True,
    pick_types_options: dict | None = None,
    blink_params: dict | None = None,
    peak_side_tolerance_s: float = 0.01,
) -> pd.DataFrame:
    """Run repeated random-drop experiments against the ground_truth table."""

    base_epochs = epochs.copy()
    prepared = prepare_epoch_detection_input(
        base_epochs,
        pick_types_options=pick_types_options,
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
    )
    params = BlinkDetector._build_detector_params(blink_params, {})
    params["sfreq"] = float(prepared.sfreq)

    rows: list[dict[str, object]] = []
    for drop_ratio in drop_ratios:
        for random_state in random_states:
            simulated_epochs, bad_indices = simulate_bad_epochs(
                base_epochs,
                drop_ratio=float(drop_ratio),
                random_state=int(random_state),
            )
            valid_epoch_indices = get_valid_epoch_indices(simulated_epochs)
            result = run_epoch_blink_pipeline(
                epochs=simulated_epochs,
                prepared=prepared,
                params=params,
                valid_epoch_indices=valid_epoch_indices,
                n_jobs=n_jobs,
                use_multiprocessing=use_multiprocessing,
            )
            filtered_reference = filter_reference_to_valid_epochs(
                reference_table,
                valid_epoch_indices,
            )
            metrics = match_blink_tables(
                result.blink_table,
                filtered_reference,
                n_epochs=len(simulated_epochs),
                signal_by_epoch={
                    int(epoch_index): prepared.data[epoch_index, prepared.channel_names.index(result.channel), :].astype(float)
                    for epoch_index in range(prepared.data.shape[0])
                },
                sfreq=float(prepared.sfreq),
                peak_side_tolerance_s=peak_side_tolerance_s,
            )
            row = {
                "drop_ratio": float(drop_ratio),
                "random_state": int(random_state),
                "n_bad_epochs": int(len(bad_indices)),
                "n_valid_epochs": int(len(valid_epoch_indices)),
                "channel": result.channel,
                "predicted_blinks": int(len(result.blink_table)),
                "reference_blinks": int(len(filtered_reference)),
            }
            row.update(asdict(metrics))
            rows.append(row)

    return pd.DataFrame(rows)


def assert_validation_target(summary: pd.DataFrame, *, min_f1: float = 0.9) -> None:
    """Raise if any validation run falls below the requested F1 threshold."""

    if summary.empty:
        raise AssertionError("Validation summary is empty.")
    observed = float(summary["f1"].min())
    if observed < float(min_f1):
        raise AssertionError(f"Minimum F1 {observed:.4f} is below the target {min_f1:.4f}.")


__all__ = [
    "BlinkValidationMetrics",
    "assert_validation_target",
    "filter_reference_to_valid_epochs",
    "load_reference_blink_table",
    "match_blink_tables",
    "run_random_drop_validation",
]
