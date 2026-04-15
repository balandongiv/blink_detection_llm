"""Strategy B channel processor: MNE Step 1 plus the legacy refinement stack."""

from __future__ import annotations

import numpy as np

from pyblinker.blink_features.waveform_features.extract_blink_properties import (
    BlinkProperties,
)
from pyblinker.blinker.fit_blink import FitBlinks
from pyblinker.epoch_detection_strategy_a.epoch_channel_processor import (
    EpochChannelBlinkResult,
    map_concatenated_blinks_to_epochs,
)
from pyblinker.utils.statistics_utils import get_blink_statistic, get_good_blink_mask

from .mne_step1 import find_eog_candidate_regions


def process_concatenated_epoch_channel_mne(
    detector_params: dict,
    concatenated_signal: np.ndarray,
    channel: str,
    valid_epoch_indices: list[int],
    epoch_boundaries: list[tuple[int, int]],
    sfreq: float,
    mne_half_window_s: float = 0.10,
    mne_l_freq: float = 1.0,
    mne_h_freq: float = 20.0,
    mne_thresh: float | None = None,
    verbose: bool = True,
) -> EpochChannelBlinkResult:
    """Run Strategy B on one channel using the Strategy A downstream steps."""

    del verbose

    df_positions = find_eog_candidate_regions(
        concatenated_signal,
        channel=channel,
        sfreq=sfreq,
        half_window_s=mne_half_window_s,
        l_freq=mne_l_freq,
        h_freq=mne_h_freq,
        thresh=mne_thresh,
    )

    fitblinks = FitBlinks(
        candidate_signal=concatenated_signal,
        df=df_positions.copy(),
        params=detector_params,
    )
    fitblinks.dprocess()
    fitted_df = fitblinks.frame_blinks

    blink_stats = get_blink_statistic(
        fitted_df,
        detector_params["z_thresholds"],
        signal=concatenated_signal,
    )
    blink_stats["ch"] = channel
    blink_stats["strategy_b_stage1_candidates"] = int(len(df_positions))

    _, good_df = get_good_blink_mask(
        fitted_df,
        blink_stats["best_median"],
        blink_stats["best_robust_std"],
        detector_params["z_thresholds"],
    )

    if good_df.empty:
        mapped = map_concatenated_blinks_to_epochs(
            good_df,
            channel=channel,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=sfreq,
        )
        return EpochChannelBlinkResult(
            channel=channel,
            stats=blink_stats,
            final_blinks=good_df.reset_index(drop=True),
            mapped_blinks=mapped,
            valid_epoch_indices=list(valid_epoch_indices),
            n_valid_epochs=len(valid_epoch_indices),
            n_epochs_with_detections=0,
            n_epochs_with_good_blinks=0,
            n_pavr_passed=0,
        )

    df_out = BlinkProperties(
        concatenated_signal,
        good_df.copy(),
        sfreq,
        detector_params,
    ).df

    condition_1 = df_out["pos_amp_vel_ratio_zero"] < detector_params["p_avr_threshold"]
    condition_2 = df_out["max_value"] < (
        blink_stats["best_median"] - blink_stats["best_robust_std"]
    )
    final_blinks = df_out.loc[~(condition_1 & condition_2)].copy().reset_index(drop=True)
    mapped = map_concatenated_blinks_to_epochs(
        final_blinks,
        channel=channel,
        valid_epoch_indices=valid_epoch_indices,
        epoch_boundaries=epoch_boundaries,
        sfreq=sfreq,
    )

    return EpochChannelBlinkResult(
        channel=channel,
        stats=blink_stats,
        final_blinks=final_blinks,
        mapped_blinks=mapped,
        valid_epoch_indices=list(valid_epoch_indices),
        n_valid_epochs=len(valid_epoch_indices),
        n_epochs_with_detections=int(mapped["epoch_index"].nunique()) if not mapped.empty else 0,
        n_epochs_with_good_blinks=int(blink_stats.get("number_good_blinks", 0)),
        n_pavr_passed=int(len(final_blinks)),
    )


__all__ = ["process_concatenated_epoch_channel_mne"]
