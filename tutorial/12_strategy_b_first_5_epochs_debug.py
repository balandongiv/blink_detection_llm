"""Debug tutorial: Strategy B (Nathanael MNE) on the first 5 epochs."""

from __future__ import annotations

from pathlib import Path
import sys

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.common.validation import (
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.strategy_b.nathanael_mne import (
    DEFAULT_STRATEGY_B_CHANNELS,
    find_eog_candidate_regions,
    summarize_candidate_regions,
)

DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"
CHANNELS = list(DEFAULT_STRATEGY_B_CHANNELS)

TARGET_EPOCH_INDEX = 0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
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
        existing = [c for c in columns if c in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


def main() -> None:
    print(f"data_path={DATA_PATH}")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"channels={CHANNELS}")
    print(f"target_epoch_index={TARGET_EPOCH_INDEX}")

    epochs = load_first_5_epochs()
    reference = load_reference_blink_table(REFERENCE_PATH)

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)

    print(f"prepared_shape={prepared.data.shape}")
    print(f"prepared_channel_names={prepared.channel_names}")
    print(f"prepared_sfreq={prepared.sfreq}")
    print(f"epoch_length_samples={prepared.epoch_length_samples}")
    print(f"valid_epoch_indices={valid_epoch_indices}")

    # Run find_eog_candidate_regions on each channel and collect all candidates
    all_candidates: list[pd.DataFrame] = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        signal = prepared.data[valid_epoch_indices, ch_idx, :].reshape(-1)
        df_positions = find_eog_candidate_regions(
            signal,
            channel=channel_name,
            sfreq=prepared.sfreq,
            half_window_s=MNE_HALF_WINDOW_S,
            l_freq=MNE_LOW_FREQ,
            h_freq=MNE_HIGH_FREQ,
            thresh=MNE_THRESH,
        )
        mapped = summarize_candidate_regions(
            df_positions,
            epoch_length_samples=prepared.epoch_length_samples,
            sfreq=prepared.sfreq,
            epoch_indices=valid_epoch_indices,
        )
        print(f"  channel={channel_name}  raw_candidates={len(df_positions)}  mapped={len(mapped)}")
        if not mapped.empty:
            all_candidates.append(mapped)

    blink_table = (
        pd.concat(all_candidates, ignore_index=True)
        .sort_values(["epoch_index", "blink_onset"])
        .reset_index(drop=True)
        if all_candidates else pd.DataFrame()
    )

    signal_by_epoch = {
        ep: prepared.data[ep, 0, :].astype(float)
        for ep in range(prepared.data.shape[0])
    }
    metrics = match_blink_tables(
        blink_table,
        reference,
        n_epochs=len(epochs),
        signal_by_epoch=signal_by_epoch,
        sfreq=prepared.sfreq,
    )

    print_frame(
        f"Predicted Blinks For Epoch {TARGET_EPOCH_INDEX}",
        blink_table[blink_table["epoch_index"] == TARGET_EPOCH_INDEX].copy(),
        ["epoch_index", "channel", "blink_onset", "blink_duration"],
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
