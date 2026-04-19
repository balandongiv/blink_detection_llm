"""Common MNE epoch construction utilities."""

from __future__ import annotations

import mne
import numpy as np


def build_stage1_epochs(
    stage1_data: np.ndarray,
    *,
    channel_names: tuple[str, ...],
    sfreq: float,
) -> mne.Epochs:
    """Create an MNE EpochsArray from stage-1 array data.

    Parameters
    ----------
    stage1_data:
        3-D array of shape (n_epochs, n_channels, n_times).
    channel_names:
        Channel labels matching the second axis of ``stage1_data``.
    sfreq:
        Sampling frequency in Hz.
    """
    info = mne.create_info(
        list(channel_names),
        sfreq=float(sfreq),
        ch_types=["eeg"] * len(channel_names),
    )
    return mne.EpochsArray(stage1_data, info, verbose="ERROR")


__all__ = ["build_stage1_epochs"]
