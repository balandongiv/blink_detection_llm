"""Strategy comparison — kleifges, nathanael_mne, dbo, dbo_drop across cao_2018 dataset.

Auto-discovers sessions under DATASET_ROOT/<subject_id>/<session_id>/ that:
  1. Have a Cao2018Viewer.yaml with status == "Complete"
  2. Have a matching <sid_lower>_<session_id>.fif and <sid_lower>_<session_id>.csv

Epoch filtering
---------------
epoch_health.csv (30s granularity, health 1–5) controls which analysis epochs
are included.  For any given EPOCH_DURATION_S, an analysis epoch is dropped if
ANY overlapping 30s health sub-epoch has health <= HEALTH_DROP_THRESHOLD (3).
Dropped epochs are excluded from both detection and ground-truth evaluation.

Toggles
-------
USE_MULTITHREAD    False → sequential (easier to debug)
VERBOSE            diagnostic output from strategy dbo_drop
OVERWRITE          False → skip tasks whose cache file already exists
"""

from __future__ import annotations

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels, load_annotation_as_reference, enrich_absolute_times
from blink_evaluation.io import dataframe_to_annotations
from src.common.epoch_input import prepare_epoch_detection_input
from pyblinker.strategies import kleifges_strategy
from src.strategy_nathanael_mne.runner import blink_position_strategy_nathanael
from src.strategy_dbo.runner import blink_position_strategy_dbo
from src.strategy_dbo_drop.runner import channel_results_strategy_dbo_drop
from tutorial.tutorial_utils import setup_tutorial_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True
OVERWRITE: bool = False   # True → recompute even when a cache file exists

# ---------------------------------------------------------------------------
# Dataset root — sessions live as DATASET_ROOT/<subject_id>/<session_id>/
# ---------------------------------------------------------------------------
DATASET_ROOT = Path(r"D:\dataset\sustained_attention_driving")

# ---------------------------------------------------------------------------
# Shared parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S = 30.0
HEALTH_DROP_THRESHOLD = 3      # drop epoch if health <= this value (30s granularity)
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Set to a positive integer to process only the first N epochs (quick inspection).
N_EPOCHS: int | None = None

# ---------------------------------------------------------------------------
# Strategy nathanael_mne parameters
# ---------------------------------------------------------------------------
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None

# ---------------------------------------------------------------------------
# Strategy dbo parameters
# ---------------------------------------------------------------------------
STAGE1_THRESHOLD_SCOPE = "per_channel"
AUTOREJECT_METHOD = "bayesian_optimization"
STAGE1_SCAN_SCALE = 0.12
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT = False

# ---------------------------------------------------------------------------
# Strategy dbo_drop parameters
# ---------------------------------------------------------------------------
MIN_FLAGGED_EPOCHS = 1
STD_THRESHOLD = 3.5
CENTER_METHOD = "median"

STRATEGIES = ["kleifges", "nathanael_mne", "dbo", "dbo_drop"]


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------

def discover_sessions(root: Path) -> list[dict]:
    """Return all Complete sessions that have matching fif + csv pairs.

    Directory layout: root/<subject_id>/<session_id>/
    File naming:      <subject_id_lower>_<session_id>.fif / .csv
    """
    sessions: list[dict] = []
    skipped_status: list[str] = []
    skipped_missing: list[str] = []

    for subject_dir in sorted(root.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name  # e.g. "S01"
        for session_dir in sorted(subject_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            session_id = session_dir.name  # e.g. "051017m"
            label = f"{sid}/{session_id}"

            yaml_path = session_dir / "Cao2018Viewer.yaml"
            if not yaml_path.is_file():
                continue
            with yaml_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if data.get("status", "") != "Complete":
                skipped_status.append(label)
                continue

            sid_lower = sid.lower()
            fif = session_dir / f"{sid_lower}_{session_id}.fif"
            csv = session_dir / f"{sid_lower}_{session_id}.csv"
            if not (fif.is_file() and csv.is_file()):
                skipped_missing.append(label)
                continue

            epoch_health = session_dir / "epoch_health.csv"
            sessions.append({
                "name": label,
                "fif": fif,
                "csv": csv,
                "epoch_health": epoch_health if epoch_health.is_file() else None,
            })

    if skipped_status:
        logger.info(
            "[yaml-filter] skipped %d session(s) with status != Complete: %s",
            len(skipped_status), ", ".join(skipped_status),
        )
    if skipped_missing:
        logger.info(
            "[files] skipped %d Complete session(s) missing fif or csv: %s",
            len(skipped_missing), ", ".join(skipped_missing),
        )
    return sessions


# ---------------------------------------------------------------------------
# Epoch health filtering
# ---------------------------------------------------------------------------

def get_valid_epochs_from_health(
    epoch_health_path: Path | None,
    epoch_duration_s: float,
    n_epochs: int,
) -> list[int]:
    """Return valid epoch indices based on epoch_health.csv.

    An analysis epoch is dropped if any overlapping 30s health sub-epoch has
    health <= HEALTH_DROP_THRESHOLD.  If no epoch_health_path is provided
    every epoch is considered valid.
    """
    if epoch_health_path is None or not epoch_health_path.is_file():
        return list(range(n_epochs))

    df = pd.read_csv(epoch_health_path)
    df["health"] = pd.to_numeric(df["health"], errors="coerce")
    valid: list[int] = []
    for i in range(n_epochs):
        epoch_start = i * epoch_duration_s
        epoch_end = (i + 1) * epoch_duration_s
        overlapping = df[
            (df["epoch_start_s"] < epoch_end) & (df["epoch_end_s"] > epoch_start)
        ]
        if overlapping.empty or (overlapping["health"] > HEALTH_DROP_THRESHOLD).all():
            valid.append(i)
    return valid


# ---------------------------------------------------------------------------
# Per-strategy runners
# ---------------------------------------------------------------------------

def _run_strategy_kleifges(prepared, valid_epoch_indices):
    return kleifges_strategy(prepared, valid_epoch_indices)


def _run_strategy_nathanael_mne(prepared, valid_epoch_indices):
    return blink_position_strategy_nathanael(
        prepared,
        valid_epoch_indices,
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )


def _run_strategy_dbo(prepared, valid_epoch_indices):
    setting = {
        "threshold_scope": STAGE1_THRESHOLD_SCOPE,
        "scan_scale": STAGE1_SCAN_SCALE,
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "autoreject_method": AUTOREJECT_METHOD,
        "autoreject_augment": AUTOREJECT_AUGMENT,
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


def _run_strategy_dbo_drop(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose": VERBOSE,
    }
    return channel_results_strategy_dbo_drop(prepared, valid_epoch_indices, setting=setting)


_STRATEGY_RUNNERS = {
    "kleifges": _run_strategy_kleifges,
    "nathanael_mne": _run_strategy_nathanael_mne,
    "dbo": _run_strategy_dbo,
    "dbo_drop": _run_strategy_dbo_drop,
}


# ---------------------------------------------------------------------------
# Single task: one strategy × one session
# ---------------------------------------------------------------------------

def _cache_path(fif_path: Path, strategy: str) -> Path:
    return fif_path.parent / "eval_cache" / f"strategy_{strategy}_filtered.json"


def run_one(
    session_name: str,
    fif_path: Path,
    csv_path: Path,
    epoch_health_path: Path | None,
    strategy: str,
) -> dict:
    """Load data, run *strategy*, evaluate, return metrics dict."""
    cache = _cache_path(fif_path, strategy)
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    n_total = len(epochs)
    valid_epoch_indices = get_valid_epochs_from_health(
        epoch_health_path, EPOCH_DURATION_S, n_total
    )
    n_valid = len(valid_epoch_indices)
    n_dropped = n_total - n_valid

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )

    channel_results = _STRATEGY_RUNNERS[strategy](prepared, valid_epoch_indices)

    # Load ground truth and restrict to valid epochs only so that blinks in
    # dropped epochs do not inflate false-negative counts.
    ground_truth_raw = load_annotation_as_reference(csv_path, EPOCH_DURATION_S)
    ground_truth_valid = ground_truth_raw[
        ground_truth_raw["epoch_index"].isin(valid_epoch_indices)
    ].reset_index(drop=True)
    ground_truth_df = enrich_absolute_times(ground_truth_valid, EPOCH_DURATION_S)
    gt_annotations = dataframe_to_annotations(ground_truth_df)

    scored = evaluate_channels(
        channel_results,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
    )

    em = scored.best_eval_result.event_metrics
    result = {
        "session": session_name,
        "strategy": strategy,
        "best_channel": scored.best_channel,
        "n_total": n_total,
        "n_valid": n_valid,
        "n_dropped": n_dropped,
        "tp": em.tp,
        "fp": em.fp,
        "fn": em.fn,
        "precision": em.precision,
        "recall": em.recall,
        "f1": em.f1,
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_results(results: list[dict]) -> None:
    results.sort(key=lambda r: (r["session"], r["strategy"]))

    col_w = {
        "session": 18, "strategy": 10, "best_channel": 14,
        "n_valid": 8, "n_dropped": 9,
        "tp": 5, "fp": 5, "fn": 5,
        "precision": 10, "recall": 8, "f1": 8,
    }

    header = (
        f"{'session':<{col_w['session']}}  "
        f"{'strategy':<{col_w['strategy']}}  "
        f"{'best_channel':<{col_w['best_channel']}}  "
        f"{'n_valid':>{col_w['n_valid']}}  "
        f"{'n_dropped':>{col_w['n_dropped']}}  "
        f"{'tp':>{col_w['tp']}}  "
        f"{'fp':>{col_w['fp']}}  "
        f"{'fn':>{col_w['fn']}}  "
        f"{'precision':>{col_w['precision']}}  "
        f"{'recall':>{col_w['recall']}}  "
        f"{'f1':>{col_w['f1']}}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print("STRATEGY COMPARISON RESULTS  —  cao_2018")
    print(f"  epoch_duration={EPOCH_DURATION_S}s  health_drop_threshold<={HEALTH_DROP_THRESHOLD}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_session = None
    for r in results:
        if prev_session and r["session"] != prev_session:
            print(sep)
        prev_session = r["session"]
        print(
            f"{r['session']:<{col_w['session']}}  "
            f"{r['strategy']:<{col_w['strategy']}}  "
            f"{str(r['best_channel']):<{col_w['best_channel']}}  "
            f"{r['n_valid']:>{col_w['n_valid']}}  "
            f"{r['n_dropped']:>{col_w['n_dropped']}}  "
            f"{r['tp']:>{col_w['tp']}}  "
            f"{r['fp']:>{col_w['fp']}}  "
            f"{r['fn']:>{col_w['fn']}}  "
            f"{r['precision']:>{col_w['precision']}.4f}  "
            f"{r['recall']:>{col_w['recall']}.4f}  "
            f"{r['f1']:>{col_w['f1']}.4f}"
        )
    print(f"{'=' * len(header)}\n")

    _print_overall_summary(results)


def _print_overall_summary(results: list[dict]) -> None:
    """Print per-strategy aggregate metrics (micro + macro) across all sessions."""
    from collections import defaultdict

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        buckets[r["strategy"]].append(r)

    col_w = {
        "strategy": 10, "n_sessions": 10,
        "tp": 7, "fp": 7, "fn": 7,
        "micro_p": 10, "micro_r": 9, "micro_f1": 9,
        "macro_p": 10, "macro_r": 9, "macro_f1": 9,
    }

    header = (
        f"{'strategy':<{col_w['strategy']}}  "
        f"{'n_sessions':>{col_w['n_sessions']}}  "
        f"{'TP(sum)':>{col_w['tp']}}  "
        f"{'FP(sum)':>{col_w['fp']}}  "
        f"{'FN(sum)':>{col_w['fn']}}  "
        f"{'micro_P':>{col_w['micro_p']}}  "
        f"{'micro_R':>{col_w['micro_r']}}  "
        f"{'micro_F1':>{col_w['micro_f1']}}  "
        f"{'macro_P':>{col_w['macro_p']}}  "
        f"{'macro_R':>{col_w['macro_r']}}  "
        f"{'macro_F1':>{col_w['macro_f1']}}"
    )
    sep = "-" * len(header)

    print(f"{'=' * len(header)}")
    print("OVERALL SUMMARY  (aggregated across all sessions)  —  cao_2018")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for strategy in sorted(buckets):
        rows = buckets[strategy]
        total_tp = sum(r["tp"] for r in rows)
        total_fp = sum(r["fp"] for r in rows)
        total_fn = sum(r["fn"] for r in rows)

        micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = (
            2 * micro_p * micro_r / (micro_p + micro_r)
            if (micro_p + micro_r) > 0
            else 0.0
        )

        macro_p = sum(r["precision"] for r in rows) / len(rows)
        macro_r = sum(r["recall"] for r in rows) / len(rows)
        macro_f1 = sum(r["f1"] for r in rows) / len(rows)

        print(
            f"{strategy:<{col_w['strategy']}}  "
            f"{len(rows):>{col_w['n_sessions']}}  "
            f"{total_tp:>{col_w['tp']}}  "
            f"{total_fp:>{col_w['fp']}}  "
            f"{total_fn:>{col_w['fn']}}  "
            f"{micro_p:>{col_w['micro_p']}.4f}  "
            f"{micro_r:>{col_w['micro_r']}.4f}  "
            f"{micro_f1:>{col_w['micro_f1']}.4f}  "
            f"{macro_p:>{col_w['macro_p']}.4f}  "
            f"{macro_r:>{col_w['macro_r']}.4f}  "
            f"{macro_f1:>{col_w['macro_f1']}.4f}"
        )
    print(f"{'=' * len(header)}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    logger.info("Scanning %s  [filter: yaml status == Complete]", DATASET_ROOT)
    sessions = discover_sessions(DATASET_ROOT)
    if not sessions:
        logger.info("No Complete sessions found under %s. Exiting.", DATASET_ROOT)
        return

    logger.info("Discovered %d Complete session(s):", len(sessions))
    for s in sessions:
        health_tag = "epoch_health.csv" if s["epoch_health"] else "no epoch_health"
        logger.info("  %s  (%s)", s["name"], health_tag)

    all_tasks = [
        (s["name"], s["fif"], s["csv"], s["epoch_health"], strategy)
        for s in sessions
        for strategy in STRATEGIES
    ]

    results: list[dict] = []
    errors: list[str] = []

    # Split into cached (load immediately) vs pending (need computation).
    pending_tasks = []
    if not OVERWRITE:
        for task in all_tasks:
            name, fif, csv, health, strat = task
            cache = _cache_path(fif, strat)
            if cache.is_file():
                results.append(json.loads(cache.read_text(encoding="utf-8")))
            else:
                pending_tasks.append(task)
        logger.info(
            "Cache status (OVERWRITE=False): %d cached, %d to compute.",
            len(results), len(pending_tasks),
        )
    else:
        pending_tasks = all_tasks
        logger.info("OVERWRITE=True: recomputing all %d tasks.", len(pending_tasks))

    if USE_MULTITHREAD and pending_tasks:
        logger.info("Running %d tasks with ThreadPoolExecutor …", len(pending_tasks))
        with ThreadPoolExecutor() as executor:
            future_to_task = {
                executor.submit(run_one, name, fif, csv, health, strat): (name, strat)
                for name, fif, csv, health, strat in pending_tasks
            }
            for future in as_completed(future_to_task):
                session_name, strategy = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(
                        "done  session=%s  strategy=%s  valid=%d/%d  f1=%.4f",
                        session_name, strategy,
                        result["n_valid"], result["n_valid"] + result["n_dropped"],
                        result["f1"],
                    )
                except Exception as exc:
                    logger.error("session=%s  strategy=%s: %s", session_name, strategy, exc)
                    errors.append(f"ERROR session={session_name}  strategy={strategy}: {exc}")
    elif pending_tasks:
        logger.info("Running %d tasks sequentially …", len(pending_tasks))
        for name, fif, csv, health, strat in pending_tasks:
            logger.info("running  session=%s  strategy=%s …", name, strat)
            try:
                result = run_one(name, fif, csv, health, strat)
                results.append(result)
                logger.info(
                    "done     session=%s  strategy=%s  valid=%d/%d  f1=%.4f",
                    name, strat,
                    result["n_valid"], result["n_valid"] + result["n_dropped"],
                    result["f1"],
                )
            except Exception as exc:
                logger.error("session=%s  strategy=%s: %s", name, strat, exc)
                errors.append(f"ERROR session={name}  strategy={strat}: {exc}")

    if results:
        _print_results(results)

    if errors:
        print("Errors encountered:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
