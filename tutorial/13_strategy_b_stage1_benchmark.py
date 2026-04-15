from __future__ import annotations

from pathlib import Path
import sys

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.blink_features.waveform_features.extract_blink_properties import (
    BlinkProperties,
)
from pyblinker.blinker.fit_blink import FitBlinks
from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_channel import map_concatenated_blinks_to_epochs
from pyblinker.common.validation import (
    filter_reference_to_valid_epochs,
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.strategy_b.nathanael_mne import find_eog_candidate_regions
from pyblinker.utils.statistics_utils import get_blink_statistic, get_good_blink_mask

DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"

TARGET_CHANNEL = "EEG X1 - Pz"
N_EPOCHS = 5
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None
MNE_HALF_WINDOW_S = 0.10
EXPECTED_STAGE1_CANDIDATE_REGIONS = 161
EXPECTED_FINAL_REGIONS = 145


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
    print(f"mne_low_freq={MNE_LOW_FREQ}")
    print(f"mne_high_freq={MNE_HIGH_FREQ}")
    print(f"mne_thresh={MNE_THRESH}")
    print(f"mne_half_window_s={MNE_HALF_WINDOW_S}")

    epochs = load_epochs()
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    params = BlinkDetector._build_detector_params(None, {})
    params["sfreq"] = float(prepared.sfreq)

    valid_epoch_indices = get_valid_epoch_indices(epochs)
    epoch_boundaries = [
        (
            idx * prepared.epoch_length_samples,
            (idx + 1) * prepared.epoch_length_samples,
        )
        for idx in range(len(valid_epoch_indices))
    ]

    channel_index = prepared.channel_names.index(TARGET_CHANNEL)
    concatenated_signal = prepared.data[valid_epoch_indices, channel_index, :].reshape(-1)
    df_positions = find_eog_candidate_regions(
        concatenated_signal,
        channel=TARGET_CHANNEL,
        sfreq=float(prepared.sfreq),
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )

    fitblinks = FitBlinks(
        candidate_signal=concatenated_signal,
        df=df_positions.copy(),
        params=params,
    )
    fitblinks.dprocess()
    fitted_df = fitblinks.frame_blinks
    blink_stats = get_blink_statistic(
        fitted_df,
        params["z_thresholds"],
        signal=concatenated_signal,
    )
    _, good_df = get_good_blink_mask(
        fitted_df,
        blink_stats["best_median"],
        blink_stats["best_robust_std"],
        params["z_thresholds"],
    )
    if good_df.empty:
        final_blinks = good_df.copy().reset_index(drop=True)
    else:
        df_out = BlinkProperties(
            concatenated_signal,
            good_df.copy(),
            prepared.sfreq,
            params,
        ).df
        condition_1 = df_out["pos_amp_vel_ratio_zero"] < params["p_avr_threshold"]
        condition_2 = df_out["max_value"] < (
            blink_stats["best_median"] - blink_stats["best_robust_std"]
        )
        final_blinks = df_out.loc[~(condition_1 & condition_2)].copy().reset_index(drop=True)

    mapped_positions = map_concatenated_blinks_to_epochs(
        final_blinks,
        channel=TARGET_CHANNEL,
        valid_epoch_indices=valid_epoch_indices,
        epoch_boundaries=epoch_boundaries,
        sfreq=prepared.sfreq,
    )

    reference = load_reference_blink_table(REFERENCE_PATH)
    reference = filter_reference_to_valid_epochs(reference, valid_epoch_indices)
    metrics = match_blink_tables(
        mapped_positions,
        reference,
        n_epochs=len(epochs),
    )

    print(f"valid_epoch_indices={valid_epoch_indices}")
    print(f"prepared_shape={prepared.data.shape}")
    print(f"concatenated_signal_length={len(concatenated_signal)}")
    print(f"stage1_candidate_regions={len(df_positions)}")
    print(f"expected_stage1_candidate_regions={EXPECTED_STAGE1_CANDIDATE_REGIONS}")
    print(
        "stage1_region_count_delta="
        f"{len(df_positions) - EXPECTED_STAGE1_CANDIDATE_REGIONS}"
    )
    print(f"final_refined_regions={len(final_blinks)}")
    print(f"expected_final_regions={EXPECTED_FINAL_REGIONS}")
    print(f"final_region_count_delta={len(final_blinks) - EXPECTED_FINAL_REGIONS}")
    print(f"reference_blinks={len(reference)}")

    print_frame(
        "Stage 1 Candidate Regions",
        df_positions,
        ["start_blink", "end_blink", "peak_sample"],
    )
    print_frame(
        "Final Refined Blinks Mapped To Epochs",
        mapped_positions,
        ["epoch_index", "channel", "blink_onset", "blink_duration", "start_blink", "end_blink"],
    )
    print_frame(
        "Reference Blinks",
        reference,
        ["epoch_index", "blink_onset", "blink_duration"],
    )

    print("\n=== Final Metrics ===")
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
