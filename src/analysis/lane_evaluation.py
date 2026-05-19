"""Cross-strategy channel lane evaluation utilities.

Evaluation is performed with the ``blink_evaluation`` library using IoU-based
event matching.  The ``peak_side_tolerance_s`` parameter is forwarded as
interval padding (``pad``) in the IoU matcher so the tolerance sweep in
experiment 4 continues to work without modification.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from blink_evaluation import evaluate_annotations
from blink_evaluation.io import dataframe_to_annotations

from src.common.validation import BlinkValidationMetrics
from src.matching.blink_matching import enrich_absolute_times


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
    iou_threshold: float = 0.1,
) -> LaneScoringResult:
    """Score every channel result against ground truth and select the best one.

    Parameters
    ----------
    channel_results:
        List of per-channel dicts as returned by the strategy runners.
        Each dict must have keys: ``channel``, ``df_positions``, ``mapped_candidates``,
        ``signal_by_epoch``.
    ground_truth:
        Enriched ground-truth blink DataFrame.  Must already have ``absolute_onset_s``
        and ``absolute_offset_s`` columns — call
        :func:`~src.matching.blink_matching.enrich_absolute_times` before passing.
    n_epochs:
        Total number of epochs (kept for API compatibility, not used internally).
    sfreq:
        Sampling frequency in Hz (kept for API compatibility, not used internally).
    epoch_duration:
        Epoch duration in seconds, used to enrich ``mapped_candidates`` with absolute times.
    peak_side_tolerance_s:
        Forwarded as interval padding in the IoU matcher (``pad``).  A value of 0.05 s
        expands each predicted and reference interval by 0.05 s on each side before
        computing intersection-over-union.
    iou_threshold:
        Minimum IoU (after padding) required for a predicted–reference pair to count
        as a true positive.

    Returns
    -------
    LaneScoringResult
        Contains ``lane_summary``, ``best_result``, ``best_metrics``, ``best_predicted``.
    """
    gt_annotations = dataframe_to_annotations(ground_truth)

    lane_rows: list[dict] = []
    best_result = None
    best_metrics: BlinkValidationMetrics | None = None

    for channel_result in channel_results:
        predicted = enrich_absolute_times(channel_result["mapped_candidates"], epoch_duration)
        pred_annotations = dataframe_to_annotations(predicted)

        eval_result = evaluate_annotations(
            gt_annotations,
            pred_annotations,
            target_label="blink",
            iou_threshold=iou_threshold,
            pad=peak_side_tolerance_s,
        )

        em = eval_result.event_metrics
        metrics = BlinkValidationMetrics(
            true_positives=em.tp,
            false_positives=em.fp,
            false_negatives=em.fn,
            precision=em.precision,
            recall=em.recall,
            f1=em.f1,
            epoch_blink_agreement=0.0,
            blink_count_agreement=0.0,
        )

        lane_rows.append(
            {
                "channel": channel_result["channel"],
                "raw_candidate_count": int(len(channel_result["df_positions"])),
                "mapped_candidate_count": int(len(channel_result["mapped_candidates"])),
                "tp": em.tp,
                "fp": em.fp,
                "fn": em.fn,
                "precision": em.precision,
                "recall": em.recall,
                "f1": em.f1,
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
