"""Strategy A evaluation runner.

Thin coordination layer over the existing
:func:`~pyblinker.epoch_detection_strategy_a.kleifges_blinker_2017.blink_position_strategy_a`
implementation.  ``blink_position_strategy_a`` already produces the standard
``{channel, df_positions, mapped_candidates, signal_by_epoch}`` dict format
required by :func:`~pyblinker.evaluation_runner.score_channel_results`.
"""

from __future__ import annotations

import mne
import pandas as pd

import mne

from blink_evaluation import ChannelEvaluationResult
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from src.evaluation_runner import score_channel_results

from .kleifges_blinker_2017 import kleifges_strategy


def channel_results_strategy_a(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Return Strategy A per-channel results in the standard format.

    Each dict has keys: ``channel``, ``df_positions``,
    ``mapped_candidates``, ``signal_by_epoch``.
    """
    return kleifges_strategy(prepared, valid_epoch_indices)


def run_strategy_a(
    epochs: mne.Epochs,
    gt_annotations: mne.Annotations,
    *,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    epoch_duration: float = 60.0,
) -> ChannelEvaluationResult:
    """Run Strategy A end-to-end on ``epochs`` and return scored results."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = channel_results_strategy_a(prepared, valid_epoch_indices)
    return score_channel_results(
        channel_results,
        gt_annotations,
        epoch_duration=epoch_duration,
    )


__all__ = ["channel_results_strategy_a", "run_strategy_a"]
