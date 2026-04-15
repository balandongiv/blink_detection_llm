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

from pyblinker.analysis.lane_evaluation import LaneScoringResult
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from pyblinker.evaluation_runner import score_channel_results
from pyblinker.matching.blink_matching import enrich_absolute_times

from .kleifges_blinker_2017 import blink_position_strategy_a


def channel_results_strategy_a(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Return Strategy A per-channel results in the standard format.

    Each dict has keys: ``channel``, ``df_positions``,
    ``mapped_candidates``, ``signal_by_epoch``.
    """
    return blink_position_strategy_a(prepared, valid_epoch_indices)


def run_strategy_a(
    epochs: mne.Epochs,
    ground_truth_raw: pd.DataFrame,
    *,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    epoch_duration: float = 60.0,
    peak_side_tolerance_s: float = 0.01,
) -> LaneScoringResult:
    """Run Strategy A end-to-end on ``epochs`` and return scored results.

    Parameters
    ----------
    epochs:
        Pre-loaded MNE Epochs object.
    ground_truth_raw:
        Epoch-relative ground-truth blink table (columns: ``epoch_index``,
        ``blink_onset``, ``blink_duration``).  Will be enriched internally.
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = channel_results_strategy_a(prepared, valid_epoch_indices)
    ground_truth = enrich_absolute_times(ground_truth_raw, epoch_duration)
    return score_channel_results(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


__all__ = ["channel_results_strategy_a", "run_strategy_a"]
