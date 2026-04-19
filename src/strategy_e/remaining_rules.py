"""Strategy E remaining variant rules.

All variants from strategy_e_derivative.md (items 3,4,6,7,8,9,10,11,13,14)
and strategy_e_derivative_2nd.md (E8, E11, E13) not covered by other E modules.

References
----------
Tutorial 26 – ``26_strategy_e_remaining_batch.py``

Per-channel variants
--------------------
e_sliding_window   : sub-epoch rolling median+MAD threshold (2-second window)
e_expand_bridge    : expand event boundaries + bridge gaps within 80 ms
e_duration_band    : reject events outside [50 ms, 500 ms]
e_slope_guard      : require blink peak in middle 70% of event window
e_abs_polarity     : detect on |signal − epoch_median|
e_adaptive_k       : scale k by recording noisiness relative to quiet baseline
e_quantile_thr     : max(93rd-percentile, global_floor) threshold
e_refractory       : 150 ms minimum inter-onset separation
e8_changepoint     : piecewise 6-block threshold (10-second blocks)
e13_self_train     : conservative pass calibrates amplitude gate for permissive pass

Pair-level (multi-channel fusion) variants
------------------------------------------
e_or_fusion        : OR union of detections across all channels, merge within 80 ms
e_vote_2of3        : keep candidates confirmed by >= 2 channels within ±100 ms
e11_lane_route     : pool all channels, cluster within 100 ms, keep highest-amplitude
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from src.blinker.default_setting import SCALING_FACTOR
from src.fitutils import mad as compute_mad

from .shared_helpers import make_candidates_df, merge_intervals, scan_threshold_crossings

# ── Default parameters ─────────────────────────────────────────────────────────
K_DEFAULT: float = 1.5
MIN_EVENT_LEN_S: float = 0.05

SLIDING_WINDOW_S: float = 2.0
VOTE_REQUIRED: int = 2
VOTE_TOLERANCE_S: float = 0.100
EXPAND_LOW_K: float = 0.5
BRIDGE_GAP_MS: float = 80.0
DURATION_MIN_MS: float = 50.0
DURATION_MAX_MS: float = 500.0
REFRACTORY_MS: float = 150.0
ADAPTIVE_K_MIN: float = 1.0
ADAPTIVE_K_MAX: float = 2.5
QUANTILE_PCT: float = 93.0
E8_BLOCK_S: float = 10.0
E11_CLUSTER_TOL_MS: float = 100.0
E13_K_CONSERVATIVE: float = 2.0
E13_K_PERMISSIVE: float = 1.2
E13_MIN_CONFIDENT: int = 5


def _global_floor(prepared, ch_idx: int, valid_epoch_indices: list[int]) -> float:
    """Compute global floor = mean + K_DEFAULT * SCALING_FACTOR * MAD(concat)."""
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    return float(np.mean(concat)) + K_DEFAULT * SCALING_FACTOR * float(compute_mad(concat))


# ── Per-channel runners ────────────────────────────────────────────────────────

def run_e_sliding_window_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Sub-epoch rolling median+MAD threshold (2-second window)."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    win_frames = int(SLIDING_WINDOW_S * sfreq)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        n = len(signal)
        T = np.empty(n)
        for i in range(n):
            lo = max(0, i - win_frames // 2)
            hi = min(n, i + win_frames // 2)
            w = signal[lo:hi]
            T[i] = float(np.median(w)) + K_DEFAULT * SCALING_FACTOR * float(compute_mad(w))
        T = np.maximum(T, gfloor)
        above = signal > T
        if not above.any():
            continue
        padded = np.concatenate([[False], above, [False]])
        diff = np.diff(padded.astype(np.int8))
        ons = np.where(diff == 1)[0]
        offs = np.where(diff == -1)[0]
        for o, f in zip(ons, offs):
            if (f - o) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": o / sfreq, "blink_duration": (f - o) / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e_expand_bridge_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Expand event boundaries + bridge gaps within BRIDGE_GAP_MS."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_low = ep_med + EXPAND_LOW_K * ep_mad
        cands = scan_threshold_crossings(signal, T_high, min_frames)
        n = len(signal)
        expanded: list[tuple[int, int]] = []
        for s, e in cands:
            while s > 0 and signal[s - 1] > T_low:
                s -= 1
            while e < n and signal[e] > T_low:
                e += 1
            expanded.append((s, e))
        merged = merge_intervals(expanded, bridge_frames)
        for s, e in merged:
            if (e - s) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e_duration_band_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Reject events outside [DURATION_MIN_MS, DURATION_MAX_MS]."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    dur_min_frames = DURATION_MIN_MS * sfreq / 1000.0
    dur_max_frames = DURATION_MAX_MS * sfreq / 1000.0
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        for s, e in scan_threshold_crossings(signal, T, min_frames):
            dur_frames = e - s
            if dur_min_frames <= dur_frames <= dur_max_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": dur_frames / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e_slope_guard_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Keep candidates where the peak falls within the middle 70% of the event window."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        for s, e in scan_threshold_crossings(signal, T, min_frames):
            seg = signal[s:e]
            peak_pos = int(np.argmax(seg))
            rel = peak_pos / max(len(seg) - 1, 1)
            if 0.15 <= rel <= 0.85:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e_abs_polarity_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Detect on |signal − epoch_median|; catches negative blinks too."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_med = float(np.median(concat))
    global_abs_mad = SCALING_FACTOR * float(compute_mad(np.abs(concat - global_med)))
    global_abs_floor = K_DEFAULT * global_abs_mad
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        centered = np.abs(signal - ep_med)
        ep_abs_mad = SCALING_FACTOR * float(compute_mad(centered))
        T = max(K_DEFAULT * ep_abs_mad, global_abs_floor)
        for s, e in scan_threshold_crossings(centered, T, min_frames):
            rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e_adaptive_k_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Scale k by recording noisiness relative to quiet-epoch baseline."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    ep_mads = [
        SCALING_FACTOR * float(compute_mad(prepared.data[ei, ch_idx, :].astype(float)))
        for ei in valid_epoch_indices
    ]
    quiet_mad = float(np.percentile(ep_mads, 25)) if ep_mads else global_mad
    ratio = global_mad / (quiet_mad + 1e-12)
    k_adj = float(np.clip(K_DEFAULT * ratio, ADAPTIVE_K_MIN, ADAPTIVE_K_MAX))
    global_floor = float(np.mean(concat)) + k_adj * global_mad
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + k_adj * ep_mad, global_floor)
        for s, e in scan_threshold_crossings(signal, T, min_frames):
            rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e_quantile_thr_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """T = max(QUANTILE_PCT-th percentile of epoch, global_floor)."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        T = max(float(np.percentile(signal, QUANTILE_PCT)), gfloor)
        for s, e in scan_threshold_crossings(signal, T, min_frames):
            rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e_refractory_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """E5-style detection followed by 150 ms refractory suppression."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    refrac_frames = int(REFRACTORY_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        raw_cands = scan_threshold_crossings(signal, T, min_frames)
        last_onset = -refrac_frames
        for s, e in raw_cands:
            if s - last_onset >= refrac_frames:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
                last_onset = s
            elif rows:
                prev = rows[-1]
                prev_s = int(prev["blink_onset"] * sfreq)
                prev_e = int(prev_s + prev["blink_duration"] * sfreq)
                if float(np.max(signal[s:e])) > float(np.max(signal[prev_s:prev_e])):
                    rows[-1] = {"epoch_index": epoch_idx, "channel": channel_name,
                                "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq}
                    last_onset = s
    return make_candidates_df(rows, channel_name)


def run_e8_changepoint_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Piecewise block threshold: divide epoch into E8_BLOCK_S-second sub-blocks."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    block_frames = int(E8_BLOCK_S * sfreq)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        n = len(signal)
        for b_start in range(0, n, block_frames):
            b_end = min(b_start + block_frames, n)
            block = signal[b_start:b_end]
            b_med = float(np.median(block))
            b_mad = SCALING_FACTOR * float(compute_mad(block))
            T = max(b_med + K_DEFAULT * b_mad, gfloor)
            for s, e in scan_threshold_crossings(block, T, min_frames):
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": (b_start + s) / sfreq,
                             "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


def run_e13_self_train_channel(
    prepared, ch_idx: int, channel_name: str, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Conservative pass calibrates amplitude gate; permissive pass detects."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_mean + K_DEFAULT * global_mad

    confident_peaks: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_cons = max(ep_med + E13_K_CONSERVATIVE * ep_mad, global_floor)
        for s, e in scan_threshold_crossings(signal, T_cons, min_frames):
            confident_peaks.append(float(np.max(signal[s:e])))

    if len(confident_peaks) >= E13_MIN_CONFIDENT:
        peaks_arr = np.array(confident_peaks)
        peak_med = float(np.median(peaks_arr))
        peak_mad = SCALING_FACTOR * float(compute_mad(peaks_arr))
        amp_gate = max(peak_med - 2.0 * peak_mad, global_floor)
    else:
        amp_gate = global_floor

    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_perm = max(ep_med + E13_K_PERMISSIVE * ep_mad, global_floor)
        for s, e in scan_threshold_crossings(signal, T_perm, min_frames):
            if float(np.max(signal[s:e])) >= amp_gate:
                rows.append({"epoch_index": epoch_idx, "channel": channel_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, channel_name)


# ── Pair-level (multi-channel fusion) runners ─────────────────────────────────

def run_e_or_fusion(
    prepared, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """OR union: pool E5 detections from all channels, merge overlaps within 80 ms."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    bridge = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    ch_name = "or_fusion"
    by_epoch: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for ch_idx in range(len(prepared.channel_names)):
        gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = SCALING_FACTOR * float(compute_mad(signal))
            T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
            for s, e in scan_threshold_crossings(signal, T, min_frames):
                by_epoch[epoch_idx].append((s, e))
    rows: list[dict] = []
    for epoch_idx, cands in by_epoch.items():
        for s, e in merge_intervals(cands, bridge):
            rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return make_candidates_df(rows, ch_name)


def run_e_vote_2of3(
    prepared, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Keep candidates confirmed by >= VOTE_REQUIRED channels within ±tolerance."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    tol_frames = int(VOTE_TOLERANCE_S * sfreq)
    ch_name = "vote_2of3"
    n_ch = len(prepared.channel_names)
    n_samples = prepared.data.shape[2]
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        vote_arr = np.zeros(n_samples, dtype=np.int8)
        for ch_idx in range(n_ch):
            gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = SCALING_FACTOR * float(compute_mad(signal))
            T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
            for s, e in scan_threshold_crossings(signal, T, min_frames):
                lo = max(0, s - tol_frames)
                hi = min(n_samples, e + tol_frames)
                vote_arr[lo:hi] += 1
        consensus = vote_arr >= VOTE_REQUIRED
        if not consensus.any():
            continue
        padded = np.concatenate([[False], consensus, [False]])
        diff = np.diff(padded.astype(np.int8))
        ons = np.where(diff == 1)[0]
        offs = np.where(diff == -1)[0]
        for o, f in zip(ons, offs):
            if (f - o) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": o / sfreq, "blink_duration": (f - o) / sfreq})
    return make_candidates_df(rows, ch_name)


def run_e11_lane_route(
    prepared, valid_epoch_indices: list[int],
    *, min_event_len_s: float = MIN_EVENT_LEN_S,
) -> pd.DataFrame:
    """Pool all channels, cluster within E11_CLUSTER_TOL_MS, keep highest-amplitude."""
    sfreq = float(prepared.sfreq)
    min_frames = min_event_len_s * sfreq
    cluster_tol = int(E11_CLUSTER_TOL_MS * sfreq / 1000.0)
    ch_name = "e11_lane_route"
    all_dets: list[tuple[int, int, int, float, int]] = []
    for ch_idx in range(len(prepared.channel_names)):
        gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = SCALING_FACTOR * float(compute_mad(signal))
            T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
            for s, e in scan_threshold_crossings(signal, T, min_frames):
                peak = float(np.max(signal[s:e]))
                all_dets.append((epoch_idx, s, e, peak, ch_idx))
    if not all_dets:
        return make_candidates_df([], ch_name)
    all_dets.sort(key=lambda x: (x[0], x[1]))
    rows: list[dict] = []
    i = 0
    while i < len(all_dets):
        cluster = [all_dets[i]]
        j = i + 1
        while j < len(all_dets):
            d = all_dets[j]
            if d[0] != cluster[0][0]:
                break
            if d[1] - cluster[-1][1] <= cluster_tol:
                cluster.append(d)
                j += 1
            else:
                break
        best = max(cluster, key=lambda x: x[3])
        ei, s, e, _, chi = best
        ch_display = prepared.channel_names[chi] + "+routed"
        rows.append({"epoch_index": ei, "channel": ch_display,
                     "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        i = j
    return make_candidates_df(rows, ch_name)


# ── Dispatch tables ────────────────────────────────────────────────────────────

PER_CHANNEL_RUNNERS: dict[str, object] = {
    "e_sliding_window": run_e_sliding_window_channel,
    "e_expand_bridge": run_e_expand_bridge_channel,
    "e_duration_band": run_e_duration_band_channel,
    "e_slope_guard": run_e_slope_guard_channel,
    "e_abs_polarity": run_e_abs_polarity_channel,
    "e_adaptive_k": run_e_adaptive_k_channel,
    "e_quantile_thr": run_e_quantile_thr_channel,
    "e_refractory": run_e_refractory_channel,
    "e8_changepoint": run_e8_changepoint_channel,
    "e13_self_train": run_e13_self_train_channel,
}

PAIR_LEVEL_RUNNERS: dict[str, object] = {
    "e_or_fusion": run_e_or_fusion,
    "e_vote_2of3": run_e_vote_2of3,
    "e11_lane_route": run_e11_lane_route,
}

ALL_REMAINING_VARIANTS: list[str] = list(PER_CHANNEL_RUNNERS) + list(PAIR_LEVEL_RUNNERS)

__all__ = [
    "ALL_REMAINING_VARIANTS",
    "PAIR_LEVEL_RUNNERS",
    "PER_CHANNEL_RUNNERS",
    "run_e11_lane_route",
    "run_e13_self_train_channel",
    "run_e8_changepoint_channel",
    "run_e_abs_polarity_channel",
    "run_e_adaptive_k_channel",
    "run_e_duration_band_channel",
    "run_e_expand_bridge_channel",
    "run_e_or_fusion",
    "run_e_quantile_thr_channel",
    "run_e_refractory_channel",
    "run_e_slope_guard_channel",
    "run_e_sliding_window_channel",
    "run_e_vote_2of3",
]
