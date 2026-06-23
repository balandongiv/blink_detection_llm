"""Tutorial 15: Dual-mode epoch blink detector — normal + long closure.

Research Question
-----------------
The new dual-mode detector combines:
  Module A: pyblinker 6-step pipeline (normal blinks, < 500 ms)
  Module B: sustained-suppression detector (long closures, ≥ 500 ms)

Does this improve long-blink recall vs. the pyblinker baseline (~0.55)?

Pyblinker baseline (Tutorial 14):
  normal recall = 0.8341   long recall = 0.5550   long F1 = 0.2729

Targets (from writing/long_blink_detection_report.md):
  normal recall ≥ 0.83    (match baseline)
  long recall   ≥ 0.80    (+25 pp improvement)
  long F1       ≥ 0.70    (improvement from 0.27)

Epoch setup
-----------
* 30-second epochs
* Epoch health >= MIN_HEALTH (4)  — same as tutorial/11a and tutorial/13b
* Concatenate valid epochs → run detection → map back

Multi-threading
---------------
USE_MULTITHREAD = True   fast, parallel per-session execution
USE_MULTITHREAD = False  sequential, easier to trace in a debugger

Development workflow
--------------------
1. Start with SELECTED_SESSIONS = 1–2 sessions (default: S4 is the "easiest"
   — shortest mean long-closure duration; S13 is the "hardest").
2. Once Module B results look promising, expand SELECTED_SESSIONS to all 5.
3. Tune Module B parameters (alpha, suppress_min_s, pad_s) if needed.
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from blink_evaluation.epoch_utils import enrich_absolute_times
from blink_evaluation.io import dataframe_to_annotations
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.strategy_dual_mode.runner import LONG_THRESHOLD_S, run_dual_mode_epoch_pipeline
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

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
MIN_HEALTH: int = 4             # keep epochs with assigned health >= 4
FILTER_LOW:  float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None

# ---------------------------------------------------------------------------
# Module B parameters  (tune these if results need improvement)
# ---------------------------------------------------------------------------
RMS_WINDOW_MS:      float = 50.0    # sliding RMS window
BASELINE_WINDOW_S:  float = 5.0    # shorter window → more local baseline, catches quiet plateaus better
ALPHA:              float = 0.3    # deeper suppression required (more selective)
DEBOUNCE_MS:        float = 150.0  # longer debounce to bridge dips in long-closure plateau
SUPPRESS_MIN_S:     float = 0.10   # shorter minimum → catch shorter plateaus
PAD_S:              float = 0.20   # onset/offset padding
MIN_LONG_S:         float = 0.5    # PERCLOS threshold
MAX_LONG_S:         float = 15.0   # artefact ceiling

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True  # set False for single-thread debugging

# Start with 2 sessions for development:
#   S4  → short long closures (0.43 s mean) — easiest for Module B
#   S13 → long closures (1.27 s mean)       — hardest
# Expand to all 5 once results look good.
# All 5 sessions from Tutorial 14 (top-5 by long-blink count).
# Uncomment the 2-session version below for faster development iterations.
SELECTED_SESSIONS: list[str] | None = [
    "S13/S26_20190108_035218_3",
    "S24/S38_20190129_035118_2",
    "S4/S04_20170606_045500_2",
    "S2/TEST_20170601_042544_2",
    "S22/S35_20190123_040805_2",
]

# Development subset (2 sessions — fastest feedback loop):
# SELECTED_SESSIONS = [
#     "S4/S04_20170606_045500_2",
#     "S13/S26_20190108_035218_3",
# ]

# ---------------------------------------------------------------------------
# Label definitions (same as Tutorial 14)
# ---------------------------------------------------------------------------
LONG_BLINK_LABELS   = frozenset({"FC_CL", "FC", "FC_A", "FC_M", "FC_CL_FRAME_VIEWER"})
NORMAL_BLINK_LABELS = frozenset({"B_CL", "HB_CL", "eye_blink", "B_A", "B_M", "HB_A", "HB_M"})


# ---------------------------------------------------------------------------
# Ground-truth helpers
# ---------------------------------------------------------------------------

def classify_events(
    csv_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load annotation CSV and split into (all_df, normal_df, long_df)."""
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
    """Convert onset/duration DataFrame to mne.Annotations (epoch-indexed)."""
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
    rich_df = enrich_absolute_times(pd.DataFrame(rows), EPOCH_DURATION_S)
    return dataframe_to_annotations(rich_df)


# ---------------------------------------------------------------------------
# Epoch health filtering
# ---------------------------------------------------------------------------

def _health_valid_indices(
    csv_path: Path,
    n_epochs: int,
    pair_name: str,
) -> list[int]:
    health_csv = csv_path.parent / "epoch_health.csv"
    if not health_csv.is_file():
        logger.warning("%s: no epoch_health.csv — using all %d epochs", pair_name, n_epochs)
        return list(range(n_epochs))

    hdf = pd.read_csv(health_csv)
    required = {"epoch_start_s", "epoch_end_s", "health"}
    if not required.issubset(hdf.columns):
        raise ValueError(f"epoch_health.csv missing columns: {required - set(hdf.columns)}")
    hdf["health"] = pd.to_numeric(hdf["health"], errors="coerce")

    health_values = assign_epoch_health(hdf, EPOCH_DURATION_S, n_epochs)
    valid = get_valid_epoch_indices_by_health(health_values, MIN_HEALTH)
    logger.info(
        "%s: health >= %d → %d / %d epochs kept",
        pair_name, MIN_HEALTH, len(valid), n_epochs,
    )
    return valid


# ---------------------------------------------------------------------------
# Per-pair runner
# ---------------------------------------------------------------------------

def _event_metrics(scored) -> dict:
    em = scored.best_eval_result.event_metrics
    return {
        "ch": scored.best_channel,
        "tp": em.tp, "fp": em.fp, "fn": em.fn,
        "P": em.precision, "R": em.recall, "F1": em.f1,
    }


def run_one_pair(
    pair_name: str,
    fif_path: Path,
    csv_path: Path,
) -> dict:
    logger.info("=== Pair: %s ===", pair_name)

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(fif_path, brain_channels)
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    n_total = len(epochs)

    valid_epoch_indices = _health_valid_indices(csv_path, n_total, pair_name)
    if not valid_epoch_indices:
        raise RuntimeError(f"No valid epochs remain for {pair_name}")

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )

    channel_results = run_dual_mode_epoch_pipeline(
        prepared,
        valid_epoch_indices,
        rms_window_ms=RMS_WINDOW_MS,
        baseline_window_s=BASELINE_WINDOW_S,
        alpha=ALPHA,
        debounce_ms=DEBOUNCE_MS,
        suppress_min_s=SUPPRESS_MIN_S,
        pad_s=PAD_S,
        min_long_duration_s=MIN_LONG_S,
        max_long_duration_s=MAX_LONG_S,
    )

    # Ground truth split
    all_df, normal_df, long_df = classify_events(csv_path)
    logger.info(
        "%s: GT %d total | %d normal | %d long  (mean_long=%.3fs)",
        pair_name, len(all_df), len(normal_df), len(long_df),
        long_df["duration"].mean() if not long_df.empty else 0.0,
    )

    gt_all    = _df_to_annotations(all_df)
    gt_normal = _df_to_annotations(normal_df)
    gt_long   = _df_to_annotations(long_df)

    scored_all    = evaluate_channels(channel_results, gt_all,    EPOCH_DURATION_S)
    scored_normal = evaluate_channels(channel_results, gt_normal, EPOCH_DURATION_S)
    scored_long   = evaluate_channels(channel_results, gt_long,   EPOCH_DURATION_S)

    return {
        "pair":          pair_name,
        "n_normal_gt":   len(normal_df),
        "n_long_gt":     len(long_df),
        "norm_dur_mean": float(normal_df["duration"].mean()) if not normal_df.empty else 0.0,
        "long_dur_mean": float(long_df["duration"].mean())   if not long_df.empty  else 0.0,
        "all":           _event_metrics(scored_all),
        "normal":        _event_metrics(scored_normal),
        "long":          _event_metrics(scored_long),
    }


# ---------------------------------------------------------------------------
# Reporting  (mirrors Tutorial 14 format for easy comparison)
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
    print("  DUAL-MODE EPOCH BLINK DETECTOR — RESULTS")
    print("#" * 72)
    print(f"\nConfig: epoch={EPOCH_DURATION_S}s  health>={MIN_HEALTH}  "
          f"filter={FILTER_LOW}-{FILTER_HIGH}Hz")
    print(f"        alpha={ALPHA}  rms={RMS_WINDOW_MS}ms  "
          f"baseline={BASELINE_WINDOW_S}s  debounce={DEBOUNCE_MS}ms")
    print(f"        suppress_min={SUPPRESS_MIN_S}s  pad={PAD_S}s  "
          f"long=[{MIN_LONG_S},{MAX_LONG_S}]s")
    print(f"\nBlink type definitions:")
    print(f"  Normal (<{LONG_THRESHOLD_S}s): {', '.join(sorted(NORMAL_BLINK_LABELS))}")
    print(f"  Long  (>={LONG_THRESHOLD_S}s): {', '.join(sorted(LONG_BLINK_LABELS))}")

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

    print("\n" + "#" * 72)
    print("  SUMMARY — recall comparison vs pyblinker baseline (Tutorial 14)")
    print("#" * 72)
    print(f"\n  {'session':<32}  {'norm_recall':>12}  {'long_recall':>12}  "
          f"{'recall_drop':>12}")
    print(f"  {'-'*32}  {'-'*12}  {'-'*12}  {'-'*12}")
    for r in results:
        nr = r["normal"]["R"]
        lr = r["long"]["R"]
        print(f"  {r['pair']:<32}  {nr:>12.4f}  {lr:>12.4f}  {nr - lr:>+12.4f}")

    n = len(results)
    avg_nr = sum(r["normal"]["R"] for r in results) / n
    avg_lr = sum(r["long"]["R"]   for r in results) / n
    print(f"\n  Macro-avg (this run):  normal={avg_nr:.4f}  long={avg_lr:.4f}  "
          f"drop={avg_nr - avg_lr:+.4f}")
    print(f"  Pyblinker baseline:    normal=0.8341  long=0.5550  drop=-0.2791")
    print(f"  Long-recall target:    >= 0.80")
    print()

    if avg_lr >= 0.80:
        print("  [TARGET MET]     long recall >= 0.80")
    elif avg_lr > 0.5550:
        improvement = avg_lr - 0.5550
        print(f"  [IMPROVED]       long recall +{improvement:.4f} over baseline")
    else:
        print("  [NO IMPROVEMENT] long recall <= pyblinker baseline")

    if avg_nr >= 0.83:
        print("  [NORMAL OK]      normal recall >= 0.83")
    else:
        regression = 0.83 - avg_nr
        print(f"  [NORMAL REGRESSION]  normal recall -{regression:.4f} below 0.83 target")

    print("#" * 72)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    logger.info("=== Tutorial 15: Dual-mode epoch blink detector ===")
    logger.info(
        "Epoch: %.0f s  |  health >= %d  |  filter: %.1f-%.1f Hz  |  "
        "threads: %s",
        EPOCH_DURATION_S, MIN_HEALTH, FILTER_LOW, FILTER_HIGH,
        "multi" if USE_MULTITHREAD else "single",
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

    logger.info("Processing %d session(s):", len(pairs))
    for p in pairs:
        logger.info("  %s", p["name"])

    all_results: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        logger.info("Running with ThreadPoolExecutor …")
        with ThreadPoolExecutor() as executor:
            future_to_name = {
                executor.submit(run_one_pair, p["name"], p["fif"], p["csv"]): p["name"]
                for p in pairs
            }
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    r = future.result()
                    all_results.append(r)
                    logger.info(
                        "done  %s  normal_R=%.4f  long_R=%.4f",
                        name, r["normal"]["R"], r["long"]["R"],
                    )
                except Exception as exc:
                    logger.error("%s: %s", name, exc, exc_info=True)
                    errors.append(f"ERROR {name}: {exc}")
    else:
        logger.info("Running sequentially (single thread) …")
        for p in pairs:
            try:
                r = run_one_pair(p["name"], p["fif"], p["csv"])
                all_results.append(r)
                logger.info(
                    "done  %s  normal_R=%.4f  long_R=%.4f",
                    p["name"], r["normal"]["R"], r["long"]["R"],
                )
            except Exception as exc:
                logger.error("%s: %s", p["name"], exc, exc_info=True)
                errors.append(f"ERROR {p['name']}: {exc}")

    # Re-sort to SELECTED_SESSIONS order for consistent reporting
    if SELECTED_SESSIONS is not None and all_results:
        order = {name: i for i, name in enumerate(SELECTED_SESSIONS)}
        all_results.sort(key=lambda r: order.get(r["pair"], len(SELECTED_SESSIONS)))

    if all_results:
        print_report(all_results)

    if errors:
        print("\nErrors encountered:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
