from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import mne
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_VENDORED_AUTOREJECT = REPO_ROOT / "autoreject"
if str(_VENDORED_AUTOREJECT) not in sys.path:
    sys.path.insert(0, str(_VENDORED_AUTOREJECT))

_PAIRS_SPEC = importlib.util.spec_from_file_location(
    "extract_annotation_fif_pair",
    REPO_ROOT / "src_project_development" / "extract_annotation_fif_pair.py",
)
_PAIRS_MOD = importlib.util.module_from_spec(_PAIRS_SPEC)  # type: ignore[arg-type]
_PAIRS_SPEC.loader.exec_module(_PAIRS_MOD)  # type: ignore[union-attr]
find_pairs = _PAIRS_MOD.find_pairs

_REPORT_22_SPEC = importlib.util.spec_from_file_location(
    "strategy_comparison_batch",
    REPO_ROOT / "tutorial" / "22_strategy_comparison_batch.py",
)
_REPORT_22_MOD = importlib.util.module_from_spec(_REPORT_22_SPEC)  # type: ignore[arg-type]
_REPORT_22_SPEC.loader.exec_module(_REPORT_22_MOD)  # type: ignore[union-attr]

_REPORT_27_SPEC = importlib.util.spec_from_file_location(
    "strategy_e_expand_bridge_derivatives_batch",
    REPO_ROOT / "tutorial" / "27_strategy_e_expand_bridge_derivatives_batch.py",
)
_REPORT_27_MOD = importlib.util.module_from_spec(_REPORT_27_SPEC)  # type: ignore[arg-type]
_REPORT_27_SPEC.loader.exec_module(_REPORT_27_MOD)  # type: ignore[union-attr]

from pyblinker.blinker.default_setting import SCALING_FACTOR
from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    epoch_detection_strategy_c_autoreject,
)
from pyblinker.fitutils import mad as compute_mad

DEFAULT_SEGMENT = "S01_20170519_043933"
DEFAULT_SUBJECT = "S1"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
OUTPUT_ROOT = REPO_ROOT / "experiment_output" / "single_pair_sw_onset_debug"
DEFAULT_STRATEGY = "expand_bridge_sw_onset_soft_gate"
REPORT_TOP10_SINGLE_CHANNEL = [
    {
        "rank": 1,
        "strategy": "expand_bridge_sw_onset",
        "report_f1": 0.6762,
        "report_recall": 0.7225,
        "source": "tutorial/report_first_iteration.md",
        "note": "Best report F1; cleaner onset with expand+bridge recovery.",
    },
    {
        "rank": 2,
        "strategy": "expand_bridge_adaptive_k",
        "report_f1": 0.6734,
        "report_recall": 0.7393,
        "source": "tutorial/report_first_iteration.md",
        "note": "Best recall/F1 balance among 4th-iteration variants.",
    },
    {
        "rank": 3,
        "strategy": "expand_bridge_soft_gate",
        "report_f1": 0.6731,
        "report_recall": 0.7376,
        "source": "tutorial/report_first_iteration.md",
        "note": "Soft amplitude gate trims the weak-FP tail.",
    },
    {
        "rank": 4,
        "strategy": "strategy_e_expand_bridge",
        "report_f1": 0.6592,
        "report_recall": 0.7460,
        "source": "tutorial/report_first_iteration.md",
        "note": "Best recall among strong-F1 single-channel candidates.",
    },
    {
        "rank": 5,
        "strategy": "strategy_e_sliding_window",
        "report_f1": 0.6587,
        "report_recall": 0.7198,
        "source": "tutorial/report_first_iteration.md",
        "note": "Low-FP onset cleaner from the report shortlist.",
    },
    {
        "rank": 6,
        "strategy": "expand_bridge_dynamic_low",
        "report_f1": 0.6585,
        "report_recall": 0.7453,
        "source": "tutorial/report_first_iteration.md",
        "note": "Noise-aware expansion threshold.",
    },
    {
        "rank": 7,
        "strategy": "expand_bridge_dynamic_gap",
        "report_f1": 0.6576,
        "report_recall": 0.7424,
        "source": "tutorial/report_first_iteration.md",
        "note": "Strength-aware gap bridging.",
    },
    {
        "rank": 8,
        "strategy": "strategy_e13_self_train",
        "report_f1": 0.6531,
        "report_recall": 0.7394,
        "source": "tutorial/report_first_iteration.md",
        "note": "Self-trained amplitude gate with permissive second pass.",
    },
    {
        "rank": 9,
        "strategy": "strategy_e_adaptive_k",
        "report_f1": 0.6530,
        "report_recall": 0.7347,
        "source": "tutorial/report_first_iteration.md",
        "note": "Adaptive threshold scaling without expand+bridge.",
    },
    {
        "rank": 10,
        "strategy": "strategy_e12_amp_filter",
        "report_f1": 0.6512,
        "report_recall": 0.7059,
        "source": "tutorial/report_first_iteration.md",
        "note": "Background-refit candidates with bottom-15% amplitude pruning.",
    },
]
IMPLEMENTED_STRATEGIES = {
    "expand_bridge_sw_onset",
    "expand_bridge_adaptive_k",
    "expand_bridge_soft_gate",
    "expand_bridge_sw_onset_soft_gate",
    "expand_bridge_adaptive_k_soft_gate",
    "expand_bridge_dynamic_low",
    "expand_bridge_dynamic_gap",
}
STRATEGY_C_CHANNELS = ("__NO_BACKBONE__",)
REPORT_TOP10_RUNNER_MAP = {
    "expand_bridge_sw_onset": _REPORT_27_MOD.run_expand_bridge_sw_onset,
    "expand_bridge_adaptive_k": _REPORT_27_MOD.run_expand_bridge_adaptive_k,
    "expand_bridge_soft_gate": _REPORT_27_MOD.run_expand_bridge_soft_gate,
    "strategy_e_expand_bridge": _REPORT_22_MOD.run_strategy_e_expand_bridge,
    "strategy_e_sliding_window": _REPORT_22_MOD.run_strategy_e_sliding_window,
    "expand_bridge_dynamic_low": _REPORT_27_MOD.run_expand_bridge_dynamic_low,
    "expand_bridge_dynamic_gap": _REPORT_27_MOD.run_expand_bridge_dynamic_gap,
    "strategy_e13_self_train": _REPORT_22_MOD.run_strategy_e13_self_train,
    "strategy_e_adaptive_k": _REPORT_22_MOD.run_strategy_e_adaptive_k,
    "strategy_e12_amp_filter": _REPORT_22_MOD.run_strategy_e12_amp_filter,
}


@dataclass(frozen=True)
class DetectorParams:
    variant: str = DEFAULT_STRATEGY
    onset_mode: str = "sw_core"
    window_s: float = 2.0
    k_open: float = 1.5
    k_close: float = 0.8
    k_low: float = 0.5
    bridge_gap_ms: float = 80.0
    min_event_len_s: float = 0.05
    use_global_floor: bool = True
    soft_gate_cons_k: float = 2.0
    soft_gate_min_confident: int = 5
    soft_gate_mad_mult: float = 2.0
    adaptive_k_min: float = 1.0
    adaptive_k_max: float = 2.5
    dynamic_low_k_min: float = 0.2
    dynamic_low_k_max: float = 1.0
    dynamic_gap_strong_ms: float = 100.0
    dynamic_gap_weak_ms: float = 40.0
    dynamic_gap_strong_k: float = 0.5


@dataclass(frozen=True)
class FusionParams:
    cluster_tol_s: float = 0.10
    min_support: int = 1
    min_peak_z: float = 0.0
    representative: str = "median"


@dataclass
class Metrics:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    epoch_blink_agreement: float
    blink_count_agreement: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--segment", default=DEFAULT_SEGMENT)
    parser.add_argument("--strategy", default=DEFAULT_STRATEGY, choices=sorted(IMPLEMENTED_STRATEGIES))
    parser.add_argument("--target-f1", type=float, default=0.90)
    parser.add_argument("--top-channels", type=int, default=4)
    parser.add_argument("--output-stamp", default=None)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def setup_logger(out_dir: Path, level_name: str) -> logging.Logger:
    logger = logging.getLogger("single_pair_single_channel_debug")
    logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    file_handler = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def build_report_top10_candidates() -> pd.DataFrame:
    rows: list[dict] = []
    for entry in REPORT_TOP10_SINGLE_CHANNEL:
        rows.append(
            {
                **entry,
                "implemented_in_single_pair_runner": entry["strategy"] in IMPLEMENTED_STRATEGIES,
            }
        )
    return pd.DataFrame(rows)


def default_report_params(strategy: str) -> DetectorParams:
    if strategy == "expand_bridge_sw_onset":
        return DetectorParams(variant=strategy, window_s=2.0, k_open=1.5, k_low=0.5, bridge_gap_ms=80.0)
    if strategy == "expand_bridge_adaptive_k":
        return DetectorParams(variant=strategy, k_open=1.5, k_low=0.5, bridge_gap_ms=80.0)
    if strategy == "expand_bridge_soft_gate":
        return DetectorParams(
            variant=strategy,
            k_open=1.5,
            k_low=0.5,
            bridge_gap_ms=80.0,
            soft_gate_cons_k=2.0,
            soft_gate_mad_mult=2.0,
        )
    if strategy == "expand_bridge_dynamic_low":
        return DetectorParams(variant=strategy, k_open=1.5, k_low=0.5, bridge_gap_ms=80.0)
    if strategy == "expand_bridge_dynamic_gap":
        return DetectorParams(variant=strategy, k_open=1.5, k_low=0.5, bridge_gap_ms=80.0)
    raise ValueError(f"No detailed parameter map for strategy: {strategy}")


def load_brain_region_channels(yaml_path: Path) -> list[str]:
    with yaml_path.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    channels: list[str] = []
    for region_channels in config["eeg_regions"].values():
        channels.extend(region_channels)
    return channels


def find_target_pair(subject: str, segment: str) -> dict:
    for pair in find_pairs():
        if pair["subject"] == subject and pair["segment"] == segment:
            return pair
    raise FileNotFoundError(f"Pair not found for {subject}/{segment}")


def load_raw_with_brain_channels(
    fif_path: Path,
    brain_channels: list[str],
    logger: logging.Logger,
) -> mne.io.BaseRaw:
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    available = [ch for ch in brain_channels if ch in raw.ch_names]
    missing = [ch for ch in brain_channels if ch not in raw.ch_names]
    if missing:
        logger.warning("Channels in YAML but absent in file: %s", missing)
    raw.pick(available)
    return raw


def make_fixed_epochs(raw: mne.io.BaseRaw, duration: float = EPOCH_DURATION_S) -> mne.Epochs:
    return mne.make_fixed_length_epochs(raw, duration=duration, preload=True, verbose="ERROR")


def load_annotation_as_reference(
    csv_path: Path,
    epoch_duration: float = EPOCH_DURATION_S,
) -> pd.DataFrame:
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
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


def interval_overlap_ratio(
    pred_onset: float,
    pred_duration: float,
    ref_onset: float,
    ref_duration: float,
) -> float:
    pred_end = pred_onset + max(float(pred_duration), 0.0)
    ref_end = ref_onset + max(float(ref_duration), 0.0)
    overlap = max(0.0, min(pred_end, ref_end) - max(pred_onset, ref_onset))
    denom = max(min(pred_end - pred_onset, ref_end - ref_onset), 1e-12)
    return overlap / denom


def event_match(
    pred_row: pd.Series,
    ref_row: pd.Series,
    onset_tolerance_s: float = 0.1,
    duration_tolerance_s: float = 0.1,
    overlap_threshold: float = 0.5,
) -> bool:
    onset_diff = abs(float(pred_row["blink_onset"]) - float(ref_row["blink_onset"]))
    duration_diff = abs(float(pred_row["blink_duration"]) - float(ref_row["blink_duration"]))
    overlap = interval_overlap_ratio(
        float(pred_row["blink_onset"]),
        float(pred_row["blink_duration"]),
        float(ref_row["blink_onset"]),
        float(ref_row["blink_duration"]),
    )
    return onset_diff <= onset_tolerance_s and (
        duration_diff <= duration_tolerance_s or overlap >= overlap_threshold
    )


def match_blink_tables_detailed(
    predicted: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    n_epochs: int,
) -> tuple[Metrics, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predicted = predicted.copy().reset_index(drop=True)
    reference = reference.copy().reset_index(drop=True)
    predicted["pred_index"] = predicted.index
    reference["ref_index"] = reference.index

    match_rows: list[dict] = []
    pred_status_rows: list[dict] = []
    ref_status_rows: list[dict] = []
    tp = 0
    fp = 0
    fn = 0

    epoch_indices = sorted(
        set(predicted.get("epoch_index", pd.Series(dtype=int)).tolist())
        | set(reference.get("epoch_index", pd.Series(dtype=int)).tolist())
    )

    for epoch_index in epoch_indices:
        pred_group = predicted[predicted["epoch_index"] == epoch_index].copy()
        ref_group = reference[reference["epoch_index"] == epoch_index].copy()
        unmatched_ref = set(ref_group.index.tolist())

        for _, pred_row in pred_group.sort_values("blink_onset").iterrows():
            best_key = None
            best_ref_index = None
            for ref_index in list(unmatched_ref):
                ref_row = ref_group.loc[ref_index]
                if not event_match(pred_row, ref_row):
                    continue
                key = (
                    abs(float(pred_row["blink_onset"]) - float(ref_row["blink_onset"]))
                    + abs(float(pred_row["blink_duration"]) - float(ref_row["blink_duration"])),
                    ref_index,
                )
                if best_key is None or key < best_key:
                    best_key = key
                    best_ref_index = ref_index

            if best_ref_index is None:
                fp += 1
                pred_status_rows.append(
                    {
                        **pred_row.to_dict(),
                        "match_status": "fp",
                        "matched_ref_index": np.nan,
                    }
                )
                continue

            unmatched_ref.remove(best_ref_index)
            ref_row = ref_group.loc[best_ref_index]
            tp += 1
            overlap = interval_overlap_ratio(
                float(pred_row["blink_onset"]),
                float(pred_row["blink_duration"]),
                float(ref_row["blink_onset"]),
                float(ref_row["blink_duration"]),
            )
            match_rows.append(
                {
                    "epoch_index": int(epoch_index),
                    "pred_index": int(pred_row["pred_index"]),
                    "ref_index": int(ref_row["ref_index"]),
                    "pred_onset": float(pred_row["blink_onset"]),
                    "pred_duration": float(pred_row["blink_duration"]),
                    "ref_onset": float(ref_row["blink_onset"]),
                    "ref_duration": float(ref_row["blink_duration"]),
                    "onset_diff_s": float(pred_row["blink_onset"] - ref_row["blink_onset"]),
                    "duration_diff_s": float(pred_row["blink_duration"] - ref_row["blink_duration"]),
                    "overlap_ratio": float(overlap),
                }
            )
            pred_status_rows.append(
                {
                    **pred_row.to_dict(),
                    "match_status": "tp",
                    "matched_ref_index": int(ref_row["ref_index"]),
                }
            )
            ref_status_rows.append(
                {
                    **ref_row.to_dict(),
                    "match_status": "tp",
                    "matched_pred_index": int(pred_row["pred_index"]),
                }
            )

        for ref_index in sorted(unmatched_ref):
            ref_row = ref_group.loc[ref_index]
            fn += 1
            ref_status_rows.append(
                {
                    **ref_row.to_dict(),
                    "match_status": "fn",
                    "matched_pred_index": np.nan,
                }
            )

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    pred_epoch_counts = predicted.groupby("epoch_index").size().reindex(range(n_epochs), fill_value=0)
    ref_epoch_counts = reference.groupby("epoch_index").size().reindex(range(n_epochs), fill_value=0)
    metrics = Metrics(
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        epoch_blink_agreement=float((pred_epoch_counts.gt(0) == ref_epoch_counts.gt(0)).mean()),
        blink_count_agreement=float((pred_epoch_counts == ref_epoch_counts).mean()),
    )

    pred_status = pd.DataFrame(pred_status_rows)
    if pred_status.empty:
        pred_status = pd.DataFrame(columns=list(predicted.columns) + ["match_status", "matched_ref_index"])
    ref_status = pd.DataFrame(ref_status_rows)
    if ref_status.empty:
        ref_status = pd.DataFrame(columns=list(reference.columns) + ["match_status", "matched_pred_index"])
    matches = pd.DataFrame(match_rows)
    if matches.empty:
        matches = pd.DataFrame(
            columns=[
                "epoch_index",
                "pred_index",
                "ref_index",
                "pred_onset",
                "pred_duration",
                "ref_onset",
                "ref_duration",
                "onset_diff_s",
                "duration_diff_s",
                "overlap_ratio",
            ]
        )
    return metrics, pred_status, ref_status, matches


def rolling_mad_threshold(signal: np.ndarray, win_frames: int, k_open: float, gfloor: float) -> np.ndarray:
    series = pd.Series(signal)
    roll_med = series.rolling(window=win_frames, center=True, min_periods=1).median()
    abs_dev = (series - roll_med).abs()
    roll_mad = abs_dev.rolling(window=win_frames, center=True, min_periods=1).median()
    threshold = roll_med.values + k_open * SCALING_FACTOR * roll_mad.values
    return np.maximum(threshold, gfloor)


def scan_threshold_crossings(
    signal: np.ndarray,
    threshold: float,
    min_frames: float,
) -> list[tuple[int, int]]:
    above = signal > threshold
    if not above.any():
        return []
    padded = np.concatenate([[False], above, [False]])
    diff = np.diff(padded.astype(np.int8))
    onsets = np.where(diff == 1)[0]
    offsets = np.where(diff == -1)[0]
    return [(int(on), int(off)) for on, off in zip(onsets, offsets) if (off - on) > min_frames]


def expand_interval(signal: np.ndarray, start: int, end: int, t_low: float) -> tuple[int, int]:
    start_i = int(start)
    end_i = int(end)
    n_samples = len(signal)
    while start_i > 0 and signal[start_i - 1] > t_low:
        start_i -= 1
    while end_i < n_samples and signal[end_i] > t_low:
        end_i += 1
    return start_i, end_i


def merge_intervals(intervals: list[tuple[int, int]], gap_frames: int) -> list[tuple[int, int]]:
    if not intervals:
        return []
    sorted_ivs = sorted(intervals)
    merged: list[list[int]] = [[sorted_ivs[0][0], sorted_ivs[0][1]]]
    for start, end in sorted_ivs[1:]:
        if start <= merged[-1][1] + gap_frames:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(int(start), int(end)) for start, end in merged]


def merge_intervals_conditional(
    intervals: list[tuple[int, int]],
    is_strong: list[bool],
    gap_strong_frames: int,
    gap_weak_frames: int,
) -> list[tuple[int, int]]:
    if not intervals:
        return []
    paired = sorted(zip(intervals, is_strong), key=lambda item: item[0][0])
    merged: list[tuple[tuple[int, int], bool]] = [(paired[0][0], paired[0][1])]
    for curr_iv, curr_strong in paired[1:]:
        prev_iv, prev_strong = merged[-1]
        max_gap = gap_strong_frames if (prev_strong and curr_strong) else gap_weak_frames
        if curr_iv[0] <= prev_iv[1] + max_gap:
            merged[-1] = ((prev_iv[0], max(prev_iv[1], curr_iv[1])), prev_strong or curr_strong)
        else:
            merged.append((curr_iv, curr_strong))
    return [interval for interval, _ in merged]


def compute_global_floors(prepared, valid_epoch_indices: list[int]) -> dict[int, float]:
    floors: dict[int, float] = {}
    for ch_idx in range(len(prepared.channel_names)):
        concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
        floors[ch_idx] = float(np.mean(concat)) + 1.5 * SCALING_FACTOR * float(compute_mad(concat))
    return floors


def detect_sw_onset_channel(
    prepared,
    ch_idx: int,
    valid_epoch_indices: list[int],
    params: DetectorParams,
    global_floors: dict[int, float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sfreq = float(prepared.sfreq)
    min_frames = params.min_event_len_s * sfreq
    win_frames = max(1, int(params.window_s * sfreq))
    bridge_frames = int(params.bridge_gap_ms * sfreq / 1000.0)
    gfloor = global_floors[ch_idx] if params.use_global_floor else -np.inf
    channel_name = prepared.channel_names[ch_idx]
    variant = params.variant
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    ep_mads = [
        SCALING_FACTOR * float(compute_mad(prepared.data[epoch_idx, ch_idx, :].astype(float)))
        for epoch_idx in valid_epoch_indices
    ]
    quiet_mad = float(np.percentile(ep_mads, 25)) if ep_mads else global_mad
    adaptive_ratio = global_mad / (quiet_mad + 1e-12)
    adaptive_k = float(np.clip(params.k_open * adaptive_ratio, params.adaptive_k_min, params.adaptive_k_max))
    adaptive_global_floor = global_mean + adaptive_k * global_mad

    amp_gate = -np.inf
    if "soft_gate" in variant:
        confident_peaks: list[float] = []
        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
            ep_median = float(np.median(signal))
            ep_mad = SCALING_FACTOR * float(compute_mad(signal))
            if "sw_onset" in variant:
                conservative_threshold = rolling_mad_threshold(signal, win_frames, params.soft_gate_cons_k, gfloor)
                conservative_candidates = scan_threshold_crossings(signal, float(np.min(conservative_threshold)), min_frames)
                if conservative_candidates:
                    mask = signal > conservative_threshold
                    padded = np.concatenate([[False], mask, [False]])
                    diff = np.diff(padded.astype(np.int8))
                    onsets = np.where(diff == 1)[0]
                    offsets = np.where(diff == -1)[0]
                    conservative_candidates = [
                        (int(on), int(off)) for on, off in zip(onsets, offsets) if (off - on) > min_frames
                    ]
            else:
                cons_k = max(adaptive_k, params.soft_gate_cons_k) if "adaptive_k" in variant else params.soft_gate_cons_k
                cons_floor = adaptive_global_floor if "adaptive_k" in variant else gfloor
                t_cons = max(ep_median + cons_k * ep_mad, cons_floor)
                conservative_candidates = scan_threshold_crossings(signal, t_cons, min_frames)
            for start, end in conservative_candidates:
                if end > start:
                    confident_peaks.append(float(np.max(signal[start:end])))
        if len(confident_peaks) >= params.soft_gate_min_confident:
            peaks_arr = np.array(confident_peaks, dtype=float)
            peak_med = float(np.median(peaks_arr))
            peak_mad = SCALING_FACTOR * float(compute_mad(peaks_arr))
            amp_gate = max(peak_med - params.soft_gate_mad_mult * peak_mad, gfloor)
        else:
            amp_gate = gfloor

    candidate_rows: list[dict] = []
    event_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        t_low = ep_median + params.k_low * ep_mad

        if variant in {"expand_bridge_sw_onset", "expand_bridge_sw_onset_soft_gate"}:
            threshold = rolling_mad_threshold(signal, win_frames, params.k_open, gfloor)
            initial_candidates = []
            above = signal > threshold
            if above.any():
                padded = np.concatenate([[False], above, [False]])
                diff = np.diff(padded.astype(np.int8))
                onsets = np.where(diff == 1)[0]
                offsets = np.where(diff == -1)[0]
                initial_candidates = [
                    (int(on), int(off)) for on, off in zip(onsets, offsets) if (off - on) > min_frames
                ]
        elif variant in {"expand_bridge_adaptive_k", "expand_bridge_adaptive_k_soft_gate"}:
            t_high = max(ep_median + adaptive_k * ep_mad, adaptive_global_floor)
            initial_candidates = scan_threshold_crossings(signal, t_high, min_frames)
        else:
            t_high = max(ep_median + params.k_open * ep_mad, gfloor)
            initial_candidates = scan_threshold_crossings(signal, t_high, min_frames)

        if not initial_candidates:
            continue

        if variant == "expand_bridge_dynamic_low":
            noise_ratio = ep_mad / (global_mad + 1e-12)
            k_low_adj = float(np.clip(params.k_low * noise_ratio, params.dynamic_low_k_min, params.dynamic_low_k_max))
            t_low = ep_median + k_low_adj * ep_mad

        expanded = [expand_interval(signal, start, end, t_low) for start, end in initial_candidates]
        if variant == "expand_bridge_dynamic_gap":
            t_high = max(ep_median + params.k_open * ep_mad, gfloor)
            t_strong = t_high + params.dynamic_gap_strong_k * ep_mad
            gap_strong_frames = int(params.dynamic_gap_strong_ms * sfreq / 1000.0)
            gap_weak_frames = int(params.dynamic_gap_weak_ms * sfreq / 1000.0)
            is_strong = [
                (float(np.max(signal[start:end])) if end > start else t_high) >= t_strong
                for start, end in expanded
            ]
            merged_events = merge_intervals_conditional(expanded, is_strong, gap_strong_frames, gap_weak_frames)
        else:
            merged_events = merge_intervals(expanded, bridge_frames)

        for start, end in merged_events:
            peak = float(np.max(signal[start:end])) if end > start else float(signal[start])
            peak_z = float((peak - ep_median) / (ep_mad + 1e-12))
            if peak < amp_gate:
                continue
            onset_s = start / sfreq
            duration_s = (end - start) / sfreq
            candidate_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "blink_onset": onset_s,
                    "blink_duration": duration_s,
                }
            )
            event_rows.append(
                {
                    "epoch_index": epoch_idx,
                    "channel": channel_name,
                    "channel_index": ch_idx,
                    "strategy": variant,
                    "start_sample": int(start),
                    "end_sample": int(end),
                    "blink_onset": onset_s,
                    "blink_duration": duration_s,
                    "peak": peak,
                    "peak_z": peak_z,
                }
            )

    candidates = pd.DataFrame(candidate_rows, columns=["epoch_index", "channel", "blink_onset", "blink_duration"])
    if not candidates.empty:
        candidates = candidates.sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)
    events = pd.DataFrame(event_rows)
    if not events.empty:
        events = events.sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)
    return candidates, events


def fuse_channel_events(events: pd.DataFrame, fusion_params: FusionParams) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["epoch_index", "channel", "blink_onset", "blink_duration", "support", "peak_z"])

    fused_rows: list[dict] = []
    tol_s = float(fusion_params.cluster_tol_s)
    for epoch_index, epoch_events in events.groupby("epoch_index", sort=True):
        rows = epoch_events.sort_values("blink_onset").to_dict("records")
        cluster: list[dict] = []

        def flush_cluster(cluster_rows: list[dict]) -> None:
            if not cluster_rows:
                return
            support = len({row["channel"] for row in cluster_rows})
            max_peak_z = max(float(row["peak_z"]) for row in cluster_rows)
            if support < fusion_params.min_support or max_peak_z < fusion_params.min_peak_z:
                return
            if fusion_params.representative == "best_peak":
                chosen = max(cluster_rows, key=lambda row: float(row["peak_z"]))
                onset_s = float(chosen["blink_onset"])
                duration_s = float(chosen["blink_duration"])
            else:
                onset_s = float(np.median([float(row["blink_onset"]) for row in cluster_rows]))
                duration_s = float(np.median([float(row["blink_duration"]) for row in cluster_rows]))
            fused_rows.append(
                {
                    "epoch_index": int(epoch_index),
                    "channel": "fused_sw_onset",
                    "blink_onset": onset_s,
                    "blink_duration": duration_s,
                    "support": int(support),
                    "peak_z": max_peak_z,
                    "member_channels": ",".join(sorted({str(row["channel"]) for row in cluster_rows})),
                }
            )

        for row in rows:
            if not cluster:
                cluster = [row]
                continue
            last = cluster[-1]
            close_in_time = abs(float(row["blink_onset"]) - float(last["blink_onset"])) <= tol_s
            overlaps = float(row["blink_onset"]) <= float(last["blink_onset"]) + float(last["blink_duration"]) + tol_s
            if close_in_time or overlaps:
                cluster.append(row)
            else:
                flush_cluster(cluster)
                cluster = [row]
        flush_cluster(cluster)

    fused = pd.DataFrame(fused_rows)
    if not fused.empty:
        fused = fused.sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)
    return fused


def score_candidates(
    predicted: pd.DataFrame,
    reference: pd.DataFrame,
    n_epochs: int,
) -> tuple[Metrics, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return match_blink_tables_detailed(predicted, reference, n_epochs=n_epochs)


def evaluate_channel(
    prepared,
    ch_idx: int,
    valid_epoch_indices: list[int],
    reference: pd.DataFrame,
    params: DetectorParams,
    global_floors: dict[int, float],
) -> dict:
    candidates, events = detect_sw_onset_channel(prepared, ch_idx, valid_epoch_indices, params, global_floors)
    metrics, pred_status, ref_status, matches = score_candidates(candidates, reference, len(prepared.data))
    return {
        "mode": "single_channel",
        "channel": prepared.channel_names[ch_idx],
        "channels_used": prepared.channel_names[ch_idx],
        "detector_params": asdict(params),
        "fusion_params": None,
        "candidates": candidates,
        "events": events,
        "metrics": metrics,
        "pred_status": pred_status,
        "ref_status": ref_status,
        "matches": matches,
    }


def evaluate_fused_channels(
    selected_events: pd.DataFrame,
    reference: pd.DataFrame,
    n_epochs: int,
    detector_params_by_channel: dict[str, DetectorParams],
    fusion_params: FusionParams,
) -> dict:
    candidates = fuse_channel_events(selected_events, fusion_params)
    metrics, pred_status, ref_status, matches = score_candidates(candidates, reference, n_epochs)
    return {
        "mode": "fused",
        "channel": "fused_sw_onset",
        "channels_used": ",".join(sorted(detector_params_by_channel)),
        "detector_params": {k: asdict(v) for k, v in detector_params_by_channel.items()},
        "fusion_params": asdict(fusion_params),
        "candidates": candidates,
        "events": selected_events,
        "metrics": metrics,
        "pred_status": pred_status,
        "ref_status": ref_status,
        "matches": matches,
    }


def result_to_row(result: dict) -> dict:
    metrics: Metrics = result["metrics"]
    return {
        "strategy": result["detector_params"].get("variant", ""),
        "mode": result["mode"],
        "channel": result["channel"],
        "channels_used": result["channels_used"],
        "tp": metrics.tp,
        "fp": metrics.fp,
        "fn": metrics.fn,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "epoch_blink_agreement": metrics.epoch_blink_agreement,
        "blink_count_agreement": metrics.blink_count_agreement,
        "detector_params_json": json.dumps(result["detector_params"], sort_keys=True),
        "fusion_params_json": json.dumps(result["fusion_params"], sort_keys=True) if result["fusion_params"] is not None else "",
    }


def is_better_result(candidate: dict, incumbent: dict | None) -> bool:
    if incumbent is None:
        return True
    c = candidate["metrics"]
    i = incumbent["metrics"]
    candidate_key = (c.f1, c.precision, c.recall, -c.fp, c.tp)
    incumbent_key = (i.f1, i.precision, i.recall, -i.fp, i.tp)
    return candidate_key > incumbent_key


def iter_strategy_params(strategy: str) -> list[DetectorParams]:
    if strategy not in IMPLEMENTED_STRATEGIES:
        raise ValueError(f"Unsupported strategy: {strategy}")

    windows = [1.0, 1.5, 2.0]
    k_open_values = [1.5, 1.8, 2.0]
    k_low_values = [0.3, 0.5, 0.8]
    bridge_values = [40.0, 80.0, 120.0]
    soft_gate_cons_values = [1.8, 2.0, 2.2]
    soft_gate_mad_values = [1.5, 2.0, 2.5]

    params_list: list[DetectorParams] = []
    if strategy == "expand_bridge_sw_onset":
        for window_s, k_open, k_low, bridge_gap_ms in itertools.product(
            windows, k_open_values, k_low_values, bridge_values
        ):
            params_list.append(
                DetectorParams(
                    variant=strategy,
                    onset_mode="sw_core",
                    window_s=window_s,
                    k_open=k_open,
                    k_low=k_low,
                    bridge_gap_ms=bridge_gap_ms,
                )
            )
    elif strategy == "expand_bridge_sw_onset_soft_gate":
        for window_s, k_open, k_low, bridge_gap_ms, soft_gate_cons_k, soft_gate_mad_mult in itertools.product(
            windows,
            k_open_values,
            k_low_values,
            bridge_values,
            soft_gate_cons_values,
            soft_gate_mad_values,
        ):
            params_list.append(
                DetectorParams(
                    variant=strategy,
                    onset_mode="sw_core",
                    window_s=window_s,
                    k_open=k_open,
                    k_low=k_low,
                    bridge_gap_ms=bridge_gap_ms,
                    soft_gate_cons_k=soft_gate_cons_k,
                    soft_gate_mad_mult=soft_gate_mad_mult,
                )
            )
    elif strategy == "expand_bridge_adaptive_k":
        for k_open, k_low, bridge_gap_ms in itertools.product(k_open_values, k_low_values, bridge_values):
            params_list.append(
                DetectorParams(
                    variant=strategy,
                    k_open=k_open,
                    k_low=k_low,
                    bridge_gap_ms=bridge_gap_ms,
                )
            )
    elif strategy == "expand_bridge_adaptive_k_soft_gate":
        for k_open, k_low, bridge_gap_ms, soft_gate_cons_k, soft_gate_mad_mult in itertools.product(
            k_open_values, k_low_values, bridge_values, soft_gate_cons_values, soft_gate_mad_values
        ):
            params_list.append(
                DetectorParams(
                    variant=strategy,
                    k_open=k_open,
                    k_low=k_low,
                    bridge_gap_ms=bridge_gap_ms,
                    soft_gate_cons_k=soft_gate_cons_k,
                    soft_gate_mad_mult=soft_gate_mad_mult,
                )
            )
    elif strategy == "expand_bridge_soft_gate":
        for k_open, k_low, bridge_gap_ms, soft_gate_cons_k, soft_gate_mad_mult in itertools.product(
            k_open_values, k_low_values, bridge_values, soft_gate_cons_values, soft_gate_mad_values
        ):
            params_list.append(
                DetectorParams(
                    variant=strategy,
                    k_open=k_open,
                    k_low=k_low,
                    bridge_gap_ms=bridge_gap_ms,
                    soft_gate_cons_k=soft_gate_cons_k,
                    soft_gate_mad_mult=soft_gate_mad_mult,
                )
            )
    elif strategy == "expand_bridge_dynamic_low":
        for k_open, k_low, bridge_gap_ms in itertools.product(k_open_values, k_low_values, bridge_values):
            params_list.append(
                DetectorParams(
                    variant=strategy,
                    k_open=k_open,
                    k_low=k_low,
                    bridge_gap_ms=bridge_gap_ms,
                )
            )
    elif strategy == "expand_bridge_dynamic_gap":
        for k_open, k_low, bridge_gap_ms, strong_ms, weak_ms in itertools.product(
            k_open_values,
            k_low_values,
            bridge_values,
            [80.0, 100.0, 120.0],
            [20.0, 40.0, 60.0],
        ):
            params_list.append(
                DetectorParams(
                    variant=strategy,
                    k_open=k_open,
                    k_low=k_low,
                    bridge_gap_ms=bridge_gap_ms,
                    dynamic_gap_strong_ms=strong_ms,
                    dynamic_gap_weak_ms=weak_ms,
                )
            )
    return params_list


def tune_selected_strategy(
    prepared,
    strategy: str,
    valid_epoch_indices: list[int],
    reference: pd.DataFrame,
    global_floors: dict[int, float],
    logger: logging.Logger,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict]]:
    trial_rows: list[dict] = []
    best_rows: list[dict] = []
    best_by_channel: dict[str, dict] = {}
    params_to_try = iter_strategy_params(strategy)

    logger.info("Selected strategy: %s (%d parameter combinations per channel)", strategy, len(params_to_try))
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        logger.info("Scanning %s on channel %s", strategy, channel_name)
        best_result: dict | None = None
        for params in params_to_try:
            result = evaluate_channel(prepared, ch_idx, valid_epoch_indices, reference, params, global_floors)
            trial_rows.append(result_to_row(result))
            if is_better_result(result, best_result):
                best_result = result
                logger.info(
                    "  new best %s | strategy=%s window=%.2f k_open=%.2f k_low=%.2f bridge=%.0f soft_cons=%.2f soft_mad=%.2f -> P=%.3f R=%.3f F1=%.3f",
                    channel_name,
                    strategy,
                    params.window_s,
                    params.k_open,
                    params.k_low,
                    params.bridge_gap_ms,
                    params.soft_gate_cons_k,
                    params.soft_gate_mad_mult,
                    result["metrics"].precision,
                    result["metrics"].recall,
                    result["metrics"].f1,
                )
        if best_result is None:
            continue
        best_by_channel[channel_name] = best_result
        best_rows.append(result_to_row(best_result))

    trials_df = pd.DataFrame(trial_rows).sort_values(["f1", "precision", "recall"], ascending=False).reset_index(drop=True)
    best_df = pd.DataFrame(best_rows).sort_values(["f1", "precision", "recall"], ascending=False).reset_index(drop=True)
    return trials_df, best_df, best_by_channel


def rerun_report_top10(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
    out_dir: Path,
    logger: logging.Logger,
) -> pd.DataFrame:
    report_rows: list[dict] = []
    for entry in REPORT_TOP10_SINGLE_CHANNEL:
        strategy = entry["strategy"]
        logger.info("Re-running report top-10 candidate %s", strategy)
        try:
            summary, _ = REPORT_TOP10_RUNNER_MAP[strategy](epochs, reference, valid_epoch_indices, out_dir)
            if summary.empty:
                report_rows.append({**entry, "best_channel": "", "tp": 0, "fp": 0, "fn": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "error": "empty_summary"})
                continue
            best = summary.iloc[0]
            report_rows.append(
                {
                    **entry,
                    "best_channel": str(best["channel"]),
                    "tp": int(best["tp"]),
                    "fp": int(best["fp"]),
                    "fn": int(best["fn"]),
                    "precision": float(best["precision"]),
                    "recall": float(best["recall"]),
                    "f1": float(best["f1"]),
                    "error": "",
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed while re-running %s", strategy)
            report_rows.append({**entry, "best_channel": "", "tp": 0, "fp": 0, "fn": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "error": str(exc)})

    return pd.DataFrame(report_rows).sort_values(["f1", "recall", "report_f1"], ascending=False).reset_index(drop=True)


def run_strategy_c_baseline(
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    valid_epoch_indices: list[int],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        n_jobs=1,
        use_multiprocessing=False,
        stage1_channels=STRATEGY_C_CHANNELS,
        stage1_threshold_scope="per_channel",
        stage1_rescale_threshold=True,
        autoreject_random_state=42,
        autoreject_method=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        autoreject_augment=False,
    )
    prepared = detector.prepare_epoch_data()
    stage1 = detector.run_stage1_candidate_scan(prepared=prepared, valid_epoch_indices=valid_epoch_indices)
    lane_rows: list[dict] = []
    candidate_tables: dict[str, pd.DataFrame] = {}
    for detection in stage1.detections:
        metrics, pred_status, ref_status, matches = match_blink_tables_detailed(
            detection.mapped_candidates,
            reference,
            n_epochs=len(epochs),
        )
        lane_rows.append(
            {
                "channel": detection.channel,
                "candidate_source": detection.candidate_source,
                "threshold": float(detection.threshold),
                "candidate_count": int(len(detection.mapped_candidates)),
                "tp": metrics.tp,
                "fp": metrics.fp,
                "fn": metrics.fn,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1": metrics.f1,
            }
        )
        candidate_tables[detection.channel] = detection.mapped_candidates.copy()
    lane_df = pd.DataFrame(lane_rows).sort_values(["f1", "precision", "recall"], ascending=False).reset_index(drop=True)
    return lane_df, candidate_tables


def apply_interval_postprocess(
    candidates: pd.DataFrame,
    *,
    pre_pad_s: float = 0.0,
    post_pad_s: float = 0.0,
    merge_gap_s: float = 0.0,
    short_event_threshold_s: float | None = None,
    short_pre_pad_s: float | None = None,
    short_post_pad_s: float | None = None,
) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()

    rows: list[dict] = []
    for epoch_index, epoch_rows in candidates.sort_values(["epoch_index", "blink_onset"]).groupby("epoch_index"):
        intervals: list[tuple[float, float]] = []
        for row in epoch_rows.itertuples(index=False):
            duration = float(row.blink_duration)
            event_pre = pre_pad_s
            event_post = post_pad_s
            if short_event_threshold_s is not None and duration <= short_event_threshold_s:
                event_pre = short_pre_pad_s if short_pre_pad_s is not None else event_pre
                event_post = short_post_pad_s if short_post_pad_s is not None else event_post
            start = max(0.0, float(row.blink_onset) - event_pre)
            end = float(row.blink_onset) + duration + event_post
            intervals.append((start, end))
        if not intervals:
            continue
        intervals.sort()
        cur_start, cur_end = intervals[0]
        for start, end in intervals[1:]:
            if start <= cur_end + merge_gap_s:
                cur_end = max(cur_end, end)
            else:
                rows.append({"epoch_index": int(epoch_index), "channel": "strategy_c_repaired", "blink_onset": cur_start, "blink_duration": cur_end - cur_start})
                cur_start, cur_end = start, end
        rows.append({"epoch_index": int(epoch_index), "channel": "strategy_c_repaired", "blink_onset": cur_start, "blink_duration": cur_end - cur_start})
    return pd.DataFrame(rows).sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)


def search_strategy_c_boundary_repair(
    reference: pd.DataFrame,
    n_epochs: int,
    base_candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    trial_rows: list[dict] = []
    best_result: dict | None = None

    for short_thr, short_pre, short_post, long_post, merge_gap in itertools.product(
        [0.08, 0.10, 0.12, 0.15],
        [0.00, 0.02, 0.04],
        [0.02, 0.04, 0.06, 0.08],
        [0.02, 0.04, 0.06, 0.08],
        [0.00, 0.02, 0.04, 0.06, 0.08],
    ):
        repaired = apply_interval_postprocess(
            base_candidates,
            pre_pad_s=0.0,
            post_pad_s=long_post,
            merge_gap_s=merge_gap,
            short_event_threshold_s=short_thr,
            short_pre_pad_s=short_pre,
            short_post_pad_s=short_post,
        )
        metrics, pred_status, ref_status, matches = match_blink_tables_detailed(repaired, reference, n_epochs=n_epochs)
        row = {
            "short_event_threshold_s": short_thr,
            "short_pre_pad_s": short_pre,
            "short_post_pad_s": short_post,
            "long_post_pad_s": long_post,
            "merge_gap_s": merge_gap,
            "tp": metrics.tp,
            "fp": metrics.fp,
            "fn": metrics.fn,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "candidate_count": int(len(repaired)),
        }
        trial_rows.append(row)
        candidate = {
            "params": row,
            "candidates": repaired,
            "metrics": metrics,
            "pred_status": pred_status,
            "ref_status": ref_status,
            "matches": matches,
        }
        if best_result is None or (metrics.f1, metrics.precision, metrics.recall, -metrics.fp, metrics.tp) > (
            best_result["metrics"].f1,
            best_result["metrics"].precision,
            best_result["metrics"].recall,
            -best_result["metrics"].fp,
            best_result["metrics"].tp,
        ):
            best_result = candidate

    if best_result is None:
        raise RuntimeError("No strategy_c boundary-repair trials were generated")
    trials_df = pd.DataFrame(trial_rows).sort_values(["f1", "precision", "recall"], ascending=False).reset_index(drop=True)
    return trials_df, best_result


def investigate_top3_recall_gaps(
    prepared,
    valid_epoch_indices: list[int],
    reference: pd.DataFrame,
    global_floors: dict[int, float],
    rerun_top10_df: pd.DataFrame,
    out_dir: Path,
    logger: logging.Logger,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows: list[dict] = []
    shared_rows: list[dict] = []
    top3 = rerun_top10_df.head(3).copy()

    for strategy in top3["strategy"].tolist():
        try:
            params = default_report_params(strategy)
        except ValueError:
            logger.warning("Skipping detailed recall-gap analysis for unsupported strategy %s", strategy)
            detail_rows.append(
                {
                    "strategy": strategy,
                    "best_channel": "",
                    "tp": 0,
                    "fp": 0,
                    "fn": 0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "missed_reference_count": 0,
                    "top_likely_cause": "unsupported_for_detailed_analysis",
                    "top_likely_cause_count": 0,
                    "missed_references_path": "",
                    "detector_params_json": "",
                }
            )
            continue
        strategy_results: dict[str, dict] = {}
        for ch_idx, channel_name in enumerate(prepared.channel_names):
            result = evaluate_channel(prepared, ch_idx, valid_epoch_indices, reference, params, global_floors)
            strategy_results[channel_name] = result
        best_result = max(strategy_results.values(), key=lambda result: (
            result["metrics"].f1,
            result["metrics"].precision,
            result["metrics"].recall,
            -result["metrics"].fp,
            result["metrics"].tp,
        ))
        all_events = pd.concat([result["events"] for result in strategy_results.values()], ignore_index=True)
        missed_references = analyze_missed_references(best_result, all_events)
        missed_path = out_dir / f"{strategy}_top3_missed_references.csv"
        missed_references.to_csv(missed_path, index=False)
        for _, row in missed_references.iterrows():
            shared_rows.append(
                {
                    "strategy": strategy,
                    "epoch_index": int(row["epoch_index"]),
                    "blink_onset": float(row["blink_onset"]),
                    "blink_duration": float(row["blink_duration"]),
                    "supporting_channel_count": int(row["supporting_channel_count"]),
                    "likely_cause": str(row["likely_cause"]),
                }
            )
        cause_counts = (
            missed_references["likely_cause"].value_counts().to_dict()
            if not missed_references.empty
            else {}
        )
        detail_rows.append(
            {
                "strategy": strategy,
                "best_channel": best_result["channel"],
                "tp": best_result["metrics"].tp,
                "fp": best_result["metrics"].fp,
                "fn": best_result["metrics"].fn,
                "precision": best_result["metrics"].precision,
                "recall": best_result["metrics"].recall,
                "f1": best_result["metrics"].f1,
                "missed_reference_count": int(len(missed_references)),
                "top_likely_cause": max(cause_counts, key=cause_counts.get) if cause_counts else "",
                "top_likely_cause_count": int(max(cause_counts.values())) if cause_counts else 0,
                "missed_references_path": str(missed_path),
                "detector_params_json": json.dumps(best_result["detector_params"], sort_keys=True),
            }
        )
        logger.info(
            "Top-3 detail %s | channel=%s P=%.3f R=%.3f F1=%.3f missed=%d",
            strategy,
            best_result["channel"],
            best_result["metrics"].precision,
            best_result["metrics"].recall,
            best_result["metrics"].f1,
            len(missed_references),
        )

    shared_df = pd.DataFrame(shared_rows)
    if not shared_df.empty:
        grouped = (
            shared_df.groupby(["epoch_index", "blink_onset", "blink_duration"], as_index=False)
            .agg(
                missed_by_count=("strategy", "nunique"),
                missed_by_strategies=("strategy", lambda values: ",".join(sorted(set(values)))),
                likely_causes=("likely_cause", lambda values: ",".join(sorted(set(values)))),
                max_supporting_channel_count=("supporting_channel_count", "max"),
            )
            .sort_values(["missed_by_count", "epoch_index", "blink_onset"], ascending=[False, True, True])
            .reset_index(drop=True)
        )
    else:
        grouped = pd.DataFrame(
            columns=[
                "epoch_index",
                "blink_onset",
                "blink_duration",
                "missed_by_count",
                "missed_by_strategies",
                "likely_causes",
                "max_supporting_channel_count",
            ]
        )
    return pd.DataFrame(detail_rows), grouped


def choose_top_channels(baseline_df: pd.DataFrame, top_n: int) -> list[str]:
    ranked = baseline_df.copy()
    ranked["rank_score"] = ranked["f1"] + 0.25 * ranked["recall"]
    ranked = ranked.sort_values(["rank_score", "recall", "precision"], ascending=False)
    return ranked["channel"].head(top_n).tolist()


def tune_single_channels(
    prepared,
    valid_epoch_indices: list[int],
    reference: pd.DataFrame,
    global_floors: dict[int, float],
    logger: logging.Logger,
) -> tuple[pd.DataFrame, dict[str, dict]]:
    tuned_rows: list[dict] = []
    best_by_channel: dict[str, dict] = {}

    variants = ["sw_onset", "sw_onset_soft_gate"]
    onset_modes = ["epoch_hysteresis", "sw_hysteresis", "sw_core"]
    windows_by_mode = {
        "sw_core": [1.0, 1.5, 2.0],
        "sw_hysteresis": [1.0, 1.5, 2.0],
        "epoch_hysteresis": [0.0],
    }
    k_open_values = [1.5, 1.8, 2.0]
    k_close_values = [0.3, 0.5, 0.8]
    bridge_gap_values = [0.0, 20.0, 40.0]
    min_len_values = [0.05]
    soft_gate_cons_values = [1.8, 2.0, 2.2]
    soft_gate_mad_mult_values = [1.5, 2.0, 2.5]

    for ch_idx, channel_name in enumerate(prepared.channel_names):
        logger.info("Tuning single channel %s", channel_name)
        best_result = evaluate_channel(
            prepared,
            ch_idx,
            valid_epoch_indices,
            reference,
            DetectorParams(),
            global_floors,
        )
        logger.info(
            "  start %s | P=%.3f R=%.3f F1=%.3f",
            channel_name,
            best_result["metrics"].precision,
            best_result["metrics"].recall,
            best_result["metrics"].f1,
        )

        for variant in variants:
            logger.info("  scanning variant=%s on %s", variant, channel_name)
            for onset_mode in onset_modes:
                logger.info("    scanning mode=%s on %s", onset_mode, channel_name)
                k_low_values = [0.5] if onset_mode != "sw_core" else [0.2, 0.5, 0.8]
                for window_s, k_open, k_close, k_low, bridge_gap_ms, min_event_len_s in itertools.product(
                    windows_by_mode[onset_mode],
                    k_open_values,
                    k_close_values,
                    k_low_values,
                    bridge_gap_values,
                    min_len_values,
                ):
                    soft_gate_cons_iter = soft_gate_cons_values if variant == "sw_onset_soft_gate" else [2.0]
                    soft_gate_mad_iter = soft_gate_mad_mult_values if variant == "sw_onset_soft_gate" else [2.0]
                    for soft_gate_cons_k, soft_gate_mad_mult in itertools.product(
                        soft_gate_cons_iter,
                        soft_gate_mad_iter,
                    ):
                        params = DetectorParams(
                            variant=variant,
                            onset_mode=onset_mode,
                            window_s=2.0 if onset_mode == "epoch_hysteresis" else window_s,
                            k_open=k_open,
                            k_close=k_close,
                            k_low=k_low,
                            bridge_gap_ms=bridge_gap_ms,
                            min_event_len_s=min_event_len_s,
                            use_global_floor=True,
                            soft_gate_cons_k=soft_gate_cons_k,
                            soft_gate_min_confident=5,
                            soft_gate_mad_mult=soft_gate_mad_mult,
                        )
                        result = evaluate_channel(prepared, ch_idx, valid_epoch_indices, reference, params, global_floors)
                        if result["metrics"].f1 > best_result["metrics"].f1:
                            best_result = result
                            logger.info(
                                "  new best %s | variant=%s mode=%s window=%.2f k_open=%.2f k_close=%.2f k_low=%.2f bridge=%.0f soft_cons=%.2f soft_mad=%.2f -> P=%.3f R=%.3f F1=%.3f",
                                channel_name,
                                variant,
                                onset_mode,
                                params.window_s,
                                k_open,
                                k_close,
                                k_low,
                                bridge_gap_ms,
                                soft_gate_cons_k,
                                soft_gate_mad_mult,
                                result["metrics"].precision,
                                result["metrics"].recall,
                                result["metrics"].f1,
                            )

        best_by_channel[channel_name] = best_result
        tuned_rows.append(result_to_row(best_result))

    tuned_df = pd.DataFrame(tuned_rows).sort_values("f1", ascending=False).reset_index(drop=True)
    return tuned_df, best_by_channel


def search_fusions(
    reference: pd.DataFrame,
    n_epochs: int,
    best_by_channel: dict[str, dict],
    logger: logging.Logger,
) -> tuple[pd.DataFrame, dict | None]:
    channels = list(best_by_channel)
    fusion_rows: list[dict] = []
    best_result: dict | None = None

    cluster_tols = [0.04, 0.08, 0.12]
    min_support_values = [1, 2]
    min_peak_z_values = [0.0, 0.5, 1.0]
    representatives = ["median", "best_peak"]

    for combo_size in range(2, len(channels) + 1):
        for combo in itertools.combinations(channels, combo_size):
            selected_events = pd.concat(
                [best_by_channel[channel]["events"] for channel in combo],
                ignore_index=True,
            )
            detector_params_by_channel = {
                channel: DetectorParams(**best_by_channel[channel]["detector_params"])
                for channel in combo
            }
            logger.info("Searching fusion combo %s", ",".join(combo))
            for cluster_tol_s, min_support, min_peak_z, representative in itertools.product(
                cluster_tols,
                min_support_values,
                min_peak_z_values,
                representatives,
            ):
                fusion_params = FusionParams(
                    cluster_tol_s=cluster_tol_s,
                    min_support=min_support,
                    min_peak_z=min_peak_z,
                    representative=representative,
                )
                result = evaluate_fused_channels(
                    selected_events,
                    reference,
                    n_epochs,
                    detector_params_by_channel,
                    fusion_params,
                )
                fusion_rows.append(result_to_row(result))
                if best_result is None or result["metrics"].f1 > best_result["metrics"].f1:
                    best_result = result
                    logger.info(
                        "  new best fusion %s | tol=%.2f support=%d min_peak_z=%.2f rep=%s -> P=%.3f R=%.3f F1=%.3f",
                        ",".join(combo),
                        cluster_tol_s,
                        min_support,
                        min_peak_z,
                        representative,
                        result["metrics"].precision,
                        result["metrics"].recall,
                        result["metrics"].f1,
                    )

    fusion_df = pd.DataFrame(fusion_rows).sort_values("f1", ascending=False).reset_index(drop=True)
    return fusion_df, best_result


def nearest_prediction_for_reference(predicted: pd.DataFrame, ref_row: pd.Series) -> pd.Series | None:
    epoch_pred = predicted[predicted["epoch_index"] == ref_row["epoch_index"]].copy()
    if epoch_pred.empty:
        return None
    epoch_pred["distance"] = (
        (epoch_pred["blink_onset"] - float(ref_row["blink_onset"])).abs()
        + (epoch_pred["blink_duration"] - float(ref_row["blink_duration"])).abs()
    )
    return epoch_pred.sort_values("distance").iloc[0]


def analyze_missed_references(
    best_result: dict,
    all_best_channel_events: pd.DataFrame,
) -> pd.DataFrame:
    ref_status = best_result["ref_status"]
    predicted = best_result["candidates"]
    missed = ref_status[ref_status["match_status"] == "fn"].copy()
    if missed.empty:
        return pd.DataFrame(
            columns=[
                "epoch_index",
                "blink_onset",
                "blink_duration",
                "nearest_pred_onset",
                "nearest_pred_duration",
                "nearest_onset_diff_s",
                "nearest_overlap_ratio",
                "supporting_channel_count",
                "supporting_channels",
                "likely_cause",
            ]
        )

    rows: list[dict] = []
    for _, miss in missed.iterrows():
        nearest = nearest_prediction_for_reference(predicted, miss)
        support = all_best_channel_events[
            (all_best_channel_events["epoch_index"] == miss["epoch_index"])
            & (
                (all_best_channel_events["blink_onset"] <= float(miss["blink_onset"]) + float(miss["blink_duration"]) + 0.15)
                & (
                    all_best_channel_events["blink_onset"] + all_best_channel_events["blink_duration"]
                    >= float(miss["blink_onset"]) - 0.15
                )
            )
        ]
        support_channels = sorted(support["channel"].astype(str).unique().tolist()) if not support.empty else []

        nearest_onset = np.nan
        nearest_duration = np.nan
        nearest_overlap = np.nan
        nearest_onset_diff = np.nan
        likely_cause = "no_candidate_on_selected_channels"
        if nearest is not None:
            nearest_onset = float(nearest["blink_onset"])
            nearest_duration = float(nearest["blink_duration"])
            nearest_onset_diff = float(nearest_onset - float(miss["blink_onset"]))
            nearest_overlap = interval_overlap_ratio(
                nearest_onset,
                nearest_duration,
                float(miss["blink_onset"]),
                float(miss["blink_duration"]),
            )
            if abs(nearest_onset_diff) <= 0.20 and nearest_overlap < 0.5:
                likely_cause = "timing_or_overlap_near_miss"
            elif nearest_duration > float(miss["blink_duration"]) * 1.8:
                likely_cause = "merged_with_neighbor"
            else:
                likely_cause = "candidate_present_but_validation_failed"
        if support_channels and likely_cause == "no_candidate_on_selected_channels":
            likely_cause = "visible_on_some_channels_but_not_fused"
        if not support_channels:
            likely_cause = "weak_region_no_channel_support"

        rows.append(
            {
                "epoch_index": int(miss["epoch_index"]),
                "blink_onset": float(miss["blink_onset"]),
                "blink_duration": float(miss["blink_duration"]),
                "nearest_pred_onset": nearest_onset,
                "nearest_pred_duration": nearest_duration,
                "nearest_onset_diff_s": nearest_onset_diff,
                "nearest_overlap_ratio": nearest_overlap,
                "supporting_channel_count": int(len(support_channels)),
                "supporting_channels": ",".join(support_channels),
                "likely_cause": likely_cause,
            }
        )
    return pd.DataFrame(rows)


def save_result_bundle(
    out_dir: Path,
    result: dict,
    missed_references: pd.DataFrame,
) -> None:
    result["candidates"].to_csv(out_dir / "best_candidates.csv", index=False)
    result["matches"].to_csv(out_dir / "best_matches.csv", index=False)
    result["pred_status"].to_csv(out_dir / "best_pred_status.csv", index=False)
    result["ref_status"].to_csv(out_dir / "best_reference_status.csv", index=False)
    missed_references.to_csv(out_dir / "best_missed_references.csv", index=False)


def main() -> None:
    args = parse_args()
    timestamp = args.output_stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_ROOT / args.segment / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(out_dir, args.log_level)

    logger.info("Single-pair top-10 rerun and top-3 recall-gap investigation")
    logger.info("Output directory: %s", out_dir)
    logger.info("Target pair: %s / %s", args.subject, args.segment)
    logger.info("Detailed follow-up strategy preference: %s", args.strategy)

    shortlist_df = build_report_top10_candidates()
    shortlist_df.to_csv(out_dir / "report_top10_single_channel_candidates.csv", index=False)
    logger.info("Saved report shortlist with %d entries", len(shortlist_df))

    pair = find_target_pair(args.subject, args.segment)
    logger.info("FIF: %s", pair["fif"])
    logger.info("CSV: %s", pair["csv"])

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(Path(pair["fif"]), brain_channels, logger)
    epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
    reference = load_annotation_as_reference(Path(pair["csv"]), epoch_duration=EPOCH_DURATION_S)
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    logger.info(
        "Epochs loaded: total=%d valid=%d reference_blinks=%d",
        len(epochs),
        len(valid_epoch_indices),
        len(reference),
    )

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    global_floors = compute_global_floors(prepared, valid_epoch_indices)
    rerun_top10_df = rerun_report_top10(epochs, reference, valid_epoch_indices, out_dir, logger)
    rerun_top10_df.to_csv(out_dir / "rerun_top10_summary.csv", index=False)

    top3_detail_df, shared_misses_df = investigate_top3_recall_gaps(
        prepared,
        valid_epoch_indices,
        reference,
        global_floors,
        rerun_top10_df,
        out_dir,
        logger,
    )
    top3_detail_df.to_csv(out_dir / "top3_recall_gap_analysis.csv", index=False)
    shared_misses_df.to_csv(out_dir / "top3_shared_missed_blink_regions.csv", index=False)

    strategy_c_lane_df, strategy_c_candidates = run_strategy_c_baseline(epochs, reference, valid_epoch_indices)
    strategy_c_lane_df.to_csv(out_dir / "strategy_c_lane_summary.csv", index=False)
    strategy_c_best_row = strategy_c_lane_df.iloc[0]
    strategy_c_best_channel = str(strategy_c_best_row["channel"])
    strategy_c_best_candidates = strategy_c_candidates[strategy_c_best_channel].copy()
    strategy_c_best_candidates.to_csv(out_dir / "strategy_c_best_candidates.csv", index=False)

    strategy_c_trials_df, strategy_c_best_repair = search_strategy_c_boundary_repair(
        reference,
        len(epochs),
        strategy_c_best_candidates,
    )
    strategy_c_trials_df.to_csv(out_dir / "strategy_c_boundary_repair_trials.csv", index=False)
    strategy_c_best_repair["candidates"].to_csv(out_dir / "strategy_c_boundary_repair_best_candidates.csv", index=False)
    strategy_c_best_repair["pred_status"].to_csv(out_dir / "strategy_c_boundary_repair_best_pred_status.csv", index=False)
    strategy_c_best_repair["ref_status"].to_csv(out_dir / "strategy_c_boundary_repair_best_reference_status.csv", index=False)
    strategy_c_best_repair["matches"].to_csv(out_dir / "strategy_c_boundary_repair_best_matches.csv", index=False)
    strategy_c_repair_misses = analyze_missed_references(
        {"ref_status": strategy_c_best_repair["ref_status"], "candidates": strategy_c_best_repair["candidates"]},
        strategy_c_best_repair["candidates"],
    )
    strategy_c_repair_misses.to_csv(out_dir / "strategy_c_boundary_repair_missed_references.csv", index=False)

    best_row = rerun_top10_df.iloc[0]
    summary = {
        "subject": args.subject,
        "segment": args.segment,
        "target_f1": args.target_f1,
        "preferred_followup_strategy": args.strategy,
        "best_rerun_strategy": str(best_row["strategy"]),
        "best_rerun_channel": str(best_row["best_channel"]),
        "best_rerun_metrics": {
            "tp": int(best_row["tp"]),
            "fp": int(best_row["fp"]),
            "fn": int(best_row["fn"]),
            "precision": float(best_row["precision"]),
            "recall": float(best_row["recall"]),
            "f1": float(best_row["f1"]),
        },
        "top3_strategies": rerun_top10_df.head(3)["strategy"].tolist(),
        "n_epochs": int(len(epochs)),
        "n_valid_epochs": int(len(valid_epoch_indices)),
        "n_reference_blinks": int(len(reference)),
        "shared_top3_missed_regions": int(len(shared_misses_df)),
        "strategy_c_baseline": {
            "best_channel": strategy_c_best_channel,
            "tp": int(strategy_c_best_row["tp"]),
            "fp": int(strategy_c_best_row["fp"]),
            "fn": int(strategy_c_best_row["fn"]),
            "precision": float(strategy_c_best_row["precision"]),
            "recall": float(strategy_c_best_row["recall"]),
            "f1": float(strategy_c_best_row["f1"]),
        },
        "strategy_c_boundary_repair_best": {
            **strategy_c_best_repair["params"],
        },
    }
    with (out_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    logger.info(
        "Best rerun result | strategy=%s channel=%s P=%.3f R=%.3f F1=%.3f",
        best_row["strategy"],
        best_row["best_channel"],
        best_row["precision"],
        best_row["recall"],
        best_row["f1"],
    )
    if float(best_row["f1"]) >= args.target_f1:
        logger.info("Target reached: F1 %.3f >= %.3f", float(best_row["f1"]), args.target_f1)
    else:
        logger.warning("Target not reached: F1 %.3f < %.3f", float(best_row["f1"]), args.target_f1)
    if not top3_detail_df.empty:
        logger.info("Top-3 recall-gap leaders:\n%s", top3_detail_df.to_string(index=False))
    if not shared_misses_df.empty:
        logger.info("Shared missed blink regions across rerun top 3:\n%s", shared_misses_df.head(15).to_string(index=False))
    logger.info(
        "Strategy C baseline | channel=%s P=%.3f R=%.3f F1=%.3f",
        strategy_c_best_channel,
        float(strategy_c_best_row["precision"]),
        float(strategy_c_best_row["recall"]),
        float(strategy_c_best_row["f1"]),
    )
    logger.info(
        "Strategy C boundary repair best | short_thr=%.2f short_pre=%.2f short_post=%.2f long_post=%.2f gap=%.2f -> P=%.3f R=%.3f F1=%.3f",
        float(strategy_c_best_repair["params"]["short_event_threshold_s"]),
        float(strategy_c_best_repair["params"]["short_pre_pad_s"]),
        float(strategy_c_best_repair["params"]["short_post_pad_s"]),
        float(strategy_c_best_repair["params"]["long_post_pad_s"]),
        float(strategy_c_best_repair["params"]["merge_gap_s"]),
        float(strategy_c_best_repair["metrics"].precision),
        float(strategy_c_best_repair["metrics"].recall),
        float(strategy_c_best_repair["metrics"].f1),
    )
    if not strategy_c_repair_misses.empty:
        logger.info("Strategy C repaired residual misses:\n%s", strategy_c_repair_misses.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
