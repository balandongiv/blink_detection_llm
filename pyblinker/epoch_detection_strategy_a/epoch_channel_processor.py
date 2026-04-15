"""Per-channel epoch-mode wrappers around the legacy blink steps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pyblinker.blink_features.waveform_features.extract_blink_properties import (
    BlinkProperties,
)
from pyblinker.blinker.fit_blink import FitBlinks
from pyblinker.blinker.get_blink_positions import get_blink_position
from pyblinker.utils.statistics_utils import get_blink_statistic, get_good_blink_mask


@dataclass
class EpochChannelBlinkResult:
    """Blink-detection outputs for one channel in epoch mode."""

    channel: str
    stats: dict[str, float]
    final_blinks: pd.DataFrame
    mapped_blinks: pd.DataFrame
    valid_epoch_indices: list[int]
    n_valid_epochs: int
    n_epochs_with_detections: int
    n_epochs_with_good_blinks: int
    n_pavr_passed: int


def map_concatenated_blinks_to_epochs(
    blink_df: pd.DataFrame,
    *,
    channel: str,
    valid_epoch_indices: list[int],
    epoch_boundaries: list[tuple[int, int]],
    sfreq: float,
) -> pd.DataFrame:
    """Project concatenated-signal blink rows back into epoch-local timing."""

    if blink_df.empty or not valid_epoch_indices:
        return pd.DataFrame(
            columns=[
                "epoch_index",
                "channel",
                "blink_onset",
                "blink_duration",
                "start_blink",
                "end_blink",
            ]
        )

    boundary_starts = np.asarray([start for start, _ in epoch_boundaries], dtype=int)
    boundary_stops = np.asarray([stop for _, stop in epoch_boundaries], dtype=int)
    blink_rows = blink_df.copy().reset_index(drop=True)
    blink_rows["channel"] = channel

    start_samples = blink_rows["start_blink"].to_numpy(dtype=int)
    epoch_offsets = np.searchsorted(boundary_stops, start_samples, side="right")
    valid_mask = (
        (epoch_offsets >= 0)
        & (epoch_offsets < len(boundary_starts))
        & (start_samples >= boundary_starts[epoch_offsets])
        & (start_samples < boundary_stops[epoch_offsets])
    )
    if not np.any(valid_mask):
        return pd.DataFrame(
            columns=[
                "epoch_index",
                "channel",
                "blink_onset",
                "blink_duration",
                "start_blink",
                "end_blink",
            ]
        )

    mapped = blink_rows.loc[valid_mask].copy().reset_index(drop=True)
    mapped_epoch_offsets = epoch_offsets[valid_mask]
    mapped["epoch_index"] = [valid_epoch_indices[idx] for idx in mapped_epoch_offsets]
    mapped["blink_onset"] = (
        mapped["start_blink"].to_numpy(dtype=float) - boundary_starts[mapped_epoch_offsets]
    ) / float(sfreq)
    mapped["blink_duration"] = (
        mapped["end_blink"].to_numpy(dtype=float)
        - mapped["start_blink"].to_numpy(dtype=float)
    ) / float(sfreq)
    return mapped.sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)


def process_concatenated_epoch_channel(
    detector_params: dict,
    concatenated_signal: np.ndarray,
    channel: str,
    valid_epoch_indices: list[int],
    epoch_boundaries: list[tuple[int, int]],
    sfreq: float,
    verbose: bool = True,
) -> EpochChannelBlinkResult:
    """Run the legacy six-step pipeline on concatenated valid-epoch data."""

    del verbose

    df_positions = get_blink_position(
        detector_params,
        blink_component=concatenated_signal,
        ch=channel,
        progress_bar=False,
    )

    fitblinks = FitBlinks(
        candidate_signal=concatenated_signal,
        df=df_positions,
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


__all__ = ["EpochChannelBlinkResult", "process_concatenated_epoch_channel"]
