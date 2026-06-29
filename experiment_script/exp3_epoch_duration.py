"""Experiment 3: Stability of Proposed-Med across epoch durations.

Tests whether the proposed three-stage pipeline (Strategy F, median estimator)
produces stable session-level F1 when the epoch grid is varied.  A robust
pipeline should not be sensitive to this administrative choice, since the
underlying physiology of blinks does not change with epoch length.

Design
------
Proposed-Med is re-run from scratch under epoch durations of 10,20, 30, 40, 50,60, and 120 seconds.

Secondary outcomes include the number of suspicious epochs
identified by Stage A and the estimated sample-level threshold θ_c from Stage B.

Two-tailed Wilcoxon signed-rank tests compare each duration against the
30-second reference, with Bonferroni correction for non-reference durations.

Datasets
--------
Drowsy Driving Raja corpus and Cao2018 sustained-attention driving corpus.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np
from scipy.stats import rankdata, wilcoxon

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels
from src.common.epoch_input import prepare_epoch_detection_input
from experiment_script.channel_group_config import apply_stage_a_channel_group
from pyblinker.double_thresholding import blink_position_strategy_dbo
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs, discover_raja_pairs,
    load_gt_annotations_for_pair, make_dataset_loaders, setup_tutorial_logging,
    valid_epoch_indices_for_pair,
)

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp3_epoch_duration.yaml")
_RAJA    = get_raja_paths()
_CAO     = get_cao_paths()

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAJA_REGION_YAML     = _RAJA["brain_region_yaml"]
CAO_REGION_YAML      = _CAO["brain_region_yaml"]
RAJA_ANNOTATION_BASE = _RAJA["annotation_base"]
RAJA_PROCESSED_BASE  = _RAJA["processed_base"]
CAO_DATASET_ROOT     = _CAO["dataset_root"]

# ---------------------------------------------------------------------------
# Experiment parameters
# ---------------------------------------------------------------------------
EPOCH_DURATIONS_S      = [10, 20.0, 30.0, 40.0, 50, 60.0, 120.0]
REFERENCE_EPOCH_S      = 30.0   # Wilcoxon comparisons are against this duration
FILTER_LOW             = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH            = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE          = 100
N_EPOCHS: int | None   = None

# Strategy dbo_drop (Proposed-Med) parameters
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD           = float(_EXP_CFG.get("std_threshold", 3.5))
CENTER_METHOD           = "median"
MIN_FLAGGED_EPOCHS      = 1




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
    dataset_loaders = make_dataset_loaders(
        raja_region_yaml=RAJA_REGION_YAML, cao_region_yaml=CAO_REGION_YAML
    )
    load_fn = dataset_loaders[pair["dataset"]]
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
    prepared = apply_stage_a_channel_group(prepared, pair["dataset"])
    valid_epoch_indices = valid_epoch_indices_for_pair(pair, epochs, epoch_duration_s)

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":      STD_THRESHOLD,
        "center_method":      CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":            VERBOSE,
    }
    channel_results = blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)

    gt_annotations = load_gt_annotations_for_pair(pair, float(epoch_duration_s), valid_epoch_indices)
    scored = evaluate_channels(channel_results, gt_annotations, epoch_duration=epoch_duration_s)
    em = scored.best_eval_result.event_metrics
    br = scored.best_channel_result or {}

    # Strategy-F diagnostics from the best channel
    n_flagged        = int(br.get("n_flagged", 0))
    thresh_center    = float(br.get("threshold_center", float("nan")))
    blink_threshold  = float(br.get("blink_region_threshold", float("nan")))

    return {
        "dataset":              pair["dataset"],
        "session":              pair["name"],
        "epoch_duration_s":     epoch_duration_s,
        "tp":                   em.tp,
        "fp":                   em.fp,
        "fn":                   em.fn,
        "precision":            em.precision,
        "recall":               em.recall,
        "f1":                   em.f1,
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
        f"{'n_flag':>7}  {'n_valid':>7}  {'theta_c':>12}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 3 - PER-SESSION RESULTS - {dataset_name.upper()}")
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
        f"{'mean_n_flag':>11}  {'mean_theta':>10}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 3 - DURATION SUMMARY - {dataset_name.upper()}")
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
        ref_marker = " <-ref" if dur == REFERENCE_EPOCH_S else ""
        print(
            f"{dur:>6.0f}  {len(bucket):>5}  "
            f"{macro_p:>8.4f}  {macro_r:>8.4f}  {macro_f1:>8.4f}  "
            f"{mean_flag:>11.2f}  {mean_thr:>10.6f}{ref_marker}"
        )
    print(f"{'=' * len(header)}\n")


def _duration_summary_rows(results: list[dict], dataset_name: str) -> list[dict]:
    """Return macro-averaged metrics per epoch duration as dict rows."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return []

    buckets: dict[float, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["epoch_duration_s"]].append(r)

    out: list[dict] = []
    for dur in sorted(buckets):
        bucket = buckets[dur]
        out.append({
            "dataset": dataset_name,
            "epoch_duration_s": float(dur),
            "n_sessions": int(len(bucket)),
            "macro_precision": float(np.mean([r["precision"] for r in bucket])),
            "macro_recall": float(np.mean([r["recall"] for r in bucket])),
            "macro_f1": float(np.mean([r["f1"] for r in bucket])),
            "mean_n_flagged": float(np.mean([r["n_flagged"] for r in bucket])),
            "mean_blink_region_threshold": float(np.mean([r["blink_region_threshold"] for r in bucket])),
        })
    return out


def _pick_best_epoch(duration_summary_all: list[dict], reference_epoch_s: float) -> tuple[float, dict]:
    """Pick best epoch based on macro-F1 (primary), with deterministic tie-breaks.

    Tie-break order:
    1) higher macro-F1 (primary)
    2) higher macro-recall
    3) higher macro-precision
    4) closer to the reference epoch (interpretability)
    """
    if not duration_summary_all:
        raise ValueError("No duration summary rows available to select best epoch.")

    def key(r: dict) -> tuple[float, float, float, float]:
        return (
            float(r["macro_f1"]),
            float(r["macro_recall"]),
            float(r["macro_precision"]),
            -abs(float(r["epoch_duration_s"]) - float(reference_epoch_s)),
        )

    best = max(duration_summary_all, key=key)
    return float(best["epoch_duration_s"]), best


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Experiment 1: epoch duration search for Proposed-Med (Strategy F, median estimator).",
    )
    p.add_argument(
        "--epoch-durations-s",
        default="20,30,40,60,120",
        help="Comma-separated epoch durations in seconds (e.g., 20,30,40,60,120).",
    )
    p.add_argument(
        "--reference-epoch-s",
        type=float,
        default=REFERENCE_EPOCH_S,
        help="Reference duration for Wilcoxon comparisons and tie-breaking.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="If set, write CSV/JSON artifacts into this directory.",
    )
    p.add_argument(
        "--no-multithread",
        action="store_true",
        help="Disable internal ThreadPoolExecutor (useful for constrained systems).",
    )
    p.add_argument(
        "--n-epochs",
        type=int,
        default=None,
        help="Limit epochs per session for quick runs (None = all).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce strategy verbosity.",
    )
    return p.parse_args()


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

    print(f"\nExp 3 - Wilcoxon vs {REFERENCE_EPOCH_S:.0f}s reference  "
          f"-  {dataset_name.upper()}")
    print(f"  n_sessions={len(complete)}  alpha_Bonferroni={alpha_corrected:.4f}")
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
    args = _parse_args()

    global USE_MULTITHREAD, VERBOSE, EPOCH_DURATIONS_S, REFERENCE_EPOCH_S, N_EPOCHS
    USE_MULTITHREAD = not args.no_multithread
    VERBOSE = not args.quiet
    N_EPOCHS = args.n_epochs
    REFERENCE_EPOCH_S = float(args.reference_epoch_s)

    try:
        EPOCH_DURATIONS_S = [float(x.strip()) for x in str(args.epoch_durations_s).split(",") if x.strip()]
    except Exception as exc:
        raise SystemExit(f"Invalid --epoch-durations-s: {args.epoch_durations_s!r} ({exc})")
    if not EPOCH_DURATIONS_S:
        raise SystemExit("No epoch durations provided.")

    setup_tutorial_logging()
    raja_pairs = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    cao_pairs  = discover_cao_pairs(CAO_DATASET_ROOT)
    all_pairs  = raja_pairs + cao_pairs

    logger.info("Raja sessions   : %d", len(raja_pairs))
    logger.info("Cao2018 sessions: %d", len(cao_pairs))
    logger.info("Epoch durations : %s", EPOCH_DURATIONS_S)

    tasks = [
        (pair, dur)
        for dur in EPOCH_DURATIONS_S
        for pair in all_pairs
    ]

    results: list[dict] = []
    errors:  list[str]  = []

    if USE_MULTITHREAD:
        logger.info("Running %d tasks with ThreadPoolExecutor …", len(tasks))
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
                    logger.info("done  %s  dur=%.0fs  f1=%.4f", name, dur, result["f1"])
                except Exception as exc:
                    logger.error("%s  dur=%.0fs: %s", name, dur, exc)
                    errors.append(f"ERROR  {name}  dur={dur:.0f}s: {exc}")
    else:
        logger.info("Running %d tasks sequentially …", len(tasks))
        for pair, dur in tasks:
            logger.info("running  %s  dur=%.0fs …", pair["name"], dur)
            try:
                result = run_one(pair, dur)
                results.append(result)
                logger.info("done     %s  dur=%.0fs  f1=%.4f", pair["name"], dur, result["f1"])
            except Exception as exc:
                logger.error("%s  dur=%.0fs: %s", pair["name"], dur, exc)
                errors.append(f"ERROR  {pair['name']}  dur={dur:.0f}s: {exc}")

    if not results:
        print("No results collected.")
        return

    for ds in ("raja", "cao2018"):
        _print_per_session_table(results, ds)

    for ds in ("raja", "cao2018", "all"):
        _print_duration_summary(results, ds)

    for ds in ("raja", "cao2018"):
        _run_wilcoxon_vs_reference(results, ds)

    # Orchestration-friendly selection + artifacts.
    duration_summary_all = _duration_summary_rows(results, "all")
    best_epoch_s, best_row = _pick_best_epoch(duration_summary_all, REFERENCE_EPOCH_S)
    print(f"\n[BEST EPOCH] Proposed-Med macro-F1 best at {best_epoch_s:.0f} seconds (dataset=all, metric=macro_F1).")

    if args.out_dir is not None:
        out_dir: Path = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        _write_csv(out_dir / "exp1_epoch_duration_results.csv", results)
        _write_csv(
            out_dir / "exp1_epoch_duration_summary.csv",
            _duration_summary_rows(results, "raja")
            + _duration_summary_rows(results, "cao2018")
            + duration_summary_all,
        )

        payload = {
            "experiment": "exp1_epoch_duration",
            "metric_primary": "macro_f1 (dataset=all)",
            "epoch_durations_s": [float(x) for x in EPOCH_DURATIONS_S],
            "reference_epoch_s": float(REFERENCE_EPOCH_S),
            "best_epoch_duration_s": float(best_epoch_s),
            "best_row": best_row,
            "n_rows": int(len(results)),
        }
        (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
