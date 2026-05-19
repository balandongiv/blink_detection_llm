"""Standardized evaluation runner for all blink-detection strategies.

All strategy runs must route through :func:`score_channel_results` so that
every strategy is scored identically.
"""

from __future__ import annotations

import mne

from blink_evaluation import ChannelEvaluationResult, evaluate_channels
from src.dataset_config import EPOCH_DURATION_S


def score_channel_results(
    channel_results: list[dict],
    gt_annotations: mne.Annotations,
    *,
    epoch_duration: float = EPOCH_DURATION_S,
) -> ChannelEvaluationResult:
    """Score per-channel detection results against ground truth.

    Parameters
    ----------
    channel_results:
        List of per-channel dicts as produced by any strategy runner.
        Each dict must have keys: ``channel``, ``df_positions``,
        ``mapped_candidates``, ``signal_by_epoch``.
    gt_annotations:
        Ground-truth blink annotations as ``mne.Annotations``.  Use
        :func:`~blink_evaluation.load_ground_truth_annotations` to load from CSV.
    epoch_duration:
        Epoch duration in seconds.  Defaults to :data:`~src.dataset_config.EPOCH_DURATION_S`.

    Returns
    -------
    ChannelEvaluationResult
        Contains ``lane_summary``, ``best_channel``, ``best_eval_result``,
        ``best_channel_result``, and ``best_predicted``.
    """
    return evaluate_channels(
        channel_results,
        gt_annotations,
        epoch_duration=epoch_duration,
    )


__all__ = ["score_channel_results"]
