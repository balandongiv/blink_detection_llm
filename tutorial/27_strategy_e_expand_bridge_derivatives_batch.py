"""
Tutorial 27 – Strategy E Expand-Bridge Derivatives (Step 1 batch evaluation).

Exploratory variants of ``strategy_e_expand_bridge`` following the roadmap
in tutorial/strategy_e_expand_bridge_exploratory_plan.md.

Baseline
--------
strategy_e_expand_bridge: micro F1 = 0.6592, recall = 0.7460, precision = 0.5905
TP / FP / FN: 30,901 / 21,428 / 10,523

Implemented variants
--------------------
expand_bridge_dynamic_low
    Replace fixed T_low expansion threshold with an epoch-aware adaptive one.
    Noisy epochs → higher T_low → less expansion.
    Quiet epochs → lower T_low → more aggressive expansion.

expand_bridge_dynamic_gap
    Replace fixed 80 ms bridge with a candidate-strength-aware bridge.
    Strong-to-strong pairs: 100 ms.
    Mixed or weak-to-weak pairs: 40 ms.

expand_bridge_confidence_weighted
    Two-tier trust before expansion and bridging.
    Strong candidates (high peak amplitude): aggressive expand (k_low=0.3) + 80 ms bridge.
    Weak candidates (lower peak amplitude): conservative expand (k_low=0.8) + 40 ms bridge.

expand_bridge_sw_onset  (Tier 1)
    Use sliding-window threshold for the onset detector (cleaner starts),
    then apply expand+bridge boundary recovery.
    Borrows the cleaner onset from strategy_e_sliding_window while recovering
    boundary quality via expand_bridge.

expand_bridge_adaptive_k  (Tier 2)
    Use adaptive-k logic for T_high (cleans the candidate pool),
    then apply normal expand+bridge post-processing.

expand_bridge_soft_gate  (Tier 1)
    Conservative pass (k=2.0) learns pair-specific amplitude gate.
    Full expand+bridge pass, then filter by that gate.
    Targets the weak-FP tail without touching the core boundary-recovery logic.

Debug mode
----------
Set DEBUG = True → run only the first pair (single-threaded, fast feedback).
Set DEBUG = False → run all 65 pairs with N_WORKERS threads.

Outputs
-------
    experiment_output/<subject>/<segment>/expand_bridge_dynamic_low_lane_summary.csv
    experiment_output/<subject>/<segment>/expand_bridge_dynamic_gap_lane_summary.csv
    experiment_output/<subject>/<segment>/expand_bridge_confidence_weighted_lane_summary.csv
    experiment_output/<subject>/<segment>/expand_bridge_sw_onset_lane_summary.csv
    experiment_output/<subject>/<segment>/expand_bridge_adaptive_k_lane_summary.csv
    experiment_output/<subject>/<segment>/expand_bridge_soft_gate_lane_summary.csv
    experiment_output/expand_bridge_derivatives_all_results.csv
    experiment_output/expand_bridge_derivatives_aggregate.csv
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
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
# Repo root on sys.path
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_VENDORED_AUTOREJECT = REPO_ROOT / "autoreject"
if str(_VENDORED_AUTOREJECT) not in sys.path:
    sys.path.insert(0, str(_VENDORED_AUTOREJECT))

# ---------------------------------------------------------------------------
# Dynamic import of find_pairs
# ---------------------------------------------------------------------------
_pairs_spec = importlib.util.spec_from_file_location(
    "extract_annotation_fif_pair",
    REPO_ROOT / "src_project_development" / "extract_annotation_fif_pair.py",
)
_pairs_mod = importlib.util.module_from_spec(_pairs_spec)  # type: ignore[arg-type]
_pairs_spec.loader.exec_module(_pairs_mod)  # type: ignore[union-attr]
find_pairs = _pairs_mod.find_pairs

from pyblinker.blinker.default_setting import SCALING_FACTOR  # noqa: E402
from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices  # noqa: E402
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (  # noqa: E402
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_a.epoch_validation import match_blink_tables  # noqa: E402
from pyblinker.fitutils import mad as compute_mad  # noqa: E402

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
DEBUG = True        # True = first pair only, single-threaded; False = all 65 pairs
N_WORKERS = 4       # only used when DEBUG = False

BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
OUTPUT_ROOT = REPO_ROOT / "experiment_output"

# Base parameters shared with strategy_e_expand_bridge
K_DEFAULT = 1.5            # standard detection threshold multiplier
MIN_EVENT_LEN_S = 0.05    # minimum blink duration in seconds
EXPAND_LOW_K = 0.5         # k for expansion boundary in base variant
BRIDGE_GAP_MS = 80.0       # bridge gaps smaller than this (ms) in base variant

# --- Dynamic low threshold (expand_bridge_dynamic_low) ---
# k_low is scaled by epoch_mad / global_mad, then clipped to [K_LOW_MIN, K_LOW_MAX]
EXPAND_DYN_LOW_K_BASE = 0.5     # baseline expansion k (same as base variant)
EXPAND_DYN_LOW_K_MIN = 0.2      # most aggressive allowed (quiet epoch)
EXPAND_DYN_LOW_K_MAX = 1.0      # most conservative allowed (noisy epoch)

# --- Dynamic gap (expand_bridge_dynamic_gap) ---
EXPAND_DYN_GAP_STRONG_MS = 100.0   # bridge between two strong candidates
EXPAND_DYN_GAP_WEAK_MS = 40.0      # bridge for weak-to-weak or mixed pairs
# A candidate is "strong" if peak amplitude > T_high + STRONG_PROMINENCE_K * ep_mad
EXPAND_DYN_GAP_STRONG_K = 0.5

# --- Confidence-weighted expansion+bridging (expand_bridge_confidence_weighted) ---
EXPAND_CONF_K_LOW_STRONG = 0.3    # aggressive expansion for strong candidates
EXPAND_CONF_K_LOW_WEAK = 0.8      # conservative expansion for weak candidates
EXPAND_CONF_BRIDGE_STRONG_MS = 80.0   # normal bridge for strong candidates
EXPAND_CONF_BRIDGE_WEAK_MS = 40.0     # short bridge for weak candidates
# Strong if peak amplitude > T_high + CONF_STRONG_K * ep_mad
EXPAND_CONF_STRONG_K = 0.5

# --- SW-onset + expand-bridge (expand_bridge_sw_onset) ---
EXPAND_SW_WINDOW_S = 2.0   # rolling window for sliding-window onset threshold

# --- Adaptive-k + expand-bridge (expand_bridge_adaptive_k) ---
EXPAND_ADAPTIVE_K_MIN = 1.0
EXPAND_ADAPTIVE_K_MAX = 2.5

# --- Soft gate after expand-bridge (expand_bridge_soft_gate) ---
SOFT_GATE_K_CONSERVATIVE = 2.0   # conservative pass k to collect confident peaks
SOFT_GATE_MIN_CONFIDENT = 5      # min confident events before using learned gate

VARIANT_NAMES = [
    "expand_bridge_dynamic_low",
    "expand_bridge_dynamic_gap",
    "expand_bridge_confidence_weighted",
    "expand_bridge_sw_onset",
    "expand_bridge_adaptive_k",
    "expand_bridge_soft_gate",
]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_brain_region_channels(yaml_path: Path) -> list[str]:
    with yaml_path.open() as fh:
        config = yaml.safe_load(fh)
    channels: list[str] = []
    for region_channels in config["eeg_regions"].values():
        channels.extend(region_channels)
    return channels


def load_raw_with_brain_channels(fif_path: Path, brain_channels: list[str]) -> mne.io.BaseRaw:
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    available = [ch for ch in brain_channels if ch in raw.ch_names]
    missing = [ch for ch in brain_channels if ch not in raw.ch_names]
    if missing:
        print(f"    [warn] channels absent in file: {missing}")
    raw.pick(available)
    return raw


def make_fixed_epochs(raw: mne.io.BaseRaw, duration: float = EPOCH_DURATION_S) -> mne.Epochs:
    return mne.make_fixed_length_epochs(raw, duration=duration, preload=True, verbose="ERROR")


def load_annotation_as_reference(
    csv_path: Path,
    epoch_duration: float = EPOCH_DURATION_S,
    blink_description: str | None = None,
) -> pd.DataFrame:
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    if blink_description is not None and "description" in df.columns:
        df = df[df["description"] == blink_description].copy()
    rows: list[dict] = []
    for _, row in df.iterrows():
        onset_abs = float(row["onset"])
        duration = float(row["duration"])
        epoch_index = int(onset_abs // epoch_duration)
        rows.append({
            "epoch_index": epoch_index,
            "blink_onset": onset_abs - epoch_index * epoch_duration,
            "blink_duration": duration,
        })
    return pd.DataFrame(rows, columns=["epoch_index", "blink_onset", "blink_duration"])


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

def _global_floor(prepared, ch_idx: int, valid_epoch_indices: list[int]) -> float:
    """Global floor = mean + K_DEFAULT * SCALING * MAD(concat)."""
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    return float(np.mean(concat)) + K_DEFAULT * SCALING_FACTOR * float(compute_mad(concat))


def _scan_threshold_crossings(
    signal: np.ndarray,
    threshold: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Vectorised threshold-crossing scan. Returns (onset_sample, offset_sample) pairs."""
    above = signal > threshold
    if not above.any():
        return []
    padded = np.concatenate([[False], above, [False]])
    diff = np.diff(padded.astype(np.int8))
    onsets = np.where(diff == 1)[0]
    offsets = np.where(diff == -1)[0]
    return [
        (int(on), int(off))
        for on, off in zip(onsets, offsets)
        if (off - on) > min_blink_frames
    ]


def _expand_interval(signal: np.ndarray, s: int, e: int, t_low: float) -> tuple[int, int]:
    """Expand (s, e) outward while signal exceeds t_low."""
    n = len(signal)
    while s > 0 and signal[s - 1] > t_low:
        s -= 1
    while e < n and signal[e] > t_low:
        e += 1
    return s, e


def _merge_intervals(
    intervals: list[tuple[int, int]],
    gap_frames: int,
) -> list[tuple[int, int]]:
    """Merge overlapping / nearby intervals within gap_frames."""
    if not intervals:
        return []
    sorted_ivs = sorted(intervals)
    merged: list[list[int]] = [[sorted_ivs[0][0], sorted_ivs[0][1]]]
    for start, end in sorted_ivs[1:]:
        if start <= merged[-1][1] + gap_frames:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def _merge_intervals_conditional(
    intervals: list[tuple[int, int]],
    is_strong: list[bool],
    gap_strong_frames: int,
    gap_weak_frames: int,
) -> list[tuple[int, int]]:
    """Merge intervals; gap size depends on whether both neighbors are strong.

    If both adjacent intervals are tagged as strong → use gap_strong_frames.
    Otherwise (one or both weak) → use gap_weak_frames.
    """
    if not intervals:
        return []
    paired = sorted(zip(intervals, is_strong), key=lambda x: x[0][0])
    merged: list[tuple[tuple[int, int], bool]] = [(paired[0][0], paired[0][1])]
    for curr_iv, curr_strong in paired[1:]:
        prev_iv, prev_strong = merged[-1]
        if prev_strong and curr_strong:
            max_gap = gap_strong_frames
        else:
            max_gap = gap_weak_frames
        gap = curr_iv[0] - prev_iv[1]
        if gap <= max_gap:
            merged[-1] = ((prev_iv[0], max(prev_iv[1], curr_iv[1])), prev_strong or curr_strong)
        else:
            merged.append((curr_iv, curr_strong))
    return [iv for iv, _ in merged]


def _make_candidates_df(cand_rows: list[dict], channel_name: str) -> pd.DataFrame:
    if cand_rows:
        return (
            pd.DataFrame(cand_rows)
            .sort_values(["epoch_index", "blink_onset"])
            .reset_index(drop=True)
        )
    return pd.DataFrame(columns=["epoch_index", "channel", "blink_onset", "blink_duration"])


def _build_lane_summary(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values(["f1", "tp", "fp", "channel"], ascending=[False, False, True, True])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Variant 1 – expand_bridge_dynamic_low
# ---------------------------------------------------------------------------

def _run_dynamic_low_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """Epoch-aware T_low: k_low scales with epoch noise level.

    In noisy epochs (ep_mad > global_mad): k_low increases → T_low rises →
        expansion is more conservative → fewer FP from over-expansion.
    In quiet epochs (ep_mad < global_mad): k_low decreases → T_low falls →
        expansion is more aggressive → better boundary recovery.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mad = SCALING_FACTOR * float(compute_mad(concat))

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)

        # Adaptive k_low: scales proportionally to epoch noise vs global noise.
        noise_ratio = ep_mad / (global_mad + 1e-12)
        k_low_adj = float(np.clip(EXPAND_DYN_LOW_K_BASE * noise_ratio,
                                  EXPAND_DYN_LOW_K_MIN, EXPAND_DYN_LOW_K_MAX))
        T_low = ep_med + k_low_adj * ep_mad

        cands = _scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]
        merged = _merge_intervals(expanded, bridge_frames)

        for s, e in merged:
            if (e - s) > min_frames:
                cand_rows.append({
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": s / sfreq,
                    "blink_duration": (e - s) / sfreq,
                })

    return _make_candidates_df(cand_rows, channel_name)


def run_expand_bridge_dynamic_low(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
    )
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        candidates = _run_dynamic_low_channel(prepared, ch_idx, ch_name, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": ch_name,
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })
    summary = _build_lane_summary(rows)
    summary.to_csv(out_dir / "expand_bridge_dynamic_low_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Variant 2 – expand_bridge_dynamic_gap
# ---------------------------------------------------------------------------

def _run_dynamic_gap_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """Candidate-strength-aware gap bridging.

    Each expanded candidate is tagged as "strong" if its peak amplitude
    exceeds T_high + EXPAND_DYN_GAP_STRONG_K * ep_mad.
    Adjacent strong–strong pairs: bridge up to EXPAND_DYN_GAP_STRONG_MS.
    All other pairs (mixed or weak–weak): bridge up to EXPAND_DYN_GAP_WEAK_MS.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    gap_strong_frames = int(EXPAND_DYN_GAP_STRONG_MS * sfreq / 1000.0)
    gap_weak_frames = int(EXPAND_DYN_GAP_WEAK_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_low = ep_med + EXPAND_LOW_K * ep_mad
        T_strong = T_high + EXPAND_DYN_GAP_STRONG_K * ep_mad

        cands = _scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]

        # Tag each interval as strong based on peak amplitude
        is_strong: list[bool] = []
        for s, e in expanded:
            peak = float(np.max(signal[s:e])) if e > s else T_high
            is_strong.append(peak >= T_strong)

        merged = _merge_intervals_conditional(
            expanded, is_strong, gap_strong_frames, gap_weak_frames
        )

        for s, e in merged:
            if (e - s) > min_frames:
                cand_rows.append({
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": s / sfreq,
                    "blink_duration": (e - s) / sfreq,
                })

    return _make_candidates_df(cand_rows, channel_name)


def run_expand_bridge_dynamic_gap(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
    )
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        candidates = _run_dynamic_gap_channel(prepared, ch_idx, ch_name, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": ch_name,
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })
    summary = _build_lane_summary(rows)
    summary.to_csv(out_dir / "expand_bridge_dynamic_gap_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Variant 3 – expand_bridge_confidence_weighted
# ---------------------------------------------------------------------------

def _run_confidence_weighted_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """Two-tier expansion and bridging based on candidate confidence.

    Strong candidates (peak > T_strong):
        - Aggressive expansion: T_low_strong = ep_med + EXPAND_CONF_K_LOW_STRONG * ep_mad
        - Normal bridge: EXPAND_CONF_BRIDGE_STRONG_MS

    Weak candidates (peak <= T_strong):
        - Conservative expansion: T_low_weak = ep_med + EXPAND_CONF_K_LOW_WEAK * ep_mad
        - Short bridge: EXPAND_CONF_BRIDGE_WEAK_MS

    After per-candidate expansion, the two populations are merged separately,
    then combined and deduplicated by overlap.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    bridge_strong_frames = int(EXPAND_CONF_BRIDGE_STRONG_MS * sfreq / 1000.0)
    bridge_weak_frames = int(EXPAND_CONF_BRIDGE_WEAK_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_strong = T_high + EXPAND_CONF_STRONG_K * ep_mad
        T_low_strong = ep_med + EXPAND_CONF_K_LOW_STRONG * ep_mad
        T_low_weak = ep_med + EXPAND_CONF_K_LOW_WEAK * ep_mad

        cands = _scan_threshold_crossings(signal, T_high, min_frames)

        strong_ivs: list[tuple[int, int]] = []
        weak_ivs: list[tuple[int, int]] = []

        for s, e in cands:
            peak = float(np.max(signal[s:e])) if e > s else T_high
            if peak >= T_strong:
                s2, e2 = _expand_interval(signal, s, e, T_low_strong)
                strong_ivs.append((s2, e2))
            else:
                s2, e2 = _expand_interval(signal, s, e, T_low_weak)
                weak_ivs.append((s2, e2))

        # Merge each group with its appropriate bridge gap
        merged_strong = _merge_intervals(strong_ivs, bridge_strong_frames)
        merged_weak = _merge_intervals(weak_ivs, bridge_weak_frames)

        # Combine and merge remaining overlaps with the weak bridge gap
        all_ivs = merged_strong + merged_weak
        final = _merge_intervals(all_ivs, gap_frames=0)  # only overlaps, no additional gap

        for s, e in final:
            if (e - s) > min_frames:
                cand_rows.append({
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": s / sfreq,
                    "blink_duration": (e - s) / sfreq,
                })

    return _make_candidates_df(cand_rows, channel_name)


def run_expand_bridge_confidence_weighted(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
    )
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        candidates = _run_confidence_weighted_channel(prepared, ch_idx, ch_name, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": ch_name,
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })
    summary = _build_lane_summary(rows)
    summary.to_csv(out_dir / "expand_bridge_confidence_weighted_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Variant 4 – expand_bridge_sw_onset  (Tier 1)
# ---------------------------------------------------------------------------

def _rolling_mad_threshold(signal: np.ndarray, win_frames: int, k: float, gfloor: float) -> np.ndarray:
    """Vectorised per-sample rolling median + k * SCALING * rolling_MAD threshold.

    Uses pandas rolling (C-backed) for speed. The rolling MAD is computed as
    median(|x - rolling_median|) inside the same window.
    """
    sig_s = pd.Series(signal)
    roll_med = sig_s.rolling(window=win_frames, center=True, min_periods=1).median()
    abs_dev = (sig_s - roll_med).abs()
    roll_mad = abs_dev.rolling(window=win_frames, center=True, min_periods=1).median()
    T = roll_med.values + k * SCALING_FACTOR * roll_mad.values
    return np.maximum(T, gfloor)


def _run_sw_onset_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """Sliding-window onset detection + expand+bridge boundary recovery.

    Step 1 (onset): per-sample rolling threshold T_sw[i] (2-second window).
        Detects crossings above the local threshold → cleaner onset starts.
    Step 2 (boundary): expand each onset candidate backward/forward to T_low
        (same as base expand_bridge: ep_med + 0.5 * ep_mad) → recovers duration.
    Step 3 (bridge): merge nearby gaps within BRIDGE_GAP_MS.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    win_frames = int(EXPAND_SW_WINDOW_S * sfreq)
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

        # --- Step 1: vectorised rolling threshold for onset detection ---
        T_sw = _rolling_mad_threshold(signal, win_frames, K_DEFAULT, gfloor)

        above_sw = signal > T_sw
        if not above_sw.any():
            continue
        padded = np.concatenate([[False], above_sw, [False]])
        diff = np.diff(padded.astype(np.int8))
        ons = np.where(diff == 1)[0]
        offs = np.where(diff == -1)[0]
        cands_sw = [
            (int(o), int(f))
            for o, f in zip(ons, offs)
            if (f - o) > min_frames
        ]

        if not cands_sw:
            continue

        # --- Step 2: expand each candidate to T_low ---
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_low = ep_med + EXPAND_LOW_K * ep_mad

        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands_sw]

        # --- Step 3: bridge gaps ---
        merged = _merge_intervals(expanded, bridge_frames)

        for s, e in merged:
            if (e - s) > min_frames:
                cand_rows.append({
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": s / sfreq,
                    "blink_duration": (e - s) / sfreq,
                })

    return _make_candidates_df(cand_rows, channel_name)


def run_expand_bridge_sw_onset(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
    )
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        candidates = _run_sw_onset_channel(prepared, ch_idx, ch_name, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": ch_name,
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })
    summary = _build_lane_summary(rows)
    summary.to_csv(out_dir / "expand_bridge_sw_onset_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Variant 5 – expand_bridge_adaptive_k
# ---------------------------------------------------------------------------

def _run_adaptive_k_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """Adaptive-k for T_high threshold, then normal expand+bridge.

    k_adj = clip(k_default * global_mad / quiet_epoch_mad, K_MIN, K_MAX)
    T_high = max(ep_med + k_adj * ep_mad, global_floor_adj)
    T_low = ep_med + EXPAND_LOW_K * ep_mad  (same as base)

    Cleaner candidate pool from adaptive_k + boundary recovery from expand+bridge.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_mean = float(np.mean(concat))

    # Compute per-epoch MADs to find the quiet-epoch baseline
    ep_mads = [
        SCALING_FACTOR * float(compute_mad(prepared.data[ei, ch_idx, :].astype(float)))
        for ei in valid_epoch_indices
    ]
    quiet_mad = float(np.percentile(ep_mads, 25)) if ep_mads else global_mad

    # Adaptive k: noisier recordings → higher k
    ratio = global_mad / (quiet_mad + 1e-12)
    k_adj = float(np.clip(K_DEFAULT * ratio, EXPAND_ADAPTIVE_K_MIN, EXPAND_ADAPTIVE_K_MAX))
    global_floor_adj = global_mean + k_adj * global_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + k_adj * ep_mad, global_floor_adj)
        T_low = ep_med + EXPAND_LOW_K * ep_mad

        cands = _scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]
        merged = _merge_intervals(expanded, bridge_frames)

        for s, e in merged:
            if (e - s) > min_frames:
                cand_rows.append({
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": s / sfreq,
                    "blink_duration": (e - s) / sfreq,
                })

    return _make_candidates_df(cand_rows, channel_name)


def run_expand_bridge_adaptive_k(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
    )
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        candidates = _run_adaptive_k_channel(prepared, ch_idx, ch_name, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": ch_name,
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })
    summary = _build_lane_summary(rows)
    summary.to_csv(out_dir / "expand_bridge_adaptive_k_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Variant 6 – expand_bridge_soft_gate  (Tier 1)
# ---------------------------------------------------------------------------

def _run_soft_gate_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """Self-trained amplitude gate after expand+bridge.

    Pass 1 (conservative, k=SOFT_GATE_K_CONSERVATIVE=2.0):
        Standard threshold crossing only → collect confident peak amplitudes.

    Learn gate:
        If >= SOFT_GATE_MIN_CONFIDENT events: gate = peak_median - 2 * peak_scaled_mad.
        Else: gate = global_floor (no learning).

    Pass 2 (full expand+bridge, k=K_DEFAULT=1.5):
        Detect, expand, bridge as normal.
        Filter: keep candidates whose peak amplitude >= gate.

    This removes the weak-FP tail without touching the core boundary recovery.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(BRIDGE_GAP_MS * sfreq / 1000.0)
    gfloor = _global_floor(prepared, ch_idx, valid_epoch_indices)

    # --- Pass 1: conservative scan to collect confident peak amplitudes ---
    confident_peaks: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_cons = max(ep_med + SOFT_GATE_K_CONSERVATIVE * ep_mad, gfloor)
        for s, e in _scan_threshold_crossings(signal, T_cons, min_frames):
            if e > s:
                confident_peaks.append(float(np.max(signal[s:e])))

    # --- Learn amplitude gate ---
    if len(confident_peaks) >= SOFT_GATE_MIN_CONFIDENT:
        peaks_arr = np.array(confident_peaks)
        peak_med = float(np.median(peaks_arr))
        peak_scaled_mad = SCALING_FACTOR * float(compute_mad(peaks_arr))
        amp_gate = max(peak_med - 2.0 * peak_scaled_mad, gfloor)
    else:
        amp_gate = gfloor

    # --- Pass 2: full expand+bridge, filter by gate ---
    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_med = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_high = max(ep_med + K_DEFAULT * ep_mad, gfloor)
        T_low = ep_med + EXPAND_LOW_K * ep_mad

        cands = _scan_threshold_crossings(signal, T_high, min_frames)
        expanded = [_expand_interval(signal, s, e, T_low) for s, e in cands]
        merged = _merge_intervals(expanded, bridge_frames)

        for s, e in merged:
            if (e - s) > min_frames:
                peak_amp = float(np.max(signal[s:e])) if e > s else 0.0
                if peak_amp >= amp_gate:
                    cand_rows.append({
                        "epoch_index": epoch_idx,
                        "channel": channel_name,
                        "blink_onset": s / sfreq,
                        "blink_duration": (e - s) / sfreq,
                    })

    return _make_candidates_df(cand_rows, channel_name)


def run_expand_bridge_soft_gate(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
    )
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        candidates = _run_soft_gate_channel(prepared, ch_idx, ch_name, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": ch_name,
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })
    summary = _build_lane_summary(rows)
    summary.to_csv(out_dir / "expand_bridge_soft_gate_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Variant runner dispatch
# ---------------------------------------------------------------------------

RUNNER_MAP = {
    "expand_bridge_dynamic_low": run_expand_bridge_dynamic_low,
    "expand_bridge_dynamic_gap": run_expand_bridge_dynamic_gap,
    "expand_bridge_confidence_weighted": run_expand_bridge_confidence_weighted,
    "expand_bridge_sw_onset": run_expand_bridge_sw_onset,
    "expand_bridge_adaptive_k": run_expand_bridge_adaptive_k,
    "expand_bridge_soft_gate": run_expand_bridge_soft_gate,
}


# ---------------------------------------------------------------------------
# Per-pair processing
# ---------------------------------------------------------------------------

def _empty_result(subject: str, segment: str, strategy: str) -> dict:
    return {
        "strategy": strategy,
        "subject": subject,
        "segment": segment,
        "elapsed_s": float("nan"),
        "n_epochs": 0,
        "n_annotations": 0,
        "n_lanes": 0,
        "best_channel": "",
        "best_tp": 0,
        "best_fp": 0,
        "best_fn": 0,
        "best_precision": float("nan"),
        "best_recall": float("nan"),
        "best_f1": float("nan"),
        "error": "",
    }


def _fill_best(result: dict, summary: pd.DataFrame) -> None:
    if summary.empty:
        return
    best = summary.iloc[0]
    result.update({
        "best_channel": str(best["channel"]),
        "best_tp": int(best["tp"]),
        "best_fp": int(best["fp"]),
        "best_fn": int(best["fn"]),
        "best_precision": float(best["precision"]),
        "best_recall": float(best["recall"]),
        "best_f1": float(best["f1"]),
    })


def process_pair(
    subject: str,
    segment: str,
    fif_path: Path,
    annotation_path: Path,
    brain_channels: list[str],
) -> list[dict]:
    out_dir = OUTPUT_ROOT / subject / segment
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load data once for all variants
    try:
        raw = load_raw_with_brain_channels(fif_path, brain_channels)
        epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
        reference = load_annotation_as_reference(annotation_path, epoch_duration=EPOCH_DURATION_S)
        valid_epoch_indices = get_valid_epoch_indices(epochs)
        reference.to_csv(out_dir / "reference_annotation.csv", index=False)
        n_epochs = len(epochs)
        n_annotations = len(reference)
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        print(f"    [ERROR] loading data for {subject}/{segment}\n{tb}")
        results = []
        for variant in VARIANT_NAMES:
            r = _empty_result(subject, segment, variant)
            r["error"] = tb
            results.append(r)
        (out_dir / "load_error.txt").write_text(tb)
        return results

    results: list[dict] = []
    for variant in VARIANT_NAMES:
        result = _empty_result(subject, segment, variant)
        result["n_epochs"] = n_epochs
        result["n_annotations"] = n_annotations

        started = perf_counter()
        try:
            summary, _ = RUNNER_MAP[variant](epochs, reference, valid_epoch_indices, out_dir)
            result["n_lanes"] = len(summary)
            _fill_best(result, summary)
        except Exception:  # noqa: BLE001
            tb = traceback.format_exc()
            result["error"] = tb
            (out_dir / f"{variant}_error.txt").write_text(tb)
            print(f"    [ERROR] {variant} on {subject}/{segment}\n{tb}")

        result["elapsed_s"] = perf_counter() - started
        results.append(result)

        if not result["error"]:
            print(
                f"      [{variant}] {result['elapsed_s']:.1f}s  "
                f"lanes={result['n_lanes']}  best_ch={result['best_channel']}  "
                f"TP={result['best_tp']}  FP={result['best_fp']}  FN={result['best_fn']}  "
                f"P={result['best_precision']:.3f}  R={result['best_recall']:.3f}  "
                f"F1={result['best_f1']:.3f}"
            )

    return results


# ---------------------------------------------------------------------------
# Aggregate helper
# ---------------------------------------------------------------------------

def compute_aggregate(df: pd.DataFrame, strategy: str) -> dict:
    sub = df[(df["strategy"] == strategy) & (df["error"].isna() | (df["error"] == ""))]
    total = len(df[df["strategy"] == strategy])
    n_ok = len(sub)
    n_fail = total - n_ok

    if sub.empty:
        return {
            "strategy": strategy,
            "n_pairs_total": total,
            "n_pairs_successful": n_ok,
            "n_pairs_failed": n_fail,
            "total_tp": 0, "total_fp": 0, "total_fn": 0,
            "micro_precision": float("nan"),
            "micro_recall": float("nan"),
            "micro_f1": float("nan"),
            "macro_precision": float("nan"),
            "macro_recall": float("nan"),
            "macro_f1": float("nan"),
        }

    total_tp = int(sub["best_tp"].sum())
    total_fp = int(sub["best_fp"].sum())
    total_fn = int(sub["best_fn"].sum())

    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else float("nan")
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else float("nan")
    if isinstance(micro_p, float) and isinstance(micro_r, float) and (micro_p + micro_r) > 0:
        micro_f1 = 2.0 * micro_p * micro_r / (micro_p + micro_r)
    else:
        micro_f1 = float("nan")

    return {
        "strategy": strategy,
        "n_pairs_total": total,
        "n_pairs_successful": n_ok,
        "n_pairs_failed": n_fail,
        "total_tp": total_tp, "total_fp": total_fp, "total_fn": total_fn,
        "micro_precision": micro_p,
        "micro_recall": micro_r,
        "micro_f1": micro_f1,
        "macro_precision": float(sub["best_precision"].mean()),
        "macro_recall": float(sub["best_recall"].mean()),
        "macro_f1": float(sub["best_f1"].mean()),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _process_pair_task(args: tuple) -> list[dict]:
    i, n_total, subject, segment, fif_path, annotation_path, brain_channels = args
    print(f"[{i}/{n_total}] {subject} / {segment}")
    results = process_pair(
        subject=subject,
        segment=segment,
        fif_path=fif_path,
        annotation_path=annotation_path,
        brain_channels=brain_channels,
    )
    print()
    return results


def main() -> None:
    print("=" * 70)
    print("Tutorial 27 – Strategy E Expand-Bridge Derivatives")
    print("=" * 70)
    print(f"Variants   : {VARIANT_NAMES}")
    print(f"DEBUG      : {DEBUG}")
    print(f"N_WORKERS  : {N_WORKERS if not DEBUG else 1} (debug forces single-thread)")
    print()

    pairs = find_pairs()
    if not pairs:
        print("No matched (fif, csv) pairs found.")
        return

    if DEBUG:
        pairs = pairs[:1]
        print(f"[DEBUG] Running only first pair: {pairs[0]['subject']} / {pairs[0]['segment']}\n")
    else:
        print(f"Found {len(pairs)} pair(s). Output root: {OUTPUT_ROOT}\n")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    print(f"Brain-region channels ({len(brain_channels)}): {brain_channels}\n")

    tasks = [
        (i, len(pairs), pair["subject"], pair["segment"],
         Path(pair["fif"]), Path(pair["csv"]), brain_channels)
        for i, pair in enumerate(pairs, 1)
    ]

    all_results: list[dict] = []
    if DEBUG or N_WORKERS == 1:
        for task in tasks:
            all_results.extend(_process_pair_task(task))
    else:
        with ThreadPoolExecutor(max_workers=N_WORKERS) as executor:
            futures = {executor.submit(_process_pair_task, task): task for task in tasks}
            for future in as_completed(futures):
                all_results.extend(future.result())

    # --- Save per-pair results ---
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    per_pair_df = pd.DataFrame(all_results)
    per_pair_csv = OUTPUT_ROOT / "expand_bridge_derivatives_all_results.csv"
    per_pair_df.to_csv(per_pair_csv, index=False)
    print(f"Per-pair results saved -> {per_pair_csv}\n")

    # --- Aggregate per variant ---
    agg_rows = [compute_aggregate(per_pair_df, v) for v in VARIANT_NAMES]
    agg_df = pd.DataFrame(agg_rows)
    agg_csv = OUTPUT_ROOT / "expand_bridge_derivatives_aggregate.csv"
    agg_df.to_csv(agg_csv, index=False)
    print(f"Aggregate saved -> {agg_csv}\n")

    # --- Print summary ---
    print("=" * 70)
    print("AGGREGATE COMPARISON  (best lane per pair)")
    print("=" * 70)
    display_cols = [
        "strategy", "n_pairs_successful", "n_pairs_failed",
        "total_tp", "total_fp", "total_fn",
        "micro_precision", "micro_recall", "micro_f1",
        "macro_precision", "macro_recall", "macro_f1",
    ]
    disp = agg_df[display_cols].copy()
    for col in ("micro_precision", "micro_recall", "micro_f1",
                "macro_precision", "macro_recall", "macro_f1"):
        disp[col] = disp[col].map(lambda x: f"{x:.4f}" if x == x else "nan")  # noqa: PLR0124
    print(disp.to_string(index=False))

    # --- Per-pair F1 pivot ---
    print("\n--- Per-pair F1 comparison ---")
    ok_df = per_pair_df[per_pair_df["error"].isna() | (per_pair_df["error"] == "")]
    if not ok_df.empty:
        pivot = ok_df.pivot_table(
            index=["subject", "segment"],
            columns="strategy",
            values="best_f1",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None
        strat_cols = [c for c in VARIANT_NAMES if c in pivot.columns]
        if strat_cols:
            pivot["winner"] = pivot[strat_cols].idxmax(axis=1)
        for col in strat_cols:
            pivot[col] = pivot[col].map(lambda x: f"{x:.4f}" if x == x else "nan")  # noqa: PLR0124
        print(pivot.to_string(index=False))
        pivot_csv = OUTPUT_ROOT / "expand_bridge_derivatives_f1_pivot.csv"
        pivot.to_csv(pivot_csv, index=False)
        print(f"\nF1 pivot saved -> {pivot_csv}")

    print()
    print("Baseline ground_truth (strategy_e_expand_bridge):")
    print("  micro F1 = 0.6592  |  recall = 0.7460  |  precision = 0.5905")
    print("  TP = 30,901  FP = 21,428  FN = 10,523  |  failures = 0")


if __name__ == "__main__":
    main()
