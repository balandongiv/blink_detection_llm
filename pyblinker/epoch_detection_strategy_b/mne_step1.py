"""Strategy B Step 1 helpers built on MNE `find_eog_events`."""

from __future__ import annotations

from typing import Sequence

import mne
import numpy as np
import pandas as pd

DEFAULT_STRATEGY_B_CHANNELS = (
    "EEG X1 - Pz",
    "EEG Fp1 - Pz",
    "EEG Fp2 - Pz",
)


def find_eog_candidate_regions(
    concatenated_signal: np.ndarray,
    *,
    channel: str,
    sfreq: float,
    half_window_s: float = 0.10,
    l_freq: float = 1.0,
    h_freq: float = 20.0,
    thresh: float | None = None,
) -> pd.DataFrame:
    """Convert MNE EOG peak events into candidate blink regions."""

    columns = ["start_blink", "end_blink", "peak_sample", "channel"]
    signal = np.asarray(concatenated_signal, dtype=float).reshape(-1)
    if signal.size == 0:
        return pd.DataFrame(columns=columns)

    info = mne.create_info([channel], sfreq=float(sfreq), ch_types=["eeg"])
    raw = mne.io.RawArray(signal[np.newaxis, :], info, verbose="ERROR")

    kwargs: dict[str, object] = {
        "ch_name": channel,
        "l_freq": float(l_freq),
        "h_freq": float(h_freq),
        "reject_by_annotation": False,
        "verbose": "ERROR",
    }
    if thresh is not None:
        kwargs["thresh"] = float(thresh)

    try:
        events = mne.preprocessing.find_eog_events(raw, **kwargs)
    except Exception:
        return pd.DataFrame(columns=columns)

    if len(events) == 0:
        return pd.DataFrame(columns=columns)

    peaks = np.asarray(events[:, 0] - raw.first_samp, dtype=int)
    half_window_samples = max(1, int(round(float(half_window_s) * float(sfreq))))
    start_blink = np.clip(peaks - half_window_samples, 0, signal.size - 1)
    end_blink = np.clip(peaks + half_window_samples, 0, signal.size - 1)

    blink_df = pd.DataFrame(
        {
            "start_blink": start_blink.astype(int),
            "end_blink": end_blink.astype(int),
            "peak_sample": peaks.astype(int),
            "channel": channel,
        }
    )
    blink_df = blink_df.drop_duplicates(subset=["start_blink", "end_blink"])
    return blink_df.sort_values(["start_blink", "end_blink"]).reset_index(drop=True)


def summarize_candidate_regions(
    blink_df: pd.DataFrame,
    *,
    epoch_length_samples: int,
    sfreq: float,
    epoch_indices: Sequence[int],
) -> pd.DataFrame:
    """Map Strategy B candidate regions to epoch-local timing for inspection."""

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
    return mapped.loc[:, columns].sort_values(
        ["epoch_index", "blink_onset"]
    ).reset_index(drop=True)


__all__ = [
    "DEFAULT_STRATEGY_B_CHANNELS",
    "find_eog_candidate_regions",
    "summarize_candidate_regions",
]
