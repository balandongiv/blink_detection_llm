"""
Tutorial 21 – Strategy A / B / C / D comparison batch runner.

For each (fif, csv) pair every strategy is run and best-lane TP/FP/FN are
collected.  Outputs:

    experiment_output/comparison_per_pair.csv
        One row per (subject, segment, strategy) with best-lane metrics.

    experiment_output/comparison_aggregate.csv
        One row per strategy: pooled micro-averages and macro-averages.

Per-strategy artefact files are written alongside the existing naming
convention used by tutorials 17-22.
"""

from __future__ import annotations

import importlib.util
import json
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

# Strategy A
from pyblinker.blinker.get_blink_positions import get_blink_position
from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_a.epoch_channel_processor import (
    map_concatenated_blinks_to_epochs,
)
from pyblinker.epoch_detection_strategy_a.epoch_validation import match_blink_tables

# Strategy B
from pyblinker.epoch_detection_strategy_b import (
    BlinkDetectorEpochStrategyB,
    find_eog_candidate_regions,
    summarize_candidate_regions,
)

# Strategy C
from pyblinker.epoch_detection_strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    epoch_detection_strategy_c_autoreject,
)

# Strategy D
from autoreject import compute_thresholds  # noqa: E402
from mne.preprocessing import peak_finder  # noqa: E402
from pyblinker.epoch_detection_strategy_c import STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE

# Strategy E
from pyblinker.blinker.default_setting import SCALING_FACTOR as _MAD_SCALING_FACTOR  # noqa: E402
from pyblinker.fitutils import mad as _compute_mad  # noqa: E402

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
OUTPUT_ROOT = REPO_ROOT / "experiment_output"

# Strategy B / C shared filter settings
FILTER_LOW = 1.0
FILTER_HIGH = 20.0

# Strategy B MNE params
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None

# Strategy C backbone placeholder
DISABLE_BACKBONE_CHANNELS = ("__NO_BACKBONE__",)

# Strategy D params
STRATEGY_D_HALF_WINDOW_S = 0.10
STRATEGY_D_AUTOREJECT_RANDOM_STATE = 42
STRATEGY_D_RESCALE_THRESHOLD = True

# Tutorial-27 expand_bridge derivatives only (set to the new exploratory variants).
# To re-run all previous strategies, restore the commented-out block below.
STRATEGIES = [
    "expand_bridge_dynamic_low",
    "expand_bridge_dynamic_gap",
    "expand_bridge_confidence_weighted",
    "expand_bridge_sw_onset",
    "expand_bridge_adaptive_k",
    "expand_bridge_soft_gate",
]

# # Full strategy list (all previous iterations):
# STRATEGIES = [
#     "strategy_e_sliding_window",
#     "strategy_e_or_fusion",
#     "strategy_e_vote_2of3",
#     "strategy_e_expand_bridge",
#     "strategy_e_duration_band",
#     "strategy_e_slope_guard",
#     "strategy_e_abs_polarity",
#     "strategy_e_adaptive_k",
#     "strategy_e_quantile_thr",
#     "strategy_e_refractory",
#     "strategy_e8_changepoint",
#     "strategy_e11_lane_route",
#     "strategy_e13_self_train",
# ]

# Number of worker threads for pair-level parallelism.
# Set to 1 for single-threaded (debug); increase for batch runs.
N_WORKERS = 4

# Strategy E per-epoch MAD threshold params (BLINKER defaults) – shared by all E variants
STRATEGY_E_STD_THRESHOLD = 1.5    # k in: threshold = mean + k * SCALING_FACTOR * MAD(epoch)
STRATEGY_E_MIN_EVENT_LEN_S = 0.05  # minimum blink duration in seconds

# E2 floor: subject-level noise floor multiplier
STRATEGY_E2_FLOOR_K = 0.5

# E3 hysteresis thresholds
STRATEGY_E3_K_HIGH = 1.5
STRATEGY_E3_K_LOW = 1.0

# E4 multiscale: k values to union and merge gap
STRATEGY_E4_K_VALUES = [1.0, 1.2, 1.5]
STRATEGY_E4_GAP_MS = 80.0

# E6 soft-shrinkage: alpha = clip(epoch_MAD / global_MAD, MIN, MAX)
STRATEGY_E6_ALPHA_MIN = 0.2
STRATEGY_E6_ALPHA_MAX = 0.9

# E7 background refit: permissive first-pass k and minimum background sample count
STRATEGY_E7_K_PASS1 = 1.0
STRATEGY_E7_MIN_BG_SAMPLES = 20

# E10 / E6+E10 cross-epoch triangular smoothing weights [prev, current, next]
STRATEGY_E10_SMOOTH_WEIGHTS = (0.25, 0.50, 0.25)

# E12 amplitude percentile filter: per-channel bottom-X% candidates removed
STRATEGY_E12_AMP_PERCENTILE = 15   # remove bottom 15% of detections by peak amplitude
STRATEGY_E12_MIN_CANDS_TO_FILTER = 10  # skip filter if too few candidates

# --- Remaining variant constants (tutorial 26 strategies) ---

# e_sliding_window: rolling window size for intra-epoch rolling threshold
STRATEGY_E_SLIDING_WINDOW_S = 2.0

# e_vote_2of3: voting parameters
STRATEGY_E_VOTE_REQUIRED = 2          # channels that must agree
STRATEGY_E_VOTE_TOLERANCE_S = 0.100   # ±100ms agreement window

# e_expand_bridge: boundary expansion and gap bridging
STRATEGY_E_EXPAND_LOW_K = 0.5         # lower threshold for boundary expansion
STRATEGY_E_BRIDGE_GAP_MS = 80.0       # bridge gaps smaller than this

# e_duration_band: acceptable blink duration range
STRATEGY_E_DURATION_MIN_MS = 50.0
STRATEGY_E_DURATION_MAX_MS = 500.0

# e_refractory: minimum inter-onset interval
STRATEGY_E_REFRACTORY_MS = 150.0

# e_adaptive_k: k clipped to [MIN, MAX] based on noise ratio
STRATEGY_E_ADAPTIVE_K_MIN = 1.0
STRATEGY_E_ADAPTIVE_K_MAX = 2.5

# e_quantile_thr: percentile threshold
STRATEGY_E_QUANTILE_PCT = 93.0

# e8_changepoint: piecewise block duration
STRATEGY_E8_BLOCK_S = 10.0

# e11_lane_route: cluster tolerance for lane routing
STRATEGY_E11_CLUSTER_TOL_MS = 100.0

# e13_self_train: conservative/permissive k and minimum confident detections
STRATEGY_E13_K_CONSERVATIVE = 2.0
STRATEGY_E13_K_PERMISSIVE = 1.2
STRATEGY_E13_MIN_CONFIDENT = 5

# --- Tutorial-27 expand_bridge derivatives ---

# expand_bridge_dynamic_low: adaptive k_low scales with epoch noise level
EXPAND_DYN_LOW_K_BASE = 0.5
EXPAND_DYN_LOW_K_MIN = 0.2
EXPAND_DYN_LOW_K_MAX = 1.0

# expand_bridge_dynamic_gap: strength-aware bridge gap
EXPAND_DYN_GAP_STRONG_MS = 100.0
EXPAND_DYN_GAP_WEAK_MS = 40.0
EXPAND_DYN_GAP_STRONG_K = 0.5    # peak > T_high + STRONG_K * ep_mad → strong

# expand_bridge_confidence_weighted: two-tier expansion
EXPAND_CONF_K_LOW_STRONG = 0.3
EXPAND_CONF_K_LOW_WEAK = 0.8
EXPAND_CONF_BRIDGE_STRONG_MS = 80.0
EXPAND_CONF_BRIDGE_WEAK_MS = 40.0
EXPAND_CONF_STRONG_K = 0.5

# expand_bridge_sw_onset: sliding window for onset detection
EXPAND_SW_WINDOW_S_27 = 2.0

# expand_bridge_adaptive_k: adaptive k bounds
EXPAND_ADAPTIVE_K_MIN_27 = 1.0
EXPAND_ADAPTIVE_K_MAX_27 = 2.5

# expand_bridge_soft_gate: conservative pass for learning amplitude gate
EXPAND_SOFT_GATE_K_CONSERVATIVE = 2.0
EXPAND_SOFT_GATE_MIN_CONFIDENT = 5


# ---------------------------------------------------------------------------
# Shared data helpers
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
        rows.append(
            {
                "epoch_index": epoch_index,
                "blink_onset": onset_abs - epoch_index * epoch_duration,
                "blink_duration": duration,
            }
        )
    return pd.DataFrame(rows, columns=["epoch_index", "blink_onset", "blink_duration"])


def build_lane_summary_from_rows(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["f1", "tp", "fp", "channel"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)


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
    result.update(
        {
            "best_channel": str(best["channel"]),
            "best_tp": int(best["tp"]),
            "best_fp": int(best["fp"]),
            "best_fn": int(best["fn"]),
            "best_precision": float(best["precision"]),
            "best_recall": float(best["recall"]),
            "best_f1": float(best["f1"]),
        }
    )


# ---------------------------------------------------------------------------
# Strategy A runner
# ---------------------------------------------------------------------------

def run_strategy_a(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )

    params = BlinkDetector._build_detector_params(None, {})
    params["sfreq"] = float(prepared.sfreq)

    epoch_boundaries = [
        (
            idx * prepared.epoch_length_samples,
            (idx + 1) * prepared.epoch_length_samples,
        )
        for idx in range(len(valid_epoch_indices))
    ]

    rows: list[dict] = []
    best_candidates: pd.DataFrame | None = None
    best_channel_name: str = ""

    for channel_index, channel_name in enumerate(prepared.channel_names):
        concatenated_signal = prepared.data[valid_epoch_indices, channel_index, :].reshape(-1)

        df_positions = get_blink_position(
            params,
            blink_component=concatenated_signal,
            ch=channel_name,
            progress_bar=False,
        )
        mapped = map_concatenated_blinks_to_epochs(
            df_positions,
            channel=channel_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )
        metrics = match_blink_tables(mapped, reference, n_epochs=len(epochs))
        rows.append(
            {
                "channel": channel_name,
                "raw_candidate_count": int(len(df_positions)),
                "mapped_candidate_count": int(len(mapped)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_a_step1_lane_summary.csv", index=False)

    if not summary.empty:
        best_channel_name = str(summary.iloc[0]["channel"])
        # re-run to get mapped candidates for best channel only (already done above)

    return summary, {}


# ---------------------------------------------------------------------------
# Strategy B runner
# ---------------------------------------------------------------------------

def run_strategy_b(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    detector = BlinkDetectorEpochStrategyB(
        epochs,
        visualize=False,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
        n_jobs=1,
        use_multiprocessing=False,
        mne_half_window_s=MNE_HALF_WINDOW_S,
        mne_l_freq=MNE_LOW_FREQ,
        mne_h_freq=MNE_HIGH_FREQ,
        mne_thresh=MNE_THRESH,
    )
    prepared = detector.prepare_epoch_data()

    rows: list[dict] = []
    for channel_index, channel_name in enumerate(prepared.channel_names):
        valid_epoch_data = prepared.data[valid_epoch_indices, channel_index, :]
        concatenated_signal = np.asarray(valid_epoch_data).reshape(-1)

        df_positions = find_eog_candidate_regions(
            concatenated_signal,
            channel=channel_name,
            sfreq=float(prepared.sfreq),
            half_window_s=MNE_HALF_WINDOW_S,
            l_freq=MNE_LOW_FREQ,
            h_freq=MNE_HIGH_FREQ,
            thresh=MNE_THRESH,
        )
        mapped = summarize_candidate_regions(
            df_positions,
            epoch_length_samples=prepared.epoch_length_samples,
            sfreq=float(prepared.sfreq),
            epoch_indices=valid_epoch_indices,
        )
        metrics = match_blink_tables(mapped, reference, n_epochs=len(epochs))
        rows.append(
            {
                "channel": channel_name,
                "raw_candidate_count": int(len(df_positions)),
                "mapped_candidate_count": int(len(mapped)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_b_step1_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy C runner
# ---------------------------------------------------------------------------

def run_strategy_c(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=1.0,
        filter_high=20.0,
        resample_rate=None,
        n_jobs=1,
        use_multiprocessing=False,
        stage1_channels=DISABLE_BACKBONE_CHANNELS,
        stage1_threshold_scope="per_channel",
        stage1_rescale_threshold=True,
        autoreject_random_state=42,
        autoreject_method=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        autoreject_augment=False,
    )
    prepared = detector.prepare_epoch_data()
    stage1 = detector.run_stage1_candidate_scan(
        prepared=prepared,
        valid_epoch_indices=valid_epoch_indices,
    )

    rows: list[dict] = []
    for detection in stage1.detections:
        metrics = match_blink_tables(
            detection.mapped_candidates,
            reference,
            n_epochs=len(epochs),
        )
        rows.append(
            {
                "channel": detection.channel,
                "candidate_source": detection.candidate_source,
                "threshold": float(detection.threshold),
                "raw_candidate_count": int(len(detection.positions)),
                "mapped_candidate_count": int(len(detection.mapped_candidates)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "step1_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy D runner
# ---------------------------------------------------------------------------

def run_strategy_d(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )

    # Learn per-channel PTP thresholds with Bayesian optimisation
    valid_indices_arr = np.asarray(valid_epoch_indices, dtype=int)
    stage1_data = prepared.data[valid_indices_arr]
    info = mne.create_info(
        list(prepared.channel_names),
        sfreq=float(prepared.sfreq),
        ch_types=["eeg"] * len(prepared.channel_names),
    )
    stage1_epochs = mne.EpochsArray(stage1_data, info, verbose="ERROR")
    threshes = compute_thresholds(
        stage1_epochs,
        method=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        random_state=STRATEGY_D_AUTOREJECT_RANDOM_STATE,
        augment=False,
        verbose=False,
    )
    raw_thresholds = {ch: float(threshes[ch]) for ch in prepared.channel_names}
    scan_scale = STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE if STRATEGY_D_RESCALE_THRESHOLD else 1.0
    scan_thresholds = {ch: raw_thresholds[ch] * scan_scale for ch in raw_thresholds}

    epoch_length_samples = int(prepared.epoch_length_samples)
    half_win = max(1, int(round(STRATEGY_D_HALF_WINDOW_S * prepared.sfreq)))

    rows: list[dict] = []
    for ch_idx, channel in enumerate(prepared.channel_names):
        x0 = prepared.data[valid_indices_arr, ch_idx, :].reshape(-1).astype(float)
        scan_thresh = scan_thresholds[channel]

        temp = x0 - np.mean(x0)
        extrema = 1 if np.abs(np.max(temp)) >= np.abs(np.min(temp)) else -1

        peak_locs, _ = peak_finder(x0, thresh=scan_thresh, extrema=extrema, verbose=False)
        peak_locs = np.asarray(peak_locs, dtype=int)

        # Map peaks back to epoch-local candidates
        cand_rows: list[dict] = []
        for peak in peak_locs:
            offset = int(peak) // epoch_length_samples
            if offset < 0 or offset >= len(valid_epoch_indices):
                continue
            epoch_index = int(valid_epoch_indices[offset])
            local_peak = int(peak) % epoch_length_samples
            start = max(0, local_peak - half_win)
            end = min(epoch_length_samples - 1, local_peak + half_win)
            cand_rows.append(
                {
                    "epoch_index": epoch_index,
                    "channel": channel,
                    "blink_onset": start / float(prepared.sfreq),
                    "blink_duration": (end - start) / float(prepared.sfreq),
                    "peak_sample": local_peak,
                }
            )
        if cand_rows:
            mapped = pd.DataFrame(cand_rows).sort_values(
                ["epoch_index", "blink_onset"]
            ).reset_index(drop=True)
        else:
            mapped = pd.DataFrame(
                columns=["epoch_index", "channel", "blink_onset", "blink_duration", "peak_sample"]
            )

        metrics = match_blink_tables(mapped, reference, n_epochs=len(epochs))
        rows.append(
            {
                "channel": channel,
                "raw_candidate_count": int(len(peak_locs)),
                "mapped_candidate_count": int(len(mapped)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_d_step1_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E runner – per-epoch MAD-based threshold scanning
# ---------------------------------------------------------------------------

def _scan_epoch_mad_crossings_e(
    signal: np.ndarray,
    threshold: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Vectorised threshold-crossing scan for a single epoch (Strategy E)."""
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


def run_strategy_e(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Strategy E: per-epoch MAD-based threshold, threshold-crossing scan.

    Replaces autoreject's per-epoch PTP feature with the BLINKER MAD-based
    threshold computed independently for every epoch:
        threshold_e = mean(epoch_e) + k * 1.4826 * MAD(epoch_e)

    Each epoch is then scanned with its own threshold, adapting to local
    signal statistics (aimed at high recall / low FN).
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )

    sfreq = float(prepared.sfreq)
    min_blink_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        cand_rows: list[dict] = []

        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

            ep_mean = float(np.mean(signal))
            ep_robust_std = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            ep_threshold = ep_mean + STRATEGY_E_STD_THRESHOLD * ep_robust_std

            blinks = _scan_epoch_mad_crossings_e(signal, ep_threshold, min_blink_frames)
            for start, end in blinks:
                cand_rows.append(
                    {
                        "epoch_index": epoch_idx,
                        "channel": channel_name,
                        "blink_onset": start / sfreq,
                        "blink_duration": (end - start) / sfreq,
                    }
                )

        candidates = (
            pd.DataFrame(cand_rows)
            .sort_values(["epoch_index", "blink_onset"])
            .reset_index(drop=True)
            if cand_rows
            else pd.DataFrame(
                columns=["epoch_index", "channel", "blink_onset", "blink_duration"]
            )
        )
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append(
            {
                "channel": channel_name,
                "raw_candidate_count": int(len(candidates)),
                "mapped_candidate_count": int(len(candidates)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_step1_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Scanning helpers shared by E derivative runners
# ---------------------------------------------------------------------------

def _scan_threshold_crossings_e(
    signal: np.ndarray,
    threshold: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
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


def _scan_hysteresis_crossings_e(
    signal: np.ndarray,
    t_high: float,
    t_low: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    blinks: list[tuple[int, int]] = []
    in_event = False
    start = 0
    n = len(signal)
    for i in range(n):
        val = signal[i]
        if not in_event:
            if val > t_high:
                in_event = True
                start = i
        else:
            if val < t_low:
                if (i - start) > min_blink_frames:
                    blinks.append((start, i))
                in_event = False
    if in_event and (n - start) > min_blink_frames:
        blinks.append((start, n))
    return blinks


def _merge_intervals_e(
    intervals: list[tuple[int, int]],
    gap_frames: int,
) -> list[tuple[int, int]]:
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


def _make_cands_df(cand_rows: list[dict]) -> pd.DataFrame:
    if cand_rows:
        return (
            pd.DataFrame(cand_rows)
            .sort_values(["epoch_index", "blink_onset"])
            .reset_index(drop=True)
        )
    return pd.DataFrame(columns=["epoch_index", "channel", "blink_onset", "blink_duration"])


# ---------------------------------------------------------------------------
# Strategy E1 – median + k * MAD  (per epoch)
# ---------------------------------------------------------------------------

def run_strategy_e1_median(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E1: replace mean with median in per-epoch MAD threshold."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            threshold = ep_median + STRATEGY_E_STD_THRESHOLD * ep_mad
            for start, end in _scan_threshold_crossings_e(signal, threshold, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e1_median_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E2 – median + MAD with global noise-floor minimum
# ---------------------------------------------------------------------------

def run_strategy_e2_floor(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E2: median + k * MAD, clamped from below by a subject-level global floor."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        # Global floor: median + FLOOR_K * MAD over all valid epochs for this channel
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_med = float(np.median(concat))
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        global_floor = global_med + STRATEGY_E2_FLOOR_K * global_mad

        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            threshold = max(ep_median + STRATEGY_E_STD_THRESHOLD * ep_mad, global_floor)
            for start, end in _scan_threshold_crossings_e(signal, threshold, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e2_floor_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E3 – hysteresis thresholds (median-based, per epoch)
# ---------------------------------------------------------------------------

def run_strategy_e3_hysteresis(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E3: dual-threshold hysteresis per epoch.

    T_high = median + k_high * SCALING_FACTOR * MAD
    T_low  = median + k_low  * SCALING_FACTOR * MAD
    Event opens above T_high, closes below T_low.
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            t_high = ep_median + STRATEGY_E3_K_HIGH * ep_mad
            t_low = ep_median + STRATEGY_E3_K_LOW * ep_mad
            for start, end in _scan_hysteresis_crossings_e(signal, t_high, t_low, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e3_hysteresis_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E4 – multiscale union  (median + multiple k values, merge within gap)
# ---------------------------------------------------------------------------

def run_strategy_e4_multiscale(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E4: union of detections at k=1.0, 1.2, 1.5 (median-based), merged within gap_ms."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    gap_frames = int(round(STRATEGY_E4_GAP_MS * sfreq / 1000.0))

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))

            raw_candidates: list[tuple[int, int]] = []
            for k in STRATEGY_E4_K_VALUES:
                threshold = ep_median + k * ep_mad
                raw_candidates.extend(
                    _scan_threshold_crossings_e(signal, threshold, min_frames)
                )
            for start, end in _merge_intervals_e(raw_candidates, gap_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e4_multiscale_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E5 – median + MAD per epoch, floored by Strategy-A global threshold
# ---------------------------------------------------------------------------

def run_strategy_e5_global_floor(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E5: per-epoch median+MAD, with Strategy-A global mean+MAD as minimum floor.

    In quiet epochs (low per-epoch MAD) the threshold can collapse too low,
    admitting many false positives.  Using the global mean+MAD threshold
    (identical to Strategy A's computation) as a hard floor prevents this
    collapse while still allowing per-epoch adaptivity in noisy epochs.

    Expected effect: recall close to E1 (median), FP closer to Strategy A.
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        # Global floor: Strategy A's formula — mean + k * SCALING_FACTOR * MAD
        # computed on the concatenated valid epochs for this channel.
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mean = float(np.mean(concat))
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        global_floor = global_mean + STRATEGY_E_STD_THRESHOLD * global_mad

        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            ep_threshold = ep_median + STRATEGY_E_STD_THRESHOLD * ep_mad
            # Floor = global Strategy-A threshold — prevents quiet-epoch FP explosion
            threshold = max(ep_threshold, global_floor)
            for start, end in _scan_threshold_crossings_e(signal, threshold, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e5_global_floor_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E6 – Soft-Shrinkage Threshold
# ---------------------------------------------------------------------------

def run_strategy_e6_soft_shrink(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E6: soft interpolation between local per-epoch and global thresholds.

    T_local = median(epoch) + k * SCALING * MAD(epoch)
    T_global = mean(concat) + k * SCALING * MAD(concat)   [Strategy A formula]
    alpha = clip(epoch_scaled_MAD / global_scaled_MAD, ALPHA_MIN, ALPHA_MAX)
    T_e = alpha * T_local + (1 - alpha) * T_global

    Quieter epochs pull toward global; noisier epochs trust local adaptation.
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mean = float(np.mean(concat))
        global_scaled_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        T_global = global_mean + STRATEGY_E_STD_THRESHOLD * global_scaled_mad

        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_scaled_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_local = ep_median + STRATEGY_E_STD_THRESHOLD * ep_scaled_mad

            alpha = float(np.clip(
                ep_scaled_mad / (global_scaled_mad + 1e-12),
                STRATEGY_E6_ALPHA_MIN,
                STRATEGY_E6_ALPHA_MAX,
            ))
            threshold = alpha * T_local + (1.0 - alpha) * T_global

            for start, end in _scan_threshold_crossings_e(signal, threshold, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e6_soft_shrink_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E7 – Iterative Background Refit
# ---------------------------------------------------------------------------

def run_strategy_e7_bg_refit(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E7: two-pass iterative background refit per epoch.

    Pass 1 (permissive, k=E7_K_PASS1): detect candidate regions.
    Mask those regions.
    Recompute median + MAD on remaining background samples.
    Pass 2 (k=K_DEFAULT): scan with refit threshold (floored by global).
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mean = float(np.mean(concat))
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        global_floor = global_mean + STRATEGY_E_STD_THRESHOLD * global_mad

        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

            # Pass 1: permissive
            ep_median_p1 = float(np.median(signal))
            ep_mad_p1 = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_pass1 = ep_median_p1 + STRATEGY_E7_K_PASS1 * ep_mad_p1
            pass1_cands = _scan_threshold_crossings_e(signal, T_pass1, min_frames)

            # Mask candidate regions
            mask = np.ones(len(signal), dtype=bool)
            for start, end in pass1_cands:
                mask[start:end] = False
            background = signal[mask]

            # Recompute on background
            if len(background) >= STRATEGY_E7_MIN_BG_SAMPLES:
                bg_median = float(np.median(background))
                bg_mad = _MAD_SCALING_FACTOR * float(_compute_mad(background))
                T_refit = max(bg_median + STRATEGY_E_STD_THRESHOLD * bg_mad, global_floor)
            else:
                T_refit = global_floor

            # Pass 2: final detection
            for start, end in _scan_threshold_crossings_e(signal, T_refit, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })

        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e7_bg_refit_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E9 – Frontal-Dominance Average Virtual Channel
# ---------------------------------------------------------------------------

def run_strategy_e9_frontal_avg(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E9: average all frontal channels into one virtual signal, apply E5-style threshold.

    With brain_region.yaml channels (E3, E9, E22 – all frontal), this creates a
    single averaged signal that reduces single-channel noise while preserving the
    shared frontal blink component.  E5 global-floor thresholding is applied.
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    virtual_ch_name = "frontal_avg"

    # Average across all channels: (n_valid_epochs, n_samples)
    avg_epochs = np.mean(prepared.data[valid_epoch_indices, :, :], axis=1)

    # Global floor from concatenated averaged signal
    concat_avg = avg_epochs.reshape(-1).astype(float)
    global_mean = float(np.mean(concat_avg))
    global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat_avg))
    global_floor = global_mean + STRATEGY_E_STD_THRESHOLD * global_mad

    cand_rows: list[dict] = []
    for i, epoch_idx in enumerate(valid_epoch_indices):
        signal = avg_epochs[i].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
        threshold = max(ep_median + STRATEGY_E_STD_THRESHOLD * ep_mad, global_floor)

        for start, end in _scan_threshold_crossings_e(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx, "channel": virtual_ch_name,
                "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
            })

    candidates = _make_cands_df(cand_rows)
    metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
    rows = [{
        "channel": virtual_ch_name,
        "raw_candidate_count": int(len(candidates)),
        "mapped_candidate_count": int(len(candidates)),
        "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
        "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
        "recall": float(metrics.recall), "f1": float(metrics.f1),
    }]

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e9_frontal_avg_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E10 – Cross-Epoch Threshold Regularisation
# ---------------------------------------------------------------------------

def run_strategy_e10_epoch_smooth(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E10: triangular smoothing of per-epoch median+MAD thresholds across epochs.

    T_raw[e] = median(epoch_e) + k * SCALING * MAD(epoch_e)
    T'[e] = 0.25*T_raw[e-1] + 0.5*T_raw[e] + 0.25*T_raw[e+1]
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    w_prev, w_curr, w_next = STRATEGY_E10_SMOOTH_WEIGHTS

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        # Compute raw per-epoch thresholds
        raw_t: list[float] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            raw_t.append(ep_median + STRATEGY_E_STD_THRESHOLD * ep_mad)

        # Triangular smoothing with edge clamping
        n = len(raw_t)
        smoothed: list[float] = [
            w_prev * raw_t[max(0, i - 1)] + w_curr * raw_t[i] + w_next * raw_t[min(n - 1, i + 1)]
            for i in range(n)
        ]

        cand_rows: list[dict] = []
        for i, epoch_idx in enumerate(valid_epoch_indices):
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            threshold = smoothed[i]
            for start, end in _scan_threshold_crossings_e(signal, threshold, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })

        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e10_epoch_smooth_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E6+E10 – Soft Shrinkage + Cross-Epoch Smoothing Combined
# ---------------------------------------------------------------------------

def run_strategy_e6_e10_combined(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E6+E10: compute E6 soft-shrinkage thresholds then smooth across epochs.

    Step 1: T_e6[e] = alpha_e * T_local[e] + (1-alpha_e) * T_global
    Step 2: T_smooth[e] = triangular average of T_e6[e-1], T_e6[e], T_e6[e+1]
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    w_prev, w_curr, w_next = STRATEGY_E10_SMOOTH_WEIGHTS

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mean = float(np.mean(concat))
        global_scaled_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        T_global = global_mean + STRATEGY_E_STD_THRESHOLD * global_scaled_mad

        # Step 1: E6 thresholds
        e6_t: list[float] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_scaled_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_local = ep_median + STRATEGY_E_STD_THRESHOLD * ep_scaled_mad
            alpha = float(np.clip(
                ep_scaled_mad / (global_scaled_mad + 1e-12),
                STRATEGY_E6_ALPHA_MIN,
                STRATEGY_E6_ALPHA_MAX,
            ))
            e6_t.append(alpha * T_local + (1.0 - alpha) * T_global)

        # Step 2: triangular smoothing
        n = len(e6_t)
        smoothed: list[float] = [
            w_prev * e6_t[max(0, i - 1)] + w_curr * e6_t[i] + w_next * e6_t[min(n - 1, i + 1)]
            for i in range(n)
        ]

        cand_rows: list[dict] = []
        for i, epoch_idx in enumerate(valid_epoch_indices):
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            threshold = smoothed[i]
            for start, end in _scan_threshold_crossings_e(signal, threshold, min_frames):
                cand_rows.append({
                    "epoch_index": epoch_idx, "channel": channel_name,
                    "blink_onset": start / sfreq, "blink_duration": (end - start) / sfreq,
                })

        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e6_e10_combined_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Strategy E12 – E7 Background Refit + Amplitude Percentile Filter
# ---------------------------------------------------------------------------

def run_strategy_e12_amp_filter(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E12: E7 background refit + per-channel bottom-percentile amplitude pruning.

    Step 1: Run E7 background refit to generate high-recall candidate set.
    Step 2: For each channel, compute peak amplitude per candidate.
    Step 3: Remove candidates with peak amplitude in the bottom PERCENTILE %.
            These small-amplitude events are predominantly noise in quiet epochs
            where E7's threshold fell to the global floor.

    Expected outcome: E7 recall preserved for moderate/large blinks; FP reduced
    by pruning the low-amplitude tail that strategy_a would never detect.
    """
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq

    rows: list[dict] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        # --- E7: background refit threshold per epoch ---
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mean = float(np.mean(concat))
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        global_floor = global_mean + STRATEGY_E_STD_THRESHOLD * global_mad

        # Collect (epoch_idx, start, end, peak_amplitude) from E7
        raw_cands: list[tuple[int, int, int, float]] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

            ep_median_p1 = float(np.median(signal))
            ep_mad_p1 = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_pass1 = ep_median_p1 + STRATEGY_E7_K_PASS1 * ep_mad_p1
            pass1_cands = _scan_threshold_crossings_e(signal, T_pass1, min_frames)

            mask = np.ones(len(signal), dtype=bool)
            for s, e in pass1_cands:
                mask[s:e] = False
            background = signal[mask]

            if len(background) >= STRATEGY_E7_MIN_BG_SAMPLES:
                bg_median = float(np.median(background))
                bg_mad = _MAD_SCALING_FACTOR * float(_compute_mad(background))
                T_refit = max(bg_median + STRATEGY_E_STD_THRESHOLD * bg_mad, global_floor)
            else:
                T_refit = global_floor

            for s, e in _scan_threshold_crossings_e(signal, T_refit, min_frames):
                peak_amp = float(np.max(signal[s:e]))
                raw_cands.append((epoch_idx, s, e, peak_amp))

        # --- Amplitude percentile filter ---
        if len(raw_cands) >= STRATEGY_E12_MIN_CANDS_TO_FILTER:
            all_peaks = np.array([c[3] for c in raw_cands])
            amp_gate = float(np.percentile(all_peaks, STRATEGY_E12_AMP_PERCENTILE))
            filtered = [(ei, s, e) for ei, s, e, p in raw_cands if p >= amp_gate]
        else:
            filtered = [(ei, s, e) for ei, s, e, _ in raw_cands]

        cand_rows = [
            {"epoch_index": ei, "channel": channel_name,
             "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq}
            for ei, s, e in filtered
        ]
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({
            "channel": channel_name,
            "raw_candidate_count": int(len(candidates)),
            "mapped_candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
            "recall": float(metrics.recall), "f1": float(metrics.f1),
        })

    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e12_amp_filter_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Tutorial-26 remaining variant runners
# ---------------------------------------------------------------------------

def _e_global_floor_22(prepared, ch_idx: int, valid_epoch_indices: list[int]) -> float:
    """Global floor = global_mean + K * SCALING_FACTOR * MAD(concat)."""
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    return (float(np.mean(concat))
            + STRATEGY_E_STD_THRESHOLD * _MAD_SCALING_FACTOR * float(_compute_mad(concat)))


def run_strategy_e_sliding_window(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Rolling median+MAD threshold within each epoch (2-second window)."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    win_frames = int(STRATEGY_E_SLIDING_WINDOW_S * sfreq)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            n = len(signal)
            T = np.empty(n)
            for i in range(n):
                lo = max(0, i - win_frames // 2)
                hi = min(n, i + win_frames // 2)
                w = signal[lo:hi]
                T[i] = float(np.median(w)) + STRATEGY_E_STD_THRESHOLD * _MAD_SCALING_FACTOR * float(_compute_mad(w))
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
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": o / sfreq, "blink_duration": (f - o) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_sliding_window_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_or_fusion(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """OR union: pool E5-style detections from all channels; merge overlaps within 80ms."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(STRATEGY_E_BRIDGE_GAP_MS * sfreq / 1000.0)
    by_epoch: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for ch_idx in range(len(prepared.channel_names)):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            for s, e in _scan_threshold_crossings_e(signal, T, min_frames):
                by_epoch[epoch_idx].append((s, e))
    ch_name = "e_or_fusion"
    cand_rows: list[dict] = []
    for epoch_idx, cands in by_epoch.items():
        merged = _merge_intervals_e(cands, bridge_frames)
        for s, e in merged:
            cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                              "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
    candidates = _make_cands_df(cand_rows)
    metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
    rows = [{"channel": ch_name, "raw_candidate_count": int(len(candidates)),
             "mapped_candidate_count": int(len(candidates)),
             "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
             "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
             "recall": float(metrics.recall), "f1": float(metrics.f1)}]
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_or_fusion_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_vote_2of3(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Keep samples confirmed by >= VOTE_REQUIRED channels within VOTE_TOLERANCE."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    tol_frames = int(STRATEGY_E_VOTE_TOLERANCE_S * sfreq)
    n_ch = len(prepared.channel_names)
    n_samples = prepared.data.shape[2]
    ch_name = "e_vote_2of3"
    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        vote_arr = np.zeros(n_samples, dtype=np.int8)
        for ch_idx in range(n_ch):
            gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            for s, e in _scan_threshold_crossings_e(signal, T, min_frames):
                lo = max(0, s - tol_frames)
                hi = min(n_samples, e + tol_frames)
                vote_arr[lo:hi] += 1
        consensus = vote_arr >= STRATEGY_E_VOTE_REQUIRED
        if not consensus.any():
            continue
        padded = np.concatenate([[False], consensus, [False]])
        diff = np.diff(padded.astype(np.int8))
        ons = np.where(diff == 1)[0]
        offs = np.where(diff == -1)[0]
        for o, f in zip(ons, offs):
            if (f - o) > min_frames:
                cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                  "blink_onset": o / sfreq, "blink_duration": (f - o) / sfreq})
    candidates = _make_cands_df(cand_rows)
    metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
    rows = [{"channel": ch_name, "raw_candidate_count": int(len(candidates)),
             "mapped_candidate_count": int(len(candidates)),
             "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
             "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
             "recall": float(metrics.recall), "f1": float(metrics.f1)}]
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_vote_2of3_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_expand_bridge(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Expand event boundaries to low threshold, then bridge small gaps."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(STRATEGY_E_BRIDGE_GAP_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_high = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            T_low = ep_med + STRATEGY_E_EXPAND_LOW_K * ep_mad
            cands = _scan_threshold_crossings_e(signal, T_high, min_frames)
            expanded = []
            n = len(signal)
            for s, e in cands:
                while s > 0 and signal[s - 1] > T_low:
                    s -= 1
                while e < n and signal[e] > T_low:
                    e += 1
                expanded.append((s, e))
            merged = _merge_intervals_e(expanded, bridge_frames)
            for s, e in merged:
                if (e - s) > min_frames:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_expand_bridge_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Tutorial-27 expand_bridge derivative helpers
# ---------------------------------------------------------------------------

def _rolling_mad_threshold_27(
    signal: np.ndarray,
    win_frames: int,
    k: float,
    gfloor: float,
) -> np.ndarray:
    """Vectorised per-sample rolling median + k * SCALING * rolling_MAD."""
    sig_s = pd.Series(signal)
    roll_med = sig_s.rolling(window=win_frames, center=True, min_periods=1).median()
    abs_dev = (sig_s - roll_med).abs()
    roll_mad = abs_dev.rolling(window=win_frames, center=True, min_periods=1).median()
    T = roll_med.values + k * _MAD_SCALING_FACTOR * roll_mad.values
    return np.maximum(T, gfloor)


def _expand_interval_27(
    signal: np.ndarray,
    s: int,
    e: int,
    t_low: float,
) -> tuple[int, int]:
    """Expand (s, e) outward while signal exceeds t_low."""
    n = len(signal)
    while s > 0 and signal[s - 1] > t_low:
        s -= 1
    while e < n and signal[e] > t_low:
        e += 1
    return s, e


def _merge_conditional_27(
    intervals: list[tuple[int, int]],
    is_strong: list[bool],
    gap_strong_frames: int,
    gap_weak_frames: int,
) -> list[tuple[int, int]]:
    """Merge intervals; gap depends on whether both neighbors are strong."""
    if not intervals:
        return []
    paired = sorted(zip(intervals, is_strong), key=lambda x: x[0][0])
    merged: list[tuple[tuple[int, int], bool]] = [(paired[0][0], paired[0][1])]
    for curr_iv, curr_strong in paired[1:]:
        prev_iv, prev_strong = merged[-1]
        max_gap = gap_strong_frames if (prev_strong and curr_strong) else gap_weak_frames
        if curr_iv[0] <= prev_iv[1] + max_gap:
            merged[-1] = ((prev_iv[0], max(prev_iv[1], curr_iv[1])), prev_strong or curr_strong)
        else:
            merged.append((curr_iv, curr_strong))
    return [iv for iv, _ in merged]


# ---------------------------------------------------------------------------
# Tutorial-27 expand_bridge derivative runners
# ---------------------------------------------------------------------------

def run_expand_bridge_dynamic_low(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Epoch-aware T_low: k_low scales with epoch_mad / global_mad ratio."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(STRATEGY_E_BRIDGE_GAP_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_high = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            noise_ratio = ep_mad / (global_mad + 1e-12)
            k_low_adj = float(np.clip(
                EXPAND_DYN_LOW_K_BASE * noise_ratio,
                EXPAND_DYN_LOW_K_MIN, EXPAND_DYN_LOW_K_MAX,
            ))
            T_low = ep_med + k_low_adj * ep_mad
            cands = _scan_threshold_crossings_e(signal, T_high, min_frames)
            expanded = [_expand_interval_27(signal, s, e, T_low) for s, e in cands]
            for s, e in _merge_intervals_e(expanded, bridge_frames):
                if (e - s) > min_frames:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "expand_bridge_dynamic_low_lane_summary.csv", index=False)
    return summary, {}


def run_expand_bridge_dynamic_gap(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Candidate-strength-aware gap bridging (strong–strong: 100ms, else: 40ms)."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    gap_strong = int(EXPAND_DYN_GAP_STRONG_MS * sfreq / 1000.0)
    gap_weak = int(EXPAND_DYN_GAP_WEAK_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_high = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            T_low = ep_med + STRATEGY_E_EXPAND_LOW_K * ep_mad
            T_strong = T_high + EXPAND_DYN_GAP_STRONG_K * ep_mad
            cands = _scan_threshold_crossings_e(signal, T_high, min_frames)
            expanded = [_expand_interval_27(signal, s, e, T_low) for s, e in cands]
            is_strong = [
                (float(np.max(signal[s:e])) if e > s else T_high) >= T_strong
                for s, e in expanded
            ]
            for s, e in _merge_conditional_27(expanded, is_strong, gap_strong, gap_weak):
                if (e - s) > min_frames:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "expand_bridge_dynamic_gap_lane_summary.csv", index=False)
    return summary, {}


def run_expand_bridge_confidence_weighted(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Two-tier trust: strong get aggressive expand+80ms bridge; weak get conservative+40ms."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    bridge_strong = int(EXPAND_CONF_BRIDGE_STRONG_MS * sfreq / 1000.0)
    bridge_weak = int(EXPAND_CONF_BRIDGE_WEAK_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_high = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            T_strong = T_high + EXPAND_CONF_STRONG_K * ep_mad
            T_low_s = ep_med + EXPAND_CONF_K_LOW_STRONG * ep_mad
            T_low_w = ep_med + EXPAND_CONF_K_LOW_WEAK * ep_mad
            cands = _scan_threshold_crossings_e(signal, T_high, min_frames)
            strong_ivs: list[tuple[int, int]] = []
            weak_ivs: list[tuple[int, int]] = []
            for s, e in cands:
                peak = float(np.max(signal[s:e])) if e > s else T_high
                if peak >= T_strong:
                    strong_ivs.append(_expand_interval_27(signal, s, e, T_low_s))
                else:
                    weak_ivs.append(_expand_interval_27(signal, s, e, T_low_w))
            all_ivs = (
                _merge_intervals_e(strong_ivs, bridge_strong)
                + _merge_intervals_e(weak_ivs, bridge_weak)
            )
            for s, e in _merge_intervals_e(all_ivs, 0):  # resolve any remaining overlaps
                if (e - s) > min_frames:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "expand_bridge_confidence_weighted_lane_summary.csv", index=False)
    return summary, {}


def run_expand_bridge_sw_onset(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Sliding-window onset detection + expand+bridge boundary recovery (Tier 1)."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    win_frames = int(EXPAND_SW_WINDOW_S_27 * sfreq)
    bridge_frames = int(STRATEGY_E_BRIDGE_GAP_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            T_sw = _rolling_mad_threshold_27(signal, win_frames, STRATEGY_E_STD_THRESHOLD, gfloor)
            above = signal > T_sw
            if not above.any():
                continue
            padded = np.concatenate([[False], above, [False]])
            diff = np.diff(padded.astype(np.int8))
            ons = np.where(diff == 1)[0]
            offs = np.where(diff == -1)[0]
            cands_sw = [(int(o), int(f)) for o, f in zip(ons, offs) if (f - o) > min_frames]
            if not cands_sw:
                continue
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_low = ep_med + STRATEGY_E_EXPAND_LOW_K * ep_mad
            expanded = [_expand_interval_27(signal, s, e, T_low) for s, e in cands_sw]
            for s, e in _merge_intervals_e(expanded, bridge_frames):
                if (e - s) > min_frames:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "expand_bridge_sw_onset_lane_summary.csv", index=False)
    return summary, {}


def run_expand_bridge_adaptive_k(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Adaptive k for T_high + normal expand+bridge post-processing (Tier 2)."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(STRATEGY_E_BRIDGE_GAP_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        global_mean = float(np.mean(concat))
        ep_mads = [_MAD_SCALING_FACTOR * float(_compute_mad(
            prepared.data[ei, ch_idx, :].astype(float))) for ei in valid_epoch_indices]
        quiet_mad = float(np.percentile(ep_mads, 25)) if ep_mads else global_mad
        ratio = global_mad / (quiet_mad + 1e-12)
        k_adj = float(np.clip(STRATEGY_E_STD_THRESHOLD * ratio,
                              EXPAND_ADAPTIVE_K_MIN_27, EXPAND_ADAPTIVE_K_MAX_27))
        global_floor_adj = global_mean + k_adj * global_mad
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_high = max(ep_med + k_adj * ep_mad, global_floor_adj)
            T_low = ep_med + STRATEGY_E_EXPAND_LOW_K * ep_mad
            cands = _scan_threshold_crossings_e(signal, T_high, min_frames)
            expanded = [_expand_interval_27(signal, s, e, T_low) for s, e in cands]
            for s, e in _merge_intervals_e(expanded, bridge_frames):
                if (e - s) > min_frames:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "expand_bridge_adaptive_k_lane_summary.csv", index=False)
    return summary, {}


def run_expand_bridge_soft_gate(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Self-trained soft amplitude gate after expand+bridge (Tier 1)."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    bridge_frames = int(STRATEGY_E_BRIDGE_GAP_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        # Pass 1: conservative scan to learn amplitude gate
        confident_peaks: list[float] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_cons = max(ep_med + EXPAND_SOFT_GATE_K_CONSERVATIVE * ep_mad, gfloor)
            for s, e in _scan_threshold_crossings_e(signal, T_cons, min_frames):
                if e > s:
                    confident_peaks.append(float(np.max(signal[s:e])))
        if len(confident_peaks) >= EXPAND_SOFT_GATE_MIN_CONFIDENT:
            peaks_arr = np.array(confident_peaks)
            peak_med = float(np.median(peaks_arr))
            peak_mad = _MAD_SCALING_FACTOR * float(_compute_mad(peaks_arr))
            amp_gate = max(peak_med - 2.0 * peak_mad, gfloor)
        else:
            amp_gate = gfloor
        # Pass 2: full expand+bridge, filter by gate
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_high = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            T_low = ep_med + STRATEGY_E_EXPAND_LOW_K * ep_mad
            cands = _scan_threshold_crossings_e(signal, T_high, min_frames)
            expanded = [_expand_interval_27(signal, s, e, T_low) for s, e in cands]
            for s, e in _merge_intervals_e(expanded, bridge_frames):
                if (e - s) > min_frames:
                    peak_amp = float(np.max(signal[s:e])) if e > s else 0.0
                    if peak_amp >= amp_gate:
                        cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                          "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "expand_bridge_soft_gate_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_duration_band(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Reject events outside [50ms, 500ms] duration range."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    dur_min = STRATEGY_E_DURATION_MIN_MS * sfreq / 1000.0
    dur_max = STRATEGY_E_DURATION_MAX_MS * sfreq / 1000.0
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            for s, e in _scan_threshold_crossings_e(signal, T, min_frames):
                dur = e - s
                if dur_min <= dur <= dur_max:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": dur / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_duration_band_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_slope_guard(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Keep events where the amplitude peak falls within the middle 70% of the window."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            for s, e in _scan_threshold_crossings_e(signal, T, min_frames):
                seg = signal[s:e]
                rel = int(np.argmax(seg)) / max(len(seg) - 1, 1)
                if 0.15 <= rel <= 0.85:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_slope_guard_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_abs_polarity(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Detect on |signal - epoch_median|; polarity-agnostic threshold."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_med = float(np.median(concat))
        global_abs_mad = _MAD_SCALING_FACTOR * float(_compute_mad(np.abs(concat - global_med)))
        global_abs_floor = STRATEGY_E_STD_THRESHOLD * global_abs_mad
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            centered = np.abs(signal - ep_med)
            ep_abs_mad = _MAD_SCALING_FACTOR * float(_compute_mad(centered))
            T = max(STRATEGY_E_STD_THRESHOLD * ep_abs_mad, global_abs_floor)
            for s, e in _scan_threshold_crossings_e(centered, T, min_frames):
                cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                  "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_abs_polarity_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_adaptive_k(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Adapt k based on ratio of global MAD to quiet-baseline (25th pct) MAD."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        ep_mads = [_MAD_SCALING_FACTOR * float(_compute_mad(
            prepared.data[ei, ch_idx, :].astype(float))) for ei in valid_epoch_indices]
        quiet_mad = float(np.percentile(ep_mads, 25)) if ep_mads else global_mad
        ratio = global_mad / (quiet_mad + 1e-12)
        k_adj = float(np.clip(STRATEGY_E_STD_THRESHOLD * ratio,
                              STRATEGY_E_ADAPTIVE_K_MIN, STRATEGY_E_ADAPTIVE_K_MAX))
        global_floor = float(np.mean(concat)) + k_adj * global_mad
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T = max(ep_med + k_adj * ep_mad, global_floor)
            for s, e in _scan_threshold_crossings_e(signal, T, min_frames):
                cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                  "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_adaptive_k_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_quantile_thr(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """T = max(93rd-pct of epoch signal, global_floor)."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            T = max(float(np.percentile(signal, STRATEGY_E_QUANTILE_PCT)), gfloor)
            for s, e in _scan_threshold_crossings_e(signal, T, min_frames):
                cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                  "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_quantile_thr_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e_refractory(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """E5-style detection with 150ms refractory suppression of closely-spaced events."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    refrac_frames = int(STRATEGY_E_REFRACTORY_MS * sfreq / 1000.0)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            raw_cands = _scan_threshold_crossings_e(signal, T, min_frames)
            last_onset = -refrac_frames
            for s, e in raw_cands:
                if s - last_onset >= refrac_frames:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
                    last_onset = s
                elif cand_rows:
                    prev = cand_rows[-1]
                    prev_s = int(prev["blink_onset"] * sfreq)
                    prev_e = int(prev_s + prev["blink_duration"] * sfreq)
                    if float(np.max(signal[s:e])) > float(np.max(signal[prev_s:prev_e])):
                        cand_rows[-1] = {"epoch_index": epoch_idx, "channel": ch_name,
                                         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq}
                        last_onset = s
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e_refractory_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e8_changepoint(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Piecewise block threshold: divide each epoch into 10-second sub-blocks."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    block_frames = int(STRATEGY_E8_BLOCK_S * sfreq)
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            n = len(signal)
            for b_start in range(0, n, block_frames):
                b_end = min(b_start + block_frames, n)
                block = signal[b_start:b_end]
                b_med = float(np.median(block))
                b_mad = _MAD_SCALING_FACTOR * float(_compute_mad(block))
                T = max(b_med + STRATEGY_E_STD_THRESHOLD * b_mad, gfloor)
                for s, e in _scan_threshold_crossings_e(block, T, min_frames):
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": (b_start + s) / sfreq,
                                      "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e8_changepoint_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e11_lane_route(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Pool all channels; cluster within 100ms; keep best (highest peak amp) per cluster."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    cluster_tol = int(STRATEGY_E11_CLUSTER_TOL_MS * sfreq / 1000.0)
    ch_name = "e11_lane_route"
    all_dets: list[tuple[int, int, int, float, int]] = []
    for ch_idx in range(len(prepared.channel_names)):
        gfloor = _e_global_floor_22(prepared, ch_idx, valid_epoch_indices)
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T = max(ep_med + STRATEGY_E_STD_THRESHOLD * ep_mad, gfloor)
            for s, e in _scan_threshold_crossings_e(signal, T, min_frames):
                all_dets.append((epoch_idx, s, e, float(np.max(signal[s:e])), ch_idx))
    cand_rows: list[dict] = []
    if all_dets:
        all_dets.sort(key=lambda x: (x[0], x[1]))
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
            ei, s, e, _, _ = best
            cand_rows.append({"epoch_index": ei, "channel": ch_name,
                              "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
            i = j
    candidates = _make_cands_df(cand_rows)
    metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
    rows = [{"channel": ch_name, "raw_candidate_count": int(len(candidates)),
             "mapped_candidate_count": int(len(candidates)),
             "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
             "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
             "recall": float(metrics.recall), "f1": float(metrics.f1)}]
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e11_lane_route_lane_summary.csv", index=False)
    return summary, {}


def run_strategy_e13_self_train(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
) -> tuple[pd.DataFrame, dict]:
    """Conservative pass (k=2.0) sets amplitude gate; permissive pass (k=1.2) detects."""
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=None,
    )
    sfreq = float(prepared.sfreq)
    min_frames = STRATEGY_E_MIN_EVENT_LEN_S * sfreq
    rows: list[dict] = []
    for ch_idx, ch_name in enumerate(prepared.channel_names):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        global_mean = float(np.mean(concat))
        global_mad = _MAD_SCALING_FACTOR * float(_compute_mad(concat))
        global_floor = global_mean + STRATEGY_E_STD_THRESHOLD * global_mad
        # Pass 1: conservative (k=2.0) → confident peaks
        confident_peaks: list[float] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_cons = max(ep_med + STRATEGY_E13_K_CONSERVATIVE * ep_mad, global_floor)
            for s, e in _scan_threshold_crossings_e(signal, T_cons, min_frames):
                confident_peaks.append(float(np.max(signal[s:e])))
        if len(confident_peaks) >= STRATEGY_E13_MIN_CONFIDENT:
            peaks_arr = np.array(confident_peaks)
            peak_med = float(np.median(peaks_arr))
            peak_mad = _MAD_SCALING_FACTOR * float(_compute_mad(peaks_arr))
            amp_gate = max(peak_med - 2.0 * peak_mad, global_floor)
        else:
            amp_gate = global_floor
        # Pass 2: permissive (k=1.2) → filtered by amplitude gate
        cand_rows: list[dict] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_med = float(np.median(signal))
            ep_mad = _MAD_SCALING_FACTOR * float(_compute_mad(signal))
            T_perm = max(ep_med + STRATEGY_E13_K_PERMISSIVE * ep_mad, global_floor)
            for s, e in _scan_threshold_crossings_e(signal, T_perm, min_frames):
                if float(np.max(signal[s:e])) >= amp_gate:
                    cand_rows.append({"epoch_index": epoch_idx, "channel": ch_name,
                                      "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq})
        candidates = _make_cands_df(cand_rows)
        metrics = match_blink_tables(candidates, reference, n_epochs=len(epochs))
        rows.append({"channel": ch_name, "raw_candidate_count": int(len(candidates)),
                     "mapped_candidate_count": int(len(candidates)),
                     "tp": int(metrics.true_positives), "fp": int(metrics.false_positives),
                     "fn": int(metrics.false_negatives), "precision": float(metrics.precision),
                     "recall": float(metrics.recall), "f1": float(metrics.f1)})
    summary = build_lane_summary_from_rows(rows)
    summary.to_csv(out_dir / "strategy_e13_self_train_lane_summary.csv", index=False)
    return summary, {}


# ---------------------------------------------------------------------------
# Per-pair processing – runs all four strategies
# ---------------------------------------------------------------------------

def process_pair(
    subject: str,
    segment: str,
    fif_path: Path,
    annotation_path: Path,
    brain_channels: list[str],
) -> list[dict]:
    """Run all four strategies on one pair.  Returns a list of 4 result dicts."""
    out_dir = OUTPUT_ROOT / subject / segment
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load data once
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
        for strategy in STRATEGIES:
            r = _empty_result(subject, segment, strategy)
            r["error"] = tb
            results.append(r)
        (out_dir / "load_error.txt").write_text(tb)
        return results

    runner_map = {
        "strategy_a": run_strategy_a,
        "strategy_b": run_strategy_b,
        "strategy_c": run_strategy_c,
        "strategy_d": run_strategy_d,
        "strategy_e": run_strategy_e,
        "strategy_e1_median": run_strategy_e1_median,
        "strategy_e2_floor": run_strategy_e2_floor,
        "strategy_e3_hysteresis": run_strategy_e3_hysteresis,
        "strategy_e4_multiscale": run_strategy_e4_multiscale,
        "strategy_e5_global_floor": run_strategy_e5_global_floor,
        "strategy_e6_soft_shrink": run_strategy_e6_soft_shrink,
        "strategy_e7_bg_refit": run_strategy_e7_bg_refit,
        "strategy_e9_frontal_avg": run_strategy_e9_frontal_avg,
        "strategy_e10_epoch_smooth": run_strategy_e10_epoch_smooth,
        "strategy_e6_e10_combined": run_strategy_e6_e10_combined,
        "strategy_e12_amp_filter": run_strategy_e12_amp_filter,
        # Tutorial-26 remaining variants
        "strategy_e_sliding_window": run_strategy_e_sliding_window,
        "strategy_e_or_fusion": run_strategy_e_or_fusion,
        "strategy_e_vote_2of3": run_strategy_e_vote_2of3,
        "strategy_e_expand_bridge": run_strategy_e_expand_bridge,
        "strategy_e_duration_band": run_strategy_e_duration_band,
        "strategy_e_slope_guard": run_strategy_e_slope_guard,
        "strategy_e_abs_polarity": run_strategy_e_abs_polarity,
        "strategy_e_adaptive_k": run_strategy_e_adaptive_k,
        "strategy_e_quantile_thr": run_strategy_e_quantile_thr,
        "strategy_e_refractory": run_strategy_e_refractory,
        "strategy_e8_changepoint": run_strategy_e8_changepoint,
        "strategy_e11_lane_route": run_strategy_e11_lane_route,
        "strategy_e13_self_train": run_strategy_e13_self_train,
        # Tutorial-27 expand_bridge derivatives
        "expand_bridge_dynamic_low": run_expand_bridge_dynamic_low,
        "expand_bridge_dynamic_gap": run_expand_bridge_dynamic_gap,
        "expand_bridge_confidence_weighted": run_expand_bridge_confidence_weighted,
        "expand_bridge_sw_onset": run_expand_bridge_sw_onset,
        "expand_bridge_adaptive_k": run_expand_bridge_adaptive_k,
        "expand_bridge_soft_gate": run_expand_bridge_soft_gate,
    }

    results: list[dict] = []
    for strategy in STRATEGIES:
        result = _empty_result(subject, segment, strategy)
        result["n_epochs"] = n_epochs
        result["n_annotations"] = n_annotations

        started = perf_counter()
        try:
            summary, _ = runner_map[strategy](epochs, reference, valid_epoch_indices, out_dir)
            result["n_lanes"] = len(summary)
            _fill_best(result, summary)
        except Exception:  # noqa: BLE001
            tb = traceback.format_exc()
            result["error"] = tb
            (out_dir / f"{strategy}_error.txt").write_text(tb)
            print(f"    [ERROR] {strategy} on {subject}/{segment}\n{tb}")

        result["elapsed_s"] = perf_counter() - started
        results.append(result)

        if not result["error"]:
            print(
                f"      [{strategy}] {result['elapsed_s']:.1f}s  "
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
            "total_tp": 0,
            "total_fp": 0,
            "total_fn": 0,
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
    if not (isinstance(micro_p, float) and isinstance(micro_r, float) and (micro_p + micro_r) == 0):
        micro_f1 = 2.0 * micro_p * micro_r / (micro_p + micro_r)
    else:
        micro_f1 = float("nan")

    return {
        "strategy": strategy,
        "n_pairs_total": total,
        "n_pairs_successful": n_ok,
        "n_pairs_failed": n_fail,
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
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
    """Wrapper for ThreadPoolExecutor – unpacks args and calls process_pair."""
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
    print("Tutorial 22 – Strategy E 2nd-Iteration Derivatives comparison run")
    print("=" * 70)
    print(f"Strategies : {STRATEGIES}")
    print(f"N_WORKERS  : {N_WORKERS}")

    pairs = find_pairs()
    if not pairs:
        print("No matched (fif, csv) pairs found. Check PROCESSED_ROOT and ANNOTATION_ROOT.")
        return
    print(f"\nFound {len(pairs)} pair(s). Output root: {OUTPUT_ROOT}\n")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    print(f"Brain-region channels ({len(brain_channels)}): {brain_channels}\n")

    tasks = [
        (i, len(pairs), pair["subject"], pair["segment"],
         Path(pair["fif"]), Path(pair["csv"]), brain_channels)
        for i, pair in enumerate(pairs, 1)
    ]

    all_results: list[dict] = []
    if N_WORKERS == 1:
        for task in tasks:
            all_results.extend(_process_pair_task(task))
    else:
        with ThreadPoolExecutor(max_workers=N_WORKERS) as executor:
            futures = {executor.submit(_process_pair_task, task): task for task in tasks}
            for future in as_completed(futures):
                all_results.extend(future.result())

    # ---------------------------------------------------------------------------
    # Save per-pair comparison CSV
    # ---------------------------------------------------------------------------
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    per_pair_df = pd.DataFrame(all_results)
    per_pair_csv = OUTPUT_ROOT / "comparison_e_derivatives_per_pair.csv"
    per_pair_df.to_csv(per_pair_csv, index=False)
    print(f"Per-pair results saved -> {per_pair_csv}\n")

    # ---------------------------------------------------------------------------
    # Aggregate per strategy
    # ---------------------------------------------------------------------------
    agg_rows = [compute_aggregate(per_pair_df, s) for s in STRATEGIES]
    agg_df = pd.DataFrame(agg_rows)
    agg_csv = OUTPUT_ROOT / "comparison_e_derivatives_aggregate.csv"
    agg_df.to_csv(agg_csv, index=False)
    print(f"Aggregate comparison saved -> {agg_csv}\n")

    # ---------------------------------------------------------------------------
    # Print side-by-side summary
    # ---------------------------------------------------------------------------
    print("=" * 70)
    print("AGGREGATE COMPARISON  (best lane per pair)")
    print("=" * 70)
    display_cols = [
        "strategy",
        "n_pairs_successful", "n_pairs_failed",
        "total_tp", "total_fp", "total_fn",
        "micro_precision", "micro_recall", "micro_f1",
        "macro_precision", "macro_recall", "macro_f1",
    ]
    disp = agg_df[display_cols].copy()
    for col in ("micro_precision", "micro_recall", "micro_f1",
                "macro_precision", "macro_recall", "macro_f1"):
        disp[col] = disp[col].map(lambda x: f"{x:.4f}" if x == x else "nan")  # noqa: PLR0124
    print(disp.to_string(index=False))

    # ---------------------------------------------------------------------------
    # Per-pair pivot view (F1 only) for quick visual comparison
    # ---------------------------------------------------------------------------
    print("\n--- Per-pair F1 comparison ---")
    pivot = per_pair_df[per_pair_df["error"].isna() | (per_pair_df["error"] == "")].pivot_table(
        index=["subject", "segment"],
        columns="strategy",
        values="best_f1",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    # Add winner column
    strat_cols = [c for c in STRATEGIES if c in pivot.columns]
    if strat_cols:
        pivot["winner"] = pivot[strat_cols].idxmax(axis=1)
    for col in strat_cols:
        pivot[col] = pivot[col].map(lambda x: f"{x:.4f}" if x == x else "nan")  # noqa: PLR0124
    print(pivot.to_string(index=False))

    pivot_csv = OUTPUT_ROOT / "comparison_e_derivatives_f1_pivot.csv"
    pivot.to_csv(pivot_csv, index=False)
    print(f"\nF1 pivot saved -> {pivot_csv}")


if __name__ == "__main__":
    main()
