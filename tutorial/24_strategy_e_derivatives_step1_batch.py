"""
Tutorial 24 – Strategy E Derivative Variants Step 1 batch evaluation.

Exploratory derivatives of Strategy E (per-epoch MAD threshold) following the
roadmap in tutorial/strategy_e_derivative.md.

Implemented variants
--------------------
E1  – e_median        : median + k * 1.4826 * MAD(epoch)  (replaces mean)
E2  – e_floor         : median + MAD with global subject-level noise-floor minimum
E3  – e_hysteresis    : dual thresholds  T_high = median + k_h * MAD,
                        T_low = median + k_l * MAD  (hysteresis crossing)
E4  – e_multiscale    : union of detections at k=1.0, 1.2, 1.5; merge within gap_ms

All variants share the same epoch pipeline as Strategy E and are evaluated
against the same ground-truth annotations using match_blink_tables.

Debug mode
----------
Set DEBUG = True to run only the first pair (single-threaded, fast feedback).
Set DEBUG = False to run all 65 pairs sequentially (single-threaded for safety).

Outputs
-------
    experiment_output/<subject>/<segment>/strategy_e_derivatives_lane_summary.csv
    experiment_output/strategy_e_derivatives_all_results.csv
    experiment_output/strategy_e_derivatives_aggregate.csv
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
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
DEBUG = False  # True = first pair only; False = all pairs

BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
OUTPUT_ROOT = REPO_ROOT / "experiment_output"

# Shared threshold params
K_DEFAULT = 1.5       # default k for mean/median + k * SCALING_FACTOR * MAD
MIN_EVENT_LEN_S = 0.05

# E2 floor: subject-level global noise floor is computed as
#   floor = global_median + FLOOR_K * SCALING_FACTOR * global_MAD
# where global_* is over all valid epochs concatenated for that channel.
FLOOR_K = 0.5

# E3 hysteresis thresholds
K_HIGH = 1.5
K_LOW = 1.0

# E4 multiscale: union of these k values, merge within GAP_MS
MULTISCALE_K_VALUES = [1.0, 1.2, 1.5]
MULTISCALE_GAP_MS = 80.0  # merge detections within this gap (ms)

VARIANT_NAMES = ["e1_median", "e2_floor", "e3_hysteresis", "e4_multiscale", "e5_global_floor"]


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
        rows.append(
            {
                "epoch_index": epoch_index,
                "blink_onset": onset_abs - epoch_index * epoch_duration,
                "blink_duration": duration,
            }
        )
    return pd.DataFrame(rows, columns=["epoch_index", "blink_onset", "blink_duration"])


# ---------------------------------------------------------------------------
# Shared scanning primitives
# ---------------------------------------------------------------------------

def _scan_threshold_crossings(
    signal: np.ndarray,
    threshold: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Standard threshold-crossing scan (same as Strategy E).

    Returns (onset_sample, offset_sample) pairs.
    """
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


def _scan_hysteresis_crossings(
    signal: np.ndarray,
    t_high: float,
    t_low: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Hysteresis threshold crossing: open when > t_high, close when < t_low.

    min_blink_frames enforced on the final event length.
    """
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
    # Close any open event at end of signal
    if in_event and (n - start) > min_blink_frames:
        blinks.append((start, n))
    return blinks


def _merge_intervals(
    intervals: list[tuple[int, int]],
    gap_frames: int,
) -> list[tuple[int, int]]:
    """Merge overlapping or nearby intervals within gap_frames."""
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


# ---------------------------------------------------------------------------
# Per-variant scanners
# ---------------------------------------------------------------------------

def _run_e1_median_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E1: median + k * SCALING_FACTOR * MAD, per epoch."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    cand_rows: list[dict] = []

    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        threshold = ep_median + K_DEFAULT * ep_mad

        for start, end in _scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


def _run_e2_floor_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E2: median + k * MAD with global noise-floor minimum per channel."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq

    # Compute global floor from all valid epochs concatenated
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_median = float(np.median(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_median + FLOOR_K * global_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        ep_threshold = ep_median + K_DEFAULT * ep_mad
        threshold = max(ep_threshold, global_floor)

        for start, end in _scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


def _run_e3_hysteresis_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E3: hysteresis thresholds, both computed from per-epoch median + MAD."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    cand_rows: list[dict] = []

    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        t_high = ep_median + K_HIGH * ep_mad
        t_low = ep_median + K_LOW * ep_mad

        for start, end in _scan_hysteresis_crossings(signal, t_high, t_low, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


def _run_e4_multiscale_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E4: union of detections at multiple k values (median + k * MAD), merged within gap_ms."""
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq
    gap_frames = int(round(MULTISCALE_GAP_MS * sfreq / 1000.0))
    cand_rows: list[dict] = []

    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))

        # Collect candidates from all k scales
        raw_candidates: list[tuple[int, int]] = []
        for k in MULTISCALE_K_VALUES:
            threshold = ep_median + k * ep_mad
            raw_candidates.extend(_scan_threshold_crossings(signal, threshold, min_frames))

        # Merge overlapping/nearby intervals
        merged = _merge_intervals(raw_candidates, gap_frames)
        for start, end in merged:
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })

    return _make_candidates_df(cand_rows, channel_name)


def _make_candidates_df(cand_rows: list[dict], channel_name: str) -> pd.DataFrame:
    if cand_rows:
        return (
            pd.DataFrame(cand_rows)
            .sort_values(["epoch_index", "blink_onset"])
            .reset_index(drop=True)
        )
    return pd.DataFrame(columns=["epoch_index", "channel", "blink_onset", "blink_duration"])


# ---------------------------------------------------------------------------
# Per-variant runner (loops over all channels)
# ---------------------------------------------------------------------------

def _run_e5_global_floor_channel(
    prepared,
    ch_idx: int,
    channel_name: str,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """E5: per-epoch median+MAD, floored by global mean+MAD (Strategy-A style).

    Prevents threshold collapse in quiet epochs (reduces FP) while still
    adapting downward in noisy epochs (preserves recall).
    """
    sfreq = float(prepared.sfreq)
    min_frames = MIN_EVENT_LEN_S * sfreq

    # Global floor = Strategy A formula on full concatenated signal
    concat = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(float)
    global_mean = float(np.mean(concat))
    global_mad = SCALING_FACTOR * float(compute_mad(concat))
    global_floor = global_mean + K_DEFAULT * global_mad

    cand_rows: list[dict] = []
    for epoch_idx in valid_epoch_indices:
        signal = prepared.data[epoch_idx, ch_idx, :].astype(float)
        ep_median = float(np.median(signal))
        ep_mad = SCALING_FACTOR * float(compute_mad(signal))
        threshold = max(ep_median + K_DEFAULT * ep_mad, global_floor)
        for start, end in _scan_threshold_crossings(signal, threshold, min_frames):
            cand_rows.append({
                "epoch_index": epoch_idx,
                "channel": channel_name,
                "blink_onset": start / sfreq,
                "blink_duration": (end - start) / sfreq,
            })
    return _make_candidates_df(cand_rows, channel_name)


_VARIANT_CHANNEL_RUNNERS = {
    "e1_median": _run_e1_median_channel,
    "e2_floor": _run_e2_floor_channel,
    "e3_hysteresis": _run_e3_hysteresis_channel,
    "e4_multiscale": _run_e4_multiscale_channel,
    "e5_global_floor": _run_e5_global_floor_channel,
}


def run_variant(
    variant: str,
    prepared,
    valid_epoch_indices: list[int],
    reference: pd.DataFrame,
    n_epochs: int,
) -> pd.DataFrame:
    """Run a single variant across all channels. Returns a lane-summary DataFrame."""
    runner = _VARIANT_CHANNEL_RUNNERS[variant]
    rows: list[dict] = []

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
    """Run all E derivative variants on one pair. Returns one result dict per variant."""
    out_dir = OUTPUT_ROOT / subject / segment
    out_dir.mkdir(parents=True, exist_ok=True)

    base = {
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

    # Load data once
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
    col = "variant"
    sub = df[(df[col] == variant) & (df["error"].isna() | (df["error"] == ""))]
    total = len(df[df[col] == variant])
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
        if (micro_p + micro_r) > 0
        else float("nan")
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

def main() -> None:
    print("=" * 70)
    print("Tutorial 24 – Strategy E Derivative Variants  (Step 1 batch)")
    print("=" * 70)
    print(f"DEBUG mode         : {DEBUG}")
    print(f"Variants           : {VARIANT_NAMES}")
    print(f"k_default          : {K_DEFAULT}   (E1/E2/E4)")
    print(f"floor_k            : {FLOOR_K}    (E2 global floor)")
    print(f"k_high / k_low     : {K_HIGH} / {K_LOW}  (E3 hysteresis)")
    print(f"multiscale_k_vals  : {MULTISCALE_K_VALUES}  (E4)")
    print(f"multiscale_gap_ms  : {MULTISCALE_GAP_MS} ms  (E4 merge)")
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

    all_results: list[dict] = []
    for i, pair in enumerate(pairs, 1):
        subject = pair["subject"]
        segment = pair["segment"]
        fif_path = Path(pair["fif"])
        annotation_path = Path(pair["csv"])
        print(f"[{i}/{len(pairs)}] {subject} / {segment}")
        results = process_pair(subject, segment, fif_path, annotation_path, brain_channels)
        all_results.extend(results)
        print()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    per_pair_df = pd.DataFrame(all_results)
    per_pair_csv = OUTPUT_ROOT / "strategy_e_derivatives_all_results.csv"
    per_pair_df.to_csv(per_pair_csv, index=False)
    print(f"Per-pair results saved -> {per_pair_csv}\n")

    agg_rows = [compute_aggregate(per_pair_df, v) for v in VARIANT_NAMES]
    agg_df = pd.DataFrame(agg_rows)
    agg_csv = OUTPUT_ROOT / "strategy_e_derivatives_aggregate.csv"
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
        pivot_csv = OUTPUT_ROOT / "strategy_e_derivatives_f1_pivot.csv"
        pivot.to_csv(pivot_csv, index=False)
        print(f"\nF1 pivot saved -> {pivot_csv}")


if __name__ == "__main__":
    main()
