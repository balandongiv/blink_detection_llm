"""Formatting, reporting, and visualization utilities for blink event comparisons.

Internally, comparisons rely on sample index units (1-based). Reporting helpers may
convert sample indices to time (seconds) using a caller-provided sampling rate for
readability.
"""

from __future__ import annotations

from typing import Iterable, Optional

import logging

import numpy as np
import pandas as pd

from pyblinker.utils.annotation_utils import (
    DIFF_EVENT_LABEL_DETECTED,
    DIFF_EVENT_LABEL_GROUND_TRUTH,
    DIFF_EVENT_LABEL_MATCH,
)

from . import similarity
from .similarity import Alignment


logger = logging.getLogger(__name__)


def _to_seconds(
    sample_index: Optional[float], sampling_rate_hz: float
) -> Optional[float]:
    if sample_index is None:
        return None
    return (float(sample_index) - 1.0) / sampling_rate_hz


def preview_side_by_side(
    detected_df: pd.DataFrame, ground_truth_df: pd.DataFrame, n: int
) -> pd.DataFrame:
    """Return the first ``n`` blink intervals from each table for quick inspection.

    All values are shown in sample index units (1-based).
    """

    similarity.validate_event_table(detected_df)
    similarity.validate_event_table(ground_truth_df)

    n = max(0, int(n))
    return pd.DataFrame(
        {
            "ground_truth_start": ground_truth_df["start_blink"]
            .astype(int)
            .to_numpy()[:n],
            "detected_start": detected_df["start_blink"].astype(int).to_numpy()[:n],
            "ground_truth_end": ground_truth_df["end_blink"].astype(int).to_numpy()[:n],
            "detected_end": detected_df["end_blink"].astype(int).to_numpy()[:n],
        }
    )


def print_comparison_summary(
    metrics_dict: dict[str, float], tolerance_samples: int
) -> None:
    """Print a human-readable summary of alignment metrics.

    Summaries are expressed in sample index units. Percentages are derived from counts
    in ``metrics_dict``.
    """

    logger.info("[comparison] Blink event alignment summary:")
    logger.info("  • Tolerance: ±%d samples", tolerance_samples)
    logger.info(
        "  • Total ground truth events: %d",
        int(metrics_dict.get("total_ground_truth", 0)),
    )
    logger.info(
        "  • Total detected events: %d",
        int(metrics_dict.get("total_detected", 0)),
    )

    gt_only = int(metrics_dict.get("ground_truth_only", 0))
    det_only = int(metrics_dict.get("detected_only", 0))
    share_count = int(metrics_dict.get("share_within_tolerance", 0))
    share_percent = metrics_dict.get("share_within_tolerance_percent", float("nan"))

    logger.info("  • Ground truth-only events: %d", gt_only)
    logger.info("  • Detected-only events: %d", det_only)
    total_unique = share_count + gt_only + det_only
    if np.isfinite(share_percent) and total_unique:
        logger.info(
            "  • Share of total unique events within tolerance: %d/%d (%.2f%%)",
            share_count,
            total_unique,
            share_percent,
        )
    else:
        logger.info("  • Share of total unique events within tolerance: n/a")


def make_diff_table(
    detected_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    alignments: Iterable[Alignment],
    tolerance_samples: int,
    max_rows: int,
    sampling_rate_hz: float,
) -> pd.DataFrame:
    """Build a diff table summarizing mismatches outside the tolerance window.

    All comparisons are performed in sample index units (1-based). Time values in the
    resulting table are derived from the provided ``sampling_rate_hz`` purely for
    display. The table includes two columns that describe how each paired
    event is classified:

    ``match_category``
        * ``"share_within_tolerance"`` — amplitude/overlap checks passed for the
          pair. The event may still sit outside the tolerance window if
          ``within_tolerance`` is ``False``.
        * ``"matches_within_tolerance"`` — start and end boundaries fall inside
          the tolerance window, but at least one amplitude/overlap requirement
          failed.
        * ``"pairs_outside_tolerance"`` — the pair violates the tolerance window
          regardless of amplitude/overlap success.
    ``within_tolerance``
        Boolean flag indicating whether the start and end differences for a
        paired event lie within ``±tolerance_samples``. Rows without a pairing
        retain ``NaN`` for both ``match_category`` and ``within_tolerance``.
    """

    similarity.validate_event_table(detected_df)
    similarity.validate_event_table(ground_truth_df)

    detected_start = detected_df["start_blink"].astype(int).to_numpy()
    detected_end = detected_df["end_blink"].astype(int).to_numpy()
    gt_start = ground_truth_df["start_blink"].astype(int).to_numpy()
    gt_end = ground_truth_df["end_blink"].astype(int).to_numpy()

    detected_amp_series = detected_df.get("max_amplitude")
    if detected_amp_series is not None:
        detected_amp = detected_amp_series.to_numpy(dtype=np.float64)
    else:
        detected_amp = np.full(detected_start.shape, np.nan, dtype=float)

    gt_amp_series = ground_truth_df.get("max_amplitude")
    if gt_amp_series is not None:
        gt_amp = gt_amp_series.to_numpy(dtype=np.float64)
    else:
        gt_amp = np.full(gt_start.shape, np.nan, dtype=float)

    rows: list[dict[str, object]] = []

    for alignment in alignments:
        if alignment.ground_truth_idx is None and alignment.detected_idx is None:
            continue

        status = "overlap" if alignment.overlap_samples > 0 else "no_overlap"
        match_category = np.nan
        within_tolerance = np.nan

        if alignment.ground_truth_idx is None:
            idx = alignment.detected_idx
            assert idx is not None
            det_amp_val = (
                float(detected_amp[idx]) if idx < detected_amp.size else np.nan
            )
            rows.append(
                {
                    "ground_truth_idx": np.nan,
                    "detected_idx": float(idx),
                    "ground_truth_start": np.nan,
                    "ground_truth_end": np.nan,
                    "detected_start": float(detected_start[idx]),
                    "detected_end": float(detected_end[idx]),
                    "detected_max_amplitude": det_amp_val,
                    "ground_truth_max_amplitude": np.nan,
                    "max_amplitude": det_amp_val,
                    "start_diff": np.nan,
                    "end_diff": np.nan,
                    "status": status,
                    "event_label": DIFF_EVENT_LABEL_DETECTED,
                    "match_category": match_category,
                    "within_tolerance": within_tolerance,
                    "onset": _to_seconds(detected_start[idx], sampling_rate_hz),
                }
            )
            continue

        if alignment.detected_idx is None:
            idx = alignment.ground_truth_idx
            assert idx is not None
            gt_amp_val = float(gt_amp[idx]) if idx < gt_amp.size else np.nan
            rows.append(
                {
                    "ground_truth_idx": float(idx),
                    "detected_idx": np.nan,
                    "ground_truth_start": float(gt_start[idx]),
                    "ground_truth_end": float(gt_end[idx]),
                    "detected_start": np.nan,
                    "detected_end": np.nan,
                    "detected_max_amplitude": np.nan,
                    "ground_truth_max_amplitude": gt_amp_val,
                    "max_amplitude": gt_amp_val,
                    "start_diff": np.nan,
                    "end_diff": np.nan,
                    "status": status,
                    "event_label": DIFF_EVENT_LABEL_GROUND_TRUTH,
                    "match_category": match_category,
                    "within_tolerance": within_tolerance,
                    "onset": _to_seconds(gt_start[idx], sampling_rate_hz),
                }
            )
            continue

        if alignment.start_diff is None or alignment.end_diff is None:
            continue

        idx_gt = alignment.ground_truth_idx
        idx_det = alignment.detected_idx
        assert idx_gt is not None and idx_det is not None
        within_tolerance = (
            abs(alignment.start_diff) <= tolerance_samples
            and abs(alignment.end_diff) <= tolerance_samples
        )

        if alignment.conditions_satisfied:
            match_category = "share_within_tolerance"
        elif within_tolerance:
            match_category = "matches_within_tolerance"
        else:
            match_category = "pairs_outside_tolerance"

        start_sample = int(min(gt_start[idx_gt], detected_start[idx_det]))
        det_amp_val = (
            float(detected_amp[idx_det]) if idx_det < detected_amp.size else np.nan
        )
        gt_amp_val = float(gt_amp[idx_gt]) if idx_gt < gt_amp.size else np.nan
        amp_values = [val for val in (gt_amp_val, det_amp_val) if np.isfinite(val)]
        avg_amp = float(np.mean(amp_values)) if amp_values else np.nan
        rows.append(
            {
                "ground_truth_idx": float(idx_gt),
                "detected_idx": float(idx_det),
                "ground_truth_start": float(gt_start[idx_gt]),
                "ground_truth_end": float(gt_end[idx_gt]),
                "detected_start": float(detected_start[idx_det]),
                "detected_end": float(detected_end[idx_det]),
                "detected_max_amplitude": det_amp_val,
                "ground_truth_max_amplitude": gt_amp_val,
                "max_amplitude": avg_amp,
                "start_diff": float(alignment.start_diff),
                "end_diff": float(alignment.end_diff),
                "status": status,
                "event_label": DIFF_EVENT_LABEL_MATCH,
                "match_category": match_category,
                "within_tolerance": bool(within_tolerance),
                "onset": _to_seconds(start_sample, sampling_rate_hz),
            }
        )

    diff_df = pd.DataFrame(rows)
    if not diff_df.empty:
        diff_df = diff_df.sort_values(
            by=["onset", "ground_truth_idx", "detected_idx"],
            kind="mergesort",
            na_position="last",
        ).copy()
        diff_df["onset"] = diff_df["onset"].round(6)

        preview_rows = max_rows if max_rows is not None else len(diff_df)
        diff_df.attrs["preview"] = diff_df.head(preview_rows).to_dict(orient="list")
    return diff_df
