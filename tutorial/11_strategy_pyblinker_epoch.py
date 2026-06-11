"""Tutorial: Traditional pyblinker full pipeline in epoch mode (concatenation approach).

Mirrors how other epoch-mode strategies (kleifges, nathanael_mne) operate:

  1. All valid epochs are concatenated into a single long signal per channel.
  2. The complete 6-step pyblinker pipeline runs on that concatenated signal.
  3. Detected blinks are mapped back to their originating epoch and converted
     to epoch-relative timing.
  4. Results are scored against the ground truth with ``evaluate_channels``.

This is the correct epoch-mode interpretation of the traditional pyblinker
pipeline — it matches the pattern in tutorial/10b_strategy_nathanael.py and
allows direct comparison with tutorial/12_strategy_pyblinker_continuous.py
(which runs the same pipeline on the raw continuous recording).

The 6 steps executed on the concatenated signal per channel:
  1. get_blink_position  — threshold-crossing scan
  2. FitBlinks           — waveform fitting
  3. get_blink_statistic — amplitude statistics
  4. _select_good_blinks — quality filtering
  5. BlinkProperties     — waveform feature extraction
  6. pAVR filter         — saccade / blink discrimination
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
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from src.common.pipeline_utils import build_epoch_boundaries
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

from pyblinker.blinker.default_setting import build_blink_params
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
EPOCH_DURATION_S: float = 30.0
FILTER_LOW: float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None

# Set to a positive integer to process only the first N epochs.
N_EPOCHS: int | None = None

# Set to a positive integer to limit the number of dataset pairs processed.
N_PAIRS: int | None = 2


# ---------------------------------------------------------------------------
# Minimal detector interface
# ---------------------------------------------------------------------------

class _MinimalDetector:
    """Satisfies the interface expected by pyblinker.pipeline_steps.

    Wraps a single-channel ``mne.io.RawArray`` (the concatenated epoch
    signal) so that ``process_channel_data`` can be called without
    constructing a full ``BlinkDetector``.  No additional filtering or
    resampling is performed here since the data from
    ``PreparedEpochDetectionInput`` is already bandpass-filtered.
    """

    def __init__(self, raw_array: mne.io.RawArray, sfreq: float) -> None:
        self.raw_data = raw_array
        self.params = build_blink_params({"sfreq": sfreq})
        self.all_data_info: list[dict] = []
        self.all_data: list[dict] = []

    @staticmethod
    def filter_point(ch: str, all_data_info: list[dict]) -> dict:
        return next(d for d in all_data_info if d["ch"] == ch)

    def filter_bad_blink(self, df: pd.DataFrame) -> pd.DataFrame:
        return df


# ---------------------------------------------------------------------------
# Core: concatenate epochs → run full pyblinker pipeline → map back
# ---------------------------------------------------------------------------

def run_pyblinker_epoch_pipeline(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Run the full 6-step pyblinker pipeline on concatenated epoch signals.

    For each channel:
      1. All valid epochs are concatenated into one long 1-D signal.
      2. The complete 6-step pipeline runs on that concatenated signal.
      3. Detected blinks are mapped back to epoch-relative timing via
         ``map_concatenated_blinks_to_epochs``.

    Returns
    -------
    list[dict]
        One dict per channel with keys ``channel``, ``df_positions``, and
        ``mapped_candidates`` — compatible with ``evaluate_channels``.
    """
    sfreq = float(prepared.sfreq)
    epoch_length_samples = prepared.epoch_length_samples
    n_valid = len(valid_epoch_indices)

    # Epoch boundaries in the concatenated signal (shared across all channels)
    epoch_boundaries = build_epoch_boundaries(n_valid, epoch_length_samples)

    logger.info(
        "Running full pyblinker 6-step pipeline: %d channel(s), "
        "%d epoch(s) concatenated per channel  "
        "[sfreq=%.1f Hz, concat_len=%.1f s]",
        len(prepared.channel_names),
        n_valid,
        sfreq,
        n_valid * epoch_length_samples / sfreq,
    )

    _empty_mapped = pd.DataFrame(
        columns=["epoch_index", "channel", "blink_onset",
                 "blink_duration", "start_blink", "end_blink"]
    )

    results: list[dict] = []

    for ch_idx, ch_name in enumerate(
        tqdm(prepared.channel_names, desc="Channels", unit="ch")
    ):
        # 1. Concatenate valid epochs for this channel into one signal
        concat_signal = (
            prepared.data[valid_epoch_indices, ch_idx, :]
            .reshape(-1)
            .astype(np.float64)
        )

        # 2. Wrap in a 1-channel RawArray (no extra filtering applied)
        info = mne.create_info(
            ch_names=[ch_name],
            sfreq=sfreq,
            ch_types=["eeg"],
            verbose=False,
        )
        raw_array = mne.io.RawArray(
            concat_signal[np.newaxis, :], info, verbose=False
        )
        detector = _MinimalDetector(raw_array, sfreq)

        # 3. Run all 6 pipeline steps on the concatenated signal
        try:
            _pyblinker_process_channel_data(detector, ch_name, verbose=False)
        except Exception as exc:
            logger.debug("Channel %s: pipeline error — %s", ch_name, exc)
            results.append({
                "channel":           ch_name,
                "df_positions":      pd.DataFrame(),
                "mapped_candidates": _empty_mapped.copy(),
            })
            continue

        if not detector.all_data_info:
            results.append({
                "channel":           ch_name,
                "df_positions":      pd.DataFrame(),
                "mapped_candidates": _empty_mapped.copy(),
            })
            continue

        df_out = detector.all_data_info[0]["df"]

        if df_out.empty:
            results.append({
                "channel":           ch_name,
                "df_positions":      pd.DataFrame(),
                "mapped_candidates": _empty_mapped.copy(),
            })
            continue

        # 4. Map concatenated-signal blink positions back to epoch-relative timing
        mapped_candidates = map_concatenated_blinks_to_epochs(
            df_out,
            channel=ch_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=sfreq,
        )

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
    logger.info("Valid epochs: %d / %d", len(valid_epoch_indices), len(epochs))

    channel_results = run_pyblinker_epoch_pipeline(prepared, valid_epoch_indices)

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
    logger.info("=== Tutorial 11: Full pyblinker pipeline in epoch mode (concatenation) ===")
    logger.info(
        "Epoch duration: %.0f s  |  filter: %.1f-%.1f Hz",
        EPOCH_DURATION_S, FILTER_LOW, FILTER_HIGH,
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
        f"{'precision':>{hdr_w['prec']}}  {'recall':>{hdr_w['rec']}}  "
        f"{'f1':>{hdr_w['f1']}}"
    )
    sep = "=" * len(header)

    print(f"\n{sep}")
    print(
        f"FULL PYBLINKER PIPELINE - EPOCH MODE (concat)  "
        f"(epoch={EPOCH_DURATION_S:.0f}s, filter={FILTER_LOW}-{FILTER_HIGH}Hz)"
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
        print(f"Lane summary - {r['pair']}")
        print("=" * 60)
        print(r["scored"].lane_summary.head(10).to_string(index=False))

    # -----------------------------------------------------------------------
    # Comparison with continuous signal (tutorial 12)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("COMPARISON  (2-pair check)")
    print("=" * 60)
    print(f"  Epoch mode - concat (this script):  micro F1={micro_f1:.4f}  macro F1={macro_f1:.4f}")
    print(f"  Continuous signal (tutorial 12):    micro F1=0.8328  macro F1=0.8373")
    print("=" * 60)


if __name__ == "__main__":
    main()
