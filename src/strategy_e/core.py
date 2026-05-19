"""Strategy E core: per-epoch MAD-based threshold scanning.

Strategy E borrows autoreject's "per-epoch feature" idea but replaces PTP with
the BLINKER MAD-based statistic computed independently for every epoch::

    threshold_e = mean(epoch_e) + k * 1.4826 * MAD(epoch_e)

Each epoch is scanned with its own threshold via the standard threshold-crossing
detector.  This adapts to per-epoch signal statistics and improves recall in
quiet epochs where a global threshold would miss blinks.

References
----------
Tutorial 23 – ``23_strategy_e_step1_batch_all_subjects.py``
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.blinker.default_setting import SCALING_FACTOR
from src.fitutils import mad as compute_mad

from .shared_helpers import make_candidates_df, scan_threshold_crossings

# ── Default parameters ─────────────────────────────────────────────────────────
STD_THRESHOLD: float = 1.5   # k in: threshold = mean + k * SCALING_FACTOR * MAD(epoch)
MIN_EVENT_LEN_S: float = 0.05


def run_e_base_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    std_threshold: float = STD_THRESHOLD,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Strategy E (base): per-epoch mean + k * SCALING_FACTOR * MAD threshold.

    Parameters
    ----------
    prepared:
        Prepared epoch detection input with ``.data``, ``.sfreq``.
    ch_idx:
        Channel axis index in ``prepared.data``.
    channel_name:
        Channel name for the output DataFrame.
    valid_epoch_indices:
        Epoch indices to process.

    Returns
    -------
    pd.DataFrame
        Epoch-relative blink candidates with columns:
        ``epoch_index``, ``channel``, ``blink_onset``, ``blink_duration``.
    """
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    cand_rows: list[dict] = []

    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_mean = float(np.mean(signal))
        ep_robust_std = SCALING_FACTOR * float(compute_mad(signal))
        threshold = ep_mean + std_threshold * ep_robust_std

        for start, end in scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": start / sfreq,
                    "blink_duration": (end - start) / sfreq,
                }
            )

    return make_candidates_df(cand_rows, channel_name)


def run_e_base_all_channels(
    prepared,
    valid_epoch_indices: list[int],
    *,
    std_threshold: float = STD_THRESHOLD,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> list[dict]:
    """Run Strategy E (base) on every channel; return per-channel result dicts.

    Each dict: ``{channel, candidates}``.
    """
    results: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        candidates = run_e_base_channel(
            prepared,
            ch_idx,
            channel_name,
            valid_epoch_indices,
            std_threshold=std_threshold,
            min_event_len_s=min_event_len_s,
        )
        results.append({"channel": channel_name, "candidates": candidates})
    return results


__all__ = [
    "MIN_EVENT_LEN_S",
    "STD_THRESHOLD",
    "run_e_base_all_channels",
    "run_e_base_channel",
]
