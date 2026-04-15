"""
Tutorial 23 – Strategy E (per-epoch MAD threshold) Step 1 batch evaluation.

Pipeline
--------
Strategy A/C use the BLINKER-style threshold computed on the *concatenated*
signal:  threshold = mean(all_epochs) + k * 1.4826 * MAD(all_epochs).

Strategy D uses autoreject's peak-to-peak (PTP) computed *per epoch*, then
Bayesian-optimises a rejection threshold over that sorted PTP distribution,
and finally drives MNE peak_finder with the result.

Strategy E borrows autoreject's "per-epoch feature" idea but replaces PTP
with the BLINKER MAD-based statistic computed independently for every epoch:

    threshold_e = mean(epoch_e) + k * 1.4826 * MAD(epoch_e)

Each epoch is then scanned with *its own* threshold via threshold-crossing
detection (same scan logic as Strategy A).  This adapts to per-epoch signal
statistics and is expected to improve recall in quiet epochs where a global
threshold would miss blinks.

Goal for Step 1: high true-positive rate / low false-negative rate.

Outputs
-------
    experiment_output/<subject>/<segment>/strategy_e_step1_lane_summary.csv
    experiment_output/strategy_e_step1_all_results.csv
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
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
OUTPUT_ROOT = REPO_ROOT / "experiment_output"

# Strategy E: per-epoch MAD threshold (BLINKER defaults)
STD_THRESHOLD = 1.5     # k in:  threshold = mean + k * SCALING_FACTOR * MAD(epoch)
MIN_EVENT_LEN_S = 0.05  # minimum blink duration (seconds) for a crossing to be kept


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
# Strategy E: per-epoch MAD-based threshold scanning
# ---------------------------------------------------------------------------

def _scan_epoch_mad_crossings(
    signal: np.ndarray,
    threshold: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Return (onset_sample, offset_sample) pairs from threshold crossings.

    Vectorised version of the BLINKER loop: onset when signal > threshold,
    offset when signal < threshold, minimum duration enforced.
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


def run_strategy_e_per_channel(
    prepared,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Run Strategy E for every channel; return list of per-channel result dicts."""
    sfreq = float(prepared.sfreq)
    min_blink_frames = MIN_EVENT_LEN_S * sfreq
    results: list[dict] = []

    for ch_idx, channel_name in enumerate(prepared.channel_names):
        cand_rows: list[dict] = []

        for epoch_idx in valid_epoch_indices:
            signal = prepared.data[epoch_idx, ch_idx, :].astype(float)

            # Per-epoch MAD threshold – adapts to each epoch's local statistics.
            ep_mean = float(np.mean(signal))
            ep_robust_std = SCALING_FACTOR * float(compute_mad(signal))
            ep_threshold = ep_mean + STD_THRESHOLD * ep_robust_std

            blinks = _scan_epoch_mad_crossings(signal, ep_threshold, min_blink_frames)
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
        results.append(
            {
                "channel": channel_name,
                "candidate_count": int(len(candidates)),
                "candidates": candidates,
            }
        )
    return results


def build_lane_summary(
    channel_results: list[dict],
    *,
    reference: pd.DataFrame,
    n_epochs: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for cr in channel_results:
        metrics = match_blink_tables(cr["candidates"], reference, n_epochs=n_epochs)
        rows.append(
            {
                "channel": cr["channel"],
                "candidate_count": cr["candidate_count"],
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )
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
) -> dict:
    result: dict = {
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
    out_dir = OUTPUT_ROOT / subject / segment
    out_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()

    try:
        raw = load_raw_with_brain_channels(fif_path, brain_channels)
        epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
        reference = load_annotation_as_reference(annotation_path, epoch_duration=EPOCH_DURATION_S)

        result["n_epochs"] = len(epochs)
        result["n_annotations"] = len(reference)
        reference.to_csv(out_dir / "reference_annotation.csv", index=False)

        prepared = prepare_epoch_detection_input(
            epochs,
            pick_types_options={"eeg": True},
            filter_low=FILTER_LOW,
            filter_high=FILTER_HIGH,
            resample_rate=RESAMPLE_RATE,
        )
        valid_epoch_indices = get_valid_epoch_indices(epochs)

        channel_results = run_strategy_e_per_channel(prepared, valid_epoch_indices)
        summary = build_lane_summary(
            channel_results, reference=reference, n_epochs=len(epochs)
        )
        result["n_lanes"] = len(summary)
        summary.to_csv(out_dir / "strategy_e_step1_lane_summary.csv", index=False)

        if not summary.empty:
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
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        result["error"] = tb
        (out_dir / "strategy_e_error.txt").write_text(tb)
        print(f"    [ERROR] {subject}/{segment}\n{tb}")

    result["elapsed_s"] = perf_counter() - started
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("Tutorial 23 – Strategy E (per-epoch MAD threshold) Step 1 batch")
    print("=" * 70)
    print(f"std_threshold (k)  : {STD_THRESHOLD}")
    print(f"scaling_factor     : {SCALING_FACTOR}  (1.4826 × MAD)")
    print(f"min_event_len_s    : {MIN_EVENT_LEN_S}")

    pairs = find_pairs()
    if not pairs:
        print("No matched (fif, csv) pairs found. Check PROCESSED_ROOT and ANNOTATION_ROOT.")
        return
    print(f"\nFound {len(pairs)} pair(s). Output root: {OUTPUT_ROOT}\n")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    print(f"Brain-region channels ({len(brain_channels)}): {brain_channels}\n")

    all_results: list[dict] = []
    for i, pair in enumerate(pairs, 1):
        subject = pair["subject"]
        segment = pair["segment"]
        fif_path = Path(pair["fif"])
        annotation_path = Path(pair["csv"])

        print(f"[{i}/{len(pairs)}] {subject} / {segment}")
        print(f"    fif : {fif_path}")
        print(f"    csv : {annotation_path}")

        res = process_pair(
            subject=subject,
            segment=segment,
            fif_path=fif_path,
            annotation_path=annotation_path,
            brain_channels=brain_channels,
        )
        all_results.append(res)

        if not res["error"]:
            print(
                f"    done in {res['elapsed_s']:.1f}s  "
                f"epochs={res['n_epochs']}  annot={res['n_annotations']}  "
                f"lanes={res['n_lanes']}  best_ch={res['best_channel']}  "
                f"TP={res['best_tp']}  FP={res['best_fp']}  FN={res['best_fn']}  "
                f"P={res['best_precision']:.3f}  R={res['best_recall']:.3f}  "
                f"F1={res['best_f1']:.3f}"
            )
        print()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results_df = pd.DataFrame(all_results)
    results_csv = OUTPUT_ROOT / "strategy_e_step1_all_results.csv"
    results_df.to_csv(results_csv, index=False)
    print(f"Full per-pair results saved → {results_csv}\n")

    successful = results_df[results_df["error"] == ""].copy()
    failed = results_df[results_df["error"] != ""]

    print("=" * 70)
    print("AGGREGATE SUMMARY  (best lane per pair)")
    print("=" * 70)
    print(f"Total pairs   : {len(results_df)}")
    print(f"Successful    : {len(successful)}")
    print(f"Failed        : {len(failed)}")

    if not successful.empty:
        total_tp = int(successful["best_tp"].sum())
        total_fp = int(successful["best_fp"].sum())
        total_fn = int(successful["best_fn"].sum())

        micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else float("nan")
        micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else float("nan")
        micro_f1 = (
            2.0 * micro_precision * micro_recall / (micro_precision + micro_recall)
            if (micro_precision + micro_recall) > 0
            else float("nan")
        )
        macro_precision = float(successful["best_precision"].mean())
        macro_recall = float(successful["best_recall"].mean())
        macro_f1 = float(successful["best_f1"].mean())

        print(f"\n--- Pooled counts ---")
        print(f"  Total TP  : {total_tp}")
        print(f"  Total FP  : {total_fp}")
        print(f"  Total FN  : {total_fn}")

        print(f"\n--- Micro-averaged ---")
        print(f"  Precision : {micro_precision:.4f}")
        print(f"  Recall    : {micro_recall:.4f}")
        print(f"  F1        : {micro_f1:.4f}")

        print(f"\n--- Macro-averaged ---")
        print(f"  Precision : {macro_precision:.4f}")
        print(f"  Recall    : {macro_recall:.4f}")
        print(f"  F1        : {macro_f1:.4f}")

        print("\n--- Per-pair breakdown ---")
        display_cols = [
            "subject", "segment",
            "n_epochs", "n_annotations", "n_lanes",
            "best_channel",
            "best_tp", "best_fp", "best_fn",
            "best_precision", "best_recall", "best_f1",
            "elapsed_s",
        ]
        display_df = successful[display_cols].copy()
        for col in ("best_precision", "best_recall", "best_f1", "elapsed_s"):
            display_df[col] = display_df[col].map(lambda x: f"{x:.4f}")
        print(display_df.to_string(index=False))

    if not failed.empty:
        print("\n--- Failed pairs ---")
        for _, row in failed.iterrows():
            print(f"  {row['subject']} / {row['segment']}")


if __name__ == "__main__":
    main()
