"""Tutorial: Traditional pyblinker full pipeline on a continuous (long) signal.

Mirrors tutorial/11_strategy_pyblinker_epoch.py but runs the same complete
6-step pyblinker pipeline on the FULL continuous recording rather than on
individual 30-second epochs.

This is the classic usage as shown in tutorial/01a_basic_usage.py — the
entire raw signal is fed to the pipeline at once.  Results are then scored
against the same ground truth and with the same evaluation framework as the
epoch-mode script, enabling a direct apples-to-apples comparison.

Key difference from tutorial 11:
  - Tutorial 11: pipeline runs independently on each 30-second epoch
  - Tutorial 12: pipeline runs once on the full-length continuous signal
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
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.pipeline_steps import process_channel_data as _pyblinker_process_channel_data

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ANNOTATION_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
PROCESSED_BASE_DIR  = Path(r"D:\dataset\drowsy_driving_raja_processed")
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
# Must match tutorial 11 so ground-truth epoch indices align.
EPOCH_DURATION_S: float = 30.0
FILTER_LOW: float  = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None   # None = no resampling

# Set to a positive integer to limit dataset pairs processed.
N_PAIRS: int | None = 2


# ---------------------------------------------------------------------------
# Core: full pyblinker pipeline on the continuous signal
# ---------------------------------------------------------------------------

def run_pyblinker_continuous_pipeline(raw: mne.io.BaseRaw) -> list[dict]:
    """Run the full 6-step pyblinker pipeline on the continuous raw signal.

    Creates a ``BlinkDetector``, applies filtering / resampling via
    ``prepare_raw_signal()``, then runs ``process_channel_data`` for every
    EEG channel.  The resulting blink sample indices are converted to
    epoch-relative timing (using ``EPOCH_DURATION_S``) so that
    ``evaluate_channels`` can score them against the ground truth.

    Returns
    -------
    list[dict]
        One dict per channel with keys ``channel``, ``df_positions``, and
        ``mapped_candidates`` — identical format to tutorial 11.
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

    # Filter (and optionally resample) the raw signal — same as BlinkDetector.get_blink()
    detector.prepare_raw_signal()
    sfreq = float(detector.sfreq)

    channel_names = list(detector.channel_list)
    logger.info(
        "Running full pyblinker 6-step pipeline on continuous signal: "
        "%d channel(s)  [sfreq=%.1f Hz, signal_len=%.1f s]",
        len(channel_names),
        sfreq,
        detector.raw_data.times[-1],
    )

    results: list[dict] = []

    for ch_name in tqdm(channel_names, desc="Channels", unit="ch"):
        detector.all_data_info = []
        detector.all_data = []

        try:
            _pyblinker_process_channel_data(detector, ch_name, verbose=False)
        except Exception as exc:
            logger.debug("Channel %s: pipeline error — %s", ch_name, exc)
            results.append({
                "channel":           ch_name,
                "df_positions":      pd.DataFrame(),
                "mapped_candidates": pd.DataFrame(
                    columns=["epoch_index", "channel", "blink_onset",
                             "blink_duration", "start_blink", "end_blink"]
                ),
            })
            continue

        if not detector.all_data_info:
            results.append({
                "channel":           ch_name,
                "df_positions":      pd.DataFrame(),
                "mapped_candidates": pd.DataFrame(
                    columns=["epoch_index", "channel", "blink_onset",
                             "blink_duration", "start_blink", "end_blink"]
                ),
            })
            continue

        df_out = detector.all_data_info[0]["df"]

        if df_out.empty:
            results.append({
                "channel":           ch_name,
                "df_positions":      pd.DataFrame(),
                "mapped_candidates": pd.DataFrame(
                    columns=["epoch_index", "channel", "blink_onset",
                             "blink_duration", "start_blink", "end_blink"]
                ),
            })
            continue

        # Convert absolute sample indices → epoch-relative timing
        start_samples = df_out["start_blink"].to_numpy(dtype=int)
        end_samples   = df_out["end_blink"].to_numpy(dtype=int)
        onset_abs     = start_samples / sfreq
        durations     = (end_samples - start_samples) / sfreq
        epoch_indices = (onset_abs // EPOCH_DURATION_S).astype(int)
        blink_onsets  = onset_abs - epoch_indices * EPOCH_DURATION_S

        mapped_candidates = pd.DataFrame({
            "epoch_index":    epoch_indices,
            "channel":        ch_name,
            "blink_onset":    blink_onsets,
            "blink_duration": durations,
            "start_blink":    start_samples,
            "end_blink":      end_samples,
        })

        results.append({
            "channel":           ch_name,
            "df_positions":      df_out.copy(),
            "mapped_candidates": mapped_candidates,
        })

    return results


# ---------------------------------------------------------------------------
# Single pair runner
# ---------------------------------------------------------------------------

def run_one_pair(pair_name: str, fif_path: Path, csv_path: Path) -> dict:
    logger.info("Loading pair: %s", pair_name)
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(fif_path, brain_channels)
    logger.info("Recording duration: %.1f s", raw.times[-1])

    channel_results = run_pyblinker_continuous_pipeline(raw)

    gt_annotations = load_ground_truth_annotations(csv_path, EPOCH_DURATION_S)
    scored = evaluate_channels(
        channel_results,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
    )

    em = scored.best_eval_result.event_metrics
    return {
        "pair":            pair_name,
        "best_channel":    scored.best_channel,
        "tp":              em.tp,
        "fp":              em.fp,
        "fn":              em.fn,
        "precision":       em.precision,
        "recall":          em.recall,
        "f1":              em.f1,
        "scored":          scored,
        "channel_results": channel_results,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    logger.info("=== Tutorial 12: Full pyblinker pipeline on continuous signal ===")
    logger.info(
        "filter: %.1f–%.1f Hz  |  resample: %s",
        FILTER_LOW, FILTER_HIGH,
        f"{RESAMPLE_RATE} Hz" if RESAMPLE_RATE else "none",
    )

    pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    if not pairs:
        logger.warning("No complete pairs found under %s. Exiting.", ANNOTATION_BASE_DIR)
        return

    if N_PAIRS is not None:
        pairs = pairs[:N_PAIRS]

    logger.info("Processing %d pair(s):", len(pairs))
    for p in pairs:
        logger.info("  %s", p["name"])

    all_results: list[dict] = []
    for pair in pairs:
        try:
            result = run_one_pair(pair["name"], pair["fif"], pair["csv"])
            all_results.append(result)
        except Exception as exc:
            logger.error("pair=%s: %s", pair["name"], exc, exc_info=True)

    if not all_results:
        logger.error("No results produced.")
        return

    # -----------------------------------------------------------------------
    # Per-pair table
    # -----------------------------------------------------------------------
    hdr_w = {"pair": 30, "ch": 16, "tp": 5, "fp": 5, "fn": 5,
              "prec": 10, "rec": 8, "f1": 8}
    header = (
        f"{'pair':<{hdr_w['pair']}}  {'best_channel':<{hdr_w['ch']}}  "
        f"{'tp':>{hdr_w['tp']}}  {'fp':>{hdr_w['fp']}}  {'fn':>{hdr_w['fn']}}  "
        f"{'precision':>{hdr_w['prec']}}  {'recall':>{hdr_w['rec']}}  {'f1':>{hdr_w['f1']}}"
    )
    sep = "=" * len(header)

    print(f"\n{sep}")
    print(
        f"FULL PYBLINKER PIPELINE — CONTINUOUS SIGNAL  "
        f"(filter={FILTER_LOW}-{FILTER_HIGH}Hz)"
    )
    print(sep)
    print(header)
    print("-" * len(header))
    for r in all_results:
        print(
            f"{r['pair']:<{hdr_w['pair']}}  "
            f"{str(r['best_channel']):<{hdr_w['ch']}}  "
            f"{r['tp']:>{hdr_w['tp']}}  "
            f"{r['fp']:>{hdr_w['fp']}}  "
            f"{r['fn']:>{hdr_w['fn']}}  "
            f"{r['precision']:>{hdr_w['prec']}.4f}  "
            f"{r['recall']:>{hdr_w['rec']}.4f}  "
            f"{r['f1']:>{hdr_w['f1']}.4f}"
        )
    print(sep)

    # -----------------------------------------------------------------------
    # Aggregate
    # -----------------------------------------------------------------------
    total_tp = sum(r["tp"] for r in all_results)
    total_fp = sum(r["fp"] for r in all_results)
    total_fn = sum(r["fn"] for r in all_results)
    micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
    macro_p  = sum(r["precision"] for r in all_results) / len(all_results)
    macro_r  = sum(r["recall"]    for r in all_results) / len(all_results)
    macro_f1 = sum(r["f1"]        for r in all_results) / len(all_results)

    print(f"\n--- Aggregate across {len(all_results)} pair(s) ---")
    print(f"  TP={total_tp}  FP={total_fp}  FN={total_fn}")
    print(f"  micro P={micro_p:.4f}  R={micro_r:.4f}  F1={micro_f1:.4f}")
    print(f"  macro P={macro_p:.4f}  R={macro_r:.4f}  F1={macro_f1:.4f}")

    # -----------------------------------------------------------------------
    # Lane summary per pair
    # -----------------------------------------------------------------------
    for r in all_results:
        print(f"\n{'='*60}")
        print(f"Lane summary — {r['pair']}")
        print("=" * 60)
        print(r["scored"].lane_summary.head(10).to_string(index=False))

        # Per-channel blink count
        print(f"\n--- Per-channel blink count (continuous signal) ---")
        print(f"{'channel':<16}  {'total_blinks':>13}")
        print("-" * 32)
        rows = sorted(
            [(cr["channel"], len(cr["mapped_candidates"])) for cr in r["channel_results"]],
            key=lambda x: x[1],
            reverse=True,
        )
        for ch, n in rows:
            print(f"{ch:<16}  {n:>13}")

    # -----------------------------------------------------------------------
    # Side-by-side comparison reminder
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("COMPARISON REFERENCE (tutorial 11 - epoch mode, 30 s):")
    print("  micro F1 ~0.4272  |  macro F1 ~0.4321  (2-pair check)")
    print(f"\nContinuous signal (this script):")
    print(f"  micro F1 = {micro_f1:.4f}  |  macro F1 = {macro_f1:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
