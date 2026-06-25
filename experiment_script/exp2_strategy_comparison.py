"""Experiment 2: Five-condition strategy comparison (the main comparison).

Naive Epoch Concatenation vs Epoch-Aware Pipeline (Sec. 3.3.1–3.3.3).
Tests whether BLINKER-concat, MNE-annot, and DBO are outperformed by the proposed
three-stage pipeline, primarily through improved recall.

Threshold Estimator at Stage B (Sec. 3.3.4).
Tests whether the robust MAD-based (median) estimator outperforms the mean-based
estimator, especially for sessions with extreme outlier amplitudes.

Both contrasts share the same result table.  Strategy F runs with ``center_method``
``"mean"`` first and ``"median"`` second, as required by the experimental design.

Conditions
----------
kleifges / BLINKER-concat       — naive concatenation with BLINKER threshold.
nathanaelmne    — MNE annotate_amplitude routine.
DBO             — direct Bayesian optimisation without epoch screening.
dbo_drop_Mean   - with center_method="mean" at Stage B.
dbo_drop_Med    - with center_method="median" at Stage B (primary).

Datasets
--------
Drowsy Driving Raja corpus and murat_2018 dataset.

Statistical tests
-----------------
Pairwise Wilcoxon signed-rank tests on matched session-level F1 scores.
Proposed vs baselines: one-tailed (alternative="greater").
Proposed-Mean vs Proposed-Med: two-tailed.
Bonferroni correction: n_pairs = C(5, 2) = 10.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
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
from pyblinker.strategies import kleifges_strategy
from src.strategy_nathanael_mne.runner import blink_position_strategy_nathanael
from src.strategy_dbo.runner import blink_position_strategy_dbo
from src.strategy_dbo_drop.runner import channel_results_strategy_dbo_drop
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs,
    discover_murat_pairs,
    discover_raja_pairs,
    load_gt_annotations_for_pair,
    make_dataset_loaders,
    setup_tutorial_logging,
    valid_epoch_indices_for_pair,
)

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp2_strategy_comparison.yaml")
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
# Shared parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S       = float(_EXP_CFG.get("epoch_duration_s", 30.0))
FILTER_LOW             = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH            = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE          = 100
N_EPOCHS: int | None   = None  # positive int → limit epochs per session for quick runs

# Strategy nathanael_mne (MNE-annot) parameters
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ      = 1.0
MNE_HIGH_FREQ     = 20.0
MNE_THRESH        = None

# Strategy dbo parameters
STAGE1_THRESHOLD_SCOPE  = "per_channel"
AUTOREJECT_METHOD       = "bayesian_optimization"
STAGE1_SCAN_SCALE       = 0.12
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT      = False

# Strategy dbo_drop (Proposed-Mean / Proposed-Med) parameters
MIN_FLAGGED_EPOCHS = 1
STD_THRESHOLD      = float(_EXP_CFG.get("std_threshold", 3.5))

# Ordered list of conditions — Proposed-Mean (mean) runs before Proposed-Med (median)
CONDITIONS = ["BLINKER-concat",
              "MNE-annot",
              "DBO",
              "Proposed-Mean",
              "Proposed-Med"]
VISIBLE_CONDITIONS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
RUN_CONDITIONS = CONDITIONS

# Conditions that are hypothesised to outperform baselines → one-tailed Wilcoxon
_PROPOSED = frozenset({"Proposed-Mean", "Proposed-Med"})
_BASELINES = frozenset({"BLINKER-concat", "MNE-annot", "DBO"})




# ---------------------------------------------------------------------------
# Per-condition runners — return standard channel_results list
# ---------------------------------------------------------------------------

def _run_blinker_concat(prepared, valid_epoch_indices):
    return kleifges_strategy(prepared, valid_epoch_indices)


def _run_mne_annot(prepared, valid_epoch_indices):
    return blink_position_strategy_nathanael(
        prepared,
        valid_epoch_indices,
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )


def _run_dbo(prepared, valid_epoch_indices):
    setting = {
        "threshold_scope":       STAGE1_THRESHOLD_SCOPE,
        "scan_scale":            STAGE1_SCAN_SCALE,
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "autoreject_method":     AUTOREJECT_METHOD,
        "autoreject_augment":    AUTOREJECT_AUGMENT,
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


def _run_proposed_mean(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":     STD_THRESHOLD,
        "center_method":     "mean",
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":           VERBOSE,
    }
    return channel_results_strategy_dbo_drop(prepared, valid_epoch_indices, setting=setting)


def _run_proposed_med(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":     STD_THRESHOLD,
        "center_method":     "median",
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":           VERBOSE,
    }
    return channel_results_strategy_dbo_drop(prepared, valid_epoch_indices, setting=setting)


_CONDITION_RUNNERS = {
    "BLINKER-concat": _run_blinker_concat,
    "MNE-annot":      _run_mne_annot,
    "DBO":            _run_dbo,
    "Proposed-Mean":  _run_proposed_mean,
    "Proposed-Med":   _run_proposed_med,
}


# ---------------------------------------------------------------------------
# Single evaluation unit: one session × one condition
# ---------------------------------------------------------------------------

def run_one(pair: dict, condition: str) -> dict:
    """Load a session, run *condition*, evaluate against ground truth.

    Parameters
    ----------
    pair:
        Session descriptor dict with keys ``dataset``, ``name``, ``fif``, ``csv``.
    condition:
        One of the strings in ``CONDITIONS``.

    Returns
    -------
    dict with keys: dataset, session, condition, best_channel, tp, fp, fn,
    precision, recall, f1.
    """
    start_s = time.perf_counter()
    dataset_loaders = make_dataset_loaders(
        raja_region_yaml=RAJA_REGION_YAML, cao_region_yaml=CAO_REGION_YAML
    )
    load_fn = dataset_loaders[pair["dataset"]]
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
    prepared = apply_stage_a_channel_group(prepared, pair["dataset"])
    valid_epoch_indices = valid_epoch_indices_for_pair(pair, epochs, EPOCH_DURATION_S)
    channel_results = _CONDITION_RUNNERS[condition](prepared, valid_epoch_indices)

    gt_annotations = load_gt_annotations_for_pair(pair, EPOCH_DURATION_S, valid_epoch_indices)
    scored = evaluate_channels(
        channel_results,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
    )
    em = scored.best_eval_result.event_metrics
    return {
        "dataset":      pair["dataset"],
        "session":      pair["name"],
        "condition":    condition,
        "best_channel": scored.best_channel,
        "tp":           em.tp,
        "fp":           em.fp,
        "fn":           em.fn,
        "precision":    em.precision,
        "recall":       em.recall,
        "f1":           em.f1,
        "wall_clock_s":  time.perf_counter() - start_s,
    }


# ---------------------------------------------------------------------------
# Result printing
# ---------------------------------------------------------------------------

def _print_per_session_table(results: list[dict], dataset_name: str) -> None:
    """Print per-session metrics for *dataset_name* grouped by session."""
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: (r["session"], RUN_CONDITIONS.index(r["condition"])))

    W_sess = max(len(r["session"]) for r in rows)
    W_sess = max(W_sess, 8)
    W_cond = 14
    header = (
        f"{'session':<{W_sess}}  {'condition':<{W_cond}}  "
        f"{'tp':>5}  {'fp':>5}  {'fn':>5}  "
        f"{'precision':>10}  {'recall':>8}  {'f1':>8}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"PER-SESSION RESULTS - {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_session = None
    for r in rows:
        if prev_session and r["session"] != prev_session:
            print(sep)
        prev_session = r["session"]
        print(
            f"{r['session']:<{W_sess}}  {r['condition']:<{W_cond}}  "
            f"{r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  "
            f"{r['precision']:>10.4f}  {r['recall']:>8.4f}  {r['f1']:>8.4f}"
        )
    print(f"{'=' * len(header)}\n")


def _print_summary_table(results: list[dict], dataset_name: str) -> None:
    """Print macro-F1 and micro-F1 per condition for *dataset_name* (or 'all')."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["condition"]].append(r)

    header = (
        f"{'condition':<14}  {'N':>5}  "
        f"{'TP':>7}  {'FP':>7}  {'FN':>7}  "
        f"{'micro_P':>8}  {'micro_R':>8}  {'micro_F1':>8}  "
        f"{'macro_P':>8}  {'macro_R':>8}  {'macro_F1':>8}"
    )
    sep = "-" * len(header)

    title = f"SUMMARY - {dataset_name.upper()}"
    print(f"\n{'=' * len(header)}")
    print(title)
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for cond in RUN_CONDITIONS:
        if cond not in buckets:
            continue
        bucket = buckets[cond]
        total_tp = sum(r["tp"] for r in bucket)
        total_fp = sum(r["fp"] for r in bucket)
        total_fn = sum(r["fn"] for r in bucket)
        micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                    if (micro_p + micro_r) > 0 else 0.0)
        macro_p  = float(np.mean([r["precision"] for r in bucket]))
        macro_r  = float(np.mean([r["recall"]    for r in bucket]))
        macro_f1 = float(np.mean([r["f1"]        for r in bucket]))
        print(
            f"{cond:<14}  {len(bucket):>5}  "
            f"{total_tp:>7}  {total_fp:>7}  {total_fn:>7}  "
            f"{micro_p:>8.4f}  {micro_r:>8.4f}  {micro_f1:>8.4f}  "
            f"{macro_p:>8.4f}  {macro_r:>8.4f}  {macro_f1:>8.4f}"
        )
    print(f"{'=' * len(header)}\n")


def _summary_rows(results: list[dict], dataset_name: str) -> list[dict]:
    """Return micro/macro metrics per condition for *dataset_name* (or 'all')."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return []

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["condition"]].append(r)

    out: list[dict] = []
    for cond in RUN_CONDITIONS:
        if cond not in buckets:
            continue
        bucket = buckets[cond]
        total_tp = sum(r["tp"] for r in bucket)
        total_fp = sum(r["fp"] for r in bucket)
        total_fn = sum(r["fn"] for r in bucket)
        micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                    if (micro_p + micro_r) > 0 else 0.0)
        macro_p  = float(np.mean([r["precision"] for r in bucket]))
        macro_r  = float(np.mean([r["recall"]    for r in bucket]))
        macro_f1 = float(np.mean([r["f1"]        for r in bucket]))
        out.append({
            "dataset": dataset_name,
            "condition": cond,
            "n_sessions": int(len(bucket)),
            "tp": int(total_tp),
            "fp": int(total_fp),
            "fn": int(total_fn),
            "micro_precision": float(micro_p),
            "micro_recall": float(micro_r),
            "micro_f1": float(micro_f1),
            "macro_precision": float(macro_p),
            "macro_recall": float(macro_r),
            "macro_f1": float(macro_f1),
        })
    return out


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
        description="Experiments 2 & 3: five-condition strategy comparison (includes Proposed-Med).",
    )
    p.add_argument(
        "--epoch-duration-s",
        type=float,
        default=EPOCH_DURATION_S,
        help="Epoch duration in seconds (should be set to the best duration from Experiment 1).",
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
        help="Disable internal ThreadPoolExecutor.",
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
    p.add_argument(
        "--use-murat2018",
        action="store_true",
        help="Use Raja + Murat2018 instead of the default Raja + Cao2018.",
    )
    p.add_argument(
        "--cao-only",
        action="store_true",
        help="Run only Cao2018 sessions (ignored with --use-murat2018).",
    )
    p.add_argument(
        "--max-cao-sessions",
        type=int,
        default=None,
        help="Limit Cao2018 sessions after discovery.",
    )
    p.add_argument(
        "--visible-conditions-only",
        action="store_true",
        help="Run the four visible conditions and exclude DBO.",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Wilcoxon signed-rank tests
# ---------------------------------------------------------------------------

def _matched_rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    """Matched-pairs rank-biserial correlation r for the Wilcoxon signed-rank test.

    r ranges from -1 to +1; positive means a tends to exceed b.
    """
    diffs = a - b
    nonzero = diffs[diffs != 0]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero))
    T_plus = float(np.sum(ranks[nonzero > 0]))
    n = len(nonzero)
    return (2.0 * T_plus / (n * (n + 1) / 2.0)) - 1.0


def _run_wilcoxon_tests(results: list[dict], dataset_name: str) -> None:
    """Run all pairwise Wilcoxon tests on session-level F1 for *dataset_name*."""
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return

    lookup: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        lookup[r["session"]][r["condition"]] = r["f1"]

    complete = sorted(
        s for s, cmap in lookup.items()
        if all(c in cmap for c in RUN_CONDITIONS)
    )
    n_pairs = len(RUN_CONDITIONS) * (len(RUN_CONDITIONS) - 1) // 2
    alpha_corrected = 0.05 / n_pairs

    print(f"\nWilcoxon signed-rank tests - {dataset_name.upper()}")
    print(f"  n_sessions={len(complete)}  "
          f"n_comparisons={n_pairs}  "
          f"alpha_Bonferroni={alpha_corrected:.4f}")
    print(f"  {'Comparison':<38}  {'tail':<9}  {'W':>8}  {'p':>8}  {'r':>6}  sig")
    print(f"  {'-' * 80}")

    for i, ca in enumerate(RUN_CONDITIONS):
        for j, cb in enumerate(RUN_CONDITIONS):
            if j <= i:
                continue
            va = np.array([lookup[s][ca] for s in complete])
            vb = np.array([lookup[s][cb] for s in complete])

            # Determine direction: proposed > baseline → one-tailed
            if ca in _PROPOSED and cb in _BASELINES:
                alt, label = "greater", f"{ca} > {cb}"
            elif cb in _PROPOSED and ca in _BASELINES:
                # swap so proposed is always "a"
                va, vb = vb, va
                alt, label = "greater", f"{cb} > {ca}"
            else:
                alt, label = "two-sided", f"{ca} vs {cb}"

            diffs = va - vb
            if np.all(diffs == 0):
                print(f"  {label:<38}  {'-':<9}  all diffs zero")
                continue
            try:
                stat, p = wilcoxon(va, vb, alternative=alt)
                r = _matched_rank_biserial(va, vb)
                sig = "***" if p < alpha_corrected else "**" if p < 0.01 else "*" if p < 0.05 else ""
                print(
                    f"  {label:<38}  {alt:<9}  {stat:>8.1f}  {p:>8.4f}  {r:>6.3f}  {sig}"
                )
            except Exception as exc:
                print(f"  {label:<38}  error: {exc}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _collect_tasks(all_pairs: list[dict]) -> list[tuple[dict, str]]:
    """Build (pair, condition) task list with Proposed-Mean before Proposed-Med."""
    other_conditions = [c for c in RUN_CONDITIONS if c not in ("Proposed-Mean", "Proposed-Med")]
    ordered_conditions = other_conditions + ["Proposed-Mean", "Proposed-Med"]
    return [(pair, cond) for cond in ordered_conditions for pair in all_pairs]


def main() -> None:
    args = _parse_args()

    global USE_MULTITHREAD, VERBOSE, EPOCH_DURATION_S, N_EPOCHS, RUN_CONDITIONS
    USE_MULTITHREAD = not args.no_multithread
    VERBOSE = not args.quiet
    EPOCH_DURATION_S = float(args.epoch_duration_s)
    N_EPOCHS = args.n_epochs
    RUN_CONDITIONS = VISIBLE_CONDITIONS if args.visible_conditions_only else CONDITIONS

    setup_tutorial_logging()
    raja_pairs  = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    if args.use_murat2018:
        cao_pairs = []
        murat_pairs = discover_murat_pairs(MURAT_DATASET_ROOT)
        all_pairs = raja_pairs + murat_pairs
    else:
        cao_pairs = discover_cao_pairs(CAO_DATASET_ROOT)
        if args.max_cao_sessions is not None:
            cao_pairs = cao_pairs[:args.max_cao_sessions]
        murat_pairs = []
        all_pairs = cao_pairs if args.cao_only else raja_pairs + cao_pairs

    logger.info("Raja sessions  : %d", len(raja_pairs))
    logger.info("Murat subjects : %d", len(murat_pairs))
    logger.info("Cao2018 sessions: %d", len(cao_pairs))
    logger.info("Total sessions : %d", len(all_pairs))
    logger.info("Conditions     : %s", RUN_CONDITIONS)

    tasks = _collect_tasks(all_pairs)
    results: list[dict] = []
    errors:  list[str]  = []

    if USE_MULTITHREAD:
        logger.info("Running %d tasks with ThreadPoolExecutor …", len(tasks))
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one, pair, cond): (pair["name"], cond)
                for pair, cond in tasks
            }
            for future in as_completed(future_map):
                name, cond = future_map[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info("done  %s  %s  f1=%.4f", name, cond, result["f1"])
                except Exception as exc:
                    logger.error("%s  %s: %s", name, cond, exc)
                    errors.append(f"ERROR  {name}  {cond}: {exc}")
    else:
        logger.info("Running %d tasks sequentially …", len(tasks))
        for pair, cond in tasks:
            logger.info("running  %s  %s …", pair["name"], cond)
            try:
                result = run_one(pair, cond)
                results.append(result)
                logger.info("done     %s  %s  f1=%.4f", pair["name"], cond, result["f1"])
            except Exception as exc:
                logger.error("%s  %s: %s", pair["name"], cond, exc)
                errors.append(f"ERROR  {pair['name']}  {cond}: {exc}")

    if not results:
        print("No results collected.")
        return

    # Per-dataset per-session tables
    report_datasets = ("raja", "murat2018") if args.use_murat2018 else ("raja", "cao2018")
    for ds in report_datasets:
        _print_per_session_table(results, ds)

    # Summary tables: per dataset and combined
    for ds in (*report_datasets, "all"):
        _print_summary_table(results, ds)

    # Wilcoxon tests per dataset (sessions within each dataset are matched pairs)
    for ds in report_datasets:
        _run_wilcoxon_tests(results, ds)

    if args.out_dir is not None:
        out_dir: Path = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # NOTE: legacy ``exp41_*`` output basenames are retained intentionally
        # (read by paper_* helpers, result.tex, and scripts/run_orchestration.py);
        # do not rename to exp2_* or the downstream consumers break.
        _write_csv(out_dir / "exp41_strategy_comparison_results.csv", results)
        _write_csv(
            out_dir / "exp41_strategy_comparison_summary.csv",
            sum((_summary_rows(results, ds) for ds in report_datasets), []) + _summary_rows(results, "all"),
        )
        payload = {
            "experiment": "exp41_strategy_comparison",
            "epoch_duration_s": float(EPOCH_DURATION_S),
            "metric_primary": "macro_f1 (dataset=all, condition=Proposed-Med)",
            "n_rows": int(len(results)),
        }
        (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
