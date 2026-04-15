from __future__ import annotations

from pathlib import Path
import sys

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.epoch_detection_strategy_a.epoch_validation import (
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.epoch_detection_strategy_b import (
    BlinkDetectorEpochStrategyB,
    DEFAULT_STRATEGY_B_CHANNELS,
)

DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"
CHANNELS = list(DEFAULT_STRATEGY_B_CHANNELS)

TARGET_EPOCH_INDEX = 0
VISUALIZE = False
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None
MNE_HALF_WINDOW_S = 0.10


def load_first_5_epochs() -> mne.Epochs:
    epochs = mne.read_epochs(str(DATA_PATH), preload=True, verbose="ERROR")
    epochs = epochs.copy().pick(CHANNELS)
    return epochs[:5].copy()


def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        existing = [column for column in columns if column in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


def main() -> None:
    print(f"data_path={DATA_PATH}")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"channels={CHANNELS}")
    print(f"target_epoch_index={TARGET_EPOCH_INDEX}")
    print(f"filter_low={FILTER_LOW}")
    print(f"filter_high={FILTER_HIGH}")
    print(f"resample_rate={RESAMPLE_RATE}")
    print(f"mne_low_freq={MNE_LOW_FREQ}")
    print(f"mne_high_freq={MNE_HIGH_FREQ}")
    print(f"mne_thresh={MNE_THRESH}")
    print(f"mne_half_window_s={MNE_HALF_WINDOW_S}")

    epochs = load_first_5_epochs()
    reference = load_reference_blink_table(REFERENCE_PATH)

    detector = BlinkDetectorEpochStrategyB(
        epochs,
        visualize=VISUALIZE,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        n_jobs=1,
        use_multiprocessing=False,
        mne_half_window_s=MNE_HALF_WINDOW_S,
        mne_l_freq=MNE_LOW_FREQ,
        mne_h_freq=MNE_HIGH_FREQ,
        mne_thresh=MNE_THRESH,
    )
    prepared = detector.prepare_epoch_data()
    print(f"prepared_shape={prepared.data.shape}")
    print(f"prepared_channel_names={prepared.channel_names}")
    print(f"prepared_sfreq={prepared.sfreq}")
    print(f"epoch_length_samples={prepared.epoch_length_samples}")

    annotations, channel, n_good_blinks, blink_table, _fig_data, selected_channel, _epochs = (
        detector.get_blink()
    )
    metrics = match_blink_tables(
        blink_table,
        reference,
        n_epochs=len(epochs),
    )

    print(f"selected_channel={channel}")
    print(f"n_good_blinks={n_good_blinks}")
    print(f"annotation_count={len(annotations)}")
    print_frame("Selected Channel Summary", selected_channel)
    print_frame(
        f"Predicted Blinks For Epoch {TARGET_EPOCH_INDEX}",
        blink_table[blink_table["epoch_index"] == TARGET_EPOCH_INDEX].copy(),
        ["epoch_index", "channel", "blink_onset", "blink_duration", "epoch_selection"],
    )
    print_frame(
        f"Reference Blinks For Epoch {TARGET_EPOCH_INDEX}",
        reference[reference["epoch_index"] == TARGET_EPOCH_INDEX].copy(),
        ["epoch_index", "blink_onset", "blink_duration"],
    )

    print("\n=== Metrics Against Reference ===")
    print(
        {
            "true_positives": metrics.true_positives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "epoch_blink_agreement": metrics.epoch_blink_agreement,
            "blink_count_agreement": metrics.blink_count_agreement,
        }
    )


if __name__ == "__main__":
    main()
