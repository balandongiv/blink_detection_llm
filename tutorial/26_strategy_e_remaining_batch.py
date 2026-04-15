"""
Tutorial 26 – Strategy E Remaining Variants (Step 1 batch evaluation).

Implements all strategies described in:
  - tutorial/strategy_e_derivative.md  (items 3,4,6,7,8,9,10,11,13,14)
  - tutorial/strategy_e_derivative_2nd.md (E8, E11, E13)

That were NOT yet implemented in tutorials 24 or 25.

New variants
------------
From strategy_e_derivative.md:
  e_sliding_window   (#3)  : sub-epoch rolling median+MAD threshold (2s window)
  e_or_fusion        (#4a) : OR union of detections across all frontal channels
  e_vote_2of3        (#4b) : keep candidates confirmed by >= 2 of 3 channels
  e_expand_bridge    (#6)  : expand event boundaries + bridge gaps within 80ms
  e_duration_band    (#7)  : reject events outside [50 ms, 500 ms]
  e_slope_guard      (#8)  : require blink peak in middle 70% of event window
  e_abs_polarity     (#9)  : detect on |signal − epoch_median| (polarity-agnostic)
  e_adaptive_k       (#10) : scale k by recording noisiness relative to quiet baseline
  e_quantile_thr     (#11) : max(93rd-percentile, global_floor) threshold
  e_refractory       (#14) : enforce 150ms minimum inter-onset separation

From strategy_e_derivative_2nd.md:
  e8_changepoint     (E8)  : piecewise 6-block threshold (10s blocks for 60s epoch)
  e11_lane_route     (E11) : pool all channels, cluster within 100ms, keep best
  e13_self_train     (E13) : conservative (k=2.0) calibrates amplitude gate for
                             permissive (k=1.2) detection pass

Debug mode
----------
DEBUG = True  → first pair only, single-threaded
DEBUG = False → all 65 pairs, N_WORKERS threads

Outputs
-------
    experiment_output/<subject>/<segment>/strategy_<variant>_lane_summary.csv
    experiment_output/strategy_e_remaining_all_results.csv
    experiment_output/strategy_e_remaining_aggregate.csv
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use("Agg")

import mne
import numpy as np
import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Repo root
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_VENDORED_AUTOREJECT = REPO_ROOT / "autoreject"
if str(_VENDORED_AUTOREJECT) not in sys.path:
    sys.path.insert(0, str(_VENDORED_AUTOREJECT))

_pairs_spec = importlib.util.spec_from_file_location(
    "extract_annotation_fif_pair",
    REPO_ROOT / "src_project_development" / "extract_annotation_fif_pair.py",
)
_pairs_mod = importlib.util.module_from_spec(_pairs_spec)   # type: ignore
_pairs_spec.loader.exec_module(_pairs_mod)                  # type: ignore
find_pairs = _pairs_mod.find_pairs

from pyblinker.blinker.default_setting import SCALING_FACTOR  # noqa: E402
from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices  # noqa: E402
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import prepare_epoch_detection_input  # noqa: E402
from pyblinker.epoch_detection_strategy_a.epoch_validation import match_blink_tables  # noqa: E402
from pyblinker.fitutils import mad as compute_mad  # noqa: E402

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
DEBUG = True
N_WORKERS = 4

BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
OUTPUT_ROOT = REPO_ROOT / "experiment_output"

K_DEFAULT = 1.5
MIN_EVENT_LEN_S = 0.05

# e_sliding_window
SLIDING_WINDOW_S = 2.0

# e_vote_2of3
VOTE_REQUIRED = 2               # min channels that must agree
VOTE_TOLERANCE_S = 0.100        # ±100ms tolerance window

# e_expand_bridge
EXPAND_LOW_K = 0.5              # low threshold = median + EXPAND_LOW_K * MAD
BRIDGE_GAP_MS = 80.0

# e_duration_band
DURATION_MIN_MS = 50.0
DURATION_MAX_MS = 500.0

# e_refractory
REFRACTORY_MS = 150.0

# e_adaptive_k
ADAPTIVE_K_MIN = 1.0
ADAPTIVE_K_MAX = 2.5

# e_quantile_thr
QUANTILE_PCT = 93.0

# e8_changepoint
E8_BLOCK_S = 10.0               # 10-second sub-blocks per epoch

# e11_lane_route
E11_CLUSTER_TOL_MS = 100.0

# e13_self_train
E13_K_CONSERVATIVE = 2.0
E13_K_PERMISSIVE = 1.2
E13_MIN_CONFIDENT = 5           # min confident detections needed to fit gate

VARIANT_NAMES = [
    "e_sliding_window",
    "e_or_fusion",
    "e_vote_2of3",
    "e_expand_bridge",
    "e_duration_band",
    "e_slope_guard",
    "e_abs_polarity",
    "e_adaptive_k",
    "e_quantile_thr",
    "e_refractory",
    "e8_changepoint",
    "e11_lane_route",
    "e13_self_train",
]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_brain_region_channels(yaml_path: Path) -> list[str]:
    with yaml_path.open() as fh:
        cfg = yaml.safe_load(fh)
    chs: list[str] = []
    for v in cfg["eeg_regions"].values():
        chs.extend(v)
    return chs


def load_raw_with_brain_channels(fif_path: Path, brain_channels: list[str]) -> mne.io.BaseRaw:
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    available = [c for c in brain_channels if c in raw.ch_names]
    raw.pick(available)
    return raw


def make_fixed_epochs(raw: mne.io.BaseRaw, duration: float = EPOCH_DURATION_S) -> mne.Epochs:
    return mne.make_fixed_length_epochs(raw, duration=duration, preload=True, verbose="ERROR")


def load_annotation_as_reference(csv_path: Path, epoch_duration: float = EPOCH_DURATION_S) -> pd.DataFrame:
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    rows = []
    for _, row in df.iterrows():
        onset = float(row["onset"])
        dur = float(row["duration"])
        ep = int(onset // epoch_duration)
        rows.append({"epoch_index": ep, "blink_onset": onset - ep * epoch_duration, "blink_duration": dur})
    return pd.DataFrame(rows, columns=["epoch_index", "blink_onset", "blink_duration"])


# ---------------------------------------------------------------------------
# Shared scanning primitives
# ---------------------------------------------------------------------------

def _crossings(signal: np.ndarray, threshold: float, min_frames: float) -> list[tuple[int, int]]:
    above = signal > threshold
    if not above.any():
        return []
    padded = np.concatenate([[False], above, [False]])
    diff = np.diff(padded.astype(np.int8))
    ons = np.where(diff == 1)[0]
    offs = np.where(diff == -1)[0]
    return [(int(o), int(f)) for o, f in zip(ons, offs) if (f - o) > min_frames]


def _merge_intervals(intervals: list[tuple[int, int]], gap_frames: int) -> list[tuple[int, int]]:
    if not intervals:
        return []
    sv = sorted(intervals)
    m: list[list[int]] = [[sv[0][0], sv[0][1]]]
    for s, e in sv[1:]:
        if s <= m[-1][1] + gap_frames:
            m[-1][1] = max(m[-1][1], e)
        else:
            m.append([s, e])
    return [(a, b) for a, b in m]


def _make_df(rows: list[dict]) -> pd.DataFrame:
    if rows:
        return pd.DataFrame(rows).sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)
    return pd.DataFrame(columns=["epoch_index", "channel", "blink_onset", "blink_duration"])


def _global_floor(prepared, ch_idx: int, valid_epoch_indices: list[int]) -> float:
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    return float(np.mean(concat)) + K_DEFAULT * SCALING_FACTOR * float(compute_mad(concat))


# ---------------------------------------------------------------------------
# Per-channel runners
# ---------------------------------------------------------------------------

def _ch_sliding_window(prepared, ch_idx, ch_name, valid_epoch_indices):
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    win_frames = int(SLIDING_WINDOW_S * sfreq)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        n = len(signal)
        # Build time-varying threshold via rolling median+MAD
        T = np.empty(n)
        for i in range(n):
            lo = max(0, i - win_frames // 2)
            hi = min(n, i + win_frames // 2)
            w = signal[lo:hi]
            T[i] = float(np.median(w)) + K_DEFAULT * SCALING_FACTOR * float(compute_mad(w))
        # Apply global floor
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
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": o / sfreq, "blink_duration": (f - o) / sfreq})
    return _make_df(rows)


def _ch_expand_bridge(prepared, ch_idx, ch_name, valid_epoch_indices):
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_low = ep_med + EXPAND_LOW_K * ep_mad  # expansion threshold

        # Initial detection at T_high
        cands = _crossings(signal, T_high, min_frames)

        # Expand each candidate boundary while signal > T_low
        expanded = []
        n = len(signal)
        for s, e in cands:
            while s > 0 and signal[s - 1] > T_low:
                s -= 1
            while e < n and signal[e] > T_low:
                e += 1
            expanded.append((s, e))

        # Bridge gaps
        merged = _merge_intervals(expanded, bridge_frames)
        for s, e in merged:
            if (e - s) > min_frames:
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


def _ch_duration_band(prepared, ch_idx, ch_name, valid_epoch_indices):
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    dur_min_frames = DURATION_MIN_MS * sfreq / 1000.0
    dur_max_frames = DURATION_MAX_MS * sfreq / 1000.0
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        for s, e in _crossings(signal, T, min_frames):
            dur_frames = e - s
            if dur_min_frames <= dur_frames <= dur_max_frames:
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": s / sfreq, "blink_duration": dur_frames / sfreq})
    return _make_df(rows)


def _ch_slope_guard(prepared, ch_idx, ch_name, valid_epoch_indices):
    """Keep candidates where the peak falls within the middle 70% of the event window."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        for s, e in _crossings(signal, T, min_frames):
            seg = signal[s:e]
            peak_pos = int(np.argmax(seg))
            rel = peak_pos / max(len(seg) - 1, 1)
            if 0.15 <= rel <= 0.85:   # peak in middle 70%
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


def _ch_abs_polarity(prepared, ch_idx, ch_name, valid_epoch_indices):
    """Detect on |signal - epoch_median|; catches negative blinks too."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    # Global floor from concatenated absolute-centered signal
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_med = float(np.median(concat))
    global_abs_mad = SCALING_FACTOR * float(compute_mad(np.abs(concat - global_med)))
    global_abs_floor = K_DEFAULT * global_abs_mad
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        centered = np.abs(signal - ep_med)
        ep_abs_mad = SCALING_FACTOR * float(compute_mad(centered))
        T = max(K_DEFAULT * ep_abs_mad, global_abs_floor)
        for s, e in _crossings(centered, T, min_frames):
            rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


def _ch_adaptive_k(prepared, ch_idx, ch_name, valid_epoch_indices):
    """Scale k by recording noisiness: noisier → higher k; quieter → lower k."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mad = SCALING_FACTOR * float(compute_mad(concat))

    # Estimate quiet-baseline MAD as the 25th percentile of per-epoch MADs
    ep_mads = []
    for epoch_idx in valid_epoch_indices:
        sig = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_mads.append(SCALING_FACTOR * float(compute_mad(sig)))
    quiet_mad = float(np.percentile(ep_mads, 25)) if ep_mads else global_mad

    # Adaptive k: proportional to ratio of global to quiet MAD
    ratio = global_mad / (quiet_mad + 1e-12)
    k_adj = float(np.clip(K_DEFAULT * ratio, ADAPTIVE_K_MIN, ADAPTIVE_K_MAX))

    global_floor = float(np.mean(concat)) + k_adj * global_mad

    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + k_adj * ep_mad, global_floor)
        for s, e in _crossings(signal, T, min_frames):
            rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


def _ch_quantile_thr(prepared, ch_idx, ch_name, valid_epoch_indices):
    """T = max(QUANTILE_PCT-th percentile of epoch, global_floor)."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        T = max(float(np.percentile(signal, QUANTILE_PCT)), gfloor)
        for s, e in _crossings(signal, T, min_frames):
            rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


def _ch_refractory(prepared, ch_idx, ch_name, valid_epoch_indices):
    """E5-style detection followed by 150ms refractory suppression."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    refrac_frames = int(REFRACTORY_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        raw_cands = _crossings(signal, T, min_frames)

        # Apply refractory: keep strongest non-overlapping candidate each period
        last_onset = -refrac_frames
        for s, e in raw_cands:
            if s - last_onset >= refrac_frames:
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
                last_onset = s
            else:
                # Compare peak amplitudes; keep the stronger one
                prev = rows[-1]
                prev_s = int(prev["blink_onset"] * sfreq)
                prev_e = int(prev_s + prev["blink_duration"] * sfreq)
                if float(np.max(signal[s:e])) > float(np.max(signal[prev_s:prev_e])):
                    rows[-1] = {"epoch_index": epoch_idx, "channel": ch_name,
                                "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq}
                    last_onset = s
    return _make_df(rows)


def _ch_e8_changepoint(prepared, ch_idx, ch_name, valid_epoch_indices):
    """Piecewise block threshold: divide epoch into 10-second sub-blocks."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    block_frames = int(E8_BLOCK_S * sfreq)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
    rows = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        n = len(signal)
        # Split into blocks and detect per-block, report absolute-within-epoch offsets
        for b_start in range(0, n, block_frames):
            b_end = min(b_start + block_frames, n)
            block = signal[b_start:b_end]
            b_med = float(np.median(block))
            b_mad = SCALING_FACTOR * float(compute_mad(block))
            T = max(b_med + K_DEFAULT * b_mad, gfloor)
            for s, e in _crossings(block, T, min_frames):
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": (b_start + s) / sfreq,
                             "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


def _ch_e13_self_train(prepared, ch_idx, ch_name, valid_epoch_indices):
    """Conservative pass (k=2.0) calibrates amplitude gate; permissive pass (k=1.2) detects."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_mean + K_DEFAULT * global_mad

    # --- Pass 1: conservative k=2.0 → high-confidence detections ---
    confident_peaks: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_cons = max(ep_med + E13_K_CONSERVATIVE * ep_mad, global_floor)
        for s, e in _crossings(signal, T_cons, min_frames):
            confident_peaks.append(float(np.max(signal[s:e])))

    # Fit amplitude gate from confident detections
    if len(confident_peaks) >= E13_MIN_CONFIDENT:
        peaks_arr = np.array(confident_peaks)
        peak_med = float(np.median(peaks_arr))
        peak_mad = SCALING_FACTOR * float(compute_mad(peaks_arr))
        amp_gate = max(peak_med - 2.0 * peak_mad, global_floor)
    else:
        amp_gate = global_floor

    # --- Pass 2: permissive k=1.2 → more candidates, filtered by amplitude gate ---
    rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_perm = max(ep_med + E13_K_PERMISSIVE * ep_mad, global_floor)
        for s, e in _crossings(signal, T_perm, min_frames):
            if float(np.max(signal[s:e])) >= amp_gate:
                rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


# ---------------------------------------------------------------------------
# Pair-level runners (multi-channel fusion strategies)
# ---------------------------------------------------------------------------

def _pair_or_fusion(prepared, valid_epoch_indices):
    """OR union: pool E5 detections from all channels, merge overlaps within 80ms."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    bridge = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    ch_name = "or_fusion"

    # Per-epoch pools
    by_epoch: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for ch_idx in range(len(prepared.channel_names)):
        gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = SCALING_FACTOR * float(compute_mad(signal))
            T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
            for s, e in _crossings(signal, T, min_frames):
                by_epoch[epoch_idx].append((s, e))

    rows: list[dict] = []
    for epoch_idx, cands in by_epoch.items():
        for s, e in _merge_intervals(cands, bridge):
            rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    return _make_df(rows)


def _pair_vote_2of3(prepared, valid_epoch_indices):
    """Keep candidates confirmed by >= VOTE_REQUIRED channels within VOTE_TOLERANCE."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    tol_frames = int(VOTE_TOLERANCE_S * sfreq)
    ch_name = "vote_2of3"
    n_ch = len(prepared.channel_names)

    # Build per-channel binary detection arrays per epoch
    # Then consensus = sum >= VOTE_REQUIRED
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
            for s, e in _crossings(signal, T, min_frames):
                # Dilate by tolerance to capture inter-channel agreement
                lo = max(0, s - tol_frames)
                hi = min(n_samples, e + tol_frames)
                vote_arr[lo:hi] += 1

        # Regions where >= VOTE_REQUIRED channels agree
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
    return _make_df(rows)


def _pair_e11_lane_route(prepared, valid_epoch_indices):
    """Pool all channels' E5 detections; cluster within 100ms; keep best per cluster."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    cluster_tol = int(E11_CLUSTER_TOL_MS * sfreq / 1000.0)
    ch_name = "e11_lane_route"

    # Collect (epoch_idx, onset, offset, peak_amp, ch_idx)
    all_dets: list[tuple[int, int, int, float, int]] = []
    for ch_idx in range(len(prepared.channel_names)):
        gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = SCALING_FACTOR * float(compute_mad(signal))
            T = max(ep_med + K_DEFAULT * ep_mad, gfloor)
            for s, e in _crossings(signal, T, min_frames):
                peak = float(np.max(signal[s:e]))
                all_dets.append((epoch_idx, s, e, peak, ch_idx))

    if not all_dets:
        return _make_df([])

    # Sort by epoch then onset
    all_dets.sort(key=lambda x: (x[0], x[1]))

    rows: list[dict] = []
    i = 0
    while i < len(all_dets):
        # Start a new cluster
        cluster = [all_dets[i]]
        j = i + 1
        while j < len(all_dets):
            d = all_dets[j]
            if d[0] != cluster[0][0]:  # different epoch
                break
            if d[1] - cluster[-1][1] <= cluster_tol:  # within tolerance of last cluster end
                cluster.append(d)
                j += 1
            else:
                break
        # Keep the detection with the highest peak amplitude
        best = max(cluster, key=lambda x: x[3])
        ei, s, e, peak, chi = best
        ch_display = prepared.channel_names[chi] + "+routed"
        rows.append({"epoch_index": ei, "channel": ch_display,
                     "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        i = j
    return _make_df(rows)


# ---------------------------------------------------------------------------
# Variant dispatch
# ---------------------------------------------------------------------------

_PER_CHANNEL_RUNNERS = {
    "e_sliding_window": _ch_sliding_window,
    "e_expand_bridge": _ch_expand_bridge,
    "e_duration_band": _ch_duration_band,
    "e_slope_guard": _ch_slope_guard,
    "e_abs_polarity": _ch_abs_polarity,
    "e_adaptive_k": _ch_adaptive_k,
    "e_quantile_thr": _ch_quantile_thr,
    "e_refractory": _ch_refractory,
    "e8_changepoint": _ch_e8_changepoint,
    "e13_self_train": _ch_e13_self_train,
}

_PAIR_LEVEL_RUNNERS = {
    "e_or_fusion": _pair_or_fusion,
    "e_vote_2of3": _pair_vote_2of3,
    "e11_lane_route": _pair_e11_lane_route,
}


def run_variant(variant: str, prepared, valid_epoch_indices: list[int],
                reference: pd.DataFrame, n_epochs: int) -> pd.DataFrame:
    rows: list[dict] = []

    if variant in _PAIR_LEVEL_RUNNERS:
        candidates = _PAIR_LEVEL_RUNNERS[variant](prepared, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=n_epochs)
        rows.append({
            "variant": variant, "channel": variant,
            "candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })
    else:
        runner = _PER_CHANNEL_RUNNERS[variant]
        for ch_idx, ch_name in enumerate(prepared.channel_names):
            candidates = runner(prepared, ch_idx, ch_name, valid_epoch_indices)
            metrics = match_blink_tables(candidates, reference, n_epochs=n_epochs)
            rows.append({
                "variant": variant, "channel": ch_name,
                "candidate_count": int(len(candidates)),
                "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                "recall": float(metrics.recall), "f1": float(metrics.f1),
            })

    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values(["f1", "tp", "fp", "channel"], ascending=[False, False, True, True])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Per-pair processing
# ---------------------------------------------------------------------------

def process_pair(subject: str, segment: str, fif_path: Path,
                 annotation_path: Path, brain_channels: list[str]) -> list[dict]:
    out_dir = OUTPUT_ROOT / subject / segment
    out_dir.mkdir(parents=True, exist_ok=True)

    base: dict = {
        "subject": subject, "segment": segment,
        "elapsed_s": float("nan"), "n_epochs": 0, "n_annotations": 0,
        "n_lanes": 0, "best_channel": "", "best_tp": 0, "best_fp": 0, "best_fn": 0,
        "best_precision": float("nan"), "best_recall": float("nan"), "best_f1": float("nan"),
        "error": "",
    }

    try:
        raw = load_raw_with_brain_channels(fif_path, brain_channels)
        epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
        reference = load_annotation_as_reference(annotation_path, epoch_duration=EPOCH_DURATION_S)
        valid_epoch_indices = get_valid_epoch_indices(epochs)
        n_epochs = len(epochs)
        n_annotations = len(reference)
        reference.to_csv(out_dir / "reference_annotation.csv", index=False)
        prepared = prepare_epoch_detection_input(
            epochs, pick_types_options={"eeg": True},
            filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
        )
    except Exception:
        tb = traceback.format_exc()
        print(f"    [ERROR] loading {subject}/{segment}\n{tb}")
        results = []
        for v in VARIANT_NAMES:
            r = dict(base); r["variant"] = v; r["error"] = tb
            results.append(r)
        (out_dir / "load_error.txt").write_text(tb)
        return results

    results: list[dict] = []
    for variant in VARIANT_NAMES:
        r = dict(base)
        r["variant"] = variant
        r["n_epochs"] = n_epochs
        r["n_annotations"] = n_annotations
        t0 = perf_counter()
        try:
            summary = run_variant(variant, prepared, valid_epoch_indices, reference, n_epochs)
            summary.to_csv(out_dir / f"strategy_{variant}_lane_summary.csv", index=False)
            r["n_lanes"] = len(summary)
            if not summary.empty:
                best = summary.iloc[0]
                r.update({
                    "best_channel": str(best["channel"]),
                    "best_tp": int(best["tp"]), "best_fp": int(best["fp"]),
                    "best_fn": int(best["fn"]), "best_precision": float(best["precision"]),
                    "best_recall": float(best["recall"]), "best_f1": float(best["f1"]),
                })
        except Exception:
            tb = traceback.format_exc()
            r["error"] = tb
            (out_dir / f"strategy_{variant}_error.txt").write_text(tb)
            print(f"    [ERROR] {variant} on {subject}/{segment}\n{tb}")

        r["elapsed_s"] = perf_counter() - t0
        results.append(r)

        if not r["error"]:
            print(f"      [{variant}] {r['elapsed_s']:.1f}s  lanes={r['n_lanes']}  "
                  f"best_ch={r['best_channel']}  TP={r['best_tp']}  FP={r['best_fp']}  "
                  f"FN={r['best_fn']}  P={r['best_precision']:.3f}  R={r['best_recall']:.3f}  "
                  f"F1={r['best_f1']:.3f}")

    return results


# ---------------------------------------------------------------------------
# Aggregate helper
# ---------------------------------------------------------------------------

def compute_aggregate(df: pd.DataFrame, variant: str) -> dict:
    sub = df[(df["variant"] == variant) & (df["error"].isna() | (df["error"] == ""))]
    total = len(df[df["variant"] == variant])
    n_ok = len(sub)
    n_fail = total - n_ok
    if sub.empty:
        return {"variant": variant, "n_pairs_total": total,
                "n_pairs_successful": n_ok, "n_pairs_failed": n_fail,
                "total_tp": 0, "total_fp": 0, "total_fn": 0,
                "micro_precision": float("nan"), "micro_recall": float("nan"),
                "micro_f1": float("nan"), "macro_precision": float("nan"),
                "macro_recall": float("nan"), "macro_f1": float("nan")}
    ttp = int(sub["best_tp"].sum()); tfp = int(sub["best_fp"].sum()); tfn = int(sub["best_fn"].sum())
    mp = ttp / (ttp + tfp) if (ttp + tfp) > 0 else float("nan")
    mr = ttp / (ttp + tfn) if (ttp + tfn) > 0 else float("nan")
    mf = 2 * mp * mr / (mp + mr) if (mp + mr) > 0 else float("nan")
    return {
        "variant": variant, "n_pairs_total": total,
        "n_pairs_successful": n_ok, "n_pairs_failed": n_fail,
        "total_tp": ttp, "total_fp": tfp, "total_fn": tfn,
        "micro_precision": mp, "micro_recall": mr, "micro_f1": mf,
        "macro_precision": float(sub["best_precision"].mean()),
        "macro_recall": float(sub["best_recall"].mean()),
        "macro_f1": float(sub["best_f1"].mean()),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _task(args: tuple) -> list[dict]:
    i, n, subj, seg, fif, ann, bch = args
    print(f"[{i}/{n}] {subj} / {seg}")
    res = process_pair(subj, seg, fif, ann, bch)
    print()
    return res


def main() -> None:
    print("=" * 70)
    print("Tutorial 26 – Strategy E Remaining Variants  (Step 1 batch)")
    print("=" * 70)
    print(f"DEBUG mode : {DEBUG}  |  N_WORKERS : {1 if DEBUG else N_WORKERS}")
    print(f"Variants   : {VARIANT_NAMES}\n")

    pairs = find_pairs()
    if not pairs:
        print("No matched pairs found."); return

    if DEBUG:
        pairs = pairs[:1]
        print(f"[DEBUG] First pair only: {pairs[0]['subject']} / {pairs[0]['segment']}")
    else:
        print(f"Found {len(pairs)} pair(s). Output root: {OUTPUT_ROOT}")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    print(f"Brain-region channels ({len(brain_channels)}): {brain_channels}\n")

    tasks = [(i, len(pairs), p["subject"], p["segment"],
              Path(p["fif"]), Path(p["csv"]), brain_channels)
             for i, p in enumerate(pairs, 1)]

    all_results: list[dict] = []
    if DEBUG or N_WORKERS == 1:
        for task in tasks:
            all_results.extend(_task(task))
    else:
        with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
            futures = {ex.submit(_task, t): t for t in tasks}
            for fut in as_completed(futures):
                all_results.extend(fut.result())

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    per_pair_df = pd.DataFrame(all_results)
    per_pair_csv = OUTPUT_ROOT / "strategy_e_remaining_all_results.csv"
    per_pair_df.to_csv(per_pair_csv, index=False)
    print(f"Per-pair results -> {per_pair_csv}\n")

    agg_rows = [compute_aggregate(per_pair_df, v) for v in VARIANT_NAMES]
    agg_df = pd.DataFrame(agg_rows)
    agg_df.to_csv(OUTPUT_ROOT / "strategy_e_remaining_aggregate.csv", index=False)
    print("=" * 70)
    print("AGGREGATE SUMMARY  (best lane per pair)")
    print("=" * 70)
    disp = agg_df[["variant", "n_pairs_successful", "n_pairs_failed",
                   "total_tp", "total_fp", "total_fn",
                   "micro_precision", "micro_recall", "micro_f1",
                   "macro_precision", "macro_recall", "macro_f1"]].copy()
    for col in ("micro_precision", "micro_recall", "micro_f1",
                "macro_precision", "macro_recall", "macro_f1"):
        disp[col] = disp[col].map(lambda x: f"{x:.4f}" if x == x else "nan")  # noqa: PLR0124
    print(disp.to_string(index=False))


if __name__ == "__main__":
    main()
