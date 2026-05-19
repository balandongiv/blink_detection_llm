"""Strategy F epoch-duration sweep across the Raja EEG annotation dataset.

This tutorial extends ``10d_strategy_autoreject_drop_threshold.py`` from one
fixed 60-second subject run to an all-subject sweep over multiple epoch sizes.

Epoch durations tested:
    3, 5, 10, 15, 20, 30, 60, 100, 120 seconds

Subjects are discovered using the same ``VideoFrameViewers.yaml`` status filter
as ``20_strategy_comparison_raja_dataset.py``: only sessions marked
``complete_eeg`` and having both ``ear_eog.csv`` and ``eeg_eog_raw.fif`` are
included.

To accelerate the run, subjects are processed concurrently with a
ThreadPoolExecutor.  Each worker loads one subject once, then evaluates all
epoch durations for that subject.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import sys

import mne
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.strategy_f.runner import channel_results_strategy_f


# ---------------------------------------------------------------------------
# Dataset root paths
# ---------------------------------------------------------------------------
ANNOTATION_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
PROCESSED_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja_processed")
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"


# ---------------------------------------------------------------------------
# Sweep parameters
# ---------------------------------------------------------------------------
EPOCH_DURATIONS_S = [3.0, 5.0, 10.0, 15.0, 20.0, 30.0, 60.0, 100.0, 120.0]
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Set to a positive integer to process only the first N epochs per duration.
N_EPOCHS: int | None = None


# ---------------------------------------------------------------------------
# Strategy F settings copied from tutorial/10d_strategy_autoreject_drop_threshold.py
# ---------------------------------------------------------------------------
AUTOREJECT_RANDOM_STATE = 42
MIN_FLAGGED_EPOCHS = 1
STD_THRESHOLD = 3.5
CENTER_METHOD = "median"
VERBOSE = False


# ---------------------------------------------------------------------------
# CPU threading
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True

# Tune this down if multiple loaded FIF files exceed available RAM.
MAX_WORKERS: int = max(1, min(8, os.cpu_count() or 1))


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
OUTPUT_CSV = REPO_ROOT / "output" / "strategy_f_epoch_duration_sweep.csv"


def _duration_label(duration_s: float) -> str:
    """Return a compact, stable label for display and sorting."""
    if float(duration_s).is_integer():
        return f"{int(duration_s)}s"
    return f"{duration_s:g}s"


def _discover_pairs() -> list[dict]:
    """Return complete Raja EEG pairs discovered from annotation YAML files."""
    pairs: list[dict] = []
    for yaml_path in sorted(ANNOTATION_BASE_DIR.rglob("VideoFrameViewers.yaml")):
        with yaml_path.open("r", encoding="utf-8") as fh:
            info = yaml.safe_load(fh) or {}
        if info.get("status") != "complete_eeg":
            continue

        session_dir = yaml_path.parent
        rel = session_dir.relative_to(ANNOTATION_BASE_DIR)
        csv_path = session_dir / "ear_eog.csv"
        fif_path = PROCESSED_BASE_DIR / rel / "seg_data_raw" / "eeg_eog_raw.fif"

        if not csv_path.exists():
            print(f"  [skip] CSV not found: {csv_path}")
            continue
        if not fif_path.exists():
            print(f"  [skip] FIF not found: {fif_path}")
            continue

        pairs.append(
            {
                "name": str(rel).replace("\\", "/"),
                "fif": fif_path,
                "csv": csv_path,
            }
        )
    return pairs


def _strategy_f_settings() -> dict:
    return {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose": VERBOSE,
    }


def _best_channel_diagnostics(channel_results: list[dict], best_channel: str) -> dict:
    best = next((r for r in channel_results if r["channel"] == best_channel), None)
    if best is None:
        return {
            "n_flagged": None,
            "used_all_epochs": None,
            "blink_region_threshold": None,
            "threshold_center": None,
            "threshold_dispersion": None,
        }
    return {
        "n_flagged": best.get("n_flagged"),
        "used_all_epochs": best.get("used_all_epochs"),
        "blink_region_threshold": best.get("blink_region_threshold"),
        "threshold_center": best.get("threshold_center"),
        "threshold_dispersion": best.get("threshold_dispersion"),
    }


def run_one_duration(
    pair_name: str,
    csv_path: Path,
    raw: mne.io.BaseRaw,
    epoch_duration_s: float,
) -> dict:
    """Run Strategy F for one subject and one epoch duration."""
    epochs = mne.make_fixed_length_epochs(
        raw,
        duration=float(epoch_duration_s),
        preload=True,
        verbose="ERROR",
    )
    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)

    channel_results = channel_results_strategy_f(
        prepared,
        valid_epoch_indices,
        setting=_strategy_f_settings(),
    )

    gt_annotations = load_ground_truth_annotations(csv_path, float(epoch_duration_s))

    scored = evaluate_channels(
        channel_results,
        gt_annotations,
        epoch_duration=float(epoch_duration_s),
    )

    em = scored.best_eval_result.event_metrics
    diagnostics = _best_channel_diagnostics(
        channel_results,
        best_channel=str(scored.best_channel),
    )
    return {
        "pair": pair_name,
        "epoch_duration_s": float(epoch_duration_s),
        "epoch_duration_label": _duration_label(epoch_duration_s),
        "n_epochs": len(epochs),
        "n_valid_epochs": len(valid_epoch_indices),
        "best_channel": scored.best_channel,
        "tp": em.tp,
        "fp": em.fp,
        "fn": em.fn,
        "precision": em.precision,
        "recall": em.recall,
        "f1": em.f1,
        **diagnostics,
    }


def run_subject(pair: dict) -> list[dict]:
    """Load one subject once and evaluate all epoch durations."""
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(pair["fif"], brain_channels)

    rows: list[dict] = []
    for duration_s in EPOCH_DURATIONS_S:
        row = run_one_duration(
            pair_name=pair["name"],
            csv_path=pair["csv"],
            raw=raw,
            epoch_duration_s=duration_s,
        )
        rows.append(row)
        print(
            f"  done  pair={pair['name']}  epoch={_duration_label(duration_s)}  "
            f"F1={row['f1']:.4f}  R={row['recall']:.4f}  P={row['precision']:.4f}"
        )
    return rows


def _micro_metrics(rows: list[dict]) -> dict:
    tp = sum(int(r["tp"]) for r in rows)
    fp = sum(int(r["fp"]) for r in rows)
    fn = sum(int(r["fn"]) for r in rows)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
    }


def _print_per_pair_table(results: list[dict]) -> None:
    results_sorted = sorted(results, key=lambda r: (r["pair"], r["epoch_duration_s"]))
    col_w = {
        "pair": 30,
        "epoch": 7,
        "best_channel": 14,
        "tp": 5,
        "fp": 5,
        "fn": 5,
        "precision": 10,
        "recall": 8,
        "f1": 8,
    }
    header = (
        f"{'pair':<{col_w['pair']}}  "
        f"{'epoch':>{col_w['epoch']}}  "
        f"{'best_channel':<{col_w['best_channel']}}  "
        f"{'tp':>{col_w['tp']}}  "
        f"{'fp':>{col_w['fp']}}  "
        f"{'fn':>{col_w['fn']}}  "
        f"{'precision':>{col_w['precision']}}  "
        f"{'recall':>{col_w['recall']}}  "
        f"{'f1':>{col_w['f1']}}"
    )
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print("PER-SUBJECT STRATEGY F EPOCH-DURATION SWEEP")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_pair = None
    for row in results_sorted:
        if prev_pair and row["pair"] != prev_pair:
            print(sep)
        prev_pair = row["pair"]
        print(
            f"{row['pair']:<{col_w['pair']}}  "
            f"{row['epoch_duration_label']:>{col_w['epoch']}}  "
            f"{str(row['best_channel']):<{col_w['best_channel']}}  "
            f"{row['tp']:>{col_w['tp']}}  "
            f"{row['fp']:>{col_w['fp']}}  "
            f"{row['fn']:>{col_w['fn']}}  "
            f"{row['precision']:>{col_w['precision']}.4f}  "
            f"{row['recall']:>{col_w['recall']}.4f}  "
            f"{row['f1']:>{col_w['f1']}.4f}"
        )
    print(f"{'=' * len(header)}\n")


def _print_summary_table(results: list[dict]) -> None:
    buckets = {
        duration_s: [r for r in results if r["epoch_duration_s"] == duration_s]
        for duration_s in EPOCH_DURATIONS_S
    }
    col_w = {
        "epoch": 7,
        "n_pairs": 8,
        "tp": 7,
        "fp": 7,
        "fn": 7,
        "micro_p": 10,
        "micro_r": 9,
        "micro_f1": 9,
        "macro_p": 10,
        "macro_r": 9,
        "macro_f1": 9,
    }
    header = (
        f"{'epoch':>{col_w['epoch']}}  "
        f"{'n_pairs':>{col_w['n_pairs']}}  "
        f"{'TP':>{col_w['tp']}}  "
        f"{'FP':>{col_w['fp']}}  "
        f"{'FN':>{col_w['fn']}}  "
        f"{'micro_P':>{col_w['micro_p']}}  "
        f"{'micro_R':>{col_w['micro_r']}}  "
        f"{'micro_F1':>{col_w['micro_f1']}}  "
        f"{'macro_P':>{col_w['macro_p']}}  "
        f"{'macro_R':>{col_w['macro_r']}}  "
        f"{'macro_F1':>{col_w['macro_f1']}}"
    )
    sep = "=" * len(header)
    print(sep)
    print("OVERALL SUMMARY BY EPOCH DURATION")
    print(sep)
    print(header)
    print("-" * len(header))

    for duration_s in EPOCH_DURATIONS_S:
        rows = buckets[duration_s]
        if not rows:
            continue
        micro = _micro_metrics(rows)
        macro_p = sum(float(r["precision"]) for r in rows) / len(rows)
        macro_r = sum(float(r["recall"]) for r in rows) / len(rows)
        macro_f1 = sum(float(r["f1"]) for r in rows) / len(rows)
        print(
            f"{_duration_label(duration_s):>{col_w['epoch']}}  "
            f"{len(rows):>{col_w['n_pairs']}}  "
            f"{micro['tp']:>{col_w['tp']}}  "
            f"{micro['fp']:>{col_w['fp']}}  "
            f"{micro['fn']:>{col_w['fn']}}  "
            f"{micro['micro_precision']:>{col_w['micro_p']}.4f}  "
            f"{micro['micro_recall']:>{col_w['micro_r']}.4f}  "
            f"{micro['micro_f1']:>{col_w['micro_f1']}.4f}  "
            f"{macro_p:>{col_w['macro_p']}.4f}  "
            f"{macro_r:>{col_w['macro_r']}.4f}  "
            f"{macro_f1:>{col_w['macro_f1']}.4f}"
        )
    print(sep)


def _save_results_csv(results: list[dict]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(results).sort_values(["epoch_duration_s", "pair"])
    frame.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved results CSV: {OUTPUT_CSV}")


def main() -> None:
    print("Strategy F epoch-duration sweep")
    print(f"Epoch durations: {', '.join(_duration_label(d) for d in EPOCH_DURATIONS_S)}")
    print(
        f"Strategy F settings: k={STD_THRESHOLD:g}, center={CENTER_METHOD}, "
        f"min_flagged_epochs={MIN_FLAGGED_EPOCHS}"
    )

    pairs = _discover_pairs()
    if not pairs:
        print("No pairs discovered; check ANNOTATION_BASE_DIR and PROCESSED_BASE_DIR.")
        return

    print(f"Discovered {len(pairs)} complete EEG pair(s):")
    for pair in pairs:
        print(f"  {pair['name']}")

    results: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        print(f"\nRunning subject-level tasks with ThreadPoolExecutor(max_workers={MAX_WORKERS}) ...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_pair = {executor.submit(run_subject, pair): pair["name"] for pair in pairs}
            for future in as_completed(future_to_pair):
                pair_name = future_to_pair[future]
                try:
                    rows = future.result()
                    results.extend(rows)
                    print(f"  finished subject={pair_name}  rows={len(rows)}")
                except Exception as exc:
                    msg = f"  ERROR subject={pair_name}: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print("\nRunning subject-level tasks sequentially ...")
        for pair in pairs:
            try:
                rows = run_subject(pair)
                results.extend(rows)
                print(f"  finished subject={pair['name']}  rows={len(rows)}")
            except Exception as exc:
                msg = f"  ERROR subject={pair['name']}: {exc}"
                print(msg)
                errors.append(msg)

    if results:
        _print_per_pair_table(results)
        _print_summary_table(results)
        _save_results_csv(results)

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  {error}")


if __name__ == "__main__":
    main()
