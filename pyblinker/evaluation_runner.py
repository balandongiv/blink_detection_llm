"""Standardized evaluation runner for all blink-detection strategies.

All strategy runs must route through :func:`score_channel_results` so that
every strategy is scored identically and ``scored.best_metrics`` is always
available at the call site.
"""

from __future__ import annotations

import pandas as pd

from pyblinker.analysis.lane_evaluation import LaneScoringResult, evaluate_channel_lanes
from pyblinker.dataset_config import EPOCH_DURATION_S, PEAK_SIDE_TOLERANCE_S


def score_channel_results(
    channel_results: list[dict],
    ground_truth: pd.DataFrame,
    *,
    n_epochs: int,
    sfreq: float,
    epoch_duration: float = EPOCH_DURATION_S,
    peak_side_tolerance_s: float = PEAK_SIDE_TOLERANCE_S,
) -> LaneScoringResult:
    """Score per-channel detection results against ground truth.

    Parameters
    ----------
    channel_results:
        List of per-channel dicts as produced by any strategy runner.
        Each dict must have keys: ``channel``, ``df_positions``,
        ``mapped_candidates``, ``signal_by_epoch``.
    ground_truth:
        Enriched ground-truth blink DataFrame.  Must already have
        ``absolute_onset_s`` and ``absolute_offset_s`` columns — call
        :func:`~pyblinker.matching.blink_matching.enrich_absolute_times`
        before passing.
    n_epochs:
        Total number of epochs (used for epoch-level agreement metrics).
    sfreq:
        Sampling frequency in Hz.
    epoch_duration:
        Epoch duration in seconds.  Defaults to :data:`~pyblinker.dataset_config.EPOCH_DURATION_S`.
    peak_side_tolerance_s:
        Tolerance for the peak-overlap matcher.

    Returns
    -------
    LaneScoringResult
        Contains ``lane_summary``, ``best_result``, ``best_metrics``,
        ``best_predicted``.  Access ``scored.best_metrics`` for the primary
        per-strategy metric summary.
    """
    return evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=n_epochs,
        sfreq=sfreq,
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


__all__ = ["score_channel_results"]
