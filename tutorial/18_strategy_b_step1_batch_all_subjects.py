"""
Tutorial 18 – Strategy B **Step 1** batch evaluation across all subjects / segments.

Pipeline
--------
1. Discover all matched (eeg_eog_raw.fif, ear_eog.csv) pairs via
   src_project_development/extract_annotation_fif_pair.find_pairs().
2. For each pair prepare epoch data with BlinkDetectorEpochStrategyB, then run
   find_eog_candidate_regions per channel — stopping intentionally before
   FitBlinks / channel selection.
3. Write per-pair outputs to
       experiment_output/<subject>/<segment>/strategy_b_step1_lane_summary.csv
       experiment_output/<subject>/<segment>/strategy_b_step1_best_lane_candidates.csv
       experiment_output/<subject>/<segment>/strategy_b_step1_metrics.json
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

from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_validation import match_blink_tables
from pyblinker.epoch_detection_strategy_b import (
    BlinkDetectorEpochStrategyB,
    find_eog_candidate_regions,
    summarize_candidate_regions,
)

# ---------------------------------------------------------------------------
# Settings (mirror Tutorial 12)
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None
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
# Per-channel candidate evaluation
# ---------------------------------------------------------------------------

def run_find_eog_per_channel(
    prepared,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Call find_eog_candidate_regions for each channel; return list of per-channel dicts."""
    results = []
    epoch_boundaries = [
        (
            idx * prepared.epoch_length_samples,
            (idx + 1) * prepared.epoch_length_samples,
        )
        for idx in range(len(valid_epoch_indices))
    ]
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

        results.append(
            {
                "channel": channel_name,
                "df_positions": df_positions,
                "mapped_candidates": mapped,
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
            cr["mapped_candidates"],
            reference,
            n_epochs=n_epochs,
        )
        rows.append(
            {
                "channel": cr["channel"],
                "raw_candidate_count": int(len(cr["df_positions"])),
                "mapped_candidate_count": int(len(cr["mapped_candidates"])),
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
    """Run Strategy B Step 1 on one pair and return a best-lane metrics dict."""
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
        valid_epoch_indices = get_valid_epoch_indices(epochs)

        # --- find_eog_candidate_regions per channel ---
        channel_results = run_find_eog_per_channel(prepared, valid_epoch_indices)

        # --- Build lane-level summary ---
        summary = build_lane_summary(
            channel_results,
            reference=reference,
            n_epochs=len(epochs),
        )
        result["n_lanes"] = len(summary)

        summary.to_csv(out_dir / "strategy_b_step1_lane_summary.csv", index=False)

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
            if best_cr is not None and not best_cr["mapped_candidates"].empty:
                best_cr["mapped_candidates"].to_csv(
                    out_dir / "strategy_b_step1_best_lane_candidates.csv", index=False
                )

        # --- Persist per-pair metrics ---
        metrics_path = out_dir / "strategy_b_step1_metrics.json"
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
    print("Tutorial 18 – Strategy B Step 1 batch evaluation (all subjects)")
    print("=" * 70)

    pairs = find_pairs()
    if not pairs:
        print("No matched (fif, csv) pairs found. Check PROCESSED_ROOT and ANNOTATION_ROOT.")
        return
    print(f"\nFound {len(pairs)} pair(s). Output root: {OUTPUT_ROOT}\n")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    print(f"Brain-region channels ({len(brain_channels)}): {brain_channels}\n")

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
    results_csv = OUTPUT_ROOT / "strategy_b_step1_all_results.csv"
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
        agg_path = OUTPUT_ROOT / "strategy_b_step1_aggregate_summary.json"
        with agg_path.open("w") as fh:
            json.dump(aggregate, fh, indent=2)
        print(f"\nAggregate summary saved → {agg_path}")

    if not failed.empty:
        print("\n--- Failed pairs ---")
        for _, row in failed.iterrows():
            print(f"  {row['subject']} / {row['segment']}")


if __name__ == "__main__":
    main()
