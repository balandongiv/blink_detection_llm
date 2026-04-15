"""
Tutorial 25 – Strategy E Second-Iteration Derivatives (Step 1 batch evaluation).

Exploratory second-wave derivatives of Strategy E following the roadmap in
tutorial/strategy_e_derivative_2nd.md.

Implemented variants
--------------------
E6  – e6_soft_shrink    : soft interpolation between local and global thresholds
                          T = alpha * T_local + (1-alpha) * T_global
                          alpha = clip(epoch_MAD / global_MAD, ALPHA_MIN, ALPHA_MAX)
E7  – e7_bg_refit       : two-pass iterative background refit
                          pass1 (permissive k=1.0) → mask candidates → refit stats
                          on background only → pass2 (k=1.5) for final candidates
E9  – e9_frontal_avg    : frontal-dominance virtual channel
                          average all available frontal channels into one signal,
                          then apply E5-style thresholding on the averaged signal
E10 – e10_epoch_smooth  : cross-epoch threshold regularisation
                          T'_e = 0.25*T_{e-1} + 0.5*T_e + 0.25*T_{e+1}
                          (triangular smoothing of per-epoch medianMAD thresholds)
E6_E10 – e6_e10_combined: E6 soft-shrinkage + E10 cross-epoch smoothing combined
                          compute E6 threshold per epoch, then smooth with E10 kernel

Debug mode
----------
Set DEBUG = True to run only the first pair (single-threaded, fast feedback).
Set DEBUG = False to run all 65 pairs using N_WORKERS threads.

Outputs
-------
    experiment_output/<subject>/<segment>/strategy_e6_soft_shrink_lane_summary.csv
    experiment_output/<subject>/<segment>/strategy_e7_bg_refit_lane_summary.csv
    experiment_output/<subject>/<segment>/strategy_e9_frontal_avg_lane_summary.csv
    experiment_output/<subject>/<segment>/strategy_e10_epoch_smooth_lane_summary.csv
    experiment_output/<subject>/<segment>/strategy_e6_e10_combined_lane_summary.csv
    experiment_output/strategy_e2nd_derivatives_all_results.csv
    experiment_output/strategy_e2nd_derivatives_aggregate.csv
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
DEBUG = True       # True = first pair only, single-threaded; False = all pairs
N_WORKERS = 4      # only used when DEBUG = False

BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
OUTPUT_ROOT = REPO_ROOT / "experiment_output"

# Shared threshold params
K_DEFAULT = 1.5           # k used across all variants for the final detection pass
MIN_EVENT_LEN_S = 0.05   # minimum blink duration in seconds

# E6 soft-shrinkage: alpha = clip(epoch_MAD / global_MAD, ALPHA_MIN, ALPHA_MAX)
SOFT_ALPHA_MIN = 0.2
SOFT_ALPHA_MAX = 0.9

# E7 background refit: permissive first-pass k
E7_K_PASS1 = 1.0          # lower k → more permissive → broader masking
E7_MIN_BG_SAMPLES = 20    # if background after masking is tiny, fall back to E5

# E10 cross-epoch smoothing weights [prev, current, next]
E10_SMOOTH_WEIGHTS = (0.25, 0.50, 0.25)

# E12 amplitude percentile filter: remove bottom-X% of detections per channel
E12_AMP_PERCENTILE = 15   # remove bottom 15% by peak amplitude
E12_MIN_CANDS_TO_FILTER = 10  # skip filter if fewer candidates than this

VARIANT_NAMES = [
    "e6_soft_shrink",
    "e7_bg_refit",
    "e9_frontal_avg",
    "e10_epoch_smooth",
    "e6_e10_combined",
    "e12_amp_filter",
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
# Shared scanning primitive
# ---------------------------------------------------------------------------

def _scan_threshold_crossings(
    signal: np.ndarray,
    threshold: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Standard threshold-crossing scan. Returns (onset_sample, offset_sample) pairs."""
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


def _make_candidates_df(cand_rows: list[dict], channel_name: str) -> pd.DataFrame:
    if cand_rows:
        return (
            pd.DataFrame(cand_rows)
            .sort_values(["epoch_index", "blink_onset"])
            .reset_index(drop=True)
        )
    return pd.DataFrame(columns=["epoch_index", "channel", "blink_onset", "blink_duration"])


# ---------------------------------------------------------------------------
# E6 – Soft-Shrinkage Threshold
# ---------------------------------------------------------------------------

def _run_e6_soft_shrink_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E6: soft interpolation between local per-epoch and global thresholds.

    T_local = median(epoch) + k * SCALING * MAD(epoch)
    T_global = mean(concat) + k * SCALING * MAD(concat)   [Strategy A formula]
    alpha = clip(epoch_scaled_MAD / global_scaled_MAD, ALPHA_MIN, ALPHA_MAX)
    T_e = alpha * T_local + (1 - alpha) * T_global

    Quiet epochs (low MAD) get alpha close to ALPHA_MIN -> pulled toward global.
    Noisy epochs (high MAD) get alpha close to ALPHA_MAX -> trust local more.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_scaled_mad = SCALING_FACTOR * float(compute_mad(concat))
    T_global = global_mean + K_DEFAULT * global_scaled_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_scaled_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_local = ep_median + K_DEFAULT * ep_scaled_mad

        alpha = float(np.clip(
            ep_scaled_mad / (global_scaled_mad + 1e-12),
            SOFT_ALPHA_MIN,
            SOFT_ALPHA_MAX,
        ))
        threshold = alpha * T_local + (1.0 - alpha) * T_global

        for start, end in _scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


# ---------------------------------------------------------------------------
# E7 – Iterative Background Refit
# ---------------------------------------------------------------------------

def _run_e7_bg_refit_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E7: two-pass iterative background refit.

    Pass 1 (permissive, k=E7_K_PASS1): detect candidate regions.
    Mask those regions.
    Recompute median + MAD on the remaining background samples.
    Pass 2 (k=K_DEFAULT): scan with refit threshold.

    This prevents blink bursts from inflating the local threshold estimate.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq

    # Global fallback (E5 style) – used when background after masking is too short
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_mean + K_DEFAULT * global_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

        # --- Pass 1: permissive detection ---
        ep_median_p1 = float(np.median(signal))
        ep_mad_p1 = SCALING_FACTOR * float(compute_mad(signal))
        T_pass1 = ep_median_p1 + E7_K_PASS1 * ep_mad_p1

        pass1_cands = _scan_threshold_crossings(signal, T_pass1, min_frames)

        # --- Build background mask ---
        mask = np.ones(len(signal), dtype=bool)
        for start, end in pass1_cands:
            mask[start:end] = False

        background = signal[mask]

        # --- Recompute stats on background ---
        if len(background) >= E7_MIN_BG_SAMPLES:
            bg_median = float(np.median(background))
            bg_mad = SCALING_FACTOR * float(compute_mad(background))
            T_refit = bg_median + K_DEFAULT * bg_mad
            # Apply same global floor to prevent threshold collapse
            T_refit = max(T_refit, global_floor)
        else:
            # Background too short – fall back to global floor
            T_refit = global_floor

        # --- Pass 2: final detection ---
        for start, end in _scan_threshold_crossings(signal, T_refit, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


# ---------------------------------------------------------------------------
# E9 – Frontal-Dominance Average Virtual Channel
# ---------------------------------------------------------------------------

def _run_e9_frontal_avg(
    prepared,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E9: average all frontal channels into one virtual signal, then apply E5-style threshold.

    With the current brain_region.yaml (E3, E9, E22 – all frontal), this creates a
    single averaged virtual channel that reduces single-channel noise while preserving
    the shared frontal ocular component (blinks appear on all frontal channels).

    The E5 global-floor strategy is applied to the averaged signal.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    virtual_ch_name = "frontal_avg"

    # Build averaged signal: shape (n_valid_epochs, n_samples)
    # prepared.data shape: (n_total_epochs, n_channels, n_samples)
    n_epochs_total = prepared.data.shape[0]
    n_samples = prepared.data.shape[2]

    avg_epochs = np.mean(prepared.data[valid_epoch_indices, :, :], axis=1)  # (n_valid, n_samples)

    # Global floor on concatenated average
    concat_avg = avg_epochs.reshape(-1).astype(float)
    global_mean = float(np.mean(concat_avg))
    global_mad = SCALING_FACTOR * float(compute_mad(concat_avg))
    global_floor = global_mean + K_DEFAULT * global_mad

    cand_rows: list[dict] = []
    for i, epoch_idx in enumerate(valid_epoch_indices):
        signal = avg_epochs[i].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        threshold = max(ep_median + K_DEFAULT * ep_mad, global_floor)

        for start, end in _scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": virtual_ch_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, virtual_ch_name)


# ---------------------------------------------------------------------------
# E10 – Cross-Epoch Threshold Regularisation
# ---------------------------------------------------------------------------

def _run_e10_epoch_smooth_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E10: triangular smoothing of per-epoch median+MAD thresholds across epochs.

    T_raw[e] = median(epoch_e) + k * SCALING * MAD(epoch_e)
    T'[e]    = w_prev * T_raw[e-1] + w_curr * T_raw[e] + w_next * T_raw[e+1]
                  (boundary epochs clamp to their neighbour)

    Prevents isolated threshold collapse in one quiet epoch while preserving
    global adaptivity across the recording.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    w_prev, w_curr, w_next = E10_SMOOTH_WEIGHTS

    # Compute raw per-epoch thresholds
    raw_thresholds: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        raw_thresholds.append(ep_median + K_DEFAULT * ep_mad)

    # Triangular smoothing with edge clamping
    n = len(raw_thresholds)
    smoothed: list[float] = []
    for i in range(n):
        T_prev = raw_thresholds[max(0, i - 1)]
        T_next = raw_thresholds[min(n - 1, i + 1)]
        smoothed.append(w_prev * T_prev + w_curr * raw_thresholds[i] + w_next * T_next)

    cand_rows: list[dict] = []
    for i, epoch_idx in enumerate(valid_epoch_indices):
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        threshold = smoothed[i]
        for start, end in _scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


# ---------------------------------------------------------------------------
# E6+E10 – Soft Shrinkage with Cross-Epoch Smoothing
# ---------------------------------------------------------------------------

def _run_e6_e10_combined_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E6+E10 combined: compute E6 soft-shrinkage thresholds then smooth across epochs.

    Step 1: T_e6[e] = alpha_e * T_local[e] + (1 - alpha_e) * T_global
    Step 2: T_smooth[e] = triangular average of T_e6[e-1], T_e6[e], T_e6[e+1]

    Combines adaptive local/global blending (E6) with cross-epoch stability (E10).
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    w_prev, w_curr, w_next = E10_SMOOTH_WEIGHTS

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_scaled_mad = SCALING_FACTOR * float(compute_mad(concat))
    T_global = global_mean + K_DEFAULT * global_scaled_mad

    # Step 1: compute E6 threshold per epoch
    e6_thresholds: list[float] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_scaled_mad = SCALING_FACTOR * float(compute_mad(signal))
        T_local = ep_median + K_DEFAULT * ep_scaled_mad
        alpha = float(np.clip(
            ep_scaled_mad / (global_scaled_mad + 1e-12),
            SOFT_ALPHA_MIN,
            SOFT_ALPHA_MAX,
        ))
        e6_thresholds.append(alpha * T_local + (1.0 - alpha) * T_global)

    # Step 2: triangular smoothing
    n = len(e6_thresholds)
    smoothed: list[float] = []
    for i in range(n):
        T_prev = e6_thresholds[max(0, i - 1)]
        T_next = e6_thresholds[min(n - 1, i + 1)]
        smoothed.append(w_prev * T_prev + w_curr * e6_thresholds[i] + w_next * T_next)

    cand_rows: list[dict] = []
    for i, epoch_idx in enumerate(valid_epoch_indices):
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        threshold = smoothed[i]
        for start, end in _scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


# ---------------------------------------------------------------------------
# Variant dispatch
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# E12 – E7 Background Refit + Amplitude Percentile Filter
# ---------------------------------------------------------------------------

def _run_e12_amp_filter_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E12: E7 background refit + per-channel bottom-percentile amplitude pruning.

    Generates E7 candidates then removes the bottom E12_AMP_PERCENTILE % by
    peak amplitude.  Those low-amplitude candidates are predominantly noise in
    quiet epochs where the threshold collapsed to the global floor.
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq

    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_mean + K_DEFAULT * global_mad

    raw_cands: list[tuple[int, int, int, float]] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

        ep_median_p1 = float(np.median(signal))
        ep_mad_p1 = SCALING_FACTOR * float(compute_mad(signal))
        T_pass1 = ep_median_p1 + E7_K_PASS1 * ep_mad_p1
        pass1_cands = _scan_threshold_crossings(signal, T_pass1, min_frames)

        mask = np.ones(len(signal), dtype=bool)
        for s, e in pass1_cands:
            mask[s:e] = False
        background = signal[mask]

        if len(background) >= E7_MIN_BG_SAMPLES:
            bg_median = float(np.median(background))
            bg_mad = SCALING_FACTOR * float(compute_mad(background))
            T_refit = max(bg_median + K_DEFAULT * bg_mad, global_floor)
        else:
            T_refit = global_floor

        for s, e in _scan_threshold_crossings(signal, T_refit, min_frames):
            peak_amp = float(np.max(signal[s:e]))
            raw_cands.append((epoch_idx, s, e, peak_amp))

    if len(raw_cands) >= E12_MIN_CANDS_TO_FILTER:
        all_peaks = np.array([c[3] for c in raw_cands])
        amp_gate = float(np.percentile(all_peaks, E12_AMP_PERCENTILE))
        filtered = [(ei, s, e) for ei, s, e, p in raw_cands if p >= amp_gate]
    else:
        filtered = [(ei, s, e) for ei, s, e, _ in raw_cands]

    cand_rows = [
        {"epoch_index": ei, "channel": channel_name,
         "blink_onset": s / sfreq, "blink_duration": (e - s) / sfreq}
        for ei, s, e in filtered
    ]
    return _make_candidates_df(cand_rows, channel_name)


# Per-channel runners (all except E9 which is a special pair-level runner)
_VARIANT_CHANNEL_RUNNERS = {
    "e6_soft_shrink": _run_e6_soft_shrink_channel,
    "e7_bg_refit": _run_e7_bg_refit_channel,
    "e10_epoch_smooth": _run_e10_epoch_smooth_channel,
    "e6_e10_combined": _run_e6_e10_combined_channel,
    "e12_amp_filter": _run_e12_amp_filter_channel,
}


def run_variant(
    variant: str,
    prepared,
    valid_epoch_indices: list[int],
    reference: pd.DataFrame,
    n_epochs: int,
) -> pd.DataFrame:
    """Run a single variant across all channels (or produce virtual channel for E9).

    Returns a lane-summary DataFrame sorted best-first by F1.
    """
    rows: list[dict] = []

    if variant == "e9_frontal_avg":
        # Special case: single virtual channel from averaged frontal signals
        candidates = _run_e9_frontal_avg(prepared, valid_epoch_indices)
        metrics = match_blink_tables(candidates, reference, n_epochs=n_epochs)
        rows.append({
            "variant": variant,
            "channel": "frontal_avg",
            "candidate_count": int(len(candidates)),
            "tp": int(metrics.true_positives),
            "fp": int(metrics.false_positives),
            "fn": int(metrics.false_negatives),
            "precision": float(metrics.precision),
            "recall": float(metrics.recall),
            "f1": float(metrics.f1),
        })
    else:
        runner = _VARIANT_CHANNEL_RUNNERS[variant]
        for ch_idx, channel_name in enumerate(prepared.channel_names):
            candidates = runner(prepared, ch_idx, channel_name, valid_epoch_indices)
            metrics = match_blink_tables(candidates, reference, n_epochs=n_epochs)
            rows.append({
                "variant": variant,
                "channel": channel_name,
                "candidate_count": int(len(candidates)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
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

def process_pair(
    subject: str,
    segment: str,
    fif_path: Path,
    annotation_path: Path,
    brain_channels: list[str],
) -> list[dict]:
    """Run all second-iteration E variants on one pair. Returns one result dict per variant."""
    out_dir = OUTPUT_ROOT / subject / segment
    out_dir.mkdir(parents=True, exist_ok=True)

    base: dict = {
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

    # Load data once for all variants
    try:
        raw = load_raw_with_brain_channels(fif_path, brain_channels)
        epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
        reference = load_annotation_as_reference(annotation_path, epoch_duration=EPOCH_DURATION_S)
        valid_epoch_indices = get_valid_epoch_indices(epochs)
        n_epochs = len(epochs)
        n_annotations = len(reference)
        reference.to_csv(out_dir / "reference_annotation.csv", index=False)

        prepared = prepare_epoch_detection_input(
            epochs,
            pick_types_options={"eeg": True},
            filter_low=FILTER_LOW,
            filter_high=FILTER_HIGH,
            resample_rate=RESAMPLE_RATE,
        )
    except Exception:
        tb = traceback.format_exc()
        print(f"    [ERROR] loading {subject}/{segment}\n{tb}")
        results = []
        for v in VARIANT_NAMES:
            r = dict(base)
            r["variant"] = v
            r["error"] = tb
            results.append(r)
        (out_dir / "load_error.txt").write_text(tb)
        return results

    results: list[dict] = []
    for variant in VARIANT_NAMES:
        r = dict(base)
        r["variant"] = variant
        r["n_epochs"] = n_epochs
        r["n_annotations"] = n_annotations
        started = perf_counter()
        try:
            summary = run_variant(variant, prepared, valid_epoch_indices, reference, n_epochs)
            summary.to_csv(out_dir / f"strategy_{variant}_lane_summary.csv", index=False)
            r["n_lanes"] = len(summary)
            if not summary.empty:
                best = summary.iloc[0]
                r["best_channel"] = str(best["channel"])
                r["best_tp"] = int(best["tp"])
                r["best_fp"] = int(best["fp"])
                r["best_fn"] = int(best["fn"])
                r["best_precision"] = float(best["precision"])
                r["best_recall"] = float(best["recall"])
                r["best_f1"] = float(best["f1"])
        except Exception:
            tb = traceback.format_exc()
            r["error"] = tb
            (out_dir / f"strategy_{variant}_error.txt").write_text(tb)
            print(f"    [ERROR] {variant} on {subject}/{segment}\n{tb}")

        r["elapsed_s"] = perf_counter() - started
        results.append(r)

        if not r["error"]:
            print(
                f"      [{variant}] {r['elapsed_s']:.1f}s  "
                f"lanes={r['n_lanes']}  best_ch={r['best_channel']}  "
                f"TP={r['best_tp']}  FP={r['best_fp']}  FN={r['best_fn']}  "
                f"P={r['best_precision']:.3f}  R={r['best_recall']:.3f}  "
                f"F1={r['best_f1']:.3f}"
            )

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
        return {
            "variant": variant, "n_pairs_total": total,
            "n_pairs_successful": n_ok, "n_pairs_failed": n_fail,
            "total_tp": 0, "total_fp": 0, "total_fn": 0,
            "micro_precision": float("nan"), "micro_recall": float("nan"),
            "micro_f1": float("nan"),
            "macro_precision": float("nan"), "macro_recall": float("nan"),
            "macro_f1": float("nan"),
        }

    total_tp = int(sub["best_tp"].sum())
    total_fp = int(sub["best_fp"].sum())
    total_fn = int(sub["best_fn"].sum())
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else float("nan")
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else float("nan")
    micro_f1 = (
        2.0 * micro_p * micro_r / (micro_p + micro_r)
        if (micro_p + micro_r) > 0 else float("nan")
    )
    return {
        "variant": variant, "n_pairs_total": total,
        "n_pairs_successful": n_ok, "n_pairs_failed": n_fail,
        "total_tp": total_tp, "total_fp": total_fp, "total_fn": total_fn,
        "micro_precision": micro_p, "micro_recall": micro_r, "micro_f1": micro_f1,
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
    print("Tutorial 25 – Strategy E 2nd-Iteration Derivatives  (Step 1 batch)")
    print("=" * 70)
    print(f"DEBUG mode         : {DEBUG}")
    print(f"N_WORKERS          : {1 if DEBUG else N_WORKERS}")
    print(f"Variants           : {VARIANT_NAMES}")
    print(f"k_default          : {K_DEFAULT}")
    print(f"soft_alpha range   : [{SOFT_ALPHA_MIN}, {SOFT_ALPHA_MAX}]  (E6)")
    print(f"e7_k_pass1         : {E7_K_PASS1}   (E7 first-pass k)")
    print(f"smooth_weights     : {E10_SMOOTH_WEIGHTS}  (E10/E6+E10)")
    print(f"min_event_len_s    : {MIN_EVENT_LEN_S}")
    print()

    pairs = find_pairs()
    if not pairs:
        print("No matched (fif, csv) pairs found.")
        return

    if DEBUG:
        pairs = pairs[:1]
        print(f"[DEBUG] Running on first pair only: {pairs[0]['subject']} / {pairs[0]['segment']}")
    else:
        print(f"Found {len(pairs)} pair(s). Output root: {OUTPUT_ROOT}")

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

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    per_pair_df = pd.DataFrame(all_results)
    per_pair_csv = OUTPUT_ROOT / "strategy_e2nd_derivatives_all_results.csv"
    per_pair_df.to_csv(per_pair_csv, index=False)
    print(f"Per-pair results saved -> {per_pair_csv}\n")

    agg_rows = [compute_aggregate(per_pair_df, v) for v in VARIANT_NAMES]
    agg_df = pd.DataFrame(agg_rows)
    agg_csv = OUTPUT_ROOT / "strategy_e2nd_derivatives_aggregate.csv"
    agg_df.to_csv(agg_csv, index=False)
    print(f"Aggregate saved -> {agg_csv}\n")

    print("=" * 70)
    print("AGGREGATE SUMMARY  (best lane per pair)")
    print("=" * 70)
    display_cols = [
        "variant", "n_pairs_successful", "n_pairs_failed",
        "total_tp", "total_fp", "total_fn",
        "micro_precision", "micro_recall", "micro_f1",
        "macro_precision", "macro_recall", "macro_f1",
    ]
    disp = agg_df[display_cols].copy()
    for col in ("micro_precision", "micro_recall", "micro_f1",
                "macro_precision", "macro_recall", "macro_f1"):
        disp[col] = disp[col].map(lambda x: f"{x:.4f}" if x == x else "nan")  # noqa: PLR0124
    print(disp.to_string(index=False))

    # Per-pair F1 pivot
    success_df = per_pair_df[per_pair_df["error"].isna() | (per_pair_df["error"] == "")]
    if not success_df.empty:
        pivot = success_df.pivot_table(
            index=["subject", "segment"],
            columns="variant",
            values="best_f1",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None
        variant_cols = [c for c in VARIANT_NAMES if c in pivot.columns]
        if variant_cols:
            pivot["winner"] = pivot[variant_cols].idxmax(axis=1)
        for col in variant_cols:
            pivot[col] = pivot[col].map(lambda x: f"{x:.4f}" if x == x else "nan")  # noqa: PLR0124
        pivot_csv = OUTPUT_ROOT / "strategy_e2nd_derivatives_f1_pivot.csv"
        pivot.to_csv(pivot_csv, index=False)
        print(f"\nF1 pivot saved -> {pivot_csv}")


if __name__ == "__main__":
    main()
