"""Peak-overlap utilities for matching predicted blinks to ground_truth labels."""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


def calculate_interval_overlap_ratio(
    pred_onset: float,
    pred_duration: float,
    ref_onset: float,
    ref_duration: float,
) -> float:
    """Return overlap divided by the shorter interval length."""

    pred_end = pred_onset + max(float(pred_duration), 0.0)
    ref_end = ref_onset + max(float(ref_duration), 0.0)
    overlap = max(0.0, min(pred_end, ref_end) - max(pred_onset, ref_onset))
    denom = max(min(pred_end - pred_onset, ref_end - ref_onset), 1e-12)
    return overlap / denom


def interval_to_samples(
    onset_s: float,
    duration_s: float,
    *,
    sfreq: float,
    n_samples: int,
) -> Tuple[int, int]:
    """Convert a time interval in seconds into clipped sample bounds."""

    start = int(np.clip(np.floor(float(onset_s) * sfreq), 0, max(n_samples - 1, 0)))
    end = int(
        np.clip(
            np.ceil((float(onset_s) + max(float(duration_s), 0.0)) * sfreq),
            start + 1,
            n_samples,
        )
    )
    return start, end


def is_peak_overlap_match(
    pred_row: pd.Series,
    ref_row: pd.Series,
    *,
    epoch_signal: np.ndarray,
    sfreq: float,
    peak_side_tolerance_s: float = 0.01,
) -> bool:
    """Return True when prediction/ground_truth share the blink peak and its local support."""

    if epoch_signal.size == 0:
        return False

    pred_start, pred_end = interval_to_samples(
        float(pred_row["blink_onset"]),
        float(pred_row["blink_duration"]),
        sfreq=sfreq,
        n_samples=len(epoch_signal),
    )
    ref_start, ref_end = interval_to_samples(
        float(ref_row["blink_onset"]),
        float(ref_row["blink_duration"]),
        sfreq=sfreq,
        n_samples=len(epoch_signal),
    )

    overlap_start = max(pred_start, ref_start)
    overlap_end = min(pred_end, ref_end)
    if overlap_end <= overlap_start:
        return False

    union_start = min(pred_start, ref_start)
    union_end = max(pred_end, ref_end)
    union_signal = epoch_signal[union_start:union_end]
    if union_signal.size == 0:
        return False

    peak_index = union_start + int(np.argmax(union_signal))
    if not (overlap_start <= peak_index < overlap_end):
        return False

    side_frames = max(1, int(round(float(peak_side_tolerance_s) * sfreq)))
    left_probe = max(union_start, peak_index - side_frames)
    right_probe = min(union_end - 1, peak_index + side_frames)
    return (overlap_start <= left_probe < overlap_end) and (
        overlap_start <= right_probe < overlap_end
    )


__all__ = [
    "calculate_interval_overlap_ratio",
    "interval_to_samples",
    "is_peak_overlap_match",
]
