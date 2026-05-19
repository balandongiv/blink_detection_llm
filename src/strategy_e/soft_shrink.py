"""Strategy E6 – Soft-Shrinkage Threshold.

Interpolates between a local (per-epoch) threshold and a global threshold:

    T_local  = median(epoch) + k * SCALING * MAD(epoch)
    T_global = mean(concat)  + k * SCALING * MAD(concat)   [Strategy A formula]
    alpha    = clip(epoch_scaled_MAD / global_scaled_MAD, ALPHA_MIN, ALPHA_MAX)
    T_e      = alpha * T_local + (1 - alpha) * T_global

Quiet epochs (low MAD) get alpha ≈ ALPHA_MIN → pulled toward global.
Noisy epochs (high MAD) get alpha ≈ ALPHA_MAX → trust local more.

References
----------
Tutorial 25 – ``25_strategy_e_2nd_derivatives_step1_batch.py``
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.blinker.default_setting import SCALING_FACTOR
from src.fitutils import mad as compute_mad

from .shared_helpers import make_candidates_df, scan_threshold_crossings

# ── Default parameters ─────────────────────────────────────────────────────────
K_DEFAULT: float = 1.5
MIN_EVENT_LEN_S: float = 0.05
SOFT_ALPHA_MIN: float = 0.2
SOFT_ALPHA_MAX: float = 0.9


def run_e6_soft_shrink_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    min_event_len_s: float = MIN_EVENT_LEN_S,
    alpha_min: float = SOFT_ALPHA_MIN,
    alpha_max: float = SOFT_ALPHA_MAX,
) -> pd.DataFrame:
    """E6: soft interpolation between local per-epoch and global thresholds.

    Parameters
    ----------
    prepared:
        Prepared epoch detection input.
    ch_idx:
        Channel axis index in ``prepared.data``.
    channel_name:
        Channel name for the output DataFrame.
    valid_epoch_indices:
        Epoch indices to process.

    Returns
    -------
    pd.DataFrame
        Epoch-relative blink candidates.
    """
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_scaled_mad = SCALING_FACTOR * float(compute_mad(concat))
    T_global = global_mean + k * global_scaled_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_scaled_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_local = ep_median + k * ep_scaled_mad

        alpha = float(
            np.clip(
                ep_scaled_mad / (global_scaled_mad + 1e-12),
                alpha_min,
                alpha_max,
            )
        )
        threshold = alpha * T_local + (1.0 - alpha) * T_global

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


__all__ = [
    "K_DEFAULT",
    "MIN_EVENT_LEN_S",
    "SOFT_ALPHA_MAX",
    "SOFT_ALPHA_MIN",
    "run_e6_soft_shrink_channel",
]
