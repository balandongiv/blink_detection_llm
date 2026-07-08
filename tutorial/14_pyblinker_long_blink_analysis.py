"""Tutorial 14: Pyblinker long-blink detection analysis.

Research Question
-----------------
The traditional pyblinker pipeline was designed for normal, involuntary eye
blinks.  How well does it detect *long* eye closures (drowsiness/microsleep
events)?

Blink Type Definitions
----------------------
Blink physiology divides eye-closure events into two categories:

1. **Normal blink** (duration <= 500 ms, typically 150-400 ms):
   An involuntary, reflexive eye closure.  The standard pyblinker pipeline
   targets this event type.  Literature reference: the average spontaneous
   blink lasts 100-400 ms (Stern et al., 1994).

   Ground-truth labels used here: ``B_CL``, ``HB_CL``, ``eye_blink``,
   ``B_A``, ``B_M``, ``HB_A``, ``HB_M``  AND  duration < LONG_THRESHOLD.

2. **Long blink / full closure** (duration >= 500 ms):
   A voluntary or drowsiness-driven prolonged lid closure.  The PERCLOS
   metric defines microsleep as >= 80% eyelid closure for >= 500 ms
   (Wierwille & Ellsworth, 1994).  In the Raja dataset these events are
   explicitly annotated with ``FC_CL`` (Full Closure) and related labels.

   Ground-truth labels used here: ``FC_CL``, ``FC``, ``FC_A``, ``FC_M``,
   ``FC_CL_FRAME_VIEWER``  OR  any event with duration >= LONG_THRESHOLD.

Why pyblinker may struggle with long blinks
-------------------------------------------
The pyblinker 6-step pipeline applies these quality filters that are
calibrated for the shape of a normal blink waveform:

- **Step 2 (FitBlinks)**: fits a Gaussian / polynomial template. A long
  closure has a plateau that yields a poor fit (low R^2).
- **Step 4 (_select_good_blinks)**: retains blinks within statistical
  limits derived from the population amplitude and width distribution.
  Long closures are statistical outliers (too wide) and are likely rejected.
- **Step 6 (pAVR filter)**: applies amplitude-velocity-ratio threshold that
  is tuned to the sharp onset/offset of a normal blink; slow onset of
  drowsiness closures may not exceed this threshold.

Methodology
-----------
1. Select Raja sessions that contain **both** normal and long blinks.
2. Run the complete pyblinker pipeline on the full continuous recording
   (same as tutorial/12_strategy_pyblinker_continuous.py).
3. Evaluate detection separately against:
   a. All ground-truth events.
   b. Only normal-blink ground truth.
   c. Only long-blink ground truth.
4. Report detection metrics per blink type to quantify the performance gap.

Note on FP interpretation
--------------------------
FP counts in the per-subset evaluation are slightly over-inflated: a
predicted blink that correctly matches a *long* blink will appear as FP when
evaluated against the normal-blink subset (and vice-versa).  For this
analysis, **recall** (how many of each type are detected) is the primary
metric of interest.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from blink_evaluation.epoch_utils import enrich_absolute_times
from blink_evaluation.io import dataframe_to_annotations
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.utils.dataset_discovery import discover_raja_pairs
from src.utils.experiment_utils import setup_tutorial_logging

from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.pipeline_steps import process_channel_data as _pyblinker_process_channel_data

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
FILTER_LOW:  float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None

# Duration threshold separating normal from long blinks (seconds)
# Reference: PERCLOS definition (Wierwille & Ellsworth, 1994)
LONG_THRESHOLD_S: float = 0.5

# Labels explicitly annotated as full closures (long blinks)
LONG_BLINK_LABELS: frozenset[str] = frozenset({
    "FC_CL", "FC", "FC_A", "FC_M", "FC_CL_FRAME_VIEWER",
})
# Labels annotated as normal blinks
NORMAL_BLINK_LABELS: frozenset[str] = frozenset({
    "B_CL", "HB_CL", "eye_blink", "B_A", "B_M", "HB_A", "HB_M",
})

# Sessions selected for analysis: must have both normal and long blinks,
# and a complete pair (CSV + FIF).  Top-5 by FC_CL event count:
SELECTED_SESSIONS: list[str] | None = [
    "S13/S26_20190108_035218_3",   # 181 FC, 319 normal
    "S24/S38_20190129_035118_2",   # 138 FC, 859 normal
    "S4/S04_20170606_045500_2",    # 112 FC, 578 normal
    "S2/TEST_20170601_042544_2",   #  85 FC, 202 normal
    "S22/S35_20190123_040805_2",   #  58 FC, 448 normal
]
# Set to None to run on all complete pairs.


# ---------------------------------------------------------------------------
# Ground-truth helpers
# ---------------------------------------------------------------------------

def classify_events(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load CSV and classify events into normal / long / other.

    Returns
    -------
    all_df, normal_df, long_df
        All filtered to known labels only.
    """
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
    df = df.dropna(subset=["duration"])

    is_long_label  = df["description"].isin(LONG_BLINK_LABELS)
    is_normal_label = df["description"].isin(NORMAL_BLINK_LABELS)
    is_long_dur    = df["duration"] >= LONG_THRESHOLD_S

    # Long: explicit FC label OR duration >= threshold
    long_mask   = is_long_label | (is_normal_label & is_long_dur)
    # Normal: normal label AND duration < threshold
    normal_mask = is_normal_label & ~is_long_dur

    known_mask = is_long_label | is_normal_label
    all_known  = df[known_mask].copy()
    normal_df  = df[normal_mask].copy()
    long_df    = df[long_mask].copy()

    return all_known, normal_df, long_df


def _df_to_annotations(df: pd.DataFrame, epoch_duration: float) -> mne.Annotations:
    """Convert a raw CSV DataFrame (onset, duration) to mne.Annotations."""
    if df.empty:
        return mne.Annotations(onset=[], duration=[], description=[])
    rows = []
    for _, row in df.iterrows():
        onset_abs = float(row["onset"])
        duration  = float(row["duration"])
        ei = int(onset_abs // epoch_duration)
        rows.append({
            "epoch_index":    ei,
            "blink_onset":    onset_abs - ei * epoch_duration,
            "blink_duration": duration,
        })
    ref_df  = pd.DataFrame(rows)
    rich_df = enrich_absolute_times(ref_df, epoch_duration)
    return dataframe_to_annotations(rich_df)


# ---------------------------------------------------------------------------
# Pyblinker continuous pipeline (same as tutorial 12)
# ---------------------------------------------------------------------------

def run_pyblinker_continuous_pipeline(raw: mne.io.BaseRaw) -> list[dict]:
    """Run the 6-step pyblinker pipeline on the full continuous signal.

    Returns one dict per channel: channel, df_positions, mapped_candidates.
    The mapped_candidates DataFrame uses epoch-relative timing so that
    evaluate_channels can score against epoch-indexed ground truth.
    """
    detector = BlinkDetector(
        raw,
        visualize=False,
        annot_label=None,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE if RESAMPLE_RATE is not None else raw.info["sfreq"],
        n_jobs=1,
        use_multiprocessing=False,
        pick_types_options={"eeg": True},
    )
    detector.prepare_raw_signal()
    sfreq = float(detector.sfreq)
    channel_names = list(detector.channel_list)

    logger.info(
        "Pyblinker on %d channel(s)  [sfreq=%.1f Hz, len=%.1f s]",
        len(channel_names), sfreq, detector.raw_data.times[-1],
    )

    _empty = pd.DataFrame(
        columns=["epoch_index", "channel", "blink_onset",
                 "blink_duration", "start_blink", "end_blink"]
    )
    results: list[dict] = []

    for ch_name in tqdm(channel_names, desc="Channels", unit="ch"):
        detector.all_data_info = []
        detector.all_data = []
        try:
            _pyblinker_process_channel_data(detector, ch_name, verbose=False)
        except Exception as exc:
            logger.debug("ch %s: %s", ch_name, exc)
            results.append({"channel": ch_name, "df_positions": pd.DataFrame(),
                            "mapped_candidates": _empty.copy()})
            continue

        if not detector.all_data_info:
            results.append({"channel": ch_name, "df_positions": pd.DataFrame(),
                            "mapped_candidates": _empty.copy()})
            continue

        df_out = detector.all_data_info[0]["df"]
        if df_out.empty:
            results.append({"channel": ch_name, "df_positions": pd.DataFrame(),
                            "mapped_candidates": _empty.copy()})
            continue

        start_samples = df_out["start_blink"].to_numpy(dtype=int)
        end_samples   = df_out["end_blink"].to_numpy(dtype=int)
        onset_abs     = start_samples / sfreq
        durations     = (end_samples - start_samples) / sfreq
        epoch_indices = (onset_abs // EPOCH_DURATION_S).astype(int)
        blink_onsets  = onset_abs - epoch_indices * EPOCH_DURATION_S

        mapped = pd.DataFrame({
            "epoch_index":    epoch_indices,
            "channel":        ch_name,
            "blink_onset":    blink_onsets,
            "blink_duration": durations,
            "start_blink":    start_samples,
            "end_blink":      end_samples,
        })
        results.append({"channel": ch_name, "df_positions": df_out.copy(),
                        "mapped_candidates": mapped})

    return results


# ---------------------------------------------------------------------------
# Per-pair evaluation
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

    # Ground truth — split into normal and long
    all_df, normal_df, long_df = classify_events(csv_path)
    logger.info(
        "Ground truth: %d total  |  %d normal  |  %d long",
        len(all_df), len(normal_df), len(long_df),
    )
    if long_df.empty:
        logger.warning("No long blinks found — skipping pair.")
        return {}

    # Duration stats per type
    logger.info(
        "Normal duration: mean=%.3fs  max=%.3fs",
        normal_df["duration"].mean(), normal_df["duration"].max(),
    )
    logger.info(
        "Long duration:   mean=%.3fs  max=%.3fs  (min=%.3fs)",
        long_df["duration"].mean(), long_df["duration"].max(),
        long_df["duration"].min(),
    )

    gt_all    = _df_to_annotations(all_df,    EPOCH_DURATION_S)
    gt_normal = _df_to_annotations(normal_df, EPOCH_DURATION_S)
    gt_long   = _df_to_annotations(long_df,   EPOCH_DURATION_S)

    # Run pipeline once
    channel_results = run_pyblinker_continuous_pipeline(raw)

    # Evaluate against each GT subset
    scored_all    = evaluate_channels(channel_results, gt_all,    EPOCH_DURATION_S)
    scored_normal = evaluate_channels(channel_results, gt_normal, EPOCH_DURATION_S)
    scored_long   = evaluate_channels(channel_results, gt_long,   EPOCH_DURATION_S)

    return {
        "pair":         pair_name,
        "n_normal_gt":  len(normal_df),
        "n_long_gt":    len(long_df),
        "norm_dur_mean": normal_df["duration"].mean(),
        "long_dur_mean": long_df["duration"].mean(),
        "all":    _event_metrics(scored_all),
        "normal": _event_metrics(scored_normal),
        "long":   _event_metrics(scored_long),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_table(all_results: list[dict], subset: str, key: str) -> tuple[int, int, int]:
    hdr = (f"{'pair':<32}  {'n_gt':>5}  {'best_ch':<12}  "
           f"{'tp':>5}  {'fp':>5}  {'fn':>5}  {'P':>8}  {'R':>8}  {'F1':>8}")
    sep = "-" * len(hdr)
    print(f"\n{'='*len(hdr)}")
    print(f"  {subset.upper()} BLINKS  (threshold={LONG_THRESHOLD_S}s)")
    print(f"{'='*len(hdr)}")
    print(hdr)
    print(sep)
    total_tp = total_fp = total_fn = 0
    n_gt_key = "n_normal_gt" if key == "normal" else "n_long_gt"
    for r in all_results:
        m = r[key]
        total_tp += m["tp"]; total_fp += m["fp"]; total_fn += m["fn"]
        print(f"{r['pair']:<32}  {r[n_gt_key]:>5}  {str(m['ch']):<12}  "
              f"{m['tp']:>5}  {m['fp']:>5}  {m['fn']:>5}  "
              f"{m['P']:>8.4f}  {m['R']:>8.4f}  {m['F1']:>8.4f}")
    print(sep)
    micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
    print(f"  MICRO  TP={total_tp}  FP={total_fp}  FN={total_fn}  "
          f"P={micro_p:.4f}  R={micro_r:.4f}  F1={micro_f1:.4f}")
    return total_tp, total_fp, total_fn


def print_report(all_results: list[dict]) -> None:
    print("\n" + "#" * 72)
    print("  PYBLINKER LONG BLINK DETECTION ANALYSIS")
    print("#" * 72)
    print(f"\nBlink type definitions:")
    print(f"  Normal  (<= {LONG_THRESHOLD_S}s): labels B_CL, HB_CL, eye_blink, B_A/M, HB_A/M")
    print(f"  Long   (>= {LONG_THRESHOLD_S}s): labels FC_CL, FC, FC_A, FC_M  OR  duration >= {LONG_THRESHOLD_S}s")

    print(f"\nDuration profile per session:")
    print(f"  {'session':<32}  {'n_normal':>8}  {'norm_dur_mean':>14}  "
          f"{'n_long':>7}  {'long_dur_mean':>14}")
    print(f"  {'-'*32}  {'-'*8}  {'-'*14}  {'-'*7}  {'-'*14}")
    for r in all_results:
        print(f"  {r['pair']:<32}  {r['n_normal_gt']:>8}  "
              f"{r['norm_dur_mean']:>14.3f}s  {r['n_long_gt']:>7}  "
              f"{r['long_dur_mean']:>14.3f}s")

    _print_table(all_results, "ALL events",    "all")
    _print_table(all_results, "NORMAL blinks", "normal")
    _print_table(all_results, "LONG blinks",   "long")

    # Summary comparison
    print("\n" + "#" * 72)
    print("  SUMMARY — recall comparison (best channel per session)")
    print("#" * 72)
    print(f"\n  {'session':<32}  {'normal_recall':>14}  {'long_recall':>12}  "
          f"{'recall_drop':>12}")
    print(f"  {'-'*32}  {'-'*14}  {'-'*12}  {'-'*12}")
    for r in all_results:
        nr = r["normal"]["R"]
        lr = r["long"]["R"]
        drop = nr - lr
        print(f"  {r['pair']:<32}  {nr:>14.4f}  {lr:>12.4f}  {drop:>+12.4f}")

    print()
    avg_nr = sum(r["normal"]["R"] for r in all_results) / len(all_results)
    avg_lr = sum(r["long"]["R"] for r in all_results) / len(all_results)
    print(f"  Macro-avg recall — normal: {avg_nr:.4f}  |  long: {avg_lr:.4f}  "
          f"|  drop: {avg_nr - avg_lr:+.4f}")
    print()
    print("  Interpretation:")
    if avg_lr < 0.2:
        print("  [POOR]  Pyblinker misses the vast majority of long closures.")
        print("          The quality filters (_select_good_blinks, FitBlinks)")
        print("          reject wide-plateau waveforms characteristic of")
        print("          drowsiness closures.")
    elif avg_lr < 0.5:
        print("  [PARTIAL]  Pyblinker detects some long closures — likely at")
        print("             the onset (short blink-like spike) but misses the")
        print("             sustained closure plateau.")
    else:
        print("  [MODERATE]  Pyblinker detects a meaningful fraction of long")
        print("              closures; however, likely classifies only the")
        print("              onset edge, not the full closure duration.")
    print("#" * 72)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    logger.info("=== Tutorial 14: Pyblinker long-blink detection analysis ===")
    logger.info(
        "Long blink threshold: >= %.1f s  |  Labels: %s",
        LONG_THRESHOLD_S,
        ", ".join(sorted(LONG_BLINK_LABELS)),
    )

    pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    if not pairs:
        logger.error("No complete pairs found. Exiting.")
        return

    if SELECTED_SESSIONS is not None:
        pairs = [p for p in pairs if p["name"] in SELECTED_SESSIONS]
        if not pairs:
            logger.error("None of SELECTED_SESSIONS found in complete pairs.")
            return
        pairs.sort(key=lambda p: SELECTED_SESSIONS.index(p["name"]))

    logger.info("Processing %d session(s):", len(pairs))
    for p in pairs:
        logger.info("  %s", p["name"])

    all_results: list[dict] = []
    for pair in pairs:
        try:
            result = run_one_pair(pair["name"], pair["fif"], pair["csv"])
            if result:
                all_results.append(result)
        except Exception as exc:
            logger.error("pair=%s: %s", pair["name"], exc, exc_info=True)

    if not all_results:
        logger.error("No results produced.")
        return

    print_report(all_results)


if __name__ == "__main__":
    main()
