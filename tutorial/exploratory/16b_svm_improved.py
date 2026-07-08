"""Tutorial 16b: SVM blink detector — all 5 generalisation improvements.

This script builds on Tutorial 16 (basic LOSO SVM) and applies every
recommendation from the comments in that script:

  Rec #1 — Hyperparameter grid search  (C × kernel)
  Rec #2 — Within-session calibration  (N_CALIB_PER_CLASS GT events)
  Rec #3 — Combined candidate finder   (threshold crossing + Module B)
  Rec #4 — Context features            (22 features instead of 18)
  Rec #5 — All Raja sessions for training (not just the 5 selected)

Design
------
LOSO is still the outer loop (test = one of the 5 selected sessions), so
results are directly comparable with Tutorial 16.  The improvements affect:

  - Training data quality  (more sessions + calibration from test session)
  - Candidate recall       (Module B adds long-closure plateaus)
  - Feature richness       (post_rms_1s, local_activity, dur_post_product …)
  - Model selection        (grid search picks C and kernel automatically)

Calibration protocol (Rec #2)
------------------------------
For each test session, the LOSO fold works as follows:

  a. Collect features from ALL other sessions (base training set).
  b. Sample N_CALIB_PER_CLASS GT events per class from the TEST session
     as calibration data.
  c. Combine base + calibration → retrain SVM.
  d. Evaluate on the REMAINING (non-calibration) test events.

This mirrors how a real deployable system would be used: a brief labelled
calibration recording from the participant before the main session.

Multi-threading
---------------
USE_MULTITHREAD = True   parallel loading of all sessions (fast)
USE_MULTITHREAD = False  single-thread for debugging

Baseline comparisons
--------------------
  Pyblinker     (Tutorial 14): normal=0.8341  long=0.5550
  Dual-mode     (Tutorial 15): normal=0.8535  long=0.7205
  SVM basic     (Tutorial 16): normal=0.5894  long=0.5200
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
# Epoch / filter parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S: float = 30.0
MIN_HEALTH: int = 4
FILTER_LOW:  float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None

LONG_THRESHOLD_S: float = 0.5

# ---------------------------------------------------------------------------
# Improvement toggles
# ---------------------------------------------------------------------------

# Rec #1 — Hyperparameter grid search
# NOTE: grid search on 40+ sessions × 24 parameter combinations takes ~60 min.
#       Set True only when running overnight; use False for interactive work.
USE_GRID_SEARCH: bool = False    # True → auto-select C and kernel (slow)
SVM_C:     float = 1.0           # used when USE_GRID_SEARCH=False
SVM_GAMMA: str   = "scale"       # used when USE_GRID_SEARCH=False
SVM_KERNEL: str  = "linear"      # linear is more regularised → better LOSO generalisation

# Rec #2 — Within-session calibration
USE_CALIBRATION: bool = True     # fast; +N_CALIB_PER_CLASS events per class from test session
N_CALIB_PER_CLASS: int = 5       # GT events taken from test session per class

# Rec #3 — Combined candidates (threshold crossing + Module B suppression)
# This is the key fix for S22 (long closures whose onset spikes are too small
# for threshold crossing).  Module B detects the quiet plateau instead.
USE_COMBINED_CANDIDATES: bool = True
CAND_THRESHOLD_FACTOR: float = 1.5
CAND_DEBOUNCE_MS:      float = 200.0
CAND_MIN_DUR_S:        float = 0.08
CAND_MAX_DUR_S:        float = 5.0

# Rec #5 — Use ALL available Raja sessions for training
# NOTE: loading 46 sessions takes ~10 min; full feature extraction adds ~20 min
#       per fold.  Set True for best accuracy; False for faster runs.
USE_ALL_SESSIONS: bool = False   # True → use all Raja sessions (slow but better)

BG_RATIO: float = 2.0
USE_MULTITHREAD: bool = True

# ---------------------------------------------------------------------------
# 5 test sessions (same as Tutorial 14/15/16)
# ---------------------------------------------------------------------------
SELECTED_SESSIONS: list[str] = [
    "S13/S26_20190108_035218_3",
    "S24/S38_20190129_035118_2",
    "S4/S04_20170606_045500_2",
    "S2/TEST_20170601_042544_2",
    "S22/S35_20190123_040805_2",
]

LONG_BLINK_LABELS   = frozenset({"FC_CL", "FC", "FC_A", "FC_M", "FC_CL_FRAME_VIEWER"})
NORMAL_BLINK_LABELS = frozenset({"B_CL", "HB_CL", "eye_blink", "B_A", "B_M", "HB_A", "HB_M"})

# Baselines from earlier tutorials
BASELINES = {
    "Pyblinker TU14": {"normal": 0.8341, "long": 0.5550},
    "Dual-mode TU15": {"normal": 0.8535, "long": 0.7205},
    "SVM basic TU16": {"normal": 0.5894, "long": 0.5200},
}


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
    long_mask    = is_long_lbl | (is_norm_lbl & is_long_dur)
    normal_mask  = is_norm_lbl & ~is_long_dur
    known_mask   = is_long_lbl | is_norm_lbl
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
# Epoch health
# ---------------------------------------------------------------------------

def _health_valid_indices(csv_path: Path, n_epochs: int, name: str) -> list[int]:
    hp = csv_path.parent / "epoch_health.csv"
    if not hp.is_file():
        logger.debug("%s: no epoch_health.csv", name)
        return list(range(n_epochs))
    hdf = pd.read_csv(hp)
    hdf["health"] = pd.to_numeric(hdf["health"], errors="coerce")
    hv  = assign_epoch_health(hdf, EPOCH_DURATION_S, n_epochs)
    return get_valid_epoch_indices_by_health(hv, MIN_HEALTH)


# ---------------------------------------------------------------------------
# Session loader
# ---------------------------------------------------------------------------

def load_session(pair_name: str, fif_path: Path, csv_path: Path) -> dict:
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
        "pair":      pair_name,
        "prepared":  prepared,
        "valid_idx": valid_idx,
        "all_df":    all_df,
        "normal_df": normal_df,
        "long_df":   long_df,
    }


def _load_all_parallel(pairs: list[dict]) -> tuple[list[dict], list[str]]:
    sessions, errors = [], []
    if USE_MULTITHREAD:
        with ThreadPoolExecutor() as exe:
            fmap = {
                exe.submit(load_session, p["name"], p["fif"], p["csv"]): p["name"]
                for p in pairs
            }
            for fut in as_completed(fmap):
                name = fmap[fut]
                try:
                    sessions.append(fut.result())
                    logger.info("loaded %s", name)
                except Exception as exc:
                    logger.error("load %s: %s", name, exc)
                    errors.append(f"load {name}: {exc}")
    else:
        for p in pairs:
            try:
                sessions.append(load_session(p["name"], p["fif"], p["csv"]))
                logger.info("loaded %s", p["name"])
            except Exception as exc:
                logger.error("load %s: %s", p["name"], exc)
                errors.append(f"load {p['name']}: {exc}")
    return sessions, errors


# ---------------------------------------------------------------------------
# Calibration helpers  (Recommendation #2)
# ---------------------------------------------------------------------------

def _split_calibration(
    df: pd.DataFrame,
    n: int,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (calib_df, rest_df) — n rows sampled without replacement."""
    if df.empty or n == 0:
        return pd.DataFrame(columns=df.columns), df
    n = min(n, len(df))
    idx = rng.choice(len(df), size=n, replace=False)
    mask = np.zeros(len(df), dtype=bool)
    mask[idx] = True
    return df.iloc[mask].reset_index(drop=True), df.iloc[~mask].reset_index(drop=True)


def build_fold_data(
    test_sess: dict,
    train_sessions: list[dict],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame, pd.DataFrame]:
    """Assemble (X_train, y_train, eval_normal_df, eval_long_df).

    If calibration is enabled:
      - N_CALIB_PER_CLASS GT events per class are taken from the test session
        and added to the training data.
      - Evaluation uses the REMAINING test-session GT events.
    """
    # Training data from base sessions
    X_parts, y_parts = [], []
    for sess in train_sessions:
        Xs, ys = collect_session_data(
            sess["prepared"], sess["valid_idx"],
            sess["normal_df"], sess["long_df"],
            EPOCH_DURATION_S, bg_ratio=BG_RATIO, rng=rng,
        )
        if len(ys) > 0:
            X_parts.append(Xs)
            y_parts.append(ys)

    eval_normal_df = test_sess["normal_df"]
    eval_long_df   = test_sess["long_df"]

    # Rec #2: calibration from test session
    if USE_CALIBRATION and N_CALIB_PER_CLASS > 0:
        calib_normal, eval_normal_df = _split_calibration(
            test_sess["normal_df"], N_CALIB_PER_CLASS, rng
        )
        calib_long, eval_long_df = _split_calibration(
            test_sess["long_df"], N_CALIB_PER_CLASS, rng
        )
        calib_all = pd.concat([calib_normal, calib_long], ignore_index=True)
        Xc, yc = collect_session_data(
            test_sess["prepared"], test_sess["valid_idx"],
            calib_normal, calib_long,
            EPOCH_DURATION_S, bg_ratio=0.5, rng=rng,
        )
        if len(yc) > 0:
            X_parts.append(Xc)
            y_parts.append(yc)
            logger.info(
                "Calibration: +%d normal, +%d long GT events from %s",
                len(calib_normal), len(calib_long), test_sess["pair"],
            )

    X_train = np.vstack(X_parts) if X_parts else np.empty((0, 22), dtype=np.float32)
    y_train = np.concatenate(y_parts) if y_parts else np.empty(0, dtype=int)
    X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
    return X_train, y_train, eval_normal_df, eval_long_df


# ---------------------------------------------------------------------------
# LOSO CV
# ---------------------------------------------------------------------------

def _event_metrics(scored) -> dict:
    em = scored.best_eval_result.event_metrics
    return {"ch": scored.best_channel,
            "tp": em.tp, "fp": em.fp, "fn": em.fn,
            "P": em.precision, "R": em.recall, "F1": em.f1}


def run_loso(
    selected_sessions: list[dict],
    all_sessions: list[dict],
) -> list[dict]:
    """LOSO CV: test = each selected session, train = everything else."""
    selected_names = {s["pair"] for s in selected_sessions}
    results = []

    for test_idx, test_sess in enumerate(selected_sessions):
        pair = test_sess["pair"]
        logger.info("LOSO fold %d/%d — test=%s", test_idx + 1, len(selected_sessions), pair)

        # Training sessions (Rec #5 — all sessions except test)
        if USE_ALL_SESSIONS:
            train_sessions = [s for s in all_sessions if s["pair"] != pair]
        else:
            train_sessions = [s for s in selected_sessions if s["pair"] != pair]

        logger.info("  Training sessions: %d", len(train_sessions))

        rng = np.random.default_rng(42 + test_idx)
        X_train, y_train, eval_normal_df, eval_long_df = build_fold_data(
            test_sess, train_sessions, rng
        )

        if len(y_train) == 0:
            logger.error("No training data for fold %d. Skipping.", test_idx + 1)
            continue

        classes_present = np.unique(y_train)
        logger.info(
            "  Training: %d samples  classes=%s",
            len(y_train), {int(c): int(np.sum(y_train == c)) for c in classes_present},
        )

        # Rec #1 — hyperparameter grid search
        model = train_svm_pipeline(
            X_train, y_train,
            C=SVM_C, gamma=SVM_GAMMA, kernel=SVM_KERNEL,
            use_grid_search=USE_GRID_SEARCH,
        )

        # Rec #3 — combined candidate detection at test time
        channel_results = predict_and_build_results(
            test_sess["prepared"],
            test_sess["valid_idx"],
            model,
            threshold_factor=CAND_THRESHOLD_FACTOR,
            debounce_ms=CAND_DEBOUNCE_MS,
            min_dur_s=CAND_MIN_DUR_S,
            max_dur_s=CAND_MAX_DUR_S,
            use_combined_candidates=USE_COMBINED_CANDIDATES,
        )

        # Evaluate against remaining GT events
        all_eval_df = pd.concat(
            [eval_normal_df, eval_long_df], ignore_index=True
        )
        gt_all    = _df_to_annotations(all_eval_df)
        gt_normal = _df_to_annotations(eval_normal_df)
        gt_long   = _df_to_annotations(eval_long_df)

        scored_all    = evaluate_channels(channel_results, gt_all,    EPOCH_DURATION_S)
        scored_normal = evaluate_channels(channel_results, gt_normal, EPOCH_DURATION_S)
        scored_long   = evaluate_channels(channel_results, gt_long,   EPOCH_DURATION_S)

        results.append({
            "pair":          pair,
            "n_normal_gt":   len(test_sess["normal_df"]),
            "n_long_gt":     len(test_sess["long_df"]),
            "n_eval_normal": len(eval_normal_df),
            "n_eval_long":   len(eval_long_df),
            "norm_dur_mean": float(test_sess["normal_df"]["duration"].mean())
                             if not test_sess["normal_df"].empty else 0.0,
            "long_dur_mean": float(test_sess["long_df"]["duration"].mean())
                             if not test_sess["long_df"].empty else 0.0,
            "all":    _event_metrics(scored_all),
            "normal": _event_metrics(scored_normal),
            "long":   _event_metrics(scored_long),
        })
        logger.info(
            "  fold done  normal_R=%.4f  long_R=%.4f",
            results[-1]["normal"]["R"], results[-1]["long"]["R"],
        )

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_table(results: list[dict], subset: str, key: str) -> None:
    n_gt_col  = "n_eval_normal" if key == "normal" else "n_eval_long"
    hdr = (f"{'pair':<32}  {'n_eval':>6}  {'best_ch':<12}  "
           f"{'tp':>5}  {'fp':>5}  {'fn':>5}  {'P':>8}  {'R':>8}  {'F1':>8}")
    sep = "-" * len(hdr)
    print(f"\n{'='*len(hdr)}")
    print(f"  {subset.upper()} BLINKS")
    print(f"{'='*len(hdr)}")
    print(hdr)
    print(sep)
    total_tp = total_fp = total_fn = 0
    for r in results:
        m = r[key]
        total_tp += m["tp"]; total_fp += m["fp"]; total_fn += m["fn"]
        print(f"{r['pair']:<32}  {r[n_gt_col]:>6}  {str(m['ch']):<12}  "
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
    print("  SVM IMPROVED (TU16b) — LOSO RESULTS")
    print("#" * 72)
    recs = []
    if USE_GRID_SEARCH:        recs.append("Rec#1 grid-search")
    if USE_CALIBRATION:        recs.append(f"Rec#2 calib(n={N_CALIB_PER_CLASS})")
    if USE_COMBINED_CANDIDATES: recs.append("Rec#3 combined-cands")
    recs.append("Rec#4 22-features")
    if USE_ALL_SESSIONS:       recs.append("Rec#5 all-sessions")
    print(f"\nActive: {' | '.join(recs)}")
    print(f"Epoch: {EPOCH_DURATION_S}s  health>={MIN_HEALTH}  "
          f"filter: {FILTER_LOW}-{FILTER_HIGH}Hz")

    print(f"\nDuration profile per session:")
    print(f"  {'session':<32}  {'n_normal':>8}  {'norm_dur':>9}  "
          f"{'n_long':>7}  {'long_dur':>9}")
    print(f"  {'-'*32}  {'-'*8}  {'-'*9}  {'-'*7}  {'-'*9}")
    for r in results:
        print(f"  {r['pair']:<32}  {r['n_normal_gt']:>8}  "
              f"{r['norm_dur_mean']:>9.3f}s  {r['n_long_gt']:>7}  "
              f"{r['long_dur_mean']:>9.3f}s")
    if USE_CALIBRATION and N_CALIB_PER_CLASS > 0:
        print(f"\n  Note: n_eval excludes {N_CALIB_PER_CLASS} calibration events per class.")

    _print_table(results, "ALL events",    "all")
    _print_table(results, "NORMAL blinks", "normal")
    _print_table(results, "LONG blinks",   "long")

    n = len(results)
    print("\n" + "#" * 72)
    print("  SUMMARY — recall comparison")
    print("#" * 72)
    print(f"\n  {'session':<32}  {'norm_recall':>12}  {'long_recall':>12}  "
          f"{'recall_drop':>12}")
    print(f"  {'-'*32}  {'-'*12}  {'-'*12}  {'-'*12}")
    for r in results:
        nr, lr = r["normal"]["R"], r["long"]["R"]
        print(f"  {r['pair']:<32}  {nr:>12.4f}  {lr:>12.4f}  {nr - lr:>+12.4f}")

    avg_nr = sum(r["normal"]["R"] for r in results) / n
    avg_lr = sum(r["long"]["R"]   for r in results) / n
    print(f"\n  Macro-avg (SVM improved): normal={avg_nr:.4f}  long={avg_lr:.4f}  "
          f"drop={avg_nr - avg_lr:+.4f}")

    # Comparison table
    print(f"\n  {'Method':<24}  {'normal recall':>14}  {'long recall':>12}")
    print(f"  {'-'*24}  {'-'*14}  {'-'*12}")
    print(f"  {'SVM improved (TU16b)':<24}  {avg_nr:>14.4f}  {avg_lr:>12.4f}")
    for name, vals in BASELINES.items():
        print(f"  {name:<24}  {vals['normal']:>14.4f}  {vals['long']:>12.4f}")
    print()

    # Assessment
    if avg_lr >= 0.80:
        print("  [LONG TARGET MET]       long recall >= 0.80")
    elif avg_lr >= BASELINES["Dual-mode TU15"]["long"]:
        print(f"  [LONG: BEST SO FAR]     {avg_lr:.4f} > dual-mode "
              f"{BASELINES['Dual-mode TU15']['long']:.4f}")
    elif avg_lr >= BASELINES["Pyblinker TU14"]["long"]:
        improvement = avg_lr - BASELINES["Pyblinker TU14"]["long"]
        print(f"  [LONG: IMPROVED]        +{improvement:.4f} over pyblinker")
    else:
        print(f"  [LONG: BELOW BASELINE]  {avg_lr:.4f}")

    if avg_nr >= 0.83:
        print("  [NORMAL OK]             recall >= 0.83")
    else:
        print(f"  [NORMAL BELOW TARGET]   {avg_nr:.4f} < 0.83")
    print("#" * 72)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    logger.info("=== Tutorial 16b: SVM improved (all 5 recommendations) ===")

    # Discover ALL Raja sessions
    all_pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    if not all_pairs:
        logger.error("No complete pairs found. Exiting.")
        return
    logger.info("Total Raja sessions available: %d", len(all_pairs))

    logger.info("Loading sessions …")
    all_sessions, errors = _load_all_parallel(all_pairs)
    if errors:
        for e in errors:
            logger.warning("skip: %s", e)

    if not all_sessions:
        logger.error("No sessions loaded. Exiting.")
        return

    # Subset: selected 5 are both train AND test (in LOSO roles)
    selected_order = {n: i for i, n in enumerate(SELECTED_SESSIONS)}
    selected_sessions = sorted(
        [s for s in all_sessions if s["pair"] in selected_order],
        key=lambda s: selected_order[s["pair"]],
    )
    if not selected_sessions:
        logger.error("None of the 5 selected sessions were loaded. Exiting.")
        return

    logger.info(
        "LOSO test sessions: %d  |  total training pool: %d",
        len(selected_sessions),
        len(all_sessions) - 1,  # minus the test session
    )

    results = run_loso(selected_sessions, all_sessions)

    if results:
        print_report(results)

    if errors:
        print("\nLoad errors (sessions skipped):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
