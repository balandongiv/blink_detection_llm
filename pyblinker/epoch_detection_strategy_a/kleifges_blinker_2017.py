"""Strategy A per-channel blink extraction and epoch mapping."""

from __future__ import annotations

from pyblinker.blinker.get_blink_positions import get_blink_position
from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.common.epoch_channel import map_concatenated_blinks_to_epochs
from pyblinker.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.common.pipeline_utils import build_epoch_boundaries, build_signal_by_epoch


def blink_position_strategy_a(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Run Strategy A blink detection on each channel and map results to epochs.

    Returns a list of dicts, one per channel, each containing:

    - ``channel``: channel name
    - ``df_positions``: DataFrame of raw blink-position candidates (concatenated signal space)
    - ``mapped_candidates``: DataFrame of epoch-relative blink candidates
      (columns: epoch_index, channel, blink_onset, blink_duration, ...)
    - ``signal_by_epoch``: dict mapping epoch_index -> 1-D filtered signal array
    """
    params = BlinkDetector._build_detector_params(None, {})
    params["sfreq"] = float(prepared.sfreq)

    epoch_boundaries = build_epoch_boundaries(
        len(valid_epoch_indices), prepared.epoch_length_samples
    )

    results = []
    for channel_index, channel_name in enumerate(prepared.channel_names):
        concatenated_signal = prepared.data[valid_epoch_indices, channel_index, :].reshape(-1)
        df_positions = get_blink_position(
            params,
            blink_component=concatenated_signal,
            ch=channel_name,
            progress_bar=False,
        )
        mapped_positions = map_concatenated_blinks_to_epochs(
            df_positions,
            channel=channel_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )
        signal_by_epoch = build_signal_by_epoch(prepared, channel_index)
        results.append(
            {
                "channel": channel_name,
                "df_positions": df_positions,
                "mapped_candidates": mapped_positions,
                "signal_by_epoch": signal_by_epoch,
            }
        )
    return results


__all__ = ["blink_position_strategy_a"]
