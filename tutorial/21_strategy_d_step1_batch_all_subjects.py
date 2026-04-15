"""
Tutorial 22 – Strategy D **Step 1** batch evaluation across all subjects / segments.

Pipeline
--------
1. Discover all matched (eeg_eog_raw.fif, ear_eog.csv) pairs via
   src_project_development/extract_annotation_fif_pair.find_pairs().
2. For each pair prepare epoch data with prepare_epoch_detection_input, learn
   per-channel PTP thresholds with autoreject Bayesian optimisation, then call
   MNE peak_finder directly on the concatenated epoch signal per channel —
   mirroring Tutorial 14 but across all subjects.
3. Write per-pair outputs to
       experiment_output/<subject>/<segment>/strategy_d_step1_lane_summary.csv
       experiment_output/<subject>/<segment>/strategy_d_step1_best_lane_candidates.csv
       experiment_output/<subject>/<segment>/strategy_d_step1_metrics.json
4. After all pairs are processed, aggregate best-lane TP / FP / FN per pair
   and compute micro- and macro-averaged precision / recall / F1.
"""

from __future__ import annotations

import importlib.util
import json
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
# Dynamic import of find_pairs from src_project_development
# ---------------------------------------------------------------------------
_pairs_spec = importlib.util.spec_from_file_location(
    "extract_annotation_fif_pair",
    REPO_ROOT / "src_project_development" / "extract_annotation_fif_pair.py",
)
_pairs_mod = importlib.util.module_from_spec(_pairs_spec)  # type: ignore[arg-type]
_pairs_spec.loader.exec_module(_pairs_mod)  # type: ignore[union-attr]
find_pairs = _pairs_mod.find_pairs

from autoreject import compute_thresholds  # noqa: E402
from mne.preprocessing import peak_finder  # noqa: E402

from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_a.epoch_validation import match_blink_tables
from pyblinker.epoch_detection_strategy_c import STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE

# ---------------------------------------------------------------------------
# Settings (mirror Tutorial 14)
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
HALF_WINDOW_S = 0.10
AUTOREJECT_METHOD = "bayesian_optimization"
AUTOREJECT_RANDOM_STATE = 42
RESCALE_THRESHOLD = True
OUTPUT_ROOT = REPO_ROOT / "experiment_output"


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
    """Convert absolute-time annotation CSV to epoch-relative ground_truth table."""
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
# Strategy D helpers (mirrors Tutorial 14)
# ---------------------------------------------------------------------------

def get_scan_threshold_scale(rescale: bool) -> float:
    return STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE if rescale else 1.0


def learn_bayesian_thresholds(
    prepared_data: np.ndarray,
    channel_names: tuple[str, ...],
    sfreq: float,
    valid_epoch_indices: list[int],
) -> dict[str, float]:
    """Learn per-channel PTP rejection thresholds with Bayesian optimisation."""
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)
    stage1_data = prepared_data[valid_indices]
    info = mne.create_info(
        list(channel_names),
        sfreq=float(sfreq),
        ch_types=["eeg"] * len(channel_names),
    )
    stage1_epochs = mne.EpochsArray(stage1_data, info, verbose="ERROR")
    threshes = compute_thresholds(
        stage1_epochs,
        method=AUTOREJECT_METHOD,
        random_state=AUTOREJECT_RANDOM_STATE,
        augment=False,
        verbose=False,
    )
    return {ch: float(threshes[ch]) for ch in channel_names}


def peaks_to_candidates(
    peak_locs: np.ndarray,
    *,
    epoch_length_samples: int,
    sfreq: float,
    valid_epoch_indices: list[int],
    channel: str,
    half_window_s: float = HALF_WINDOW_S,
) -> pd.DataFrame:
    """Map sample positions in the concatenated signal back to epoch-local rows."""
    columns = ["epoch_index", "channel", "blink_onset", "blink_duration", "peak_sample"]
    if len(peak_locs) == 0:
        return pd.DataFrame(columns=columns)

    half_win = max(1, int(round(half_window_s * sfreq)))
    rows: list[dict] = []
    for peak in peak_locs:
        offset = int(peak) // epoch_length_samples
        if offset < 0 or offset >= len(valid_epoch_indices):
            continue
        epoch_index = int(valid_epoch_indices[offset])
        local_peak = int(peak) % epoch_length_samples
        start = max(0, local_peak - half_win)
        end = min(epoch_length_samples - 1, local_peak + half_win)
        rows.append(
            {
                "epoch_index": epoch_index,
                "channel": channel,
                "blink_onset": start / float(sfreq),
                "blink_duration": (end - start) / float(sfreq),
                "peak_sample": local_peak,
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    return df.sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)


def run_strategy_d_per_channel(
    prepared,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Run Strategy D Step 1 per channel; return list of per-channel dicts."""
    scan_threshold_scale = get_scan_threshold_scale(RESCALE_THRESHOLD)
    raw_thresholds = learn_bayesian_thresholds(
        prepared.data,
        channel_names=prepared.channel_names,
        sfreq=prepared.sfreq,
        valid_epoch_indices=valid_epoch_indices,
    )
    scan_thresholds = {
        ch: raw_thresholds[ch] * scan_threshold_scale for ch in raw_thresholds
    }

    epoch_length_samples = int(prepared.epoch_length_samples)
    valid_indices_arr = np.asarray(valid_epoch_indices, dtype=int)
    results: list[dict] = []

    for ch_idx, channel in enumerate(prepared.channel_names):
        x0 = prepared.data[valid_indices_arr, ch_idx, :].reshape(-1).astype(float)
        raw_thresh = raw_thresholds[channel]
        scan_thresh = scan_thresholds[channel]

        temp = x0 - np.mean(x0)
        extrema = 1 if np.abs(np.max(temp)) >= np.abs(np.min(temp)) else -1

        peak_locs, _ = peak_finder(x0, thresh=scan_thresh, extrema=extrema, verbose=False)
        peak_locs = np.asarray(peak_locs, dtype=int)

        candidates = peaks_to_candidates(
            peak_locs,
            epoch_length_samples=epoch_length_samples,
            sfreq=prepared.sfreq,
            valid_epoch_indices=valid_epoch_indices,
            channel=channel,
        )
        results.append(
            {
                "channel": channel,
                "raw_threshold": raw_thresh,
                "scan_threshold": scan_thresh,
                "extrema": extrema,
                "peak_count": int(len(peak_locs)),
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
        metrics = match_blink_tables(
            cr["candidates"],
            reference,
            n_epochs=n_epochs,
        )
        rows.append(
            {
                "channel": cr["channel"],
                "raw_threshold": cr["raw_threshold"],
                "scan_threshold": cr["scan_threshold"],
                "extrema": cr["extrema"],
                "peak_count": cr["peak_count"],
                "candidate_count": int(len(cr["candidates"])),
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
    return pd.DataFrame(rows).sort_values(
        ["f1", "tp", "fp", "channel"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)


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
    """Run Strategy D Step 1 on one pair and return a best-lane metrics dict."""
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
        # --- Load data ---
        raw = load_raw_with_brain_channels(fif_path, brain_channels)
        epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
        reference = load_annotation_as_reference(annotation_path, epoch_duration=EPOCH_DURATION_S)

        result["n_epochs"] = len(epochs)
        result["n_annotations"] = len(reference)

        reference.to_csv(out_dir / "reference_annotation.csv", index=False)

        # --- Prepare epoch data ---
        prepared = prepare_epoch_detection_input(
            epochs,
            pick_types_options={"eeg": True},
            filter_low=FILTER_LOW,
            filter_high=FILTER_HIGH,
            resample_rate=RESAMPLE_RATE,
        )
        valid_epoch_indices = get_valid_epoch_indices(epochs)

        # --- Strategy D Step 1: Bayesian threshold + peak_finder per channel ---
        channel_results = run_strategy_d_per_channel(prepared, valid_epoch_indices)

        # --- Build lane-level summary ---
        summary = build_lane_summary(
            channel_results,
            reference=reference,
            n_epochs=len(epochs),
        )
        result["n_lanes"] = len(summary)

        summary.to_csv(out_dir / "strategy_d_step1_lane_summary.csv", index=False)

        # --- Best lane ---
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
            best_channel = str(best["channel"])
            best_cr = next(
                (cr for cr in channel_results if cr["channel"] == best_channel), None
            )
            if best_cr is not None and not best_cr["candidates"].empty:
                best_cr["candidates"].to_csv(
                    out_dir / "strategy_d_step1_best_lane_candidates.csv", index=False
                )

        # --- Persist per-pair metrics ---
        metrics_path = out_dir / "strategy_d_step1_metrics.json"
        with metrics_path.open("w") as fh:
            json.dump(result, fh, indent=2)

    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        result["error"] = tb
        (out_dir / "error.txt").write_text(tb)
        print(f"    [ERROR] {subject}/{segment}\n{tb}")

    result["elapsed_s"] = perf_counter() - started
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("Tutorial 22 – Strategy D Step 1 batch evaluation (all subjects)")
    print("=" * 70)

    pairs = find_pairs()
    if not pairs:
        print("No matched (fif, csv) pairs found. Check PROCESSED_ROOT and ANNOTATION_ROOT.")
        return
    print(f"\nFound {len(pairs)} pair(s). Output root: {OUTPUT_ROOT}\n")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    print(f"Brain-region channels ({len(brain_channels)}): {brain_channels}\n")
    print(f"autoreject_method={AUTOREJECT_METHOD}")
    print(f"autoreject_random_state={AUTOREJECT_RANDOM_STATE}")
    print(f"rescale_threshold={RESCALE_THRESHOLD}")
    print(f"scan_threshold_scale={get_scan_threshold_scale(RESCALE_THRESHOLD)}\n")

    # --- Process each pair ---
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
                f"lanes={res['n_lanes']}  "
                f"best_ch={res['best_channel']}  "
                f"TP={res['best_tp']}  FP={res['best_fp']}  FN={res['best_fn']}  "
                f"P={res['best_precision']:.3f}  R={res['best_recall']:.3f}  "
                f"F1={res['best_f1']:.3f}"
            )
        print()

    # --- Save full results table ---
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results_df = pd.DataFrame(all_results)
    results_csv = OUTPUT_ROOT / "strategy_d_step1_all_results.csv"
    results_df.to_csv(results_csv, index=False)
    print(f"Full per-pair results saved → {results_csv}\n")

    # --- Aggregate ---
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
            if not (isinstance(micro_precision, float) and isinstance(micro_recall, float)
                    and (micro_precision + micro_recall) == 0)
            else float("nan")
        )

        macro_precision = float(successful["best_precision"].mean())
        macro_recall = float(successful["best_recall"].mean())
        macro_f1 = float(successful["best_f1"].mean())

        print("\n--- Pooled counts (best lane per pair) ---")
        print(f"  Total TP  : {total_tp}")
        print(f"  Total FP  : {total_fp}")
        print(f"  Total FN  : {total_fn}")

        print("\n--- Micro-averaged (from pooled TP/FP/FN) ---")
        print(f"  Precision : {micro_precision:.4f}")
        print(f"  Recall    : {micro_recall:.4f}")
        print(f"  F1        : {micro_f1:.4f}")

        print("\n--- Macro-averaged (mean over pairs) ---")
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

        aggregate = {
            "n_pairs_total": len(results_df),
            "n_pairs_successful": len(successful),
            "n_pairs_failed": len(failed),
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
            "micro_f1": micro_f1,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
        }
        agg_path = OUTPUT_ROOT / "strategy_d_step1_aggregate_summary.json"
        with agg_path.open("w") as fh:
            json.dump(aggregate, fh, indent=2)
        print(f"\nAggregate summary saved → {agg_path}")

    if not failed.empty:
        print("\n--- Failed pairs ---")
        for _, row in failed.iterrows():
            print(f"  {row['subject']} / {row['segment']}")


if __name__ == "__main__":
    main()
