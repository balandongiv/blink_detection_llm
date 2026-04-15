"""Strategy C per-channel runner in the standardized channel_results format.

Adapts the autoreject-backed Stage 1 scan to produce the
``{channel, df_positions, mapped_candidates, signal_by_epoch}`` dict
required by :func:`~pyblinker.evaluation_runner.score_channel_results`.
"""

from __future__ import annotations

import mne
import pandas as pd

from pyblinker.analysis.lane_evaluation import LaneScoringResult
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.evaluation_runner import score_channel_results
from pyblinker.matching.blink_matching import enrich_absolute_times

from . import AUTOREJECT_BAYESIAN_OPTIMIZATION, epoch_detection_strategy_c_autoreject

_DISABLE_BACKBONE = ("__NO_BACKBONE__",)


def blink_position_strategy_c(
    detector,
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Run Strategy C Stage 1 scan and return standardized channel_results.

    Parameters
    ----------
    detector:
        An initialized ``EpochDetectionStrategyCAutoreject`` whose
        ``prepare_epoch_data()`` has already been called externally.
    prepared:
        Pre-prepared epoch data from ``detector.prepare_epoch_data()``.
    valid_epoch_indices:
        Valid epoch indices to process.

    Returns
    -------
    list[dict]
        Per-detection dicts with keys: ``channel``, ``df_positions``,
        ``mapped_candidates``, ``signal_by_epoch``.
    """
    stage1 = detector.run_stage1_candidate_scan(
        prepared=prepared,
        valid_epoch_indices=valid_epoch_indices,
    )
    ch_to_idx: dict[str, int] = {
        ch: i for i, ch in enumerate(prepared.channel_names)
    }
    results: list[dict] = []
    for detection in stage1.detections:
        channel_name = detection.channel
        ch_idx = ch_to_idx.get(channel_name)
        if ch_idx is not None:
            signal_by_epoch: dict[int, object] = {
                epoch_idx: prepared.data[epoch_idx, ch_idx, :].astype(float)
                for epoch_idx in range(prepared.data.shape[0])
            }
        else:
            signal_by_epoch = {}
        results.append(
            {
                "channel": channel_name,
                "df_positions": detection.positions,
                "mapped_candidates": detection.mapped_candidates,
                "signal_by_epoch": signal_by_epoch,
            }
        )
    return results


def run_strategy_c(
    epochs: mne.Epochs,
    ground_truth_raw: pd.DataFrame,
    *,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    epoch_duration: float = 60.0,
    peak_side_tolerance_s: float = 0.01,
    autoreject_method: str = AUTOREJECT_BAYESIAN_OPTIMIZATION,
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
        stage1_channels=_DISABLE_BACKBONE,
        stage1_threshold_scope="per_channel",
        stage1_rescale_threshold=True,
        autoreject_random_state=autoreject_random_state,
        autoreject_method=autoreject_method,
        autoreject_augment=False,
    )
    prepared = detector.prepare_epoch_data()
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
