"""Strategy E second-iteration derivative variants (E7, E9, E10, E12, E6+E10).

References
----------
Tutorial 25 – ``25_strategy_e_2nd_derivatives_step1_batch.py``

Variants
--------
E7  – e7_bg_refit       : two-pass iterative background refit
E9  – e9_frontal_avg    : frontal-channel average virtual channel
E10 – e10_epoch_smooth  : cross-epoch triangular threshold regularisation
E12 – e12_amp_filter    : E7 background refit + amplitude percentile pruning
E6+E10 – e6_e10_combined: E6 soft-shrinkage + E10 cross-epoch smoothing
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.blinker.default_setting import SCALING_FACTOR
from src.fitutils import mad as compute_mad

from .shared_helpers import make_candidates_df, scan_threshold_crossings
from .soft_shrink import K_DEFAULT, MIN_EVENT_LEN_S, SOFT_ALPHA_MAX, SOFT_ALPHA_MIN

# ── E7 parameters ──────────────────────────────────────────────────────────────
E7_K_PASS1: float = 1.0
E7_MIN_BG_SAMPLES: int = 20

# ── E10 parameters ─────────────────────────────────────────────────────────────
E10_SMOOTH_WEIGHTS: tuple[float, float, float] = (0.25, 0.50, 0.25)

# ── E12 parameters ─────────────────────────────────────────────────────────────
E12_AMP_PERCENTILE: float = 15.0
E12_MIN_CANDS_TO_FILTER: int = 10


# ── E7 – Iterative Background Refit ───────────────────────────────────────────

def run_e7_bg_refit_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    k_pass1: float = E7_K_PASS1,
    min_bg_samples: int = E7_MIN_BG_SAMPLES,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E7: two-pass iterative background refit.

    Pass 1 (permissive k_pass1): detect candidate regions → mask them.
    Recompute median + MAD on remaining background.
    Pass 2 (k): scan with refit threshold.
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

        ep_median_p1 = float(np.median(signal))
        ep_mad_p1 = SCALING_FACTOR * float(compute_mad(signal))
        T_pass1 = ep_median_p1 + k_pass1 * ep_mad_p1

        pass1_cands = scan_threshold_crossings(signal, T_pass1, min_frames)
        mask = np.ones(len(signal), dtype=bool)
        for s, e in pass1_cands:
            mask[s:e] = False

        background = signal[mask]
        if len(background) >= min_bg_samples:
            bg_median = float(np.median(background))
            bg_mad = SCALING_FACTOR * float(compute_mad(background))
            T_refit = max(bg_median + k * bg_mad, global_floor)
        else:
            T_refit = global_floor

        for start, end in scan_threshold_crossings(signal, T_refit, min_frames):
            cand_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": start / sfreq,
                    "blink_duration": (end - start) / sfreq,
                }
            )

    return make_candidates_df(cand_rows, channel_name)


# ── E9 – Frontal Average Virtual Channel ──────────────────────────────────────

def run_e9_frontal_avg(
    prepared,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E9: average all channels into one virtual signal, apply E5-style threshold.

    This is a pair-level (not per-channel) runner; returns candidates tagged
    with channel name ``"frontal_avg"``.
    """
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    virtual_ch_name = "frontal_avg"

    avg_epochs = np.mean(prepared.data[valid_epoch_indices, :, :], axis=1)
    concat_avg = avg_epochs.reshape(-1).astype(float)
    global_mean = float(np.mean(concat_avg))
    global_mad = SCALING_FACTOR * float(compute_mad(concat_avg))
    global_floor = global_mean + k * global_mad

    cand_rows: list[dict] = []
    for i, epoch_idx in enumerate(valid_epoch_indices):
        signal = avg_epochs[i].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        threshold = max(ep_median + k * ep_mad, global_floor)
        for start, end in scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": virtual_ch_name,
                    "blink_onset": start / sfreq,
                    "blink_duration": (end - start) / sfreq,
                }
            )

    return make_candidates_df(cand_rows, virtual_ch_name)


# ── E10 – Cross-Epoch Threshold Regularisation ────────────────────────────────

def run_e10_epoch_smooth_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    smooth_weights: tuple[float, float, float] = E10_SMOOTH_WEIGHTS,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E10: triangular smoothing of per-epoch median+MAD thresholds across epochs."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    w_prev, w_curr, w_next = smooth_weights

    raw_thresholds: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        raw_thresholds.append(ep_median + k * ep_mad)

    n = len(raw_thresholds)
    smoothed: list[float] = []
    for i in range(n):
        T_prev = raw_thresholds[max(0, i - 1)]
        T_next = raw_thresholds[min(n - 1, i + 1)]
        smoothed.append(w_prev * T_prev + w_curr * raw_thresholds[i] + w_next * T_next)

    cand_rows: list[dict] = []
    for i, epoch_idx in enumerate(valid_epoch_indices):
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        for start, end in scan_threshold_crossings(signal, smoothed[i], min_frames):
            cand_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": start / sfreq,
                    "blink_duration": (end - start) / sfreq,
                }
            )

    return make_candidates_df(cand_rows, channel_name)


# ── E6+E10 – Soft Shrinkage + Cross-Epoch Smoothing Combined ──────────────────

def run_e6_e10_combined_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    alpha_min: float = SOFT_ALPHA_MIN,
    alpha_max: float = SOFT_ALPHA_MAX,
    smooth_weights: tuple[float, float, float] = E10_SMOOTH_WEIGHTS,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E6+E10: E6 soft-shrinkage thresholds smoothed with E10 triangular kernel."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    w_prev, w_curr, w_next = smooth_weights

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_scaled_mad = SCALING_FACTOR * float(compute_mad(concat))
    T_global = global_mean + k * global_scaled_mad

    e6_thresholds: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_scaled_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_local = ep_median + k * ep_scaled_mad
        alpha = float(
            np.clip(ep_scaled_mad / (global_scaled_mad + 1e-12), alpha_min, alpha_max)
        )
        e6_thresholds.append(alpha * T_local + (1.0 - alpha) * T_global)

    n = len(e6_thresholds)
    smoothed: list[float] = []
    for i in range(n):
        T_prev = e6_thresholds[max(0, i - 1)]
        T_next = e6_thresholds[min(n - 1, i + 1)]
        smoothed.append(w_prev * T_prev + w_curr * e6_thresholds[i] + w_next * T_next)

    cand_rows: list[dict] = []
    for i, epoch_idx in enumerate(valid_epoch_indices):
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        for start, end in scan_threshold_crossings(signal, smoothed[i], min_frames):
            cand_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": start / sfreq,
                    "blink_duration": (end - start) / sfreq,
                }
            )

    return make_candidates_df(cand_rows, channel_name)


# ── E12 – E7 Background Refit + Amplitude Percentile Filter ───────────────────

def run_e12_amp_filter_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
    *,
    k: float = K_DEFAULT,
    k_pass1: float = E7_K_PASS1,
    min_bg_samples: int = E7_MIN_BG_SAMPLES,
    amp_percentile: float = E12_AMP_PERCENTILE,
    min_cands_to_filter: int = E12_MIN_CANDS_TO_FILTER,
    min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E12: E7 background refit + bottom-percentile amplitude pruning."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_mean + k * global_mad

    raw_cands: list[tuple[int, int, int, float]] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

        ep_median_p1 = float(np.median(signal))
        ep_mad_p1 = SCALING_FACTOR * float(compute_mad(signal))
        T_pass1 = ep_median_p1 + k_pass1 * ep_mad_p1
        pass1_cands = scan_threshold_crossings(signal, T_pass1, min_frames)

        mask = np.ones(len(signal), dtype=bool)
        for s, e in pass1_cands:
            mask[s:e] = False
        background = signal[mask]

        if len(background) >= min_bg_samples:
            bg_median = float(np.median(background))
            bg_mad = SCALING_FACTOR * float(compute_mad(background))
            T_refit = max(bg_median + k * bg_mad, global_floor)
        else:
            T_refit = global_floor

        for s, e in scan_threshold_crossings(signal, T_refit, min_frames):
            peak_amp = float(np.max(signal[s:e]))
            raw_cands.append((epoch_idx, s, e, peak_amp))

    if len(raw_cands) >= min_cands_to_filter:
        all_peaks = np.array([c[3] for c in raw_cands])
        amp_gate = float(np.percentile(all_peaks, amp_percentile))
        filtered = [(ei, s, e) for ei, s, e, p in raw_cands if p >= amp_gate]
    else:
        filtered = [(ei, s, e) for ei, s, e, _ in raw_cands]

    cand_rows = [
        {
            "epoch_index": ei,
            "channel": channel_name,
            "blink_onset": s / sfreq,
            "blink_duration": (e - s) / sfreq,
        }
        for ei, s, e in filtered
    ]
    return make_candidates_df(cand_rows, channel_name)


# ── Dispatch ───────────────────────────────────────────────────────────────────

SECOND_DERIVATIVE_CHANNEL_RUNNERS: dict[str, object] = {
    "e7_bg_refit": run_e7_bg_refit_channel,
    "e10_epoch_smooth": run_e10_epoch_smooth_channel,
    "e6_e10_combined": run_e6_e10_combined_channel,
    "e12_amp_filter": run_e12_amp_filter_channel,
}

__all__ = [
    "E10_SMOOTH_WEIGHTS",
    "E12_AMP_PERCENTILE",
    "E7_K_PASS1",
    "SECOND_DERIVATIVE_CHANNEL_RUNNERS",
    "run_e10_epoch_smooth_channel",
    "run_e12_amp_filter_channel",
    "run_e6_e10_combined_channel",
    "run_e7_bg_refit_channel",
    "run_e9_frontal_avg",
]
