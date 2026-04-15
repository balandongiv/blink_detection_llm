"""Strategy C evaluation runner."""

from __future__ import annotations

import mne
import pandas as pd

from pyblinker.analysis.lane_evaluation import LaneScoringResult
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import (
    PreparedEpochDetectionInput,
    prepare_epoch_detection_input,
)
from pyblinker.evaluation_runner import score_channel_results
from pyblinker.matching.blink_matching import enrich_absolute_times

from .single_channel_autoreject import (
    channel_results_strategy_c,
    epoch_detection_strategy_c_autoreject,
)


def blink_position_strategy_c(
    detector_or_prepared,
    prepared_or_valid_epoch_indices,
    valid_epoch_indices: list[int] | None = None,
    **kwargs,
) -> list[dict]:
    """Return Strategy C per-channel results in the standard format.

    Supports both:
    - ``blink_position_strategy_c(prepared, valid_epoch_indices, ...)``
    - ``blink_position_strategy_c(detector, prepared, valid_epoch_indices)``
    """

    if hasattr(detector_or_prepared, "run_stage1_candidate_scan"):
        detector = detector_or_prepared
        prepared = prepared_or_valid_epoch_indices
        if valid_epoch_indices is None:
            raise ValueError("valid_epoch_indices is required when passing a detector.")
        stage1 = detector.run_stage1_candidate_scan(
            prepared=prepared,
            valid_epoch_indices=valid_epoch_indices,
        )
        return [
            {
                "channel": detection.channel,
                "df_positions": detection.positions,
                "mapped_candidates": detection.mapped_candidates,
                "signal_by_epoch": {
                    epoch_idx: prepared.data[
                        epoch_idx,
                        prepared.channel_names.index(detection.channel),
                        :,
                    ].astype(float)
                    for epoch_idx in range(prepared.data.shape[0])
                },
                "raw_threshold": detection.raw_threshold,
                "scan_threshold": detection.threshold,
                "candidate_source": detection.candidate_source,
            }
            for detection in stage1.detections
        ]

    prepared = detector_or_prepared
    valid_epoch_indices = prepared_or_valid_epoch_indices
    if not isinstance(prepared, PreparedEpochDetectionInput):
        raise TypeError("Expected a PreparedEpochDetectionInput or a Strategy C detector.")
    return channel_results_strategy_c(prepared, valid_epoch_indices, **kwargs)


def run_strategy_c(
    epochs: mne.Epochs,
    ground_truth_raw: pd.DataFrame,
    *,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    epoch_duration: float = 60.0,
    peak_side_tolerance_s: float = 0.01,
    autoreject_method: str | None = None,
    autoreject_random_state: int = 42,
) -> LaneScoringResult:
    """Run Strategy C end-to-end on ``epochs`` and return scored results."""

    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=None,
        n_jobs=1,
        use_multiprocessing=False,
        stage1_channels=("__NO_BACKBONE__",),
        stage1_threshold_scope="per_channel",
        stage1_rescale_threshold=True,
        autoreject_random_state=autoreject_random_state,
        autoreject_method=autoreject_method,
    )
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=None,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = blink_position_strategy_c(detector, prepared, valid_epoch_indices)
    ground_truth = enrich_absolute_times(ground_truth_raw, epoch_duration)
    return score_channel_results(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


__all__ = ["blink_position_strategy_c", "run_strategy_c"]
