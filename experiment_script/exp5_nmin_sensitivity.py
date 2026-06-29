"""Experiment 7: Sensitivity to the minimum suspicious-epoch count n_min.

n_min is the fallback threshold for Stage B: when the number of suspicious
epochs |B| < n_min, the pipeline falls back to using all valid epochs for
threshold estimation.  Too-low n_min risks estimating a threshold from an
unrepresentative handful of epochs; too-high n_min triggers the fallback
unnecessarily, discarding the benefit of Stage A.

Two complementary analyses are performed.

Part A — Threshold-variance analysis
    For each session that has ≥ N_MIN_RICH suspicious epochs after Stage A, the
    flagged epoch set B is randomly sub-sampled to n ∈ N_SUBSAMPLE_LEVELS.  For
    each n, Stage B is recomputed over N_SUBSAMPLES independent sub-samples and
    the inter-subsample standard deviation of the resulting threshold θ_c is
    recorded.  The smallest n at which the variance stabilises (knee point) gives
    an empirical lower bound for n_min.

Part B — Fallback-frequency analysis
    For each combination of epoch duration (from Experiment 3) and candidate
    n_min value, the fraction of sessions for which |B| < n_min is computed.
    This reveals whether the n_min choice interacts with epoch duration and which
    combinations lead to excessive fallback.

Datasets
--------
Drowsy Driving Raja corpus and Cao2018 sustained-attention driving corpus.
"""

from __future__ import annotations

import logging
import random
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.common.epoch_input import prepare_epoch_detection_input
from experiment_script.channel_group_config import apply_stage_a_channel_group
from pyblinker.double_thresholding import screen_epochs_with_autoreject
from pyblinker.double_thresholding import compute_flagged_epoch_threshold
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs, discover_raja_pairs, make_dataset_loaders, setup_tutorial_logging,
    valid_epoch_indices_for_pair,
)

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp5_nmin_sensitivity.yaml")
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
FILTER_LOW    = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH   = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE = 100
N_EPOCHS: int | None = None

# Stage A / B fixed settings
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD           = float(_EXP_CFG.get("std_threshold", 3.5))
CENTER_METHOD           = _EXP_CFG.get("center_method", "median")

# Part A — threshold-variance analysis
N_MIN_RICH       = 20                        # sessions with ≥ this many flagged epochs
N_SUBSAMPLE_LEVELS = [2, 3, 5, 7, 10, 15, 20]  # sub-sample sizes n
N_SUBSAMPLES     = 50                        # independent draws per n
RANDOM_SEED      = 42

# Part B — fallback-frequency analysis
FALLBACK_EPOCH_DURATIONS_S = [20.0, 30.0, 60.0, 120.0]
CANDIDATE_NMIN_VALUES      = [3, 5, 10]



# ---------------------------------------------------------------------------
# Part A helpers
# ---------------------------------------------------------------------------

def _run_stage_a(pair: dict, epoch_duration_s: float = 60.0):
    """Load session and run Stage A only. Return (prepared, valid_epoch_indices, flagged)."""
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
    screen_result = screen_epochs_with_autoreject(
        prepared,
        valid_epoch_indices,
        random_state=AUTOREJECT_RANDOM_STATE,
        verbose=VERBOSE,
    )
    return prepared, valid_epoch_indices, screen_result.flagged_valid_epoch_indices


def _threshold_variance_one_session(pair: dict) -> dict | None:
    """Run threshold-variance analysis for *pair* (Part A).

    Returns a dict with subsample-level std values, or None if the session
    does not have ≥ N_MIN_RICH suspicious epochs.
    """
    prepared, valid_epoch_indices, flagged = _run_stage_a(pair, epoch_duration_s=60.0)

    if len(flagged) < N_MIN_RICH:
        return None

    rng = random.Random(RANDOM_SEED)
    variance_by_n: dict[int, float] = {}

    for n in N_SUBSAMPLE_LEVELS:
        if n > len(flagged):
            continue
        thresh_samples: list[float] = []
        for _ in range(N_SUBSAMPLES):
            subsample = rng.sample(flagged, n)
            thresh_result = compute_flagged_epoch_threshold(
                prepared,
                valid_epoch_indices,
                subsample,
                std_threshold=STD_THRESHOLD,
                center_method=CENTER_METHOD,
                verbose=False,
            )
            # Average threshold across all channels for a single scalar summary
            avg_thresh = float(np.mean(list(thresh_result.thresholds.values())))
            thresh_samples.append(avg_thresh)
        variance_by_n[n] = float(np.std(thresh_samples))

    return {
        "dataset":        pair["dataset"],
        "session":        pair["name"],
        "n_flagged":      len(flagged),
        "variance_by_n":  variance_by_n,
    }


# ---------------------------------------------------------------------------
# Part B helpers
# ---------------------------------------------------------------------------

def _fallback_frequency_one_session(pair: dict, epoch_duration_s: float) -> dict:
    """Return the number of flagged epochs for *pair* at *epoch_duration_s*."""
    prepared, valid_epoch_indices, flagged = _run_stage_a(pair, epoch_duration_s=epoch_duration_s)
    return {
        "dataset":          pair["dataset"],
        "session":          pair["name"],
        "epoch_duration_s": epoch_duration_s,
        "n_flagged":        len(flagged),
        "n_valid":          len(valid_epoch_indices),
    }


# ---------------------------------------------------------------------------
# Printing utilities — Part A
# ---------------------------------------------------------------------------

def _print_variance_table(records: list[dict], dataset_name: str) -> None:
    rows = [r for r in records if r["dataset"] == dataset_name]
    if not rows:
        print(f"\nPart A — no qualifying sessions for {dataset_name}")
        return

    col_sess = max(len(r["session"]) for r in rows)
    col_sess = max(col_sess, 8)

    n_cols = [str(n) for n in N_SUBSAMPLE_LEVELS]
    col_n_width = 10

    header = (
        f"{'session':<{col_sess}}  {'n_flagged':>9}  "
        + "  ".join(f"{'std@n='+nc:>{col_n_width}}" for nc in n_cols)
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 7 PART A — THRESHOLD VARIANCE  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for r in sorted(rows, key=lambda x: x["session"]):
        parts = [f"{r['session']:<{col_sess}}  {r['n_flagged']:>9}"]
        for n in N_SUBSAMPLE_LEVELS:
            std_val = r["variance_by_n"].get(n, float("nan"))
            parts.append(f"{std_val:>{col_n_width}.6f}")
        print("  ".join(parts))

    # Column-wise averages
    print(sep)
    avg_parts = [f"{'MEAN':<{col_sess}}  {'':>9}"]
    for n in N_SUBSAMPLE_LEVELS:
        vals = [r["variance_by_n"].get(n) for r in rows if r["variance_by_n"].get(n) is not None]
        avg = float(np.mean(vals)) if vals else float("nan")
        avg_parts.append(f"{avg:>{col_n_width}.6f}")
    print("  ".join(avg_parts))
    print(f"{'=' * len(header)}\n")


# ---------------------------------------------------------------------------
# Printing utilities — Part B
# ---------------------------------------------------------------------------

def _print_fallback_table(records: list[dict], dataset_name: str) -> None:
    rows = [r for r in records if r["dataset"] == dataset_name]
    if not rows:
        return

    # Group by epoch_duration
    by_dur: dict[float, list[dict]] = defaultdict(list)
    for r in rows:
        by_dur[r["epoch_duration_s"]].append(r)

    # Compute n_sessions for header
    all_sessions = {r["session"] for r in rows}
    n_total = len(all_sessions)

    header = (
        f"{'dur_s':>6}  {'N':>5}  "
        + "  ".join(f"{'nmin='+str(nm)+' fallback%':>18}" for nm in CANDIDATE_NMIN_VALUES)
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 7 PART B — FALLBACK FREQUENCY  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for dur in sorted(by_dur):
        bucket = by_dur[dur]
        parts = [f"{dur:>6.0f}  {len(bucket):>5}"]
        for n_min in CANDIDATE_NMIN_VALUES:
            n_fallback = sum(1 for r in bucket if r["n_flagged"] < n_min)
            pct = 100.0 * n_fallback / len(bucket) if bucket else 0.0
            parts.append(f"{pct:>18.1f}")
        print("  ".join(parts))

    print(f"{'=' * len(header)}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    raja_pairs = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    cao_pairs  = discover_cao_pairs(CAO_DATASET_ROOT)
    all_pairs  = raja_pairs + cao_pairs

    logger.info("Raja sessions   : %d", len(raja_pairs))
    logger.info("Cao2018 sessions: %d", len(cao_pairs))

    # -----------------------------------------------------------------------
    # Part A — threshold-variance analysis at 60 s epoch duration
    # -----------------------------------------------------------------------
    logger.info("Part A — Threshold-variance analysis (epoch=60s)")

    variance_records: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        logger.info("Running %d sessions with ThreadPoolExecutor (Part A) …", len(all_pairs))
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(_threshold_variance_one_session, pair): pair["name"]
                for pair in all_pairs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    rec = future.result()
                    if rec is not None:
                        variance_records.append(rec)
                        logger.info("done  %s  n_flagged=%d", name, rec["n_flagged"])
                    else:
                        logger.info("skip  %s  (< %d flagged epochs)", name, N_MIN_RICH)
                except Exception as exc:
                    logger.error("%s: %s", name, exc)
                    errors.append(f"ERROR  {name}: {exc}")
    else:
        logger.info("Running %d sessions sequentially (Part A) …", len(all_pairs))
        for pair in all_pairs:
            logger.info("running  %s …", pair["name"])
            try:
                rec = _threshold_variance_one_session(pair)
                if rec is not None:
                    variance_records.append(rec)
                    logger.info("done  %s  n_flagged=%d", pair["name"], rec["n_flagged"])
                else:
                    logger.info("skip  %s  (< %d flagged epochs)", pair["name"], N_MIN_RICH)
            except Exception as exc:
                logger.error("%s: %s", pair["name"], exc)
                errors.append(f"ERROR  {pair['name']}: {exc}")

    for ds in ("raja", "cao2018"):
        _print_variance_table(variance_records, ds)

    # -----------------------------------------------------------------------
    # Part B — fallback-frequency analysis across epoch durations
    # -----------------------------------------------------------------------
    logger.info("Part B — Fallback-frequency analysis")

    fallback_records: list[dict] = []
    tasks_b = [
        (pair, dur)
        for dur in FALLBACK_EPOCH_DURATIONS_S
        for pair in all_pairs
    ]

    if USE_MULTITHREAD:
        logger.info("Running %d tasks with ThreadPoolExecutor (Part B) …", len(tasks_b))
        with ThreadPoolExecutor() as executor:
            future_map_b = {
                executor.submit(_fallback_frequency_one_session, pair, dur): (pair["name"], dur)
                for pair, dur in tasks_b
            }
            for future in as_completed(future_map_b):
                name, dur = future_map_b[future]
                try:
                    rec = future.result()
                    fallback_records.append(rec)
                    logger.info("done  %s  dur=%.0fs  n_flagged=%d", name, dur, rec["n_flagged"])
                except Exception as exc:
                    logger.error("%s  dur=%.0fs: %s", name, dur, exc)
                    errors.append(f"ERROR  {name}  dur={dur:.0f}s: {exc}")
    else:
        logger.info("Running %d tasks sequentially (Part B) …", len(tasks_b))
        for pair, dur in tasks_b:
            logger.info("running  %s  dur=%.0fs …", pair["name"], dur)
            try:
                rec = _fallback_frequency_one_session(pair, dur)
                fallback_records.append(rec)
                logger.info("done  %s  dur=%.0fs  n_flagged=%d", pair["name"], dur, rec["n_flagged"])
            except Exception as exc:
                logger.error("%s  dur=%.0fs: %s", pair["name"], dur, exc)
                errors.append(f"ERROR  {pair['name']}  dur={dur:.0f}s: {exc}")

    for ds in ("raja", "cao2018"):
        _print_fallback_table(fallback_records, ds)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
