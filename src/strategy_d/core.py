"""Strategy D core: Bayesian-optimised PTP threshold learning + MNE peak_finder.

Mirrors Tutorial 14 (strategy_d_ncyoder) — per-channel autoreject threshold
learning followed by MNE ``peak_finder`` scanning of the concatenated epoch
signal.

References
----------
Tutorial 21 – ``21_strategy_d_step1_batch_all_subjects.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

import mne
import numpy as np
import pandas as pd

# Ensure the vendored autoreject is importable when this module is loaded
# independently of a session that already set up sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_VENDORED_AUTOREJECT = _REPO_ROOT / "autoreject"
if str(_VENDORED_AUTOREJECT) not in sys.path:
    sys.path.insert(0, str(_VENDORED_AUTOREJECT))

from autoreject import compute_thresholds  # noqa: E402
from mne.preprocessing import peak_finder  # noqa: E402

from src.strategy_dbo import STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE

_AUTOREJECT_METHOD = "bayesian_optimization"
_AUTOREJECT_RANDOM_STATE = 42
_HALF_WINDOW_S = 0.10


def learn_bayesian_thresholds(
    epoch_data: np.ndarray,
    channel_names: tuple[str, ...],
    sfreq: float,
    valid_epoch_indices: list[int],
    *,
    method: str = _AUTOREJECT_METHOD,
    random_state: int = _AUTOREJECT_RANDOM_STATE,
) -> dict[str, float]:
    """Learn per-channel PTP rejection thresholds with Bayesian optimisation.

    Parameters
    ----------
    epoch_data:
        3-D array of shape ``(n_epochs, n_channels, n_samples)``.
    channel_names:
        Ordered channel names matching the second axis of ``epoch_data``.
    sfreq:
        Sampling frequency in Hz.
    valid_epoch_indices:
        Indices into the first axis of ``epoch_data`` to include.

    Returns
    -------
    dict[str, float]
        Mapping ``{channel_name: threshold}``.
    """
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)
    stage1_data = epoch_data[valid_indices]
    info = mne.create_info(
        list(channel_names),
        sfreq=float(sfreq),
        ch_types=["eeg"] * len(channel_names),
    )
    stage1_epochs = mne.EpochsArray(stage1_data, info, verbose="ERROR")
    threshes = compute_thresholds(
        stage1_epochs,
        method=method,
        random_state=random_state,
        augment=False,
        verbose=False,
    )
    return {ch: float(threshes[ch]) for ch in channel_names}


def peaks_to_candidates(
    peak_locs: np.ndarray,
    *,
    epoch_length_samples: int,
    sfreq: float,
    valid_epoch_indices: list[int],
    channel: str,
    half_window_s: float = _HALF_WINDOW_S,
) -> pd.DataFrame:
    """Map peak sample positions in the concatenated signal back to epoch-local rows.

    Parameters
    ----------
    peak_locs:
        Sample indices in the concatenated (all valid epochs) signal.
    epoch_length_samples:
        Number of samples per epoch.
    sfreq:
        Sampling frequency in Hz.
    valid_epoch_indices:
        Ordered list of valid epoch indices (maps offsets to original epoch IDs).
    channel:
        Channel name for the output ``channel`` column.
    half_window_s:
        Half-window in seconds around each peak to define blink onset/duration.

    Returns
    -------
    pd.DataFrame
        Columns: ``epoch_index``, ``channel``, ``blink_onset``,
        ``blink_duration``, ``peak_sample``.
    """
    columns = ["epoch_index", "channel", "blink_onset", "blink_duration", "peak_sample"]
    if len(peak_locs) == 0:
        return pd.DataFrame(columns=columns)

    half_win = max(1, int(round(half_window_s * sfreq)))
    rows: list[dict] = []
    for peak in peak_locs:
        offset = int(peak) // epoch_length_samples
        if offset < 0 or offset >= len(valid_epoch_indices):
            continue
        epoch_index = int(valid_epoch_indices[offset])
        local_peak = int(peak) % epoch_length_samples
        start = max(0, local_peak - half_win)
        end = min(epoch_length_samples - 1, local_peak + half_win)
        rows.append(
            {
                "epoch_index": epoch_index,
                "channel": channel,
                "blink_onset": start / float(sfreq),
                "blink_duration": (end - start) / float(sfreq),
                "peak_sample": local_peak,
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    return (
        pd.DataFrame(rows)
        .sort_values(["epoch_index", "blink_onset"])
        .reset_index(drop=True)
    )


def detect_peaks_per_channel(
    prepared,
    valid_epoch_indices: list[int],
    *,
    rescale_threshold: bool = True,
    half_window_s: float = _HALF_WINDOW_S,
    autoreject_method: str = _AUTOREJECT_METHOD,
    autoreject_random_state: int = _AUTOREJECT_RANDOM_STATE,
) -> list[dict]:
    """Run Strategy D Step 1 per channel; return per-channel result dicts.

    Learns Bayesian PTP thresholds, then calls ``peak_finder`` on each
    channel's concatenated valid-epoch signal.

    Returns
    -------
    list[dict]
        Each dict has: ``channel``, ``raw_threshold``, ``scan_threshold``,
        ``extrema``, ``peak_locs``, ``candidates``.
    """
    scan_scale = STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE if rescale_threshold else 1.0
    raw_thresholds = learn_bayesian_thresholds(
        prepared.data,
        channel_names=prepared.channel_names,
        sfreq=prepared.sfreq,
        valid_epoch_indices=valid_epoch_indices,
        method=autoreject_method,
        random_state=autoreject_random_state,
    )
    scan_thresholds = {ch: raw_thresholds[ch] * scan_scale for ch in raw_thresholds}

    epoch_length_samples = int(prepared.epoch_length_samples)
    valid_indices_arr = np.asarray(valid_epoch_indices, dtype=int)
    results: list[dict] = []

    for ch_idx, channel in enumerate(prepared.channel_names):
        signal = prepared.data[valid_indices_arr, ch_idx, :].reshape(-1).astype(float)
        raw_thresh = raw_thresholds[channel]
        scan_thresh = scan_thresholds[channel]

        temp = signal - np.mean(signal)
        extrema = 1 if np.abs(np.max(temp)) >= np.abs(np.min(temp)) else -1

        peak_locs_raw, _ = peak_finder(
            signal, thresh=scan_thresh, extrema=extrema, verbose=False
        )
        peak_locs = np.asarray(peak_locs_raw, dtype=int)

        candidates = peaks_to_candidates(
            peak_locs,
            epoch_length_samples=epoch_length_samples,
            sfreq=prepared.sfreq,
            valid_epoch_indices=valid_epoch_indices,
            channel=channel,
            half_window_s=half_window_s,
        )
        results.append(
            {
                "channel": channel,
                "raw_threshold": raw_thresh,
                "scan_threshold": scan_thresh,
                "extrema": extrema,
                "peak_locs": peak_locs,
                "candidates": candidates,
            }
        )
    return results


__all__ = [
    "detect_peaks_per_channel",
    "learn_bayesian_thresholds",
    "peaks_to_candidates",
]
