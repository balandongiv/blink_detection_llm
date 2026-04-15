from __future__ import annotations

from pathlib import Path

import mne
import pandas as pd

from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.channel_blink_benchmark import (
    blink_position_strategy_a,
)
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_a.epoch_validation import (
    filter_reference_to_valid_epochs,
    load_reference_blink_table,
    match_blink_tables,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"

TARGET_CHANNEL = "EEG X1 - Pz"
N_EPOCHS = 5
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
EXPECTED_STAGE1_REGIONS = 185


def load_epochs() -> mne.Epochs:
    epochs = mne.read_epochs(str(DATA_PATH), preload=True, verbose="ERROR")
    return epochs[:N_EPOCHS].copy().pick([TARGET_CHANNEL])


def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        columns = [column for column in columns if column in frame.columns]
        frame = frame.loc[:, columns]
    print(frame.to_string(index=False))


def main() -> None:
    print(f"data_path={DATA_PATH}")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"target_channel={TARGET_CHANNEL}")
    print(f"n_epochs={N_EPOCHS}")
    print(f"filter_low={FILTER_LOW}")
    print(f"filter_high={FILTER_HIGH}")
    print(f"resample_rate={RESAMPLE_RATE}")

    epochs = load_epochs()
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )

    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = blink_position_strategy_a(prepared, valid_epoch_indices)
    result = channel_results[0]  # Single channel: TARGET_CHANNEL
    df_positions = result["df_positions"]
    mapped_positions = result["mapped_candidates"]
    signal_by_epoch = result["signal_by_epoch"]

    reference = load_reference_blink_table(REFERENCE_PATH)
    reference = filter_reference_to_valid_epochs(reference, valid_epoch_indices)
    metrics = match_blink_tables(
        mapped_positions,
        reference,
        n_epochs=len(epochs),
        signal_by_epoch=signal_by_epoch,
        sfreq=float(prepared.sfreq),
    )

    print(f"valid_epoch_indices={valid_epoch_indices}")
    print(f"prepared_shape={prepared.data.shape}")
    concatenated_length = len(valid_epoch_indices) * prepared.epoch_length_samples
    print(f"concatenated_signal_length={concatenated_length}")
    print(f"stage1_candidate_regions={len(df_positions)}")
    print(f"expected_stage1_candidate_regions={EXPECTED_STAGE1_REGIONS}")
    print(f"stage1_region_count_delta={len(df_positions) - EXPECTED_STAGE1_REGIONS}")
    print(f"reference_blinks={len(reference)}")

    print_frame(
        "Stage 1 Candidate Regions",
        df_positions,
        ["start_blink", "end_blink"],
    )
    print_frame(
        "Stage 1 Candidate Regions Mapped To Epochs",
        mapped_positions,
        ["epoch_index", "channel", "blink_onset", "blink_duration", "start_blink", "end_blink"],
    )
    print_frame(
        "Reference Blinks",
        reference,
        ["epoch_index", "blink_onset", "blink_duration"],
    )

    print("\n=== Stage 1 Metrics ===")
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
