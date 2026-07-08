"""Experiment 46: STAGE1_SCAN_SCALE optimisation for Strategy DBO via Bayesian Optimisation.

The scan threshold applied per channel is:

    scan_threshold = raw_threshold * scan_scale

Raw autoreject thresholds are expensive (they run Bayesian optimisation internally), so
they are precomputed ONCE per subject with scale=1.0. Finding the best scan_scale is then
a cheap multiplicative post-step evaluated across all precomputed subjects.

A Gaussian-Process Bayesian optimisation (GP-BO) loop searches the scan_scale in
log-space to maximise macro-averaged F1 across all raja sessions. After convergence, the
selected scale is cross-validated on the independent cao_2018 dataset.

Usage (standalone):
    conda run -n pyblinker_worktree_epoch_blink \\
        python tutorial/46_dbo_scan_scale_tuning.py \\
        --epoch-duration-s 30 \\
        --out-dir logs/exp46

Usage (via orchestration):
    python scripts/run_orchestration.py
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np
import pandas as pd
import yaml
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern
from scipy.stats import norm as scipy_norm

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import (
    evaluate_channels,
    load_ground_truth_annotations,
    load_annotation_as_reference,
    enrich_absolute_times,
)
from blink_evaluation.io import dataframe_to_annotations
from pyblinker.blinker.get_blink_positions import scan_threshold_crossings_kleifges
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import prepare_epoch_detection_input
from src.common.pipeline_utils import build_epoch_boundaries, build_signal_by_epoch
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.strategy_dbo.single_channel_autoreject import learn_strategy_dbo_thresholds
from src.utils.dataset_discovery import discover_raja_pairs
from src.utils.experiment_utils import setup_tutorial_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataset paths
# ---------------------------------------------------------------------------
ANNOTATION_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
PROCESSED_BASE_DIR  = Path(r"D:\dataset\drowsy_driving_raja_processed")
CAO2018_ROOT        = Path(r"D:\dataset\sustained_attention_driving")

# ---------------------------------------------------------------------------
# Shared EEG parameters
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML    = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S     = 30.0
FILTER_LOW           = 1.0
FILTER_HIGH          = 20.0
RESAMPLE_RATE        = None
HEALTH_DROP_THRESHOLD = 3

# ---------------------------------------------------------------------------
# Fixed DBO settings
# ---------------------------------------------------------------------------
AUTOREJECT_METHOD        = "bayesian_optimization"
STAGE1_THRESHOLD_SCOPE   = "per_channel"
AUTOREJECT_RANDOM_STATE  = 42
AUTOREJECT_AUGMENT       = False
MIN_EVENT_LEN_S          = 0.05

# ---------------------------------------------------------------------------
# Bayesian optimisation configuration
# ---------------------------------------------------------------------------
BO_SCALE_BOUNDS:   tuple[float, float] = (0.01, 2.0)  # log-uniform search range
N_BO_CALLS:        int   = 25    # total evaluations (random + GP-guided)
N_INITIAL_POINTS:  int   = 5     # random points before GP fits
BO_RANDOM_STATE:   int   = 42
BO_N_CANDIDATES:   int   = 1000  # dense grid for acquisition maximisation
BO_XI:             float = 0.01  # EI exploration bonus

USE_MULTITHREAD: bool = True


# ---------------------------------------------------------------------------
# Precomputation — expensive, run once per subject
# ---------------------------------------------------------------------------

def _precompute_raja_one(pair: dict, epoch_duration_s: float) -> dict | None:
    """Load a raja session and compute raw autoreject thresholds (scale=1.0)."""
    pair_name = pair["name"]
    try:
        brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
        raw = load_raw_with_brain_channels(pair["fif"], brain_channels)
        epochs = mne.make_fixed_length_epochs(
            raw, duration=epoch_duration_s, preload=True, verbose="ERROR"
        )
        prepared = prepare_epoch_detection_input(
            epochs,
            pick_types_options={"eeg": True},
            filter_low=FILTER_LOW,
            filter_high=FILTER_HIGH,
            resample_rate=RESAMPLE_RATE,
        )
        valid_epoch_indices = get_valid_epoch_indices(epochs)

        threshold_result = learn_strategy_dbo_thresholds(
            prepared,
            valid_epoch_indices,
            stage1_threshold_scope=STAGE1_THRESHOLD_SCOPE,
            autoreject_method=AUTOREJECT_METHOD,
            stage1_scan_scale=1.0,   # raw thresholds; scale applied separately
            autoreject_random_state=AUTOREJECT_RANDOM_STATE,
            autoreject_augment=AUTOREJECT_AUGMENT,
        )
        gt_annotations = load_ground_truth_annotations(pair["csv"], epoch_duration_s)
        epoch_boundaries = build_epoch_boundaries(
            len(valid_epoch_indices), prepared.epoch_length_samples
        )
        signal_by_epochs = {
            ch: build_signal_by_epoch(prepared, prepared.channel_names.index(ch))
            for ch in threshold_result.channel_names
        }
        return {
            "pair_name":           pair_name,
            "dataset":             "raja",
            "prepared":            prepared,
            "valid_epoch_indices": valid_epoch_indices,
            "raw_thresholds":      dict(threshold_result.raw_thresholds),
            "channel_names":       list(threshold_result.channel_names),
            "sfreq":               float(prepared.sfreq),
            "epoch_boundaries":    epoch_boundaries,
            "signal_by_epochs":    signal_by_epochs,
            "gt_annotations":      gt_annotations,
            "epoch_duration_s":    epoch_duration_s,
        }
    except Exception as exc:
        logger.error("precompute raja  pair=%s: %s", pair_name, exc)
        return None


def precompute_raja_thresholds(
    pairs: list[dict], epoch_duration_s: float
) -> list[dict]:
    """Precompute autoreject thresholds for all raja pairs."""
    logger.info("Precomputing autoreject thresholds for %d raja subjects …", len(pairs))
    results: list[dict] = []

    if USE_MULTITHREAD:
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(_precompute_raja_one, pair, epoch_duration_s): pair["name"]
                for pair in pairs
            }
            for future in as_completed(future_map):
                result = future.result()
                if result is not None:
                    results.append(result)
                    logger.info(
                        "precompute ok  %s  sfreq=%.0f  n_channels=%d",
                        result["pair_name"], result["sfreq"], len(result["channel_names"]),
                    )
    else:
        for pair in pairs:
            result = _precompute_raja_one(pair, epoch_duration_s)
            if result is not None:
                results.append(result)
                logger.info("precompute ok  %s", result["pair_name"])

    logger.info("Precomputed thresholds for %d / %d subjects.", len(results), len(pairs))
    return results


# ---------------------------------------------------------------------------
# Scale evaluation — fast, no autoreject
# ---------------------------------------------------------------------------

def _evaluate_scale_one(precomputed: dict, scan_scale: float) -> dict:
    """Apply scan_scale to precomputed raw thresholds and score one subject."""
    prepared            = precomputed["prepared"]
    valid_epoch_indices = precomputed["valid_epoch_indices"]
    raw_thresholds      = precomputed["raw_thresholds"]
    channel_names       = precomputed["channel_names"]
    sfreq               = precomputed["sfreq"]
    epoch_boundaries    = precomputed["epoch_boundaries"]
    signal_by_epochs    = precomputed["signal_by_epochs"]
    gt_annotations      = precomputed["gt_annotations"]
    epoch_duration_s    = precomputed["epoch_duration_s"]

    min_blink_frames = float(MIN_EVENT_LEN_S * sfreq)
    valid_indices    = np.asarray(valid_epoch_indices, dtype=int)

    channel_results: list[dict] = []
    for channel in channel_names:
        channel_index       = prepared.channel_names.index(channel)
        concatenated_signal = prepared.data[valid_indices, channel_index, :].reshape(-1)
        scan_threshold      = float(raw_thresholds[channel]) * float(scan_scale)

        start_blinks, end_blinks = scan_threshold_crossings_kleifges(
            concatenated_signal,
            scan_threshold,
            min_blink_frames,
            progress_bar=False,
            channel_name=channel,
        )
        df_positions = pd.DataFrame({"start_blink": start_blinks, "end_blink": end_blinks})
        mapped_candidates = map_concatenated_blinks_to_epochs(
            df_positions,
            channel=channel,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=sfreq,
        )
        channel_results.append({
            "channel":           channel,
            "df_positions":      df_positions,
            "mapped_candidates": mapped_candidates,
            "signal_by_epoch":   signal_by_epochs[channel],
            "raw_threshold":     float(raw_thresholds[channel]),
            "scan_threshold":    scan_threshold,
            "candidate_source":  "channel_threshold",
        })

    scored = evaluate_channels(
        channel_results, gt_annotations, epoch_duration=epoch_duration_s
    )
    em = scored.best_eval_result.event_metrics
    return {
        "pair_name":    precomputed["pair_name"],
        "dataset":      precomputed["dataset"],
        "scan_scale":   float(scan_scale),
        "best_channel": scored.best_channel,
        "tp":           int(em.tp),
        "fp":           int(em.fp),
        "fn":           int(em.fn),
        "precision":    float(em.precision),
        "recall":       float(em.recall),
        "f1":           float(em.f1),
    }


def evaluate_scale(precomputed_list: list[dict], scan_scale: float) -> list[dict]:
    """Evaluate one scan_scale on all subjects. Returns per-session result dicts."""
    results: list[dict] = []
    for pc in precomputed_list:
        try:
            results.append(_evaluate_scale_one(pc, scan_scale))
        except Exception as exc:
            logger.error("evaluate  pair=%s  scale=%.4f: %s", pc["pair_name"], scan_scale, exc)
    return results


def _mean_f1(results: list[dict]) -> float:
    return float(np.mean([r["f1"] for r in results])) if results else 0.0


# ---------------------------------------------------------------------------
# Gaussian-Process Bayesian Optimisation over log(scan_scale)
# ---------------------------------------------------------------------------

def _expected_improvement(
    X_cand: np.ndarray,
    gp: GaussianProcessRegressor,
    f1_best: float,
) -> np.ndarray:
    """Expected Improvement acquisition function (maximising F1)."""
    mu, sigma = gp.predict(X_cand, return_std=True)
    improvement = mu - f1_best - BO_XI
    Z  = improvement / (sigma + 1e-9)
    ei = improvement * scipy_norm.cdf(Z) + sigma * scipy_norm.pdf(Z)
    ei[sigma < 1e-10] = 0.0
    return ei


def bayesian_scale_search(
    all_precomputed: list[dict],
    *,
    scale_bounds: tuple[float, float] = BO_SCALE_BOUNDS,
    n_calls: int = N_BO_CALLS,
    n_initial_points: int = N_INITIAL_POINTS,
    random_state: int = BO_RANDOM_STATE,
) -> tuple[float, list[dict], list[dict]]:
    """GP-BO in log(scan_scale) space. Maximises macro-F1 across all subjects.

    Returns
    -------
    best_scale : float
        Scale value with the highest observed mean F1.
    trial_summary : list[dict]
        One aggregated row per evaluated scale (used for the summary CSV).
    detail_rows : list[dict]
        Per-session rows across all trials (used for the detail CSV).
    """
    rng       = np.random.default_rng(random_state)
    log_lo    = np.log(scale_bounds[0])
    log_hi    = np.log(scale_bounds[1])

    # Dense candidate grid used for acquisition maximisation
    X_cand = np.linspace(log_lo, log_hi, BO_N_CANDIDATES).reshape(-1, 1)

    gp = GaussianProcessRegressor(
        kernel=Matern(nu=2.5),
        n_restarts_optimizer=5,
        normalize_y=True,
        random_state=random_state,
    )

    X_log_obs: list[float] = []
    y_obs:     list[float] = []
    trial_summary: list[dict] = []
    detail_rows:   list[dict] = []

    def _run_trial(log_scale: float, phase: str) -> None:
        scale   = float(np.exp(log_scale))
        results = evaluate_scale(all_precomputed, scale)
        mf1     = _mean_f1(results)
        mp      = float(np.mean([r["precision"] for r in results])) if results else 0.0
        mr      = float(np.mean([r["recall"]    for r in results])) if results else 0.0
        logger.info("BO  phase=%-12s  scale=%.4f  mean_f1=%.4f", phase, scale, mf1)

        X_log_obs.append(log_scale)
        y_obs.append(mf1)
        trial_summary.append({
            "phase":           phase,
            "scan_scale":      scale,
            "n_sessions":      len(results),
            "macro_precision": mp,
            "macro_recall":    mr,
            "mean_f1":         mf1,
        })
        for r in results:
            row = dict(r)
            row["phase"] = phase
            detail_rows.append(row)

    # ── Phase 1: random initial points ──────────────────────────────────────
    init_log_scales = rng.uniform(log_lo, log_hi, n_initial_points)
    for ls in init_log_scales:
        _run_trial(float(ls), "bo_random")

    # ── Phase 2: GP-guided iterations ───────────────────────────────────────
    n_bo_iters = n_calls - n_initial_points
    for i in range(n_bo_iters):
        X_arr = np.array(X_log_obs).reshape(-1, 1)
        y_arr = np.array(y_obs)
        gp.fit(X_arr, y_arr)

        ei           = _expected_improvement(X_cand, gp, max(y_obs))
        next_log_s   = float(X_cand[int(np.argmax(ei)), 0])
        _run_trial(next_log_s, f"bo_iter_{i + 1:02d}")

    best_idx   = int(np.argmax(y_obs))
    best_scale = float(np.exp(X_log_obs[best_idx]))
    logger.info(
        "BO converged: best_scale=%.4f  best_mean_f1=%.4f  (over %d trials)",
        best_scale, y_obs[best_idx], len(y_obs),
    )
    return best_scale, trial_summary, detail_rows


# ---------------------------------------------------------------------------
# Cao-2018 cross-dataset validation
# ---------------------------------------------------------------------------

def _discover_cao2018_sessions(root: Path) -> list[dict]:
    sessions: list[dict] = []
    if not root.exists():
        logger.warning("CAO2018_ROOT not found: %s", root)
        return sessions
    for subject_dir in sorted(root.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name
        for session_dir in sorted(subject_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            session_id = session_dir.name
            yaml_path  = session_dir / "Cao2018Viewer.yaml"
            if not yaml_path.is_file():
                continue
            with yaml_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if data.get("status", "") != "Complete":
                continue
            sid_lower = sid.lower()
            fif      = session_dir / f"{sid_lower}_{session_id}.fif"
            csv_file = session_dir / f"{sid_lower}_{session_id}.csv"
            if not (fif.is_file() and csv_file.is_file()):
                continue
            epoch_health = session_dir / "epoch_health.csv"
            sessions.append({
                "name":         f"{sid}/{session_id}",
                "fif":          fif,
                "csv":          csv_file,
                "epoch_health": epoch_health if epoch_health.is_file() else None,
            })
    return sessions


def _get_valid_epochs_health(
    epoch_health_path: Path | None,
    epoch_duration_s: float,
    n_epochs: int,
) -> list[int]:
    if epoch_health_path is None or not epoch_health_path.is_file():
        return list(range(n_epochs))
    df = pd.read_csv(epoch_health_path)
    df["health"] = pd.to_numeric(df["health"], errors="coerce")
    valid: list[int] = []
    for i in range(n_epochs):
        epoch_start = i * epoch_duration_s
        epoch_end   = (i + 1) * epoch_duration_s
        overlap = df[
            (df["epoch_start_s"] < epoch_end) & (df["epoch_end_s"] > epoch_start)
        ]
        if overlap.empty or (overlap["health"] > HEALTH_DROP_THRESHOLD).all():
            valid.append(i)
    return valid


def _precompute_cao2018_one(session: dict, epoch_duration_s: float) -> dict | None:
    try:
        raw    = mne.io.read_raw_fif(str(session["fif"]), preload=True, verbose="ERROR")
        epochs = mne.make_fixed_length_epochs(
            raw, duration=epoch_duration_s, preload=True, verbose="ERROR"
        )
        n_total             = len(epochs)
        valid_epoch_indices = _get_valid_epochs_health(
            session["epoch_health"], epoch_duration_s, n_total
        )
        prepared = prepare_epoch_detection_input(
            epochs,
            pick_types_options={"eeg": True},
            filter_low=FILTER_LOW,
            filter_high=FILTER_HIGH,
            resample_rate=RESAMPLE_RATE,
        )
        threshold_result = learn_strategy_dbo_thresholds(
            prepared,
            valid_epoch_indices,
            stage1_threshold_scope=STAGE1_THRESHOLD_SCOPE,
            autoreject_method=AUTOREJECT_METHOD,
            stage1_scan_scale=1.0,
            autoreject_random_state=AUTOREJECT_RANDOM_STATE,
            autoreject_augment=AUTOREJECT_AUGMENT,
        )
        ground_truth_raw   = load_annotation_as_reference(session["csv"], epoch_duration_s)
        ground_truth_valid = ground_truth_raw[
            ground_truth_raw["epoch_index"].isin(valid_epoch_indices)
        ].reset_index(drop=True)
        ground_truth_df    = enrich_absolute_times(ground_truth_valid, epoch_duration_s)
        gt_annotations     = dataframe_to_annotations(ground_truth_df)

        epoch_boundaries = build_epoch_boundaries(
            len(valid_epoch_indices), prepared.epoch_length_samples
        )
        signal_by_epochs = {
            ch: build_signal_by_epoch(prepared, prepared.channel_names.index(ch))
            for ch in threshold_result.channel_names
        }
        return {
            "pair_name":           session["name"],
            "dataset":             "cao2018",
            "prepared":            prepared,
            "valid_epoch_indices": valid_epoch_indices,
            "raw_thresholds":      dict(threshold_result.raw_thresholds),
            "channel_names":       list(threshold_result.channel_names),
            "sfreq":               float(prepared.sfreq),
            "epoch_boundaries":    epoch_boundaries,
            "signal_by_epochs":    signal_by_epochs,
            "gt_annotations":      gt_annotations,
            "epoch_duration_s":    epoch_duration_s,
        }
    except Exception as exc:
        logger.error("precompute cao2018  session=%s: %s", session["name"], exc)
        return None


def validate_on_cao2018(best_scale: float, epoch_duration_s: float) -> list[dict]:
    """Precompute cao_2018 thresholds and evaluate with best_scale."""
    sessions = _discover_cao2018_sessions(CAO2018_ROOT)
    logger.info("Discovered %d cao_2018 sessions.", len(sessions))
    if not sessions:
        return []

    logger.info("Precomputing cao_2018 autoreject thresholds …")
    cao_precomputed: list[dict] = []
    if USE_MULTITHREAD:
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(_precompute_cao2018_one, s, epoch_duration_s): s["name"]
                for s in sessions
            }
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    cao_precomputed.append(result)
                    logger.info("cao2018 precompute ok  %s", result["pair_name"])
    else:
        for session in sessions:
            result = _precompute_cao2018_one(session, epoch_duration_s)
            if result is not None:
                cao_precomputed.append(result)
                logger.info("cao2018 precompute ok  %s", result["pair_name"])

    results = evaluate_scale(cao_precomputed, best_scale)
    mf1 = _mean_f1(results)
    logger.info(
        "cao_2018 validation: scale=%.4f  n=%d  macro_f1=%.4f",
        best_scale, len(results), mf1,
    )
    return results


# ---------------------------------------------------------------------------
# Console reporting
# ---------------------------------------------------------------------------

def _print_bo_table(trial_summary: list[dict], best_scale: float) -> None:
    print("\nBayesian Optimisation Trial Results (raja dataset)")
    print("-" * 58)
    print(f"  {'phase':<16}  {'scale':>8}  {'mean_f1':>9}  {'n':>4}")
    print("-" * 58)
    for t in trial_summary:
        marker = " <-- BEST" if abs(t["scan_scale"] - best_scale) < 1e-6 else ""
        print(
            f"  {t['phase']:<16}  {t['scan_scale']:>8.4f}  "
            f"{t['mean_f1']:>9.4f}  {t['n_sessions']:>4}{marker}"
        )
    print()


def _print_cao2018_summary(cao_results: list[dict], best_scale: float) -> None:
    if not cao_results:
        print("\ncao_2018 validation: no data (dataset path not found or empty).")
        return
    mf1 = _mean_f1(cao_results)
    mp  = float(np.mean([r["precision"] for r in cao_results]))
    mr  = float(np.mean([r["recall"]    for r in cao_results]))
    print(f"\ncao_2018 cross-dataset validation  (scale={best_scale:.4f})")
    print(f"  n_sessions={len(cao_results)}")
    print(f"  macro_precision={mp:.4f}  macro_recall={mr:.4f}  macro_f1={mf1:.4f}")


# ---------------------------------------------------------------------------
# CSV / JSON writers
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _build_summary(
    trial_summary: list[dict],
    cao_results: list[dict],
    best_scale: float,
) -> list[dict]:
    """Build per-scale summary rows compatible with analyze_and_update.py."""
    rows: list[dict] = []
    for t in trial_summary:
        rows.append({
            "dataset":         "raja",
            "phase":           t["phase"],
            "scan_scale":      t["scan_scale"],
            "is_best":         abs(t["scan_scale"] - best_scale) < 1e-6,
            "n_sessions":      t["n_sessions"],
            "macro_precision": t["macro_precision"],
            "macro_recall":    t["macro_recall"],
            "macro_f1":        t["mean_f1"],
        })
    if cao_results:
        rows.append({
            "dataset":         "cao2018",
            "phase":           "cao2018_validation",
            "scan_scale":      best_scale,
            "is_best":         True,
            "n_sessions":      len(cao_results),
            "macro_precision": float(np.mean([r["precision"] for r in cao_results])),
            "macro_recall":    float(np.mean([r["recall"]    for r in cao_results])),
            "macro_f1":        float(np.mean([r["f1"]        for r in cao_results])),
        })
    return rows


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Exp 46: DBO STAGE1_SCAN_SCALE optimisation via Bayesian optimisation."
    )
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--out-dir",          type=Path,  default=None)
    p.add_argument("--quiet",            action="store_true")
    p.add_argument("--no-multithread",   action="store_true")
    p.add_argument("--n-bo-calls",       type=int,   default=N_BO_CALLS,
                   help="Total BO evaluations (random + GP-guided).")
    p.add_argument("--n-initial-points", type=int,   default=N_INITIAL_POINTS,
                   help="Random initial evaluations before GP fits.")
    p.add_argument("--max-pairs",        type=int,   default=None,
                   help="Limit raja sessions to first N (for quick testing).")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    global USE_MULTITHREAD
    USE_MULTITHREAD = not args.no_multithread
    epoch_duration_s  = float(args.epoch_duration_s)
    n_bo_calls        = int(args.n_bo_calls)
    n_initial_points  = int(args.n_initial_points)

    setup_tutorial_logging()
    logger.info("=" * 60)
    logger.info("Experiment 46: DBO STAGE1_SCAN_SCALE — GP Bayesian Optimisation")
    logger.info("  epoch_duration_s  = %.0f s",  epoch_duration_s)
    logger.info("  autoreject_method = %s",       AUTOREJECT_METHOD)
    logger.info("  scale_bounds      = [%.2f, %.2f]", *BO_SCALE_BOUNDS)
    logger.info("  n_bo_calls        = %d",       n_bo_calls)
    logger.info("  n_initial_points  = %d",       n_initial_points)
    logger.info("=" * 60)

    # ── Discover raja sessions ───────────────────────────────────────────────
    pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    logger.info("Discovered %d raja sessions.", len(pairs))
    if args.max_pairs is not None:
        pairs = pairs[: args.max_pairs]
        logger.info("Limiting to %d raja session(s) (--max-pairs).", len(pairs))
    if not pairs:
        logger.error("No raja sessions found. Exiting.")
        return

    # ── Precompute raw autoreject thresholds (once per subject) ─────────────
    all_precomputed = precompute_raja_thresholds(pairs, epoch_duration_s)
    if not all_precomputed:
        logger.error("No subjects successfully precomputed. Exiting.")
        return

    # ── GP-BO scan-scale search ──────────────────────────────────────────────
    best_scale, trial_summary, detail_rows = bayesian_scale_search(
        all_precomputed,
        n_calls=n_bo_calls,
        n_initial_points=n_initial_points,
    )
    _print_bo_table(trial_summary, best_scale)

    print(f"\n{'=' * 60}")
    print(f"  SELECTED  STAGE1_SCAN_SCALE = {best_scale:.4f}")
    print(f"  Default value (bayesian)    = 0.12")
    change = "unchanged" if abs(best_scale - 0.12) < 0.005 else f"changed from 0.12"
    print(f"  Recommendation              : {change}")
    print(f"{'=' * 60}")

    # ── Cross-dataset validation on cao_2018 ────────────────────────────────
    cao_results = validate_on_cao2018(best_scale, epoch_duration_s)
    _print_cao2018_summary(cao_results, best_scale)

    # Append cao2018 per-session rows to detail_rows
    for r in cao_results:
        row = dict(r)
        row["phase"] = "cao2018_validation"
        detail_rows.append(row)

    summary_rows = _build_summary(trial_summary, cao_results, best_scale)

    best_trial   = max(trial_summary, key=lambda t: t["mean_f1"])
    cao_mean_f1  = float(np.mean([r["f1"] for r in cao_results])) if cao_results else None

    payload = {
        "experiment":            "exp46_dbo_scan_scale_bo",
        "epoch_duration_s":      epoch_duration_s,
        "autoreject_method":     AUTOREJECT_METHOD,
        "bo_scale_bounds":       list(BO_SCALE_BOUNDS),
        "n_bo_calls":            n_bo_calls,
        "n_initial_points":      n_initial_points,
        "best_scale":            best_scale,
        "best_scale_mean_f1_raja": best_trial["mean_f1"],
        "cao2018_mean_f1":       cao_mean_f1,
        "n_raja_sessions":       len(all_precomputed),
        "n_cao2018_sessions":    len(cao_results),
        "summary":               summary_rows,
    }

    # ── Write artifacts ──────────────────────────────────────────────────────
    if args.out_dir is not None:
        out_dir: Path = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_csv(out_dir / "exp46_scan_scale_results.csv",  detail_rows)
        _write_csv(out_dir / "exp46_scan_scale_summary.csv",  summary_rows)
        (out_dir / "summary.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        logger.info("Results written to %s", out_dir)

    print("\n[DONE] Experiment 46 completed.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:  # no CLI args → inject test defaults for IDE run
        sys.argv += ["--out-dir", "logs/exp46"]
    main()
