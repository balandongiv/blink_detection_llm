"""Strategy E expand-bridge derivative variants.

All six variants from Tutorial 27.

References
----------
Tutorial 27 – ``27_strategy_e_expand_bridge_derivatives_batch.py``

Variants
--------
expand_bridge_dynamic_low        : epoch-aware adaptive T_low
expand_bridge_dynamic_gap        : candidate-strength-aware bridge gap
expand_bridge_confidence_weighted: two-tier expansion + bridging
expand_bridge_sw_onset           : sliding-window onset + expand+bridge recovery
expand_bridge_adaptive_k         : adaptive-k T_high + normal expand+bridge
expand_bridge_soft_gate          : conservative pass learns amplitude gate
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pyblinker.blinker.default_setting import SCALING_FACTOR
from pyblinker.fitutils import mad as compute_mad

from .shared_helpers import make_candidates_df, merge_intervals, scan_threshold_crossings

# ── Default parameters ─────────────────────────────────────────────────────────
K_DEFAULT: float = 1.5
MIN_EVENT_LEN_S: float = 0.05
EXPAND_LOW_K: float = 0.5
BRIDGE_GAP_MS: float = 80.0

EXPAND_DYN_LOW_K_BASE: float = 0.5
EXPAND_DYN_LOW_K_MIN: float = 0.2
EXPAND_DYN_LOW_K_MAX: float = 1.0

EXPAND_DYN_GAP_STRONG_MS: float = 100.0
EXPAND_DYN_GAP_WEAK_MS: float = 40.0
EXPAND_DYN_GAP_STRONG_K: float = 0.5

EXPAND_CONF_K_LOW_STRONG: float = 0.3
EXPAND_CONF_K_LOW_WEAK: float = 0.8
EXPAND_CONF_BRIDGE_STRONG_MS: float = 80.0
EXPAND_CONF_BRIDGE_WEAK_MS: float = 40.0
EXPAND_CONF_STRONG_K: float = 0.5

EXPAND_SW_WINDOW_S: float = 2.0

EXPAND_ADAPTIVE_K_MIN: float = 1.0
EXPAND_ADAPTIVE_K_MAX: float = 2.5

SOFT_GATE_K_CONSERVATIVE: float = 2.0
SOFT_GATE_MIN_CONFIDENT: int = 5


def _global_floor(prepared, ch_idx: int, valid_epoch_indices: list[int]) -> float:
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    return float(np.mean(concat)) + K_DEFAULT * SCALING_FACTOR * float(compute_mad(concat))


def _expand_interval(signal: np.ndarray, s: int, e: int, t_low: float) -> tuple[int, int]:
    n = len(signal)
    while s > 0 and signal[s - 1] > t_low:
        s -= 1
    while e < n and signal[e] > t_low:
        e += 1
    return s, e


def _merge_intervals_conditional(
    intervals: list[tuple[int, int]],
    is_strong: list[bool],
    gap_strong_frames: int,
    gap_weak_frames: int,
) -> list[tuple[int, int]]:
    """Merge intervals with gap size depending on whether both neighbors are strong."""
    if not intervals:
        return []
    paired = sorted(zip(intervals, is_strong), key=lambda x: x[0][0])
    merged: list[tuple[tuple[int, int], bool]] = [(paired[0][0], paired[0][1])]
    for curr_iv, curr_strong in paired[1:]:
        prev_iv, prev_strong = merged[-1]
        max_gap = gap_strong_frames if (prev_strong and curr_strong) else gap_weak_frames
        if curr_iv[0] - prev_iv[1] <= max_gap:
            merged[-1] = ((prev_iv[0], max(prev_iv[1], curr_iv[1])), prev_strong or curr_strong)
        else:
            merged.append((curr_iv, curr_strong))
    return [iv for iv, _ in merged]


# ── Variant 1 – expand_bridge_dynamic_low ─────────────────────────────────────

def run_dynamic_low_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Epoch-aware adaptive T_low: scales with epoch noise vs global noise."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        noise_ratio = ep_mad / (global_mad + 1e-12)
        k_low_adj = float(np.clip(EXPAND_DYN_LOW_K_BASE * noise_ratio,
                                  EXPAND_DYN_LOW_K_MIN, EXPAND_DYN_LOW_K_MAX))
        T_low = ep_med + k_low_adj * ep_mad
        cands = scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]
        merged = merge_intervals(expanded, bridge_frames)
        for s, e in merged:
            if (e - s) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


# ── Variant 2 – expand_bridge_dynamic_gap ─────────────────────────────────────

def run_dynamic_gap_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Candidate-strength-aware bridge gap."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    gap_strong_frames = int(EXPAND_DYN_GAP_STRONG_MS * sfreq / 1000.0)
    gap_weak_frames = int(EXPAND_DYN_GAP_WEAK_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_low = ep_med + EXPAND_LOW_K * ep_mad
        T_strong = T_high + EXPAND_DYN_GAP_STRONG_K * ep_mad
        cands = scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]
        is_strong = [
            (float(np.max(signal[s:e])) if e > s else T_high) >= T_strong
            for s, e in expanded
        ]
        merged = _merge_intervals_conditional(expanded, is_strong, gap_strong_frames, gap_weak_frames)
        for s, e in merged:
            if (e - s) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


# ── Variant 3 – expand_bridge_confidence_weighted ─────────────────────────────

def run_confidence_weighted_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Two-tier expansion and bridging based on candidate confidence."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    bridge_strong_frames = int(EXPAND_CONF_BRIDGE_STRONG_MS * sfreq / 1000.0)
    bridge_weak_frames = int(EXPAND_CONF_BRIDGE_WEAK_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_strong = T_high + EXPAND_CONF_STRONG_K * ep_mad
        T_low_strong = ep_med + EXPAND_CONF_K_LOW_STRONG * ep_mad
        T_low_weak = ep_med + EXPAND_CONF_K_LOW_WEAK * ep_mad
        cands = scan_threshold_crossings(signal, T_high, min_frames)
        strong_ivs: list[tuple[int, int]] = []
        weak_ivs: list[tuple[int, int]] = []
        for s, e in cands:
            peak = float(np.max(signal[s:e])) if e > s else T_high
            if peak >= T_strong:
                strong_ivs.append(_expand_interval(signal, s, e, T_low_strong))
            else:
                weak_ivs.append(_expand_interval(signal, s, e, T_low_weak))
        merged_strong = merge_intervals(strong_ivs, bridge_strong_frames)
        merged_weak = merge_intervals(weak_ivs, bridge_weak_frames)
        final = merge_intervals(merged_strong + merged_weak, gap_frames=0)
        for s, e in final:
            if (e - s) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


# ── Variant 4 – expand_bridge_sw_onset ────────────────────────────────────────

def _rolling_mad_threshold(signal: np.ndarray, win_frames: int, k: float, gfloor: float) -> np.ndarray:
    """Vectorised per-sample rolling median + k * SCALING * rolling_MAD threshold."""
    sig_s = pd.Series(signal)
    roll_med = sig_s.rolling(window=win_frames, center=True, min_periods=1).median()
    abs_dev = (sig_s - roll_med).abs()
    roll_mad = abs_dev.rolling(window=win_frames, center=True, min_periods=1).median()
    T = roll_med.values + k * SCALING_FACTOR * roll_mad.values
    return np.maximum(T, gfloor)


def run_sw_onset_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Sliding-window onset detection + expand+bridge boundary recovery."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    win_frames = int(EXPAND_SW_WINDOW_S * sfreq)
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        T_sw = _rolling_mad_threshold(signal, win_frames, K_DEFAULT, gfloor)
        above_sw = signal > T_sw
        if not above_sw.any():
            continue
        padded = np.concatenate([[False], above_sw, [False]])
        diff = np.diff(padded.astype(np.int8))
        ons = np.where(diff == 1)[0]
        offs = np.where(diff == -1)[0]
        cands_sw = [(int(o), int(f)) for o, f in zip(ons, offs) if (f - o) > min_frames]
        if not cands_sw:
            continue
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_low = ep_med + EXPAND_LOW_K * ep_mad
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands_sw]
        merged = merge_intervals(expanded, bridge_frames)
        for s, e in merged:
            if (e - s) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


# ── Variant 5 – expand_bridge_adaptive_k ──────────────────────────────────────

def run_adaptive_k_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Adaptive-k for T_high + normal expand+bridge."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_mean = float(np.mean(concat))
    ep_mads = [
        SCALING_FACTOR * float(compute_mad(prepared.data[ei, ch_idx, :].astype(float)))
        for ei in valid_epoch_indices
    ]
    quiet_mad = float(np.percentile(ep_mads, 25)) if ep_mads else global_mad
    ratio = global_mad / (quiet_mad + 1e-12)
    k_adj = float(np.clip(K_DEFAULT * ratio, EXPAND_ADAPTIVE_K_MIN, EXPAND_ADAPTIVE_K_MAX))
    global_floor_adj = global_mean + k_adj * global_mad
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + k_adj * ep_mad, global_floor_adj)
        T_low = ep_med + EXPAND_LOW_K * ep_mad
        cands = scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]
        merged = merge_intervals(expanded, bridge_frames)
        for s, e in merged:
            if (e - s) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


# ── Variant 6 – expand_bridge_soft_gate ───────────────────────────────────────

def run_soft_gate_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Self-trained amplitude gate after expand+bridge."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    confident_peaks: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_cons = max(ep_med + SOFT_GATE_K_CONSERVATIVE * ep_mad, gfloor)
        for s, e in scan_threshold_crossings(signal, T_cons, min_frames):
            if e > s:
                confident_peaks.append(float(np.max(signal[s:e])))
    if len(confident_peaks) >= SOFT_GATE_MIN_CONFIDENT:
        peaks_arr = np.array(confident_peaks)
        peak_med = float(np.median(peaks_arr))
        peak_scaled_mad = SCALING_FACTOR * float(compute_mad(peaks_arr))
        amp_gate = max(peak_med - 2.0 * peak_scaled_mad, gfloor)
    else:
        amp_gate = gfloor
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_low = ep_med + EXPAND_LOW_K * ep_mad
        cands = scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]
        merged = merge_intervals(expanded, bridge_frames)
        for s, e in merged:
            if (e - s) > min_frames:
                peak_amp = float(np.max(signal[s:e])) if e > s else 0.0
                if peak_amp >= amp_gate:
                    rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                                 "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


# ── Dispatch ───────────────────────────────────────────────────────────────────

EXPAND_BRIDGE_CHANNEL_RUNNERS: dict[str, object] = {
    "expand_bridge_dynamic_low": run_dynamic_low_channel,
    "expand_bridge_dynamic_gap": run_dynamic_gap_channel,
    "expand_bridge_confidence_weighted": run_confidence_weighted_channel,
    "expand_bridge_sw_onset": run_sw_onset_channel,
    "expand_bridge_adaptive_k": run_adaptive_k_channel,
    "expand_bridge_soft_gate": run_soft_gate_channel,
}

ALL_EXPAND_BRIDGE_VARIANTS: list[str] = list(EXPAND_BRIDGE_CHANNEL_RUNNERS)

__all__ = [
    "ALL_EXPAND_BRIDGE_VARIANTS",
    "EXPAND_BRIDGE_CHANNEL_RUNNERS",
    "run_adaptive_k_channel",
    "run_confidence_weighted_channel",
    "run_dynamic_gap_channel",
    "run_dynamic_low_channel",
    "run_soft_gate_channel",
    "run_sw_onset_channel",
]
