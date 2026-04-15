"""Cross-strategy channel lane evaluation utilities."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pyblinker.common.validation import (
    BlinkValidationMetrics,
    match_blink_tables,
)
from pyblinker.matching.blink_matching import enrich_absolute_times


@dataclass
class LaneScoringResult:
    """Output of :func:`evaluate_channel_lanes`."""

    lane_summary: pd.DataFrame
    """Per-channel metrics sorted by F1 descending."""

    best_result: dict
    """The channel result dict (channel, df_positions, mapped_candidates, signal_by_epoch)
    for the channel with the highest F1."""

    best_metrics: BlinkValidationMetrics
    """Validation metrics for the best channel."""

    best_predicted: pd.DataFrame
    """Enriched predicted blinks for the best channel (has absolute_onset_s / absolute_offset_s)."""


def evaluate_channel_lanes(
    channel_results: list[dict],
    ground_truth: pd.DataFrame,
    *,
    n_epochs: int,
    sfreq: float,
    epoch_duration: float,
    peak_side_tolerance_s: float = 0.01,
) -> LaneScoringResult:
    """Score every channel result against ground truth and select the best one.

    Parameters
    ----------
    channel_results:
        List of per-channel dicts as returned by
        :func:`~pyblinker.epoch_detection_strategy_a.kleifges_blinker_2017.blink_position_strategy_a`.
        Each dict must have keys: ``channel``, ``df_positions``, ``mapped_candidates``,
        ``signal_by_epoch``.
    ground_truth:
        Enriched ground_truth blink DataFrame.  Must already have ``absolute_onset_s``
        and ``absolute_offset_s`` columns — call
        :func:`~pyblinker.matching.blink_matching.enrich_absolute_times` before passing.
    n_epochs:
        Total number of epochs (used for agreement metrics).
    sfreq:
        Sampling frequency in Hz.
    epoch_duration:
        Epoch duration in seconds, used to enrich ``mapped_candidates`` with absolute times.
    peak_side_tolerance_s:
        Tolerance passed to the peak-overlap matcher.

    Returns
    -------
    LaneScoringResult
        Contains ``lane_summary``, ``best_result``, ``best_metrics``, ``best_predicted``.
    """
    lane_rows: list[dict] = []
    best_result = None
    best_metrics = None

    for channel_result in channel_results:
        predicted = enrich_absolute_times(channel_result["mapped_candidates"], epoch_duration)
        metrics = match_blink_tables(
            predicted,
            ground_truth,
            n_epochs=n_epochs,
            signal_by_epoch=channel_result["signal_by_epoch"],
            sfreq=sfreq,
            peak_side_tolerance_s=peak_side_tolerance_s,
        )
        lane_rows.append(
            {
                "channel": channel_result["channel"],
                "raw_candidate_count": int(len(channel_result["df_positions"])),
                "mapped_candidate_count": int(len(channel_result["mapped_candidates"])),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )
        if best_metrics is None or (
            metrics.f1,
            metrics.true_positives,
            -metrics.false_positives,
            channel_result["channel"],
        ) > (
            best_metrics.f1,
            best_metrics.true_positives,
            -best_metrics.false_positives,
            best_result["channel"],
        ):
            best_result = channel_result
            best_metrics = metrics

    lane_summary = (
        pd.DataFrame(lane_rows)
        .sort_values(["f1", "tp", "fp", "channel"], ascending=[False, False, True, True])
        .reset_index(drop=True)
    )
    best_predicted = enrich_absolute_times(best_result["mapped_candidates"], epoch_duration)

    return LaneScoringResult(
        lane_summary=lane_summary,
        best_result=best_result,
        best_metrics=best_metrics,
        best_predicted=best_predicted,
    )


__all__ = [
    "LaneScoringResult",
    "evaluate_channel_lanes",
]
