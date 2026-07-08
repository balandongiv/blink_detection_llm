"""Tutorial 13a: Full pyblinker pipeline — epoch mode, ALL epochs included.

Identical pipeline to tutorial/11_strategy_pyblinker_epoch.py (concatenate all
valid epochs → run 6-step pyblinker pipeline → map blinks back to epochs), but
with epoch health awareness made explicit:

  - ALL epochs are included regardless of their epoch_health score.
  - This serves as the baseline / upper-bound recall reference for comparing
    against 13b (which filters by epoch health >= 3).

Epoch health background
-----------------------
``epoch_health.csv`` assigns a quality score (1–5) to every 30-second baseline
window of a recording.  A score of 1 means heavily artefacted; 5 means clean.
The file lives alongside ``ear_eog.csv`` in the annotation session directory.

Existing epoch-health implementations in this project
------------------------------------------------------
* ``pyblinker.epoch_detection.epoch_health``
    - ``assign_epoch_health(health_df, epoch_duration_s, n_epochs)``:
        maps baseline health scores onto analysis epochs by taking the minimum
        health of all overlapping 30-second baseline windows.
    - ``get_valid_epoch_indices_by_health(health_values, min_health=3)``:
        returns epoch indices whose assigned health >= min_health.
  (installed package:
   pyblinker/epoch_detection/epoch_health.py)

* ``tutorial/11a_kleifges_drop_epoch.py``  (MIN_HEALTH=4)
    - ``load_epoch_health(path)``
    - ``attach_health_metadata(epochs, health_df, min_health)``
    Uses ``assign_epoch_health`` + ``get_valid_epoch_indices_by_health`` to
    attach ``is_bad_epoch`` flags to ``epochs.metadata`` before running the
    Kleifges strategy.

* ``tutorial/22_strategy_comparison_cao2018.py``  (HEALTH_DROP_THRESHOLD=3)
    - ``get_valid_epochs_from_health(epoch_health_path, epoch_duration_s, n_epochs)``
    Drops an analysis epoch if ANY overlapping 30-second baseline sub-epoch has
    health <= HEALTH_DROP_THRESHOLD (i.e. keeps epoch only when all sub-epochs
    have health > threshold).

This script (13a) intentionally skips all health filtering so that results are
directly comparable to 13b.
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
from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from src.common.pipeline_utils import build_epoch_boundaries
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.utils.dataset_discovery import discover_raja_pairs
from src.utils.experiment_utils import setup_tutorial_logging

from pyblinker.blinker.default_setting import build_blink_params
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
FILTER_LOW: float  = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None

# For initial testing, target S1/S01_20170519_043933_3 — it has 5 low-health
# epochs (1×health=3, 4×health=1) so 13b's filter will actually drop epochs.
# Set to None to auto-discover all complete pairs.
TEST_SESSION: str | None = "S1/S01_20170519_043933_3"


# ---------------------------------------------------------------------------
# Minimal detector interface (same as tutorial 11)
# ---------------------------------------------------------------------------

class _MinimalDetector:
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
# Core pipeline (same as tutorial 11)
# ---------------------------------------------------------------------------

def run_pyblinker_epoch_pipeline(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Concatenate valid epochs per channel → run 6-step pipeline → map back."""
    sfreq = float(prepared.sfreq)
    n_valid = len(valid_epoch_indices)
    epoch_boundaries = build_epoch_boundaries(n_valid, prepared.epoch_length_samples)

    logger.info(
        "Pipeline: %d channel(s), %d epoch(s)  [sfreq=%.1f Hz, concat=%.1f s]",
        len(prepared.channel_names), n_valid, sfreq,
        n_valid * prepared.epoch_length_samples / sfreq,
    )

    _empty = pd.DataFrame(
        columns=["epoch_index", "channel", "blink_onset",
                 "blink_duration", "start_blink", "end_blink"]
    )
    results: list[dict] = []

    for ch_idx, ch_name in enumerate(
        tqdm(prepared.channel_names, desc="Channels", unit="ch")
    ):
        concat_signal = (
            prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1).astype(np.float64)
        )
        info = mne.create_info(ch_names=[ch_name], sfreq=sfreq,
                               ch_types=["eeg"], verbose=False)
        raw_array = mne.io.RawArray(concat_signal[np.newaxis, :], info, verbose=False)
        detector = _MinimalDetector(raw_array, sfreq)

        try:
            _pyblinker_process_channel_data(detector, ch_name, verbose=False)
        except Exception as exc:
            logger.debug("ch %s: %s", ch_name, exc)
            results.append({"channel": ch_name, "df_positions": pd.DataFrame(),
                            "mapped_candidates": _empty.copy()})
            continue

        if not detector.all_data_info or detector.all_data_info[0]["df"].empty:
            results.append({"channel": ch_name, "df_positions": pd.DataFrame(),
                            "mapped_candidates": _empty.copy()})
            continue

        df_out = detector.all_data_info[0]["df"]
        mapped = map_concatenated_blinks_to_epochs(
            df_out,
            channel=ch_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=sfreq,
        )
        results.append({"channel": ch_name, "df_positions": df_out.copy(),
                        "mapped_candidates": mapped})

    return results


# ---------------------------------------------------------------------------
# Single pair runner
# ---------------------------------------------------------------------------

def run_one_pair(pair_name: str, fif_path: Path, csv_path: Path) -> dict:
    logger.info("Pair: %s", pair_name)
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(fif_path, brain_channels)

    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    n_total = len(epochs)

    # ALL epochs — no health filtering
    valid_epoch_indices = list(range(n_total))
    logger.info("Using ALL %d epochs (no health filter)", n_total)

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )

    channel_results = run_pyblinker_epoch_pipeline(prepared, valid_epoch_indices)
    gt_annotations  = load_ground_truth_annotations(csv_path, EPOCH_DURATION_S)
    scored = evaluate_channels(channel_results, gt_annotations,
                               epoch_duration=EPOCH_DURATION_S)
    em = scored.best_eval_result.event_metrics
    return {
        "pair":            pair_name,
        "n_epochs_total":  n_total,
        "n_epochs_used":   n_total,
        "best_channel":    scored.best_channel,
        "tp":              em.tp, "fp": em.fp, "fn": em.fn,
        "precision":       em.precision,
        "recall":          em.recall,
        "f1":              em.f1,
        "scored":          scored,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    logger.info("=== Tutorial 13a: Pyblinker epoch mode — ALL epochs ===")

    pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    if not pairs:
        logger.warning("No pairs found. Exiting.")
        return
    if TEST_SESSION is not None:
        pairs = [p for p in pairs if p["name"] == TEST_SESSION]
        if not pairs:
            logger.error("TEST_SESSION %r not found among discovered pairs.", TEST_SESSION)
            return
    logger.info("Processing %d pair(s)", len(pairs))

    all_results: list[dict] = []
    for pair in pairs:
        try:
            all_results.append(run_one_pair(pair["name"], pair["fif"], pair["csv"]))
        except Exception as exc:
            logger.error("pair=%s: %s", pair["name"], exc, exc_info=True)

    if not all_results:
        return

    # Table
    header = (f"{'pair':<30}  {'epochs':>6}  {'best_ch':<12}  "
              f"{'tp':>5}  {'fp':>5}  {'fn':>5}  "
              f"{'precision':>10}  {'recall':>8}  {'f1':>8}")
    sep = "=" * len(header)
    print(f"\n{sep}")
    print(f"PYBLINKER EPOCH MODE - ALL EPOCHS  (epoch={EPOCH_DURATION_S:.0f}s)")
    print(sep)
    print(header)
    print("-" * len(header))
    for r in all_results:
        print(f"{r['pair']:<30}  {r['n_epochs_used']:>6}  {str(r['best_channel']):<12}  "
              f"{r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  "
              f"{r['precision']:>10.4f}  {r['recall']:>8.4f}  {r['f1']:>8.4f}")
    print(sep)

    # Aggregate
    total_tp = sum(r["tp"] for r in all_results)
    total_fp = sum(r["fp"] for r in all_results)
    total_fn = sum(r["fn"] for r in all_results)
    micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
    macro_f1 = sum(r["f1"] for r in all_results) / len(all_results)
    print(f"\n  micro F1={micro_f1:.4f}  macro F1={macro_f1:.4f}")
    print(f"  (see tutorial 13b for epoch-health >= 3 comparison)")

    for r in all_results:
        print(f"\n--- Lane summary: {r['pair']} ---")
        print(r["scored"].lane_summary.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
