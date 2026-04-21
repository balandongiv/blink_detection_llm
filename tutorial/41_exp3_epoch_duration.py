"""Experiment 3: Stability of Proposed-Med across epoch durations.

Tests whether the proposed three-stage pipeline (Strategy F, median estimator)
produces stable session-level F1 when the epoch grid is varied.  A robust
pipeline should not be sensitive to this administrative choice, since the
underlying physiology of blinks does not change with epoch length.

Design
------
Proposed-Med is re-run from scratch under epoch durations of 20, 30, 60, and
120 seconds.  Secondary outcomes include the number of suspicious epochs
identified by Stage A and the estimated sample-level threshold θ_c from Stage B.

Two-tailed Wilcoxon signed-rank tests compare each duration against the
60-second reference, with Bonferroni correction for 3 non-reference durations.

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
from scipy.stats import rankdata, wilcoxon

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
EPOCH_DURATIONS_S      = [20.0, 30.0, 60.0, 120.0]
REFERENCE_EPOCH_S      = 60.0   # Wilcoxon comparisons are against this duration
PEAK_SIDE_TOLERANCE_S  = 0.01
FILTER_LOW             = 1.0
FILTER_HIGH            = 20.0
RESAMPLE_RATE          = None
N_EPOCHS: int | None   = None

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
# Single evaluation unit: one session × one epoch duration
# ---------------------------------------------------------------------------

def run_one(pair: dict, epoch_duration_s: float) -> dict:
    """Run Proposed-Med on *pair* with *epoch_duration_s* and return metrics.

    Returns
    -------
    dict with keys: dataset, session, epoch_duration_s, tp, fp, fn,
    precision, recall, f1, n_flagged, threshold_center, blink_region_threshold.
    """
    load_fn = _DATASET_LOADERS[pair["dataset"]]
    raw = load_fn(pair["fif"])
    epochs = mne.make_fixed_length_epochs(
        raw, duration=epoch_duration_s, preload=True, verbose="ERROR"
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
        load_annotation_as_reference(pair["csv"], epoch_duration_s),
        epoch_duration_s,
    )
    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=epoch_duration_s,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )
    m = scored.best_metrics
    br = scored.best_result

    # Strategy-F diagnostics from the best channel
    n_flagged        = int(br.get("n_flagged", 0))
    thresh_center    = float(br.get("threshold_center", float("nan")))
    blink_threshold  = float(br.get("blink_region_threshold", float("nan")))

    return {
        "dataset":              pair["dataset"],
        "session":              pair["name"],
        "epoch_duration_s":     epoch_duration_s,
        "tp":                   m.true_positives,
        "fp":                   m.false_positives,
        "fn":                   m.false_negatives,
        "precision":            m.precision,
        "recall":               m.recall,
        "f1":                   m.f1,
        "n_flagged":            n_flagged,
        "n_valid_epochs":       len(valid_epoch_indices),
        "threshold_center":     thresh_center,
        "blink_region_threshold": blink_threshold,
    }


# ---------------------------------------------------------------------------
# Result printing
# ---------------------------------------------------------------------------

def _print_per_session_table(results: list[dict], dataset_name: str) -> None:
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: (r["session"], r["epoch_duration_s"]))

    W_sess = max(len(r["session"]) for r in rows)
    W_sess = max(W_sess, 8)
    header = (
        f"{'session':<{W_sess}}  {'dur_s':>6}  "
        f"{'tp':>5}  {'fp':>5}  {'fn':>5}  "
        f"{'prec':>8}  {'recall':>8}  {'f1':>8}  "
        f"{'n_flag':>7}  {'n_valid':>7}  {'θ_c':>12}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 3 — PER-SESSION RESULTS  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_session = None
    for r in rows:
        if prev_session and r["session"] != prev_session:
            print(sep)
        prev_session = r["session"]
        print(
            f"{r['session']:<{W_sess}}  {r['epoch_duration_s']:>6.0f}  "
            f"{r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  "
            f"{r['precision']:>8.4f}  {r['recall']:>8.4f}  {r['f1']:>8.4f}  "
            f"{r['n_flagged']:>7}  {r['n_valid_epochs']:>7}  "
            f"{r['blink_region_threshold']:>12.6f}"
        )
    print(f"{'=' * len(header)}\n")


def _print_duration_summary(results: list[dict], dataset_name: str) -> None:
    """Print macro-averaged metrics per epoch duration."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return

    buckets: dict[float, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["epoch_duration_s"]].append(r)

    header = (
        f"{'dur_s':>6}  {'N':>5}  "
        f"{'macroP':>8}  {'macroR':>8}  {'macroF1':>8}  "
        f"{'mean_n_flag':>11}  {'mean_θ_c':>10}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 3 — DURATION SUMMARY  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for dur in sorted(buckets):
        bucket = buckets[dur]
        macro_p   = float(np.mean([r["precision"] for r in bucket]))
        macro_r   = float(np.mean([r["recall"]    for r in bucket]))
        macro_f1  = float(np.mean([r["f1"]        for r in bucket]))
        mean_flag = float(np.mean([r["n_flagged"]  for r in bucket]))
        mean_thr  = float(np.mean([r["blink_region_threshold"] for r in bucket]))
        ref_marker = " ←ref" if dur == REFERENCE_EPOCH_S else ""
        print(
            f"{dur:>6.0f}  {len(bucket):>5}  "
            f"{macro_p:>8.4f}  {macro_r:>8.4f}  {macro_f1:>8.4f}  "
            f"{mean_flag:>11.2f}  {mean_thr:>10.6f}{ref_marker}"
        )
    print(f"{'=' * len(header)}\n")


def _run_wilcoxon_vs_reference(results: list[dict], dataset_name: str) -> None:
    """Two-tailed Wilcoxon comparing each duration against REFERENCE_EPOCH_S."""
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return

    lookup: dict[str, dict[float, float]] = defaultdict(dict)
    for r in rows:
        lookup[r["session"]][r["epoch_duration_s"]] = r["f1"]

    non_ref = [d for d in EPOCH_DURATIONS_S if d != REFERENCE_EPOCH_S]
    alpha_corrected = 0.05 / len(non_ref)

    complete = sorted(
        s for s, dmap in lookup.items()
        if all(d in dmap for d in EPOCH_DURATIONS_S)
    )

    print(f"\nExp 3 — Wilcoxon vs {REFERENCE_EPOCH_S:.0f}s reference  "
          f"—  {dataset_name.upper()}")
    print(f"  n_sessions={len(complete)}  α_Bonferroni={alpha_corrected:.4f}")
    print(f"  {'Comparison':<20}  {'W':>8}  {'p':>8}  {'r':>6}  sig")
    print(f"  {'-' * 55}")

    ref_f1 = np.array([lookup[s][REFERENCE_EPOCH_S] for s in complete])
    for dur in non_ref:
        dur_f1 = np.array([lookup[s][dur] for s in complete])
        diffs = dur_f1 - ref_f1
        if np.all(diffs == 0):
            print(f"  {dur:.0f}s vs {REFERENCE_EPOCH_S:.0f}s  all diffs zero")
            continue
        try:
            stat, p = wilcoxon(dur_f1, ref_f1, alternative="two-sided")
            nonzero = diffs[diffs != 0]
            ranks = rankdata(np.abs(nonzero))
            T_plus = float(np.sum(ranks[nonzero > 0]))
            n = len(nonzero)
            r = (2.0 * T_plus / (n * (n + 1) / 2.0)) - 1.0
            sig = "***" if p < alpha_corrected else "**" if p < 0.01 else "*" if p < 0.05 else ""
            label = f"{dur:.0f}s vs {REFERENCE_EPOCH_S:.0f}s"
            print(f"  {label:<20}  {stat:>8.1f}  {p:>8.4f}  {r:>6.3f}  {sig}")
        except Exception as exc:
            print(f"  {dur:.0f}s vs {REFERENCE_EPOCH_S:.0f}s  error: {exc}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    raja_pairs  = _discover_raja_pairs()
    murat_pairs = _discover_murat_pairs()
    all_pairs   = raja_pairs + murat_pairs

    print(f"Raja sessions  : {len(raja_pairs)}")
    print(f"Murat subjects : {len(murat_pairs)}")
    print(f"Epoch durations: {EPOCH_DURATIONS_S}")

    tasks = [
        (pair, dur)
        for dur in EPOCH_DURATIONS_S
        for pair in all_pairs
    ]

    results: list[dict] = []
    errors:  list[str]  = []

    if USE_MULTITHREAD:
        print(f"\nRunning {len(tasks)} tasks with ThreadPoolExecutor …")
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one, pair, dur): (pair["name"], dur)
                for pair, dur in tasks
            }
            for future in as_completed(future_map):
                name, dur = future_map[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  done  {name}  dur={dur:.0f}s  f1={result['f1']:.4f}")
                except Exception as exc:
                    msg = f"  ERROR  {name}  dur={dur:.0f}s: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"\nRunning {len(tasks)} tasks sequentially …")
        for pair, dur in tasks:
            print(f"  running  {pair['name']}  dur={dur:.0f}s …")
            try:
                result = run_one(pair, dur)
                results.append(result)
                print(f"  done     {pair['name']}  dur={dur:.0f}s  f1={result['f1']:.4f}")
            except Exception as exc:
                msg = f"  ERROR  {pair['name']}  dur={dur:.0f}s: {exc}"
                print(msg)
                errors.append(msg)

    if not results:
        print("No results collected.")
        return

    for ds in ("raja", "murat2018"):
        _print_per_session_table(results, ds)

    for ds in ("raja", "murat2018", "all"):
        _print_duration_summary(results, ds)

    for ds in ("raja", "murat2018"):
        _run_wilcoxon_vs_reference(results, ds)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
