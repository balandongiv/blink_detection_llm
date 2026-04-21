"""Experiment 5: Robustness under user-initiated pre-rejection.

Simulates the real-world scenario where an analyst has already discarded a
fraction of epochs on quality grounds before the pipeline is invoked.
Pre-rejected epochs are withheld from the pipeline's valid epoch set and never
enter Stage A; the pipeline must tolerate this reduced input.

Design
------
For each session, a random subset of valid epochs is withheld from Stage A at
withholding rates of 0%, 20%, and 40%.  Each non-zero rate is replicated over
N_REPLICATIONS independent random draws; per-session F1 is averaged across
replications before statistical testing.

Ground truth is held fixed (blinks in withheld epochs appear as false negatives),
so the experiment specifically tests how the pipeline handles a non-representative
reduced input set.

Two-tailed Wilcoxon signed-rank tests compare each non-zero rate against 0%,
with Bonferroni correction for 2 non-reference rates.

Datasets
--------
Drowsy Driving Raja corpus and murat_2018.
"""

from __future__ import annotations

import random
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
VERBOSE: bool = False

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
PEAK_SIDE_TOLERANCE_S   = 0.01
WITHHOLDING_RATES       = [0.0, 0.2, 0.4]
REFERENCE_RATE          = 0.0
N_REPLICATIONS          = 20    # independent random draws per non-zero rate
RANDOM_SEED             = 0     # base seed; each replication adds its index
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
# Core evaluation helper
# ---------------------------------------------------------------------------

def _evaluate_with_reduced_epochs(
    pair: dict,
    prepared,
    valid_epoch_indices: list[int],
    ground_truth,
    n_epochs_total: int,
    sfreq: float,
    withheld_set: set[int],
) -> float:
    """Run Proposed-Med on the subset of valid epochs that excludes *withheld_set*.

    Blinks in withheld epochs count as false negatives in the evaluation.

    Returns
    -------
    float : session-level F1 score.
    """
    reduced_valid = [i for i in valid_epoch_indices if i not in withheld_set]

    if len(reduced_valid) == 0:
        return 0.0

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":      STD_THRESHOLD,
        "center_method":      CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":            VERBOSE,
    }
    channel_results = channel_results_strategy_f(prepared, reduced_valid, setting=setting)

    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=n_epochs_total,
        sfreq=sfreq,
        epoch_duration=EPOCH_DURATION_S,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )
    return scored.best_metrics.f1


# ---------------------------------------------------------------------------
# Single session evaluation across all withholding rates
# ---------------------------------------------------------------------------

def run_one_session(pair: dict) -> list[dict]:
    """Evaluate Proposed-Med across all withholding rates with replications.

    Returns
    -------
    List of dicts, one per (session, withholding_rate), with the average F1
    across replications and individual per-replication F1 values.
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
    n_epochs_total = len(epochs)
    sfreq = float(prepared.sfreq)

    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(pair["csv"], EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )

    records: list[dict] = []

    for rate in WITHHOLDING_RATES:
        n_withhold = int(round(rate * len(valid_epoch_indices)))

        if rate == REFERENCE_RATE or n_withhold == 0:
            # No withholding: single deterministic run
            f1 = _evaluate_with_reduced_epochs(
                pair, prepared, valid_epoch_indices, ground_truth,
                n_epochs_total, sfreq, withheld_set=set()
            )
            rep_f1s = [f1]
        else:
            # N_REPLICATIONS random draws of the withheld set
            rep_f1s = []
            for rep in range(N_REPLICATIONS):
                rng = random.Random(RANDOM_SEED + rep)
                withheld = set(rng.sample(valid_epoch_indices, n_withhold))
                f1_rep = _evaluate_with_reduced_epochs(
                    pair, prepared, valid_epoch_indices, ground_truth,
                    n_epochs_total, sfreq, withheld_set=withheld
                )
                rep_f1s.append(f1_rep)

        records.append({
            "dataset":        pair["dataset"],
            "session":        pair["name"],
            "rate":           rate,
            "rate_pct":       int(round(rate * 100)),
            "n_valid":        len(valid_epoch_indices),
            "n_withheld":     n_withhold,
            "mean_f1":        float(np.mean(rep_f1s)),
            "std_f1":         float(np.std(rep_f1s)),
            "rep_f1s":        rep_f1s,
        })

    return records


# ---------------------------------------------------------------------------
# Result printing
# ---------------------------------------------------------------------------

def _print_per_session_table(results: list[dict], dataset_name: str) -> None:
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: (r["session"], r["rate"]))

    W_sess = max(len(r["session"]) for r in rows)
    W_sess = max(W_sess, 8)
    header = (
        f"{'session':<{W_sess}}  {'rate%':>6}  "
        f"{'n_valid':>7}  {'n_withheld':>10}  "
        f"{'mean_f1':>9}  {'std_f1':>9}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 5 — PER-SESSION  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_session = None
    for r in rows:
        if prev_session and r["session"] != prev_session:
            print(sep)
        prev_session = r["session"]
        print(
            f"{r['session']:<{W_sess}}  {r['rate_pct']:>6}  "
            f"{r['n_valid']:>7}  {r['n_withheld']:>10}  "
            f"{r['mean_f1']:>9.4f}  {r['std_f1']:>9.4f}"
        )
    print(f"{'=' * len(header)}\n")


def _print_rate_summary(results: list[dict], dataset_name: str) -> None:
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return

    buckets: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["rate_pct"]].append(r)

    header = (
        f"{'rate%':>6}  {'N':>5}  "
        f"{'macro_mean_F1':>13}  {'macro_std_F1':>12}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 5 — RATE SUMMARY  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for rate_pct in sorted(buckets):
        bucket = buckets[rate_pct]
        macro_mean = float(np.mean([r["mean_f1"] for r in bucket]))
        macro_std  = float(np.mean([r["std_f1"]  for r in bucket]))
        ref_marker = " ←ref" if rate_pct == int(REFERENCE_RATE * 100) else ""
        print(f"{rate_pct:>6}  {len(bucket):>5}  {macro_mean:>13.4f}  {macro_std:>12.4f}{ref_marker}")
    print(f"{'=' * len(header)}\n")


def _matched_rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    diffs = a - b
    nonzero = diffs[diffs != 0]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero))
    T_plus = float(np.sum(ranks[nonzero > 0]))
    n = len(nonzero)
    return (2.0 * T_plus / (n * (n + 1) / 2.0)) - 1.0


def _run_wilcoxon_tests(results: list[dict], dataset_name: str) -> None:
    """Two-tailed Wilcoxon: each non-zero withholding rate vs the 0% reference."""
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return

    lookup: dict[str, dict[int, float]] = defaultdict(dict)
    for r in rows:
        lookup[r["session"]][r["rate_pct"]] = r["mean_f1"]

    ref_pct = int(REFERENCE_RATE * 100)
    non_ref_rates = [int(round(rt * 100)) for rt in WITHHOLDING_RATES if rt != REFERENCE_RATE]
    alpha_corrected = 0.05 / len(non_ref_rates)

    all_rates_pct = [int(round(rt * 100)) for rt in WITHHOLDING_RATES]
    complete = sorted(
        s for s, rmap in lookup.items()
        if all(rp in rmap for rp in all_rates_pct)
    )

    print(f"\nExp 5 — Wilcoxon vs {ref_pct}% reference  —  {dataset_name.upper()}")
    print(f"  n_sessions={len(complete)}  α_Bonferroni={alpha_corrected:.4f}")
    print(f"  {'Comparison':<18}  {'W':>8}  {'p':>8}  {'r':>6}  sig")
    print(f"  {'-' * 50}")

    ref_f1 = np.array([lookup[s][ref_pct] for s in complete])
    for rate_pct in non_ref_rates:
        rate_f1 = np.array([lookup[s][rate_pct] for s in complete])
        diffs = rate_f1 - ref_f1
        if np.all(diffs == 0):
            print(f"  {rate_pct}% vs {ref_pct}%  all diffs zero")
            continue
        try:
            stat, p = wilcoxon(rate_f1, ref_f1, alternative="two-sided")
            r = _matched_rank_biserial(rate_f1, ref_f1)
            sig = "***" if p < alpha_corrected else "**" if p < 0.01 else "*" if p < 0.05 else ""
            label = f"{rate_pct}% vs {ref_pct}%"
            print(f"  {label:<18}  {stat:>8.1f}  {p:>8.4f}  {r:>6.3f}  {sig}")
        except Exception as exc:
            print(f"  {rate_pct}% vs {ref_pct}%  error: {exc}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    raja_pairs  = _discover_raja_pairs()
    murat_pairs = _discover_murat_pairs()
    all_pairs   = raja_pairs + murat_pairs

    print(f"Raja sessions    : {len(raja_pairs)}")
    print(f"Murat subjects   : {len(murat_pairs)}")
    print(f"Withholding rates: {[f'{r*100:.0f}%' for r in WITHHOLDING_RATES]}")
    print(f"Replications     : {N_REPLICATIONS}  (per non-zero rate)")

    results: list[dict] = []
    errors:  list[str]  = []

    if USE_MULTITHREAD:
        print(f"\nRunning {len(all_pairs)} sessions with ThreadPoolExecutor …")
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one_session, pair): pair["name"]
                for pair in all_pairs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    records = future.result()
                    results.extend(records)
                    ref_r = next(r for r in records if r["rate"] == REFERENCE_RATE)
                    print(f"  done  {name}  f1@0%={ref_r['mean_f1']:.4f}")
                except Exception as exc:
                    msg = f"  ERROR  {name}: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"\nRunning {len(all_pairs)} sessions sequentially …")
        for pair in all_pairs:
            print(f"  running  {pair['name']} …")
            try:
                records = run_one_session(pair)
                results.extend(records)
                ref_r = next(r for r in records if r["rate"] == REFERENCE_RATE)
                print(f"  done     {pair['name']}  f1@0%={ref_r['mean_f1']:.4f}")
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
        _print_rate_summary(results, ds)

    for ds in ("raja", "murat2018"):
        _run_wilcoxon_tests(results, ds)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
