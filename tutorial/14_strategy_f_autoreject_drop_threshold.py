"""Strategy F — autoreject epoch screening + robust threshold blink detection tutorial.

Two-stage thresholding:
  Stage A  Autoreject identifies which epochs are likely blink-heavy.
  Stage B  A per-channel sample-level threshold is estimated from those
           flagged epochs using center + k * MAD robust statistics.
           The center can be the median (default, more robust) or the mean
           (more sensitive to large peaks, more conservative threshold).
  Stage C  Blink regions are located via scan_threshold_crossings_kleifges
           using the Stage B threshold.
"""

from __future__ import annotations

from pathlib import Path
import sys

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.analysis.lane_evaluation import evaluate_channel_lanes
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from pyblinker.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference
from pyblinker.strategy_f.runner import channel_results_strategy_f

FIF_PATH = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif"
)
CSV_PATH = Path(
    r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg\S1\S01_20170519_043933\ear_eog.csv"
    )
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
PEAK_SIDE_TOLERANCE_S = 0.01
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Stage A: autoreject settings
AUTOREJECT_RANDOM_STATE = 42
MIN_FLAGGED_EPOCHS = 1          # fall back when fewer flagged epochs are found

# Stage B: robust threshold settings
STD_THRESHOLD = 3.5             # k in: threshold = center + k * (1.4826 * MAD)
CENTER_METHOD = "median"        # "median" (robust, detects more blinks) or
                                # "mean"   (pulled by peaks, more conservative)

VERBOSE = True                  # print Stage A/B diagnostic lines

# Set to a positive integer to process only the first N epochs.
N_EPOCHS: int | None = None


def main() -> None:
    print(f"Strategy autoreject drop threshold and centre method {CENTER_METHOD}")
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
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

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose": VERBOSE,
    }
    channel_results = channel_results_strategy_f(
        prepared,
        valid_epoch_indices,
        setting=setting,
    )

    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(CSV_PATH, EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )

    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=EPOCH_DURATION_S,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )

    # Print a brief diagnostic for the best channel
    best = channel_results[0]
    for r in channel_results:
        if r["channel"] == scored.best_result["channel"]:
            best = r
            break

    print(f"\nn_flagged_epochs={best['n_flagged']}  used_all_epochs={best['used_all_epochs']}")
    print(
        f"blink_region_threshold={best['blink_region_threshold']:.6f}  "
        f"center={best['threshold_center']:.6f}  "
        f"dispersion={best['threshold_dispersion']:.6f}"
    )

    m = scored.best_metrics
    print(f"\nbest_channel={scored.best_result['channel']}")
    print(f"tp={m.true_positives}  fp={m.false_positives}  fn={m.false_negatives}")
    print(f"precision={m.precision:.4f}  recall={m.recall:.4f}  f1={m.f1:.4f}")
    print(f"\n=== Lane Summary (top 10) ===")
    print(scored.lane_summary.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
