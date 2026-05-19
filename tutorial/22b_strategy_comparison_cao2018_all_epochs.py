"""Strategy comparison — A, B, C, F across cao_2018 dataset (no epoch rejection).

Identical to 22_strategy_comparison_cao2018.py except that epoch_health.csv is
ignored and ALL epochs are treated as healthy.  Every epoch contributes to
detection and is evaluated against the full ground truth.

Auto-discovers sessions under DATASET_ROOT/<subject_id>/<session_id>/ that:
  1. Have a Cao2018Viewer.yaml with status == "Complete"
  2. Have a matching <sid_lower>_<session_id>.fif and <sid_lower>_<session_id>.csv

Toggles
-------
USE_MULTITHREAD    False → sequential (easier to debug)
VERBOSE            diagnostic output from Strategy F stage A/B
OVERWRITE          False → skip tasks whose cache file already exists
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.epoch_input import prepare_epoch_detection_input
from src.strategy_kleifges.kleifges_blinker_2017 import kleifges_strategy
from src.strategy_nathanael_mne.runner import blink_position_strategy_nathanael
from src.strategy_c.runner import blink_position_strategy_c
from src.strategy_f.runner import channel_results_strategy_f

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
EPOCH_DURATION_S = 60.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Set to a positive integer to process only the first N epochs (quick inspection).
N_EPOCHS: int | None = None

# ---------------------------------------------------------------------------
# Strategy B parameters
# ---------------------------------------------------------------------------
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None

# ---------------------------------------------------------------------------
# Strategy C parameters
# ---------------------------------------------------------------------------
STAGE1_THRESHOLD_SCOPE = "per_channel"
AUTOREJECT_METHOD = "bayesian_optimization"
STAGE1_SCAN_SCALE = 0.12
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT = False

# ---------------------------------------------------------------------------
# Strategy F parameters
# ---------------------------------------------------------------------------
MIN_FLAGGED_EPOCHS = 1
STD_THRESHOLD = 3.5
CENTER_METHOD = "median"

STRATEGIES = ["A", "B", "C", "F"]


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
        sid = subject_dir.name
        for session_dir in sorted(subject_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            session_id = session_dir.name
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

            sessions.append({"name": label, "fif": fif, "csv": csv})

    if skipped_status:
        print(
            f"  [yaml-filter] skipped {len(skipped_status)} session(s) with"
            f" status != Complete: {', '.join(skipped_status)}"
        )
    if skipped_missing:
        print(
            f"  [files] skipped {len(skipped_missing)} Complete session(s)"
            f" missing fif or csv: {', '.join(skipped_missing)}"
        )
    return sessions


# ---------------------------------------------------------------------------
# Per-strategy runners
# ---------------------------------------------------------------------------

def _run_strategy_a(prepared, valid_epoch_indices):
    return kleifges_strategy(prepared, valid_epoch_indices)


def _run_strategy_b(prepared, valid_epoch_indices):
    return blink_position_strategy_nathanael(
        prepared,
        valid_epoch_indices,
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )


def _run_strategy_c(prepared, valid_epoch_indices):
    setting = {
        "threshold_scope": STAGE1_THRESHOLD_SCOPE,
        "scan_scale": STAGE1_SCAN_SCALE,
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "autoreject_method": AUTOREJECT_METHOD,
        "autoreject_augment": AUTOREJECT_AUGMENT,
    }
    return blink_position_strategy_c(prepared, valid_epoch_indices, setting=setting)


def _run_strategy_f(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose": VERBOSE,
    }
    return channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)


_STRATEGY_RUNNERS = {
    "A": _run_strategy_a,
    "B": _run_strategy_b,
    "C": _run_strategy_c,
    "F": _run_strategy_f,
}


# ---------------------------------------------------------------------------
# Single task: one strategy × one session
# ---------------------------------------------------------------------------

def _cache_path(fif_path: Path, strategy: str) -> Path:
    return fif_path.parent / "eval_cache" / f"strategy_{strategy}_all.json"


def run_one(
    session_name: str,
    fif_path: Path,
    csv_path: Path,
    strategy: str,
) -> dict:
    """Load data, run *strategy* on ALL epochs, evaluate, return metrics dict."""
    cache = _cache_path(fif_path, strategy)
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    n_total = len(epochs)
    all_epoch_indices = list(range(n_total))

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )

    channel_results = _STRATEGY_RUNNERS[strategy](prepared, all_epoch_indices)

    gt_annotations = load_ground_truth_annotations(csv_path, EPOCH_DURATION_S)

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
        "n_epochs": n_total,
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
        "n_epochs": 8,
        "tp": 5, "fp": 5, "fn": 5,
        "precision": 10, "recall": 8, "f1": 8,
    }

    header = (
        f"{'session':<{col_w['session']}}  "
        f"{'strategy':<{col_w['strategy']}}  "
        f"{'best_channel':<{col_w['best_channel']}}  "
        f"{'n_epochs':>{col_w['n_epochs']}}  "
        f"{'tp':>{col_w['tp']}}  "
        f"{'fp':>{col_w['fp']}}  "
        f"{'fn':>{col_w['fn']}}  "
        f"{'precision':>{col_w['precision']}}  "
        f"{'recall':>{col_w['recall']}}  "
        f"{'f1':>{col_w['f1']}}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print("STRATEGY COMPARISON RESULTS  —  cao_2018  (all epochs, no health rejection)")
    print(f"  epoch_duration={EPOCH_DURATION_S}s")
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
            f"{r['n_epochs']:>{col_w['n_epochs']}}  "
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
    print("OVERALL SUMMARY  (aggregated across all sessions)  —  cao_2018  (no health rejection)")
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
    print(f"Scanning {DATASET_ROOT}  [filter: yaml status == Complete]")
    print("  Epoch health filtering: DISABLED (all epochs treated as healthy)")
    sessions = discover_sessions(DATASET_ROOT)
    if not sessions:
        print(f"No Complete sessions found under {DATASET_ROOT}. Exiting.")
        return

    print(f"Discovered {len(sessions)} Complete session(s):")
    for s in sessions:
        print(f"  {s['name']}")

    all_tasks = [
        (s["name"], s["fif"], s["csv"], strategy)
        for s in sessions
        for strategy in STRATEGIES
    ]

    results: list[dict] = []
    errors: list[str] = []

    # Split into cached (load immediately) vs pending (need computation).
    pending_tasks = []
    if not OVERWRITE:
        for task in all_tasks:
            name, fif, csv, strat = task
            cache = _cache_path(fif, strat)
            if cache.is_file():
                results.append(json.loads(cache.read_text(encoding="utf-8")))
            else:
                pending_tasks.append(task)
        print(
            f"\nCache status (OVERWRITE=False): "
            f"{len(results)} cached, {len(pending_tasks)} to compute."
        )
    else:
        pending_tasks = all_tasks
        print(f"\nOVERWRITE=True: recomputing all {len(pending_tasks)} tasks.")

    if USE_MULTITHREAD and pending_tasks:
        print(f"Running {len(pending_tasks)} tasks with ThreadPoolExecutor …")
        with ThreadPoolExecutor() as executor:
            future_to_task = {
                executor.submit(run_one, name, fif, csv, strat): (name, strat)
                for name, fif, csv, strat in pending_tasks
            }
            for future in as_completed(future_to_task):
                session_name, strategy = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(
                        f"  done  session={session_name}  strategy={strategy}"
                        f"  n_epochs={result['n_epochs']}"
                        f"  f1={result['f1']:.4f}"
                    )
                except Exception as exc:
                    msg = f"  ERROR session={session_name}  strategy={strategy}: {exc}"
                    print(msg)
                    errors.append(msg)
    elif pending_tasks:
        print(f"Running {len(pending_tasks)} tasks sequentially …")
        for name, fif, csv, strat in pending_tasks:
            print(f"  running  session={name}  strategy={strat} …")
            try:
                result = run_one(name, fif, csv, strat)
                results.append(result)
                print(
                    f"  done     session={name}  strategy={strat}"
                    f"  n_epochs={result['n_epochs']}"
                    f"  f1={result['f1']:.4f}"
                )
            except Exception as exc:
                msg = f"  ERROR session={name}  strategy={strat}: {exc}"
                print(msg)
                errors.append(msg)

    if results:
        _print_results(results)

    if errors:
        print("Errors encountered:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
