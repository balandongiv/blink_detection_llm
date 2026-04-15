"""Strategy A per-channel blink extraction and epoch mapping."""

from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.common.epoch_channel import map_concatenated_blinks_to_epochs
from pyblinker.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.common.pipeline_utils import build_epoch_boundaries, build_signal_by_epoch
from .thresholding import compute_basic_statistics, scan_threshold_crossings
import pandas as pd

def kleifges_strategy_a(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """In this experimentation, we employ the kleifges approach,its a bare as we remove
    the logic that filter short blink (i.e.,  min_event_sep = float(params.get("min_event_sep", params["min_event_len"])

    We only concern the logic of getting the threshold, which is calculate via compute_basic_statistics,
    and the filter strategy which is implemented via the scan_threshold_crossings function.

    Run Strategy A blink detection on each channel and map results to epochs.

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

        min_blink_frames, threshold = compute_basic_statistics(params, concatenated_signal)
        start_blinks, end_blinks = scan_threshold_crossings(
            concatenated_signal,
            float(threshold),
            min_blink_frames,
            progress_bar=False,
            channel_name=channel_name,
            )

        df_positions = pd.DataFrame({"start_blink": start_blinks,"end_blink": end_blinks})
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


__all__ = ["kleifges_strategy_a"]
