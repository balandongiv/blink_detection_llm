"""Strategy E first-wave derivative variants (E1–E5).

Each variant modifies how the per-epoch threshold is computed.

References
----------
Tutorial 24 – ``24_strategy_e_derivatives_step1_batch.py``

Variants
--------
E1  – e1_median        : median + k * SCALING_FACTOR * MAD(epoch)
E2  – e2_floor         : median + MAD with subject-level noise-floor minimum
E3  – e3_hysteresis    : dual thresholds (T_high, T_low) from per-epoch median+MAD
E4  – e4_multiscale    : union of detections at k=1.0, 1.2, 1.5; merge within gap_ms
E5  – e5_global_floor  : per-epoch median+MAD, floored by global mean+MAD (Strategy A)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.blinker.default_setting import SCALING_FACTOR
from src.fitutils import mad as compute_mad

from .shared_helpers import (
    make_candidates_df,
    merge_intervals,
    scan_hysteresis_crossings,
    scan_threshold_crossings,
)

# ── Shared defaults (mirrors Tutorial 24 settings) ────────────────────────────
K_DEFAULT: float = 1.5
MIN_EVENT_LEN_S: float = 0.05
FLOOR_K: float = 0.5       # noise-floor multiplier for E2
K_HIGH: float = 1.5        # high threshold for E3
K_LOW: float = 1.0         # low  threshold for E3
MULTISCALE_K_VALUES: list[float] = [1.0, 1.2, 1.5]
MULTISCALE_GAP_MS: float = 80.0


# ── E1 – median + k * SCALING_FACTOR * MAD ────────────────────────────────────

def run_e1_median_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E1: replace mean with median in the per-epoch threshold."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        threshold = ep_median + k * ep_mad
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


# ── E2 – median + MAD with global noise-floor minimum ─────────────────────────

def run_e2_floor_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    floor_k: float = FLOOR_K,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E2: per-epoch median+MAD floored by a subject-level noise floor."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_median = float(np.median(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_median + floor_k * global_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        threshold = max(ep_median + k * ep_mad, global_floor)
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


# ── E3 – hysteresis thresholds ────────────────────────────────────────────────

def run_e3_hysteresis_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k_high: float = K_HIGH,
    k_low: float = K_LOW,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E3: dual hysteresis thresholds from per-epoch median+MAD."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        t_high = ep_median + k_high * ep_mad
        t_low = ep_median + k_low * ep_mad
        for start, end in scan_hysteresis_crossings(signal, t_high, t_low, min_frames):
            cand_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": start / sfreq,
                    "blink_duration": (end - start) / sfreq,
                }
            )
    return make_candidates_df(cand_rows, channel_name)


# ── E4 – multi-scale union ────────────────────────────────────────────────────

def run_e4_multiscale_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k_values: list[float] | None = None,
    gap_ms: float = MULTISCALE_GAP_MS,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E4: union of detections at multiple k values, merged within gap_ms."""
    if k_values is None:
        k_values = MULTISCALE_K_VALUES
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    gap_frames = int(round(gap_ms * sfreq / 1000.0))
    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        raw_candidates: list[tuple[int, int]] = []
        for k in k_values:
            threshold = ep_median + k * ep_mad
            raw_candidates.extend(
                scan_threshold_crossings(signal, threshold, min_frames)
            )
        merged = merge_intervals(raw_candidates, gap_frames)
        for start, end in merged:
            cand_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": start / sfreq,
                    "blink_duration": (end - start) / sfreq,
                }
            )
    return make_candidates_df(cand_rows, channel_name)


# ── E5 – global-floor (Strategy-A style) ──────────────────────────────────────

def run_e5_global_floor_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E5: per-epoch median+MAD floored by the global mean+MAD (Strategy A formula).

    Prevents threshold collapse in quiet epochs (reduces FP) while still
    adapting downward in noisy epochs (preserves recall).
    """
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_mean + k * global_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        threshold = max(ep_median + k * ep_mad, global_floor)
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


# ── Dispatch table ─────────────────────────────────────────────────────────────

DERIVATIVE_CHANNEL_RUNNERS: dict[str, object] = {
    "e1_median": run_e1_median_channel,
    "e2_floor": run_e2_floor_channel,
    "e3_hysteresis": run_e3_hysteresis_channel,
    "e4_multiscale": run_e4_multiscale_channel,
    "e5_global_floor": run_e5_global_floor_channel,
}

__all__ = [
    "DERIVATIVE_CHANNEL_RUNNERS",
    "K_DEFAULT",
    "MIN_EVENT_LEN_S",
    "run_e1_median_channel",
    "run_e2_floor_channel",
    "run_e3_hysteresis_channel",
    "run_e4_multiscale_channel",
    "run_e5_global_floor_channel",
]
