"""Strategy F evaluation runner.

Two-stage thresholding approach:
  Stage A — autoreject epoch-level screening (identifies suspicious epochs)
  Stage B — robust median+MAD threshold computed from the flagged epochs
  Stage C — blink region detection via scan_threshold_crossings_kleifges
"""

from __future__ import annotations

import mne
import pandas as pd

from pyblinker.analysis.lane_evaluation import LaneScoringResult
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from pyblinker.evaluation_runner import score_channel_results
from pyblinker.matching.blink_matching import enrich_absolute_times

from .core import blink_position_strategy_f


def channel_results_strategy_f(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    setting: dict | None = None,
) -> list[dict]:
    """Return Strategy F per-channel results in the standard format.

    Each dict has keys: ``channel``, ``df_positions``,
    ``mapped_candidates``, ``signal_by_epoch``.
    """
    return blink_position_strategy_f(prepared, valid_epoch_indices, setting=setting)


def run_strategy_f(
    epochs: mne.Epochs,
    ground_truth_raw: pd.DataFrame,
    *,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    epoch_duration: float = 60.0,
    peak_side_tolerance_s: float = 0.01,
    autoreject_random_state: int = 42,
    std_threshold: float = 1.5,
    k_confirm: float | None = None,
    k_flagged: float | None = None,
    k_nonflagged: float | None = None,
) -> LaneScoringResult:
    """Run Strategy F end-to-end on ``epochs`` and return scored results.

    Parameters
    ----------
    epochs:
        Pre-loaded MNE Epochs object.
    ground_truth_raw:
        Epoch-relative ground-truth blink table (columns: ``epoch_index``,
        ``blink_onset``, ``blink_duration``).  Will be enriched internally.
    filter_low:
        High-pass filter cut-off in Hz.
    filter_high:
        Low-pass filter cut-off in Hz.
    resample_rate:
        If not None, data are resampled to this rate before processing.
    epoch_duration:
        Duration of each epoch in seconds.
    peak_side_tolerance_s:
        Tolerance in seconds for matching detected blinks to ground truth.
    autoreject_random_state:
        Random seed forwarded to autoreject in Stage A.
    std_threshold:
        Multiplier ``k`` for the MAD dispersion term in Stage B.
    k_confirm:
        If not None, Stage D peak confirmation threshold multiplier.
        Only events whose peak amplitude satisfies
        ``peak >= center + k_confirm * dispersion`` are kept.
    k_flagged:
        G3 mode: threshold multiplier for autoreject-flagged epochs.
        Must be set together with ``k_nonflagged``.
    k_nonflagged:
        G3 mode: threshold multiplier for non-flagged epochs (threshold
        estimated from all valid epochs).
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    setting = {
        "autoreject_random_state": autoreject_random_state,
        "std_threshold": std_threshold,
        "k_confirm": k_confirm,
        "k_flagged": k_flagged,
        "k_nonflagged": k_nonflagged,
    }
    channel_results = channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)
    ground_truth = enrich_absolute_times(ground_truth_raw, epoch_duration)
    return score_channel_results(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


__all__ = ["channel_results_strategy_f", "run_strategy_f"]
