"""Experiments 1 & 2: Five-condition strategy comparison.

Experiment 1 — Naive Epoch Concatenation vs Epoch-Aware Pipeline (Sec. 3.3.1–3.3.3).
Tests whether BLINKER-concat, MNE-annot, and DBO are outperformed by the proposed
three-stage pipeline, primarily through improved recall.

Experiment 2 — Threshold Estimator at Stage B (Sec. 3.3.4).
Tests whether the robust MAD-based (median) estimator outperforms the mean-based
estimator, especially for sessions with extreme outlier amplitudes.

Both experiments share the same result table.  Strategy F runs with ``center_method``
``"mean"`` first and ``"median"`` second, as required by the experimental design.

Conditions
----------
BLINKER-concat  Strategy A — naive concatenation with BLINKER threshold.
MNE-annot       Strategy B — MNE annotate_amplitude routine.
DBO             Strategy C — direct Bayesian optimisation without epoch screening.
Proposed-Mean   Strategy F with center_method="mean" at Stage B.
Proposed-Med    Strategy F with center_method="median" at Stage B (primary).

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

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.strategy_kleifges.kleifges_blinker_2017 import kleifges_strategy
from src.strategy_b.runner import blink_position_strategy_b
from src.strategy_c.runner import blink_position_strategy_c
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
# Shared parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S       = 60.0
FILTER_LOW             = 1.0
FILTER_HIGH            = 20.0
RESAMPLE_RATE          = None
N_EPOCHS: int | None   = None  # positive int → limit epochs per session for quick runs

# Strategy B (MNE-annot) parameters
MNE_HALF_WINDOW_S = 0.10
MNE_LOW_FREQ      = 1.0
MNE_HIGH_FREQ     = 20.0
MNE_THRESH        = None

# Strategy C (DBO) parameters
STAGE1_THRESHOLD_SCOPE  = "per_channel"
AUTOREJECT_METHOD       = "bayesian_optimization"
STAGE1_SCAN_SCALE       = 0.12
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT      = False

# Strategy F (Proposed-Mean / Proposed-Med) parameters
MIN_FLAGGED_EPOCHS = 1
STD_THRESHOLD      = 3.5

# Ordered list of conditions — Proposed-Mean (mean) runs before Proposed-Med (median)
CONDITIONS = ["BLINKER-concat", "MNE-annot", "DBO", "Proposed-Mean", "Proposed-Med"]

# Conditions that are hypothesised to outperform baselines → one-tailed Wilcoxon
_PROPOSED = frozenset({"Proposed-Mean", "Proposed-Med"})
_BASELINES = frozenset({"BLINKER-concat", "MNE-annot", "DBO"})


# ---------------------------------------------------------------------------
# Dataset discovery
# ---------------------------------------------------------------------------

def _discover_raja_pairs() -> list[dict]:
    """Return Raja sessions with status == 'complete_eeg' that have .fif and .csv."""
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
    """Return murat_2018 subjects that have both <id>.fif and <id>.csv."""
    pairs: list[dict] = []
    for subject_dir in sorted(MURAT_DATASET_ROOT.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name
        fif = subject_dir / f"{sid}.fif"
        csv = subject_dir / f"{sid}.csv"
        if fif.is_file() and csv.is_file():
            pairs.append({
                "dataset": "murat2018",
                "name":    sid,
                "fif":     fif,
                "csv":     csv,
            })
    return pairs


# ---------------------------------------------------------------------------
# Raw loading helpers (dataset-specific)
# ---------------------------------------------------------------------------

def _load_raja_raw(fif_path: Path) -> mne.io.BaseRaw:
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    return load_raw_with_brain_channels(fif_path, brain_channels)


def _load_murat_raw(fif_path: Path) -> mne.io.BaseRaw:
    return mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")


_DATASET_LOADERS: dict[str, object] = {
    "raja":     _load_raja_raw,
    "murat2018": _load_murat_raw,
}


# ---------------------------------------------------------------------------
# Per-condition runners — return standard channel_results list
# ---------------------------------------------------------------------------

def _run_blinker_concat(prepared, valid_epoch_indices):
    return kleifges_strategy(prepared, valid_epoch_indices)


def _run_mne_annot(prepared, valid_epoch_indices):
    return blink_position_strategy_b(
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
    return blink_position_strategy_c(prepared, valid_epoch_indices, setting=setting)


def _run_proposed_mean(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":     STD_THRESHOLD,
        "center_method":     "mean",
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":           VERBOSE,
    }
    return channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)


def _run_proposed_med(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":     STD_THRESHOLD,
        "center_method":     "median",
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":           VERBOSE,
    }
    return channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)


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
    channel_results = _CONDITION_RUNNERS[condition](prepared, valid_epoch_indices)

    gt_annotations = load_ground_truth_annotations(pair["csv"], EPOCH_DURATION_S)
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
    }


# ---------------------------------------------------------------------------
# Result printing
# ---------------------------------------------------------------------------

def _print_per_session_table(results: list[dict], dataset_name: str) -> None:
    """Print per-session metrics for *dataset_name* grouped by session."""
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: (r["session"], CONDITIONS.index(r["condition"])))

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
    print(f"PER-SESSION RESULTS  —  {dataset_name.upper()}")
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

    title = f"SUMMARY — {dataset_name.upper()}"
    print(f"\n{'=' * len(header)}")
    print(title)
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for cond in CONDITIONS:
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
        if all(c in cmap for c in CONDITIONS)
    )
    n_pairs = len(CONDITIONS) * (len(CONDITIONS) - 1) // 2
    alpha_corrected = 0.05 / n_pairs

    print(f"\nWilcoxon signed-rank tests  —  {dataset_name.upper()}")
    print(f"  n_sessions={len(complete)}  "
          f"n_comparisons={n_pairs}  "
          f"α_Bonferroni={alpha_corrected:.4f}")
    print(f"  {'Comparison':<38}  {'tail':<9}  {'W':>8}  {'p':>8}  {'r':>6}  sig")
    print(f"  {'-' * 80}")

    for i, ca in enumerate(CONDITIONS):
        for j, cb in enumerate(CONDITIONS):
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
                print(f"  {label:<38}  {'—':<9}  all diffs zero")
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
    other_conditions = [c for c in CONDITIONS if c not in ("Proposed-Mean", "Proposed-Med")]
    ordered_conditions = other_conditions + ["Proposed-Mean", "Proposed-Med"]
    return [(pair, cond) for cond in ordered_conditions for pair in all_pairs]


def main() -> None:
    raja_pairs  = _discover_raja_pairs()
    murat_pairs = _discover_murat_pairs()
    all_pairs   = raja_pairs + murat_pairs

    print(f"Raja sessions  : {len(raja_pairs)}")
    print(f"Murat subjects : {len(murat_pairs)}")
    print(f"Total sessions : {len(all_pairs)}")
    print(f"Conditions     : {CONDITIONS}")

    tasks = _collect_tasks(all_pairs)
    results: list[dict] = []
    errors:  list[str]  = []

    if USE_MULTITHREAD:
        print(f"\nRunning {len(tasks)} tasks with ThreadPoolExecutor …")
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
                    print(f"  done  {name}  {cond}  f1={result['f1']:.4f}")
                except Exception as exc:
                    msg = f"  ERROR  {name}  {cond}: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"\nRunning {len(tasks)} tasks sequentially …")
        for pair, cond in tasks:
            print(f"  running  {pair['name']}  {cond} …")
            try:
                result = run_one(pair, cond)
                results.append(result)
                print(f"  done     {pair['name']}  {cond}  f1={result['f1']:.4f}")
            except Exception as exc:
                msg = f"  ERROR  {pair['name']}  {cond}: {exc}"
                print(msg)
                errors.append(msg)

    if not results:
        print("No results collected.")
        return

    # Per-dataset per-session tables
    for ds in ("raja", "murat2018"):
        _print_per_session_table(results, ds)

    # Summary tables: per dataset and combined
    for ds in ("raja", "murat2018", "all"):
        _print_summary_table(results, ds)

    # Wilcoxon tests per dataset (sessions within each dataset are matched pairs)
    for ds in ("raja", "murat2018"):
        _run_wilcoxon_tests(results, ds)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
