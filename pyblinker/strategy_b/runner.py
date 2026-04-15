"""Strategy B per-channel runner in the standardized channel_results format.

Wraps :func:`~pyblinker.strategy_b.nathanael_mne.find_eog_candidate_regions`
to produce the ``{channel, df_positions, mapped_candidates, signal_by_epoch}``
dict required by :func:`~pyblinker.evaluation_runner.score_channel_results`.
"""

from __future__ import annotations

from typing import Sequence

import mne
import numpy as np
import pandas as pd

from pyblinker.analysis.lane_evaluation import LaneScoringResult
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from pyblinker.common.pipeline_utils import build_signal_by_epoch
from pyblinker.evaluation_runner import score_channel_results
from pyblinker.matching.blink_matching import enrich_absolute_times

from .nathanael_mne import find_eog_candidate_regions


def summarize_candidate_regions(
    blink_df: pd.DataFrame,
    *,
    epoch_length_samples: int,
    sfreq: float,
    epoch_indices: Sequence[int],
) -> pd.DataFrame:
    """Map Strategy B candidate regions to epoch-local timing.

    Parameters
    ----------
    blink_df:
        Output of :func:`find_eog_candidate_regions` (concatenated-signal space).
    epoch_length_samples:
        Number of samples per epoch.
    sfreq:
        Sampling frequency in Hz.
    epoch_indices:
        Ordered list of valid epoch indices (maps offsets back to original IDs).

    Returns
    -------
    pd.DataFrame
        Columns: ``epoch_index``, ``channel``, ``peak_sample``, ``blink_onset``,
        ``blink_duration``, ``start_blink``, ``end_blink``.
    """
    columns = [
        "epoch_index",
        "channel",
        "peak_sample",
        "blink_onset",
        "blink_duration",
        "start_blink",
        "end_blink",
    ]
    if blink_df.empty:
        return pd.DataFrame(columns=columns)

    mapped = blink_df.copy()
    epoch_offsets = mapped["start_blink"].to_numpy(dtype=int) // int(epoch_length_samples)
    valid_mask = (epoch_offsets >= 0) & (epoch_offsets < len(epoch_indices))
    mapped = mapped.loc[valid_mask].copy().reset_index(drop=True)
    epoch_offsets = epoch_offsets[valid_mask]
    mapped["epoch_index"] = [int(epoch_indices[offset]) for offset in epoch_offsets]
    mapped["blink_onset"] = (
        mapped["start_blink"].to_numpy(dtype=float) % float(epoch_length_samples)
    ) / float(sfreq)
    mapped["blink_duration"] = (
        mapped["end_blink"].to_numpy(dtype=float)
        - mapped["start_blink"].to_numpy(dtype=float)
    ) / float(sfreq)
    mapped["peak_sample"] = (
        mapped["peak_sample"].to_numpy(dtype=float) % float(epoch_length_samples)
    ).astype(int)
    return (
        mapped.loc[:, columns]
        .sort_values(["epoch_index", "blink_onset"])
        .reset_index(drop=True)
    )


def blink_position_strategy_b(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    half_window_s: float = 0.10,
    l_freq: float = 1.0,
    h_freq: float = 20.0,
    thresh: float | None = None,
) -> list[dict]:
    """Run Strategy B blink detection on each channel.

    Uses MNE ``find_eog_events`` on the concatenated valid-epoch signal, then
    maps peak events back to epoch-local timing.

    Returns a list of per-channel dicts, each containing:

    - ``channel``: channel name
    - ``df_positions``: raw MNE-EOG region DataFrame (concatenated signal space)
    - ``mapped_candidates``: epoch-relative blink candidates
    - ``signal_by_epoch``: dict mapping epoch_index -> filtered signal array
    """
    sfreq = float(prepared.sfreq)
    epoch_length_samples = int(prepared.epoch_length_samples)
    results: list[dict] = []

    for channel_index, channel_name in enumerate(prepared.channel_names):
        valid_epoch_data = prepared.data[valid_epoch_indices, channel_index, :]
        concatenated_signal = np.asarray(valid_epoch_data).reshape(-1)

        df_positions = find_eog_candidate_regions(
            concatenated_signal,
            channel=channel_name,
            sfreq=sfreq,
            half_window_s=half_window_s,
            l_freq=l_freq,
            h_freq=h_freq,
            thresh=thresh,
        )
        mapped_candidates = summarize_candidate_regions(
            df_positions,
            epoch_length_samples=epoch_length_samples,
            sfreq=sfreq,
            epoch_indices=valid_epoch_indices,
        )
        results.append(
            {
                "channel": channel_name,
                "df_positions": df_positions,
                "mapped_candidates": mapped_candidates,
                "signal_by_epoch": build_signal_by_epoch(prepared, channel_index),
            }
        )
    return results


def run_strategy_b(
    epochs: mne.Epochs,
    ground_truth_raw: pd.DataFrame,
    *,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    half_window_s: float = 0.10,
    l_freq: float = 1.0,
    h_freq: float = 20.0,
    thresh: float | None = None,
    epoch_duration: float = 60.0,
    peak_side_tolerance_s: float = 0.01,
) -> LaneScoringResult:
    """Run Strategy B end-to-end on ``epochs`` and return scored results."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = blink_position_strategy_b(
        prepared,
        valid_epoch_indices,
        half_window_s=half_window_s,
        l_freq=l_freq,
        h_freq=h_freq,
        thresh=thresh,
    )
    ground_truth = enrich_absolute_times(ground_truth_raw, epoch_duration)
    return score_channel_results(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


__all__ = ["blink_position_strategy_b", "run_strategy_b", "summarize_candidate_regions"]
