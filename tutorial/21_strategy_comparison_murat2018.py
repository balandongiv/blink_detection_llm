"""Strategy comparison — A, B, C, F across murat_2018 dataset.

Auto-discovers subjects that have a complete pair (matching <id>.fif + <id>.csv)
under DATASET_ROOT. Subjects with only a .fif (annotation not yet ready) are
silently skipped.

Toggles
-------
USE_MULTITHREAD        False → sequential (easier to debug)
VERBOSE                diagnostic output from Strategy F stage A/B
USE_YAML_STATUS_FILTER When True, also reads Murat2018Viewer.yaml in each
                       subject folder and skips any subject whose status is not
                       "Completed".  When False (default), only the presence of
                       <id>.fif + <id>.csv determines inclusion.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.analysis.lane_evaluation import evaluate_channel_lanes
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference
from pyblinker.strategy_a.kleifges_blinker_2017 import kleifges_strategy_a
from pyblinker.strategy_b.runner import blink_position_strategy_b
from pyblinker.strategy_c.runner import blink_position_strategy_c
from pyblinker.strategy_f.runner import channel_results_strategy_f

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True        # False → sequential (easier to debug)
VERBOSE: bool = True                # diagnostic output from Strategy F stage A/B
USE_YAML_STATUS_FILTER: bool = False  # True → only include subjects where
                                      # Murat2018Viewer.yaml status == "Completed"

# ---------------------------------------------------------------------------
# Dataset root — subjects live as DATASET_ROOT/<id>/<id>.fif + <id>.csv
# ---------------------------------------------------------------------------
DATASET_ROOT = Path(r"D:\dataset\murat_2018")

# ---------------------------------------------------------------------------
# Shared parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S = 60.0
PEAK_SIDE_TOLERANCE_S = 0.01
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
# Auto-discover complete pairs
# ---------------------------------------------------------------------------

def _yaml_status_is_completed(subject_dir: Path) -> bool:
    """Return True if Murat2018Viewer.yaml exists and status == 'Completed'."""
    yaml_path = subject_dir / "Murat2018Viewer.yaml"
    if not yaml_path.is_file():
        return False
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("status", "") == "Completed"


def discover_pairs(root: Path, use_yaml_filter: bool = False) -> list[dict]:
    """Return pairs where both <id>.fif and <id>.csv exist under root/<id>/.

    When *use_yaml_filter* is True, additionally requires that
    Murat2018Viewer.yaml reports ``status: Completed``.
    """
    pairs = []
    skipped_yaml: list[str] = []
    for subject_dir in sorted(root.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name
        fif = subject_dir / f"{sid}.fif"
        csv = subject_dir / f"{sid}.csv"
        if not (fif.is_file() and csv.is_file()):
            continue
        if use_yaml_filter and not _yaml_status_is_completed(subject_dir):
            skipped_yaml.append(sid)
            continue
        pairs.append({"name": sid, "fif": fif, "csv": csv})

    if skipped_yaml:
        print(
            f"  [yaml-filter] skipped {len(skipped_yaml)} subject(s) with"
            f" status != Completed: {', '.join(skipped_yaml)}"
        )
    return pairs


# ---------------------------------------------------------------------------
# Per-strategy runners
# ---------------------------------------------------------------------------

def _run_strategy_a(prepared, valid_epoch_indices):
    return kleifges_strategy_a(prepared, valid_epoch_indices)


def _run_strategy_b(prepared, valid_epoch_indices):
    return blink_position_strategy_b(
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
# Single task: one strategy × one pair
# ---------------------------------------------------------------------------

def run_one(pair_name: str, fif_path: Path, csv_path: Path, strategy: str) -> dict:
    """Load data, run *strategy*, evaluate, return metrics dict."""
    # murat_2018 uses channels CH1/CH2 — load all channels directly instead of
    # filtering by brain_region.yaml (which targets a different dataset).
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
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

    channel_results = _STRATEGY_RUNNERS[strategy](prepared, valid_epoch_indices)

    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(csv_path, EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )

    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=EPOCH_DURATION_S,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )

    m = scored.best_metrics
    return {
        "pair": pair_name,
        "strategy": strategy,
        "best_channel": scored.best_result["channel"],
        "tp": m.true_positives,
        "fp": m.false_positives,
        "fn": m.false_negatives,
        "precision": m.precision,
        "recall": m.recall,
        "f1": m.f1,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _print_results(results: list[dict]) -> None:
    results.sort(key=lambda r: (r["pair"], r["strategy"]))

    col_w = {"pair": 12, "strategy": 10, "best_channel": 14,
              "tp": 5, "fp": 5, "fn": 5,
              "precision": 10, "recall": 8, "f1": 8}

    header = (
        f"{'pair':<{col_w['pair']}}  "
        f"{'strategy':<{col_w['strategy']}}  "
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
    print("STRATEGY COMPARISON RESULTS  —  murat_2018")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_pair = None
    for r in results:
        if prev_pair and r["pair"] != prev_pair:
            print(sep)
        prev_pair = r["pair"]
        print(
            f"{r['pair']:<{col_w['pair']}}  "
            f"{r['strategy']:<{col_w['strategy']}}  "
            f"{str(r['best_channel']):<{col_w['best_channel']}}  "
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
    """Print per-strategy aggregate metrics (micro + macro) across all pairs."""
    from collections import defaultdict

    # Collect per-strategy buckets
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        buckets[r["strategy"]].append(r)

    col_w = {"strategy": 10, "n_pairs": 8,
              "tp": 7, "fp": 7, "fn": 7,
              "micro_p": 10, "micro_r": 9, "micro_f1": 9,
              "macro_p": 10, "macro_r": 9, "macro_f1": 9}

    header = (
        f"{'strategy':<{col_w['strategy']}}  "
        f"{'n_pairs':>{col_w['n_pairs']}}  "
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
    print("OVERALL SUMMARY  (aggregated across all pairs)  —  murat_2018")
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
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                    if (micro_p + micro_r) > 0 else 0.0)

        macro_p = sum(r["precision"] for r in rows) / len(rows)
        macro_r = sum(r["recall"] for r in rows) / len(rows)
        macro_f1 = sum(r["f1"] for r in rows) / len(rows)

        print(
            f"{strategy:<{col_w['strategy']}}  "
            f"{len(rows):>{col_w['n_pairs']}}  "
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


def main() -> None:
    filter_label = "csv-pair + yaml-Completed" if USE_YAML_STATUS_FILTER else "csv-pair only"
    print(f"Scanning {DATASET_ROOT}  [filter: {filter_label}]")
    pairs = discover_pairs(DATASET_ROOT, use_yaml_filter=USE_YAML_STATUS_FILTER)
    if not pairs:
        print(f"No complete pairs found under {DATASET_ROOT}. Exiting.")
        return

    print(f"Discovered {len(pairs)} complete pair(s):")
    for p in pairs:
        print(f"  {p['name']}")

    tasks = [
        (pair["name"], pair["fif"], pair["csv"], strategy)
        for pair in pairs
        for strategy in STRATEGIES
    ]

    results: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        print(f"\nRunning {len(tasks)} tasks with ThreadPoolExecutor …")
        with ThreadPoolExecutor() as executor:
            future_to_task = {
                executor.submit(run_one, name, fif, csv, strat): (name, strat)
                for name, fif, csv, strat in tasks
            }
            for future in as_completed(future_to_task):
                pair_name, strategy = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  done  pair={pair_name}  strategy={strategy}  f1={result['f1']:.4f}")
                except Exception as exc:
                    msg = f"  ERROR pair={pair_name}  strategy={strategy}: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"\nRunning {len(tasks)} tasks sequentially …")
        for name, fif, csv, strat in tasks:
            print(f"  running  pair={name}  strategy={strat} …")
            try:
                result = run_one(name, fif, csv, strat)
                results.append(result)
                print(f"  done     pair={name}  strategy={strat}  f1={result['f1']:.4f}")
            except Exception as exc:
                msg = f"  ERROR pair={name}  strategy={strat}: {exc}"
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
