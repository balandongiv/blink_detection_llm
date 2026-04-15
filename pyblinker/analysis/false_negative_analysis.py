"""Cross-strategy false-negative analysis utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pyblinker.utils.peak_overlap_metric import (
    calculate_interval_overlap_ratio,
    is_peak_overlap_match,
)


def nearest_row(
    table: pd.DataFrame,
    epoch_index: int,
    onset: float,
    duration: float,
) -> pd.Series | None:
    """Return the row from table whose epoch-relative onset/duration is closest to the query.

    Searches only within the given epoch_index.  Returns None when the table is
    empty or has no rows for that epoch.
    """
    if table.empty:
        return None
    epoch_rows = table[table["epoch_index"] == epoch_index].copy()
    if epoch_rows.empty:
        return None
    epoch_rows["distance"] = (
        (epoch_rows["blink_onset"] - onset).abs()
        + (epoch_rows["blink_duration"] - duration).abs()
    )
    return epoch_rows.sort_values("distance").iloc[0]


def collect_false_negatives(
    predicted: pd.DataFrame,
    ground_truth: pd.DataFrame,
    *,
    signal_by_epoch: dict[int, np.ndarray],
    sfreq: float,
    peak_side_tolerance_s: float,
) -> pd.DataFrame:
    """Identify ground_truth blinks that were not matched by any predicted blink.

    Both *predicted* and *ground_truth* must already contain ``absolute_onset_s``
    and ``absolute_offset_s`` columns — call
    :func:`~pyblinker.matching.blink_matching.enrich_absolute_times` on each
    DataFrame before passing it here.

    Uses the same greedy peak-overlap matching algorithm as
    :func:`~pyblinker.epoch_detection_strategy_a.epoch_validation.match_blink_tables`.

    Returns a DataFrame with one row per false negative containing:
    epoch_index, blink_onset, blink_duration, absolute_onset_s,
    absolute_offset_s, nearest_pred_onset_s, nearest_pred_duration_s,
    nearest_pred_absolute_onset_s, nearest_overlap_ratio,
    nearest_onset_diff_s.
    """
    predicted = predicted.copy().reset_index(drop=True)
    ground_truth = ground_truth.copy().reset_index(drop=True)
    rows: list[dict] = []

    epoch_indices = sorted(
        set(predicted.get("epoch_index", pd.Series(dtype=int)).tolist())
        | set(ground_truth.get("epoch_index", pd.Series(dtype=int)).tolist())
    )

    for epoch_index in epoch_indices:
        pred_group = predicted[predicted["epoch_index"] == epoch_index].copy()
        ref_group = ground_truth[ground_truth["epoch_index"] == epoch_index].copy()
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
                    sfreq=sfreq,
                    peak_side_tolerance_s=peak_side_tolerance_s,
                )
                if not is_match:
                    continue
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
                if best_key is None or key < best_key:
                    best_key = key
                    best_ref_index = ref_index
            if best_ref_index is not None:
                unmatched_ref.remove(best_ref_index)

        for ref_index in sorted(unmatched_ref):
            ref_row = ref_group.loc[ref_index]
            nearest_pred = nearest_row(
                pred_group,
                int(ref_row["epoch_index"]),
                float(ref_row["blink_onset"]),
                float(ref_row["blink_duration"]),
            )
            overlap_ratio = np.nan
            onset_diff = np.nan
            if nearest_pred is not None:
                overlap_ratio = calculate_interval_overlap_ratio(
                    float(nearest_pred["blink_onset"]),
                    float(nearest_pred["blink_duration"]),
                    float(ref_row["blink_onset"]),
                    float(ref_row["blink_duration"]),
                )
                onset_diff = abs(
                    float(nearest_pred["blink_onset"]) - float(ref_row["blink_onset"])
                )
            rows.append(
                {
                    "epoch_index": int(ref_row["epoch_index"]),
                    "blink_onset": float(ref_row["blink_onset"]),
                    "blink_duration": float(ref_row["blink_duration"]),
                    "absolute_onset_s": float(ref_row["absolute_onset_s"]),
                    "absolute_offset_s": float(ref_row["absolute_offset_s"]),
                    "nearest_pred_onset_s": float(nearest_pred["blink_onset"]) if nearest_pred is not None else np.nan,
                    "nearest_pred_duration_s": float(nearest_pred["blink_duration"]) if nearest_pred is not None else np.nan,
                    "nearest_pred_absolute_onset_s": float(nearest_pred["absolute_onset_s"]) if nearest_pred is not None else np.nan,
                    "nearest_overlap_ratio": float(overlap_ratio) if overlap_ratio == overlap_ratio else np.nan,
                    "nearest_onset_diff_s": float(onset_diff) if onset_diff == onset_diff else np.nan,
                }
            )
    return pd.DataFrame(rows)


__all__ = [
    "collect_false_negatives",
    "nearest_row",
]
