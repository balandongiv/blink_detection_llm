"""Experiment 4: Stability across peak-side boundary tolerances.

Tests whether Proposed-Med's event-level F1 is sensitive to the temporal
tolerance used when matching detected blink intervals to ground-truth intervals.
A detector whose F1 varies greatly with tolerance is fragile: its apparent
performance depends on an arbitrary methodological choice rather than on true
detection quality.

Design
------
Proposed-Med (Strategy F, median estimator, 60-second epochs) is evaluated under
five boundary tolerances: {0, 50, 100, 150, 200} milliseconds, applied
symmetrically to both onset and offset.

Primary outcome: macro-averaged F1 at each tolerance level.
Secondary outcome: range of macro F1 across the five levels.  A range < 1
percentage point indicates the evaluation is insensitive to reasonable tolerance
choices.

Datasets
--------
Drowsy Driving Raja corpus and murat_2018.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.lane_evaluation import evaluate_channel_lanes
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference
from src.strategy_f.runner import channel_results_strategy_f

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML    = REPO_ROOT / "brain_region.yaml"
RAJA_ANNOTATION_BASE = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
RAJA_PROCESSED_BASE  = Path(r"D:\dataset\drowsy_driving_raja_processed")
MURAT_DATASET_ROOT   = Path(r"D:\dataset\murat_2018")

# ---------------------------------------------------------------------------
# Experiment parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S        = 60.0
# Boundary tolerances in seconds (0 ms, 50 ms, 100 ms, 150 ms, 200 ms)
TOLERANCES_S            = [0.0, 0.050, 0.100, 0.150, 0.200]
FILTER_LOW              = 1.0
FILTER_HIGH             = 20.0
RESAMPLE_RATE           = None
N_EPOCHS: int | None    = None

# Strategy F (Proposed-Med) parameters
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD           = 3.5
CENTER_METHOD           = "median"
MIN_FLAGGED_EPOCHS      = 1


# ---------------------------------------------------------------------------
# Dataset discovery
# ---------------------------------------------------------------------------

def _discover_raja_pairs() -> list[dict]:
    pairs: list[dict] = []
    for yaml_path in sorted(RAJA_ANNOTATION_BASE.rglob("VideoFrameViewers.yaml")):
        with yaml_path.open("r", encoding="utf-8") as fh:
            info = yaml.safe_load(fh)
        if (info or {}).get("status") != "complete_eeg":
            continue
        session_dir = yaml_path.parent
        rel = session_dir.relative_to(RAJA_ANNOTATION_BASE)
        csv_path = session_dir / "ear_eog.csv"
        fif_path = RAJA_PROCESSED_BASE / rel / "seg_data_raw" / "eeg_eog_raw.fif"
        if not csv_path.exists() or not fif_path.exists():
            continue
        pairs.append({
            "dataset": "raja",
            "name":    str(rel).replace("\\", "/"),
            "fif":     fif_path,
            "csv":     csv_path,
        })
    return pairs


def _discover_murat_pairs() -> list[dict]:
    pairs: list[dict] = []
    for subject_dir in sorted(MURAT_DATASET_ROOT.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name
        fif = subject_dir / f"{sid}.fif"
        csv = subject_dir / f"{sid}.csv"
        if fif.is_file() and csv.is_file():
            pairs.append({"dataset": "murat2018", "name": sid, "fif": fif, "csv": csv})
    return pairs


# ---------------------------------------------------------------------------
# Raw loading helpers
# ---------------------------------------------------------------------------

def _load_raja_raw(fif_path: Path) -> mne.io.BaseRaw:
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    return load_raw_with_brain_channels(fif_path, brain_channels)


def _load_murat_raw(fif_path: Path) -> mne.io.BaseRaw:
    return mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")


_DATASET_LOADERS = {"raja": _load_raja_raw, "murat2018": _load_murat_raw}


# ---------------------------------------------------------------------------
# Single evaluation unit: one session × one tolerance
# ---------------------------------------------------------------------------

def _run_session(pair: dict) -> dict:
    """Load session and run Proposed-Med once; cache channel_results for reuse."""
    load_fn = _DATASET_LOADERS[pair["dataset"]]
    raw = load_fn(pair["fif"])
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
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

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":      STD_THRESHOLD,
        "center_method":      CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":            VERBOSE,
    }
    channel_results = channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)

    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(pair["csv"], EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )
    return {
        "pair":            pair,
        "channel_results": channel_results,
        "ground_truth":    ground_truth,
        "n_epochs":        len(epochs),
        "sfreq":           float(prepared.sfreq),
    }


def run_one_session_all_tolerances(pair: dict) -> list[dict]:
    """Run the pipeline once and evaluate across all boundary tolerances.

    This avoids repeating Stage A/B computation for each tolerance level.

    Returns
    -------
    List of metric dicts, one per tolerance value.
    """
    session_data = _run_session(pair)
    channel_results = session_data["channel_results"]
    ground_truth    = session_data["ground_truth"]
    n_epochs        = session_data["n_epochs"]
    sfreq           = session_data["sfreq"]

    records: list[dict] = []
    for tol_s in TOLERANCES_S:
        scored = evaluate_channel_lanes(
            channel_results,
            ground_truth,
            n_epochs=n_epochs,
            sfreq=sfreq,
            epoch_duration=EPOCH_DURATION_S,
            peak_side_tolerance_s=tol_s,
        )
        m = scored.best_metrics
        records.append({
            "dataset":        pair["dataset"],
            "session":        pair["name"],
            "tolerance_ms":   int(round(tol_s * 1000)),
            "tolerance_s":    tol_s,
            "tp":             m.true_positives,
            "fp":             m.false_positives,
            "fn":             m.false_negatives,
            "precision":      m.precision,
            "recall":         m.recall,
            "f1":             m.f1,
        })
    return records


# ---------------------------------------------------------------------------
# Result printing
# ---------------------------------------------------------------------------

def _print_per_session_table(results: list[dict], dataset_name: str) -> None:
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: (r["session"], r["tolerance_ms"]))

    W_sess = max(len(r["session"]) for r in rows)
    W_sess = max(W_sess, 8)
    header = (
        f"{'session':<{W_sess}}  {'tol_ms':>7}  "
        f"{'tp':>5}  {'fp':>5}  {'fn':>5}  "
        f"{'precision':>10}  {'recall':>8}  {'f1':>8}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 4 — PER-SESSION  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_session = None
    for r in rows:
        if prev_session and r["session"] != prev_session:
            print(sep)
        prev_session = r["session"]
        print(
            f"{r['session']:<{W_sess}}  {r['tolerance_ms']:>7}  "
            f"{r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  "
            f"{r['precision']:>10.4f}  {r['recall']:>8.4f}  {r['f1']:>8.4f}"
        )
    print(f"{'=' * len(header)}\n")


def _print_tolerance_summary(results: list[dict], dataset_name: str) -> None:
    """Print macro-averaged P/R/F1 per tolerance and report the F1 range."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return

    buckets: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["tolerance_ms"]].append(r)

    header = (
        f"{'tol_ms':>7}  {'N':>5}  "
        f"{'macro_P':>9}  {'macro_R':>9}  {'macro_F1':>9}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 4 — TOLERANCE SUMMARY  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    f1_values: list[float] = []
    for tol_ms in sorted(buckets):
        bucket = buckets[tol_ms]
        macro_p  = float(np.mean([r["precision"] for r in bucket]))
        macro_r  = float(np.mean([r["recall"]    for r in bucket]))
        macro_f1 = float(np.mean([r["f1"]        for r in bucket]))
        f1_values.append(macro_f1)
        print(
            f"{tol_ms:>7}  {len(bucket):>5}  "
            f"{macro_p:>9.4f}  {macro_r:>9.4f}  {macro_f1:>9.4f}"
        )

    if f1_values:
        f1_range = max(f1_values) - min(f1_values)
        stable = "YES" if f1_range < 0.01 else "NO"
        print(sep)
        print(f"  macro-F1 range = {f1_range:.4f}  stable (<1 pp) = {stable}")
    print(f"{'=' * len(header)}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    raja_pairs  = _discover_raja_pairs()
    murat_pairs = _discover_murat_pairs()
    all_pairs   = raja_pairs + murat_pairs

    print(f"Raja sessions  : {len(raja_pairs)}")
    print(f"Murat subjects : {len(murat_pairs)}")
    print(f"Tolerances (ms): {[int(t * 1000) for t in TOLERANCES_S]}")

    results: list[dict] = []
    errors:  list[str]  = []

    if USE_MULTITHREAD:
        print(f"\nRunning {len(all_pairs)} sessions with ThreadPoolExecutor …")
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one_session_all_tolerances, pair): pair["name"]
                for pair in all_pairs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    records = future.result()
                    results.extend(records)
                    print(f"  done  {name}  ({len(records)} tolerances)")
                except Exception as exc:
                    msg = f"  ERROR  {name}: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"\nRunning {len(all_pairs)} sessions sequentially …")
        for pair in all_pairs:
            print(f"  running  {pair['name']} …")
            try:
                records = run_one_session_all_tolerances(pair)
                results.extend(records)
                print(f"  done     {pair['name']}  ({len(records)} tolerances)")
            except Exception as exc:
                msg = f"  ERROR  {pair['name']}: {exc}"
                print(msg)
                errors.append(msg)

    if not results:
        print("No results collected.")
        return

    for ds in ("raja", "murat2018"):
        _print_per_session_table(results, ds)

    for ds in ("raja", "murat2018", "all"):
        _print_tolerance_summary(results, ds)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
