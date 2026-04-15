"""Strategy C — autoreject Bayesian-optimization blink detection tutorial."""

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
from pyblinker.strategy_c import AUTOREJECT_BAYESIAN_OPTIMIZATION
from pyblinker.strategy_c.runner import blink_position_strategy_c

FIF_PATH = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif"
)
CSV_PATH = Path(
    r"D:\dataset\drowsy_driving_raja\human_label_annotation\S1\S01_20170519_043933\ear_eog.csv"
)
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
PEAK_SIDE_TOLERANCE_S = 0.01
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
STAGE1_CHANNELS = ("__NO_BACKBONE__",)
STAGE1_THRESHOLD_SCOPE = "per_channel"
STAGE1_RESCALE_THRESHOLD = True
AUTOREJECT_METHOD = AUTOREJECT_BAYESIAN_OPTIMIZATION
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT = False

# Set to a positive integer to process only the first N epochs.
N_EPOCHS: int | None = None


def main() -> None:
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
    channel_results = blink_position_strategy_c(
        prepared,
        valid_epoch_indices,
        stage1_channels=STAGE1_CHANNELS,
        stage1_threshold_scope=STAGE1_THRESHOLD_SCOPE,
        stage1_rescale_threshold=STAGE1_RESCALE_THRESHOLD,
        autoreject_random_state=AUTOREJECT_RANDOM_STATE,
        autoreject_method=AUTOREJECT_METHOD,
        autoreject_augment=AUTOREJECT_AUGMENT,
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

    m = scored.best_metrics
    print(f"\nbest_channel={scored.best_result['channel']}")
    print(f"tp={m.true_positives}  fp={m.false_positives}  fn={m.false_negatives}")
    print(f"precision={m.precision:.4f}  recall={m.recall:.4f}  f1={m.f1:.4f}")
    print(f"\n=== Lane Summary (top 10) ===")
    print(scored.lane_summary.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
