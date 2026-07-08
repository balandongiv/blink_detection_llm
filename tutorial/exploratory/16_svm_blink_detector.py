"""Tutorial 16: SVM-based blink detector with engineered features.

Research Question
-----------------
Can a supervised SVM trained on 18 hand-crafted features (duration, shape,
recovery, plateau flatness, pAVR, etc.) accurately classify candidate blink
events as: normal blink (1), long closure (2), or background noise (0)?

Methodology
-----------
1. Epoch setup: 30-second epochs, epoch health >= 4  (same as Tutorial 15).
2. Training data: for each training session extract labelled feature vectors
   directly from the ground-truth CSV annotations:
     Class 1 (normal blink): GT normal events
     Class 2 (long closure):  GT long events
     Class 0 (background):   random windows ≥ 1 s from any GT event
3. Classifier:  StandardScaler → SVC(kernel='rbf', class_weight='balanced').
4. Evaluation:  Leave-One-Session-Out (LOSO) cross-validation across the
   5 sessions from Tutorial 14.
5. Metrics reported per session AND micro/macro averaged:
     a. All events combined
     b. Normal blinks only
     c. Long blinks only
   Baseline comparisons printed at end of report.

Feature vector  (18 features, see src/strategy_svm/features.py)
----------------------------------------------------------------
duration_s, log_dur_ms,
peak_amp, fill_factor, snr,
symmetry, rise_slope, fall_slope_100ms, fall_slope_400ms,
recovery_100ms, recovery_200ms, recovery_400ms,
plateau_cv, pavr,
post_rms_ratio, post_early_ratio,
skewness, kurtosis

Candidate detection at test time
---------------------------------
Low-threshold (1.5 σ) amplitude crossing with 200 ms debounce — generates
a high-recall set of candidate events; SVM then filters and classifies.

Multi-threading
---------------
USE_MULTITHREAD = True   → parallel data collection per session
USE_MULTITHREAD = False  → single-thread, easier to debug
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

from blink_evaluation import evaluate_channels
from blink_evaluation.epoch_utils import enrich_absolute_times
from blink_evaluation.io import dataframe_to_annotations
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.strategy_svm.pipeline import (
    collect_session_data,
    predict_and_build_results,
    train_svm_pipeline,
)
from src.utils.dataset_discovery import discover_raja_pairs
from src.utils.experiment_utils import setup_tutorial_logging

from pyblinker.epoch_detection import assign_epoch_health, get_valid_epoch_indices_by_health

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ANNOTATION_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
PROCESSED_BASE_DIR  = Path(r"D:\dataset\drowsy_driving_raja_processed")
BRAIN_REGION_YAML   = REPO_ROOT / "brain_region.yaml"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S: float = 30.0
MIN_HEALTH: int = 4
FILTER_LOW:  float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None

LONG_THRESHOLD_S: float = 0.5     # PERCLOS boundary

# SVM hyperparameters
SVM_C:      float = 1.0
SVM_GAMMA:  str   = "scale"       # 'scale' | 'auto' | float

# Candidate detection at test time
CAND_THRESHOLD_FACTOR: float = 1.5   # σ above mean for threshold
CAND_DEBOUNCE_MS:      float = 200.0 # gap-fill to merge onset/offset pairs
CAND_MIN_DUR_S:        float = 0.08  # 80 ms minimum candidate
CAND_MAX_DUR_S:        float = 5.0   # 5 s maximum candidate

# Training data
BG_RATIO: float = 2.0   # background samples per positive sample

USE_MULTITHREAD: bool = True  # False → single-thread for debugging

# ---------------------------------------------------------------------------
# Known limitations and tuning guidance
# ---------------------------------------------------------------------------
# LOSO generalisation: the SVM relies on cross-session feature transfer.
# Sessions with very different signal character (e.g. S22 with 1.75 s mean
# closures) can fail when out-of-distribution from the training fold.
#
# To improve generalisation, consider:
#   1. Increase SVM_C (e.g. 0.1–10) or switch to kernel='linear' for fewer
#      spurious feature interactions.
#   2. Add within-session calibration: fine-tune on 2–3 labelled events from
#      the test session itself (semi-supervised).
#   3. Raise CAND_DEBOUNCE_MS to 400–500 ms so onset/offset spike pairs for
#      very long closures (≥ 1.5 s) merge into one candidate.
#   4. Add duration-band features that capture the "inter-event gap" (a blink
#      cluster vs. a long closure has a different surrounding pattern).
#   5. Expand training data beyond 5 sessions for a more robust model.
# ---------------------------------------------------------------------------

# 5 sessions from Tutorial 14 (same as Tutorial 15)
SELECTED_SESSIONS: list[str] | None = [
    "S13/S26_20190108_035218_3",
    "S24/S38_20190129_035118_2",
    "S4/S04_20170606_045500_2",
    "S2/TEST_20170601_042544_2",
    "S22/S35_20190123_040805_2",
]

# Label sets (same as Tutorial 14 / 15)
LONG_BLINK_LABELS   = frozenset({"FC_CL", "FC", "FC_A", "FC_M", "FC_CL_FRAME_VIEWER"})
NORMAL_BLINK_LABELS = frozenset({"B_CL", "HB_CL", "eye_blink", "B_A", "B_M", "HB_A", "HB_M"})

# Pyblinker + Dual-mode baselines for comparison (Tutorial 14 / 15 macro-averages)
BASELINE_PYBLINKER = {"normal": 0.8341, "long": 0.5550}
BASELINE_DUALMODE  = {"normal": 0.8535, "long": 0.7205}


# ---------------------------------------------------------------------------
# Ground-truth helpers
# ---------------------------------------------------------------------------

def classify_events(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
    df = df.dropna(subset=["duration"])

    is_long_lbl  = df["description"].isin(LONG_BLINK_LABELS)
    is_norm_lbl  = df["description"].isin(NORMAL_BLINK_LABELS)
    is_long_dur  = df["duration"] >= LONG_THRESHOLD_S

    long_mask   = is_long_lbl | (is_norm_lbl & is_long_dur)
    normal_mask = is_norm_lbl & ~is_long_dur
    known_mask  = is_long_lbl | is_norm_lbl

    return df[known_mask].copy(), df[normal_mask].copy(), df[long_mask].copy()


def _df_to_annotations(df: pd.DataFrame) -> mne.Annotations:
    if df.empty:
        return mne.Annotations(onset=[], duration=[], description=[])
    rows = []
    for _, row in df.iterrows():
        onset_abs = float(row["onset"])
        dur       = float(row["duration"])
        ei        = int(onset_abs // EPOCH_DURATION_S)
        rows.append({
            "epoch_index":    ei,
            "blink_onset":    onset_abs - ei * EPOCH_DURATION_S,
            "blink_duration": dur,
        })
    return dataframe_to_annotations(
        enrich_absolute_times(pd.DataFrame(rows), EPOCH_DURATION_S)
    )


# ---------------------------------------------------------------------------
# Epoch health filtering
# ---------------------------------------------------------------------------

def _health_valid_indices(csv_path: Path, n_epochs: int, pair_name: str) -> list[int]:
    health_csv = csv_path.parent / "epoch_health.csv"
    if not health_csv.is_file():
        logger.warning("%s: no epoch_health.csv — using all epochs", pair_name)
        return list(range(n_epochs))
    hdf = pd.read_csv(health_csv)
    hdf["health"] = pd.to_numeric(hdf["health"], errors="coerce")
    health_values = assign_epoch_health(hdf, EPOCH_DURATION_S, n_epochs)
    valid = get_valid_epoch_indices_by_health(health_values, MIN_HEALTH)
    logger.info("%s: health >= %d → %d / %d epochs", pair_name, MIN_HEALTH, len(valid), n_epochs)
    return valid


# ---------------------------------------------------------------------------
# Session loader: returns prepared + valid_indices + GT + csv_path
# ---------------------------------------------------------------------------

def load_session(
    pair_name: str,
    fif_path: Path,
    csv_path: Path,
) -> dict:
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(fif_path, brain_channels)
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    n_total = len(epochs)
    valid_idx = _health_valid_indices(csv_path, n_total, pair_name)
    if not valid_idx:
        raise RuntimeError(f"No valid epochs for {pair_name}")

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    all_df, normal_df, long_df = classify_events(csv_path)
    return {
        "pair":         pair_name,
        "prepared":     prepared,
        "valid_idx":    valid_idx,
        "all_df":       all_df,
        "normal_df":    normal_df,
        "long_df":      long_df,
    }


# ---------------------------------------------------------------------------
# LOSO cross-validation
# ---------------------------------------------------------------------------

def _event_metrics(scored) -> dict:
    em = scored.best_eval_result.event_metrics
    return {"ch": scored.best_channel,
            "tp": em.tp, "fp": em.fp, "fn": em.fn,
            "P": em.precision, "R": em.recall, "F1": em.f1}


def run_loso(sessions: list[dict]) -> list[dict]:
    """Leave-one-session-out cross-validation."""
    n = len(sessions)
    all_results: list[dict] = []

    for test_idx in range(n):
        test  = sessions[test_idx]
        train = [sessions[i] for i in range(n) if i != test_idx]
        pair  = test["pair"]
        logger.info("LOSO fold %d/%d — test=%s", test_idx + 1, n, pair)

        # Collect training data
        X_parts, y_parts = [], []
        for sess in train:
            X_s, y_s = collect_session_data(
                sess["prepared"],
                sess["valid_idx"],
                sess["normal_df"],
                sess["long_df"],
                EPOCH_DURATION_S,
                bg_ratio=BG_RATIO,
                rng=np.random.default_rng(test_idx),
            )
            if len(y_s) > 0:
                X_parts.append(X_s)
                y_parts.append(y_s)

        if not X_parts:
            logger.error("No training data for fold %d. Skipping.", test_idx + 1)
            continue

        X_train = np.vstack(X_parts)
        y_train = np.concatenate(y_parts)

        # Replace any NaN/Inf in training features
        X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)

        logger.info(
            "Training SVM: %d samples  classes=%s",
            len(y_train),
            {int(c): int(np.sum(y_train == c)) for c in np.unique(y_train)},
        )
        model = train_svm_pipeline(X_train, y_train, C=SVM_C, gamma=SVM_GAMMA)

        # Predict on test session
        channel_results = predict_and_build_results(
            test["prepared"],
            test["valid_idx"],
            model,
            threshold_factor=CAND_THRESHOLD_FACTOR,
            debounce_ms=CAND_DEBOUNCE_MS,
            min_dur_s=CAND_MIN_DUR_S,
            max_dur_s=CAND_MAX_DUR_S,
        )

        gt_all    = _df_to_annotations(test["all_df"])
        gt_normal = _df_to_annotations(test["normal_df"])
        gt_long   = _df_to_annotations(test["long_df"])

        scored_all    = evaluate_channels(channel_results, gt_all,    EPOCH_DURATION_S)
        scored_normal = evaluate_channels(channel_results, gt_normal, EPOCH_DURATION_S)
        scored_long   = evaluate_channels(channel_results, gt_long,   EPOCH_DURATION_S)

        all_results.append({
            "pair":          pair,
            "n_normal_gt":   len(test["normal_df"]),
            "n_long_gt":     len(test["long_df"]),
            "norm_dur_mean": float(test["normal_df"]["duration"].mean())
                             if not test["normal_df"].empty else 0.0,
            "long_dur_mean": float(test["long_df"]["duration"].mean())
                             if not test["long_df"].empty else 0.0,
            "all":    _event_metrics(scored_all),
            "normal": _event_metrics(scored_normal),
            "long":   _event_metrics(scored_long),
        })
        logger.info(
            "fold done  %s  normal_R=%.4f  long_R=%.4f",
            pair,
            all_results[-1]["normal"]["R"],
            all_results[-1]["long"]["R"],
        )

    return all_results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_table(results: list[dict], subset: str, key: str) -> None:
    n_gt_col = "n_normal_gt" if key == "normal" else "n_long_gt"
    hdr = (f"{'pair':<32}  {'n_gt':>5}  {'best_ch':<12}  "
           f"{'tp':>5}  {'fp':>5}  {'fn':>5}  {'P':>8}  {'R':>8}  {'F1':>8}")
    sep = "-" * len(hdr)
    print(f"\n{'='*len(hdr)}")
    print(f"  {subset.upper()} BLINKS  (threshold={LONG_THRESHOLD_S}s)")
    print(f"{'='*len(hdr)}")
    print(hdr)
    print(sep)
    total_tp = total_fp = total_fn = 0
    for r in results:
        m = r[key]
        total_tp += m["tp"]; total_fp += m["fp"]; total_fn += m["fn"]
        print(f"{r['pair']:<32}  {r[n_gt_col]:>5}  {str(m['ch']):<12}  "
              f"{m['tp']:>5}  {m['fp']:>5}  {m['fn']:>5}  "
              f"{m['P']:>8.4f}  {m['R']:>8.4f}  {m['F1']:>8.4f}")
    print(sep)
    micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
    print(f"  MICRO  TP={total_tp}  FP={total_fp}  FN={total_fn}  "
          f"P={micro_p:.4f}  R={micro_r:.4f}  F1={micro_f1:.4f}")


def print_report(results: list[dict]) -> None:
    print("\n" + "#" * 72)
    print("  SVM BLINK DETECTOR — LOSO CROSS-VALIDATION RESULTS")
    print("#" * 72)
    print(f"\nConfig: epoch={EPOCH_DURATION_S}s  health>={MIN_HEALTH}  "
          f"filter={FILTER_LOW}-{FILTER_HIGH}Hz  SVM C={SVM_C} gamma={SVM_GAMMA}")
    print(f"        candidates: thr_factor={CAND_THRESHOLD_FACTOR}  "
          f"debounce={CAND_DEBOUNCE_MS}ms  [{CAND_MIN_DUR_S},{CAND_MAX_DUR_S}]s")
    print(f"\nDuration profile per session:")
    print(f"  {'session':<32}  {'n_normal':>8}  {'norm_dur':>9}  "
          f"{'n_long':>7}  {'long_dur':>9}")
    print(f"  {'-'*32}  {'-'*8}  {'-'*9}  {'-'*7}  {'-'*9}")
    for r in results:
        print(f"  {r['pair']:<32}  {r['n_normal_gt']:>8}  "
              f"{r['norm_dur_mean']:>9.3f}s  {r['n_long_gt']:>7}  "
              f"{r['long_dur_mean']:>9.3f}s")

    _print_table(results, "ALL events",    "all")
    _print_table(results, "NORMAL blinks", "normal")
    _print_table(results, "LONG blinks",   "long")

    n = len(results)
    print("\n" + "#" * 72)
    print("  SUMMARY — LOSO recall comparison")
    print("#" * 72)
    print(f"\n  {'session':<32}  {'norm_recall':>12}  {'long_recall':>12}  "
          f"{'recall_drop':>12}")
    print(f"  {'-'*32}  {'-'*12}  {'-'*12}  {'-'*12}")
    for r in results:
        nr, lr = r["normal"]["R"], r["long"]["R"]
        print(f"  {r['pair']:<32}  {nr:>12.4f}  {lr:>12.4f}  {nr - lr:>+12.4f}")

    avg_nr = sum(r["normal"]["R"] for r in results) / n
    avg_lr = sum(r["long"]["R"]   for r in results) / n
    print(f"\n  Macro-avg (SVM LOSO):  normal={avg_nr:.4f}  long={avg_lr:.4f}  "
          f"drop={avg_nr - avg_lr:+.4f}")

    print(f"\n  {'Method':<20}  {'normal recall':>14}  {'long recall':>12}")
    print(f"  {'-'*20}  {'-'*14}  {'-'*12}")
    print(f"  {'SVM (LOSO)':<20}  {avg_nr:>14.4f}  {avg_lr:>12.4f}")
    print(f"  {'Dual-mode (TU15)':<20}  "
          f"{BASELINE_DUALMODE['normal']:>14.4f}  "
          f"{BASELINE_DUALMODE['long']:>12.4f}")
    print(f"  {'Pyblinker (TU14)':<20}  "
          f"{BASELINE_PYBLINKER['normal']:>14.4f}  "
          f"{BASELINE_PYBLINKER['long']:>12.4f}")
    print()
    # Evaluation
    if avg_lr >= 0.80:
        print("  [LONG TARGET MET]     recall >= 0.80")
    elif avg_lr >= BASELINE_DUALMODE["long"]:
        print(f"  [LONG: BEST SO FAR]   SVM > dual-mode ({avg_lr:.4f} > {BASELINE_DUALMODE['long']:.4f})")
    elif avg_lr >= BASELINE_PYBLINKER["long"]:
        print(f"  [LONG: IMPROVED]      SVM > pyblinker ({avg_lr:.4f} > {BASELINE_PYBLINKER['long']:.4f})")
    else:
        print(f"  [LONG: BELOW BASELINE] {avg_lr:.4f} < pyblinker {BASELINE_PYBLINKER['long']:.4f}")

    if avg_nr >= 0.83:
        print("  [NORMAL OK]           recall >= 0.83")
    else:
        print(f"  [NORMAL BELOW TARGET] {avg_nr:.4f} < 0.83")

    # Session-specific diagnostics
    worst = min(results, key=lambda r: r["long"]["R"])
    best  = max(results, key=lambda r: r["long"]["R"])
    print(f"\n  Best  long recall: {best['pair']} = {best['long']['R']:.4f}")
    print(f"  Worst long recall: {worst['pair']} = {worst['long']['R']:.4f}")
    low_sessions = [r["pair"] for r in results if r["long"]["R"] < 0.30]
    if low_sessions:
        print(f"\n  Sessions with long recall < 0.30 (likely out-of-distribution):")
        for s in low_sessions:
            print(f"    {s}  — increase CAND_DEBOUNCE_MS or add within-session calibration")
        print(f"\n  NOTE: LOSO CV is sensitive to session-level distribution shift.")
        print(f"  Poor sessions reduce the macro average disproportionately.")
        print(f"  Consider per-session or within-session SVM fine-tuning.")

    print("#" * 72)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    logger.info("=== Tutorial 16: SVM blink detector (LOSO CV) ===")
    logger.info(
        "Epoch: %.0f s  |  health >= %d  |  filter: %.1f-%.1f Hz  |  "
        "SVM C=%.1f gamma=%s  |  threads: %s",
        EPOCH_DURATION_S, MIN_HEALTH, FILTER_LOW, FILTER_HIGH,
        SVM_C, SVM_GAMMA, "multi" if USE_MULTITHREAD else "single",
    )

    pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    if not pairs:
        logger.error("No complete pairs found. Exiting.")
        return

    if SELECTED_SESSIONS is not None:
        order = {name: i for i, name in enumerate(SELECTED_SESSIONS)}
        pairs = [p for p in pairs if p["name"] in order]
        if not pairs:
            logger.error("None of SELECTED_SESSIONS found in complete pairs.")
            return
        pairs.sort(key=lambda p: order[p["name"]])

    logger.info("Loading %d session(s) …", len(pairs))

    sessions: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        with ThreadPoolExecutor() as exe:
            future_map = {
                exe.submit(load_session, p["name"], p["fif"], p["csv"]): p["name"]
                for p in pairs
            }
            for fut in as_completed(future_map):
                name = future_map[fut]
                try:
                    sessions.append(fut.result())
                    logger.info("loaded %s", name)
                except Exception as exc:
                    logger.error("load %s: %s", name, exc, exc_info=True)
                    errors.append(f"ERROR load {name}: {exc}")
    else:
        for p in pairs:
            try:
                sessions.append(load_session(p["name"], p["fif"], p["csv"]))
                logger.info("loaded %s", p["name"])
            except Exception as exc:
                logger.error("load %s: %s", p["name"], exc, exc_info=True)
                errors.append(f"ERROR load {p['name']}: {exc}")

    if not sessions:
        logger.error("No sessions loaded. Exiting.")
        return

    # Sort sessions to match SELECTED_SESSIONS order for consistent LOSO CV
    if SELECTED_SESSIONS is not None:
        order = {name: i for i, name in enumerate(SELECTED_SESSIONS)}
        sessions.sort(key=lambda s: order.get(s["pair"], len(SELECTED_SESSIONS)))

    logger.info("Running LOSO CV over %d sessions …", len(sessions))
    results = run_loso(sessions)

    if results:
        print_report(results)

    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
