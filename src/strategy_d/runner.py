"""Strategy D evaluation runner.

Produces the standardized ``{channel, df_positions, mapped_candidates,
signal_by_epoch}`` format required by
:func:`~pyblinker.evaluation_runner.score_channel_results`.
"""

from __future__ import annotations

import mne
import numpy as np
import pandas as pd

from blink_evaluation import ChannelEvaluationResult
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from src.common.pipeline_utils import build_signal_by_epoch
from src.evaluation_runner import score_channel_results

from .core import detect_peaks_per_channel


def blink_position_strategy_d(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    rescale_threshold: bool = True,
    half_window_s: float = 0.10,
    autoreject_method: str = "bayesian_optimization",
    autoreject_random_state: int = 42,
) -> list[dict]:
    """Run Strategy D blink detection on each channel.

    Returns a list of per-channel dicts, each with keys:
    ``channel``, ``df_positions``, ``mapped_candidates``, ``signal_by_epoch``.

    ``df_positions`` is a DataFrame whose row count equals the raw peak count
    before epoch mapping (used for ``raw_candidate_count`` in lane summaries).
    ``mapped_candidates`` is the epoch-relative blink table.
    """
    raw_results = detect_peaks_per_channel(
        prepared,
        valid_epoch_indices,
        rescale_threshold=rescale_threshold,
        half_window_s=half_window_s,
        autoreject_method=autoreject_method,
        autoreject_random_state=autoreject_random_state,
    )
    results: list[dict] = []
    for cr in raw_results:
        channel_name: str = cr["channel"]
        ch_idx = list(prepared.channel_names).index(channel_name)

        peak_locs = cr["peak_locs"]
        df_positions = pd.DataFrame(
            {"peak_sample": peak_locs.tolist(), "channel": channel_name}
        ) if len(peak_locs) > 0 else pd.DataFrame(columns=["peak_sample", "channel"])

        results.append(
            {
                "channel": channel_name,
                "df_positions": df_positions,
                "mapped_candidates": cr["candidates"],
                "signal_by_epoch": build_signal_by_epoch(prepared, ch_idx),
            }
        )
    return results


def run_strategy_d(
    epochs: mne.Epochs,
    gt_annotations: mne.Annotations,
    *,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    rescale_threshold: bool = True,
    half_window_s: float = 0.10,
    autoreject_method: str = "bayesian_optimization",
    autoreject_random_state: int = 42,
    epoch_duration: float = 60.0,
) -> ChannelEvaluationResult:
    """Run Strategy D end-to-end on ``epochs`` and return scored results."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = blink_position_strategy_d(
        prepared,
        valid_epoch_indices,
        rescale_threshold=rescale_threshold,
        half_window_s=half_window_s,
        autoreject_method=autoreject_method,
        autoreject_random_state=autoreject_random_state,
    )
    return score_channel_results(
        channel_results,
        gt_annotations,
        epoch_duration=epoch_duration,
    )


__all__ = ["blink_position_strategy_d", "run_strategy_d"]
