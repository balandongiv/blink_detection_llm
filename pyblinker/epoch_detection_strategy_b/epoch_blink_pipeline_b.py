"""Epoch-aware Strategy B pipeline using MNE candidate generation."""

from __future__ import annotations

import mne
import numpy as np
import pandas as pd

from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.logging import get_logger
from pyblinker.utils.annotation_utils import create_annotation
from pyblinker.viz.viz_pd import viz_complete_blink_prop

from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (
    EpochBlinkDetectionOutput,
    PreparedEpochDetectionInput,
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_a.epoch_metadata_export import (
    attach_epoch_blink_metadata,
    normalize_blink_table,
)
from pyblinker.epoch_detection_strategy_a.epoch_result_aggregation import (
    get_selected_channel_result,
    select_candidate_channel_from_results,
)

from .epoch_channel_processor_b import process_concatenated_epoch_channel_mne

logger = get_logger(__name__)


def _empty_annotations() -> mne.Annotations:
    return mne.Annotations(onset=[], duration=[], description=[])


def _finalize_blink_table(
    blink_table: pd.DataFrame,
    *,
    epochs: mne.Epochs,
    prepared: PreparedEpochDetectionInput,
) -> pd.DataFrame:
    normalized = normalize_blink_table(blink_table)
    if normalized.empty:
        return normalized

    normalized = normalized.copy()
    normalized["epoch_selection"] = normalized["epoch_index"].map(
        {idx: int(selection) for idx, selection in enumerate(prepared.selection)}
    )

    if isinstance(epochs.metadata, pd.DataFrame):
        metadata = epochs.metadata.reset_index(drop=True)
        if "epoch_id" in metadata.columns:
            normalized["epoch_id"] = normalized["epoch_index"].map(
                {idx: metadata.loc[idx, "epoch_id"] for idx in range(len(metadata))}
            )
    return normalized


def _channel_task_payload(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    params: dict,
    *,
    mne_half_window_s: float,
    mne_l_freq: float,
    mne_h_freq: float,
    mne_thresh: float | None,
) -> list[dict[str, object]]:
    epoch_boundaries = [
        (
            idx * prepared.epoch_length_samples,
            (idx + 1) * prepared.epoch_length_samples,
        )
        for idx in range(len(valid_epoch_indices))
    ]

    tasks: list[dict[str, object]] = []
    for channel_index, channel_name in enumerate(prepared.channel_names):
        valid_epoch_data = prepared.data[valid_epoch_indices, channel_index, :]
        tasks.append(
            {
                "detector_params": params,
                "concatenated_signal": np.asarray(valid_epoch_data).reshape(-1),
                "channel": channel_name,
                "valid_epoch_indices": list(valid_epoch_indices),
                "epoch_boundaries": epoch_boundaries,
                "sfreq": prepared.sfreq,
                "mne_half_window_s": mne_half_window_s,
                "mne_l_freq": mne_l_freq,
                "mne_h_freq": mne_h_freq,
                "mne_thresh": mne_thresh,
            }
        )
    return tasks


def run_epoch_blink_pipeline_mne(
    *,
    epochs: mne.Epochs,
    prepared: PreparedEpochDetectionInput,
    params: dict,
    valid_epoch_indices: list[int],
    annot_label: str | None = None,
    visualize: bool = False,
    n_jobs: int = 2,
    use_multiprocessing: bool = True,
    mne_half_window_s: float = 0.10,
    mne_l_freq: float = 1.0,
    mne_h_freq: float = 20.0,
    mne_thresh: float | None = None,
) -> EpochBlinkDetectionOutput:
    """Run Strategy B with the Strategy A downstream selection flow."""

    del n_jobs, use_multiprocessing
    epochs_out = epochs.copy()

    if not valid_epoch_indices:
        attach_epoch_blink_metadata(
            epochs_out,
            pd.DataFrame(),
            candidate_channel=None,
            valid_epoch_indices=[],
        )
        return EpochBlinkDetectionOutput(
            annotations=_empty_annotations(),
            channel=None,
            n_good_blinks=0,
            blink_table=pd.DataFrame(),
            fig_data=[],
            selected_channel=pd.DataFrame(),
            epochs=epochs_out,
            valid_epoch_indices=[],
        )

    tasks = _channel_task_payload(
        prepared,
        valid_epoch_indices,
        params,
        mne_half_window_s=mne_half_window_s,
        mne_l_freq=mne_l_freq,
        mne_h_freq=mne_h_freq,
        mne_thresh=mne_thresh,
    )
    results = [process_concatenated_epoch_channel_mne(**task) for task in tasks]

    selected_channel = select_candidate_channel_from_results(results, params)
    selected_result = get_selected_channel_result(results, selected_channel)
    selected_name = None if selected_result is None else selected_result.channel

    blink_table = (
        selected_result.mapped_blinks.copy()
        if selected_result is not None
        else pd.DataFrame()
    )
    blink_table = _finalize_blink_table(
        blink_table,
        epochs=epochs_out,
        prepared=prepared,
    )

    attach_epoch_blink_metadata(
        epochs_out,
        blink_table,
        candidate_channel=selected_name,
        valid_epoch_indices=valid_epoch_indices,
    )

    if selected_result is None:
        return EpochBlinkDetectionOutput(
            annotations=_empty_annotations(),
            channel=None,
            n_good_blinks=0,
            blink_table=blink_table,
            fig_data=[],
            selected_channel=selected_channel,
            epochs=epochs_out,
            valid_epoch_indices=list(valid_epoch_indices),
        )

    annotation_label = annot_label if annot_label else "eye_blink"
    annotations = create_annotation(
        selected_result.final_blinks,
        prepared.sfreq,
        annotation_label,
    )
    fig_data: list[object] = []
    if visualize and not selected_result.final_blinks.empty:
        selected_channel_index = prepared.channel_names.index(selected_name)
        channel_signal = prepared.data[valid_epoch_indices, selected_channel_index, :].reshape(-1)
        fig_data = [
            viz_complete_blink_prop(channel_signal, row, prepared.sfreq)
            for _, row in selected_result.final_blinks.iterrows()
        ]

    n_good_blinks = (
        int(selected_channel.loc[0, "number_good_blinks"])
        if not selected_channel.empty and "number_good_blinks" in selected_channel.columns
        else int(selected_result.stats.get("number_good_blinks", 0))
    )

    return EpochBlinkDetectionOutput(
        annotations=annotations,
        channel=selected_name,
        n_good_blinks=n_good_blinks,
        blink_table=blink_table,
        fig_data=fig_data,
        selected_channel=selected_channel,
        epochs=epochs_out,
        valid_epoch_indices=list(valid_epoch_indices),
    )


class BlinkDetectorEpochStrategyB:
    """Strategy B detector with Strategy A refinement and channel selection."""

    def __init__(
        self,
        epoch: mne.Epochs,
        visualize: bool = False,
        annot_label: str | None = None,
        filter_low: float = 1.0,
        filter_high: float = 20.0,
        resample_rate: float | None = None,
        n_jobs: int = 2,
        use_multiprocessing: bool = True,
        pick_types_options: dict | None = None,
        blink_params: dict | None = None,
        mne_half_window_s: float = 0.10,
        mne_l_freq: float = 1.0,
        mne_h_freq: float = 20.0,
        mne_thresh: float | None = None,
        **blink_param_overrides,
    ) -> None:
        self.epoch = epoch.copy()
        self.viz_data = visualize
        self.annot_label = annot_label
        self.filter_low = float(filter_low)
        self.filter_high = float(filter_high)
        self.resample_rate = resample_rate
        self.n_jobs = max(2, int(n_jobs))
        self.use_multiprocessing = use_multiprocessing
        self.pick_types_options = pick_types_options or {"eeg": True}
        self.params = BlinkDetector._build_detector_params(
            blink_params,
            blink_param_overrides,
        )
        self.mne_half_window_s = float(mne_half_window_s)
        self.mne_l_freq = float(mne_l_freq)
        self.mne_h_freq = float(mne_h_freq)
        self.mne_thresh = mne_thresh
        self._prepared: PreparedEpochDetectionInput | None = None
        self.last_result: EpochBlinkDetectionOutput | None = None

    def prepare_epoch_data(self) -> PreparedEpochDetectionInput:
        """Preprocess epoch data once and cache it for repeated Strategy B runs."""

        if self._prepared is None:
            self._prepared = prepare_epoch_detection_input(
                self.epoch,
                pick_types_options=self.pick_types_options,
                filter_low=self.filter_low,
                filter_high=self.filter_high,
                resample_rate=self.resample_rate,
            )
        self.params["sfreq"] = float(self._prepared.sfreq)
        return self._prepared

    def get_blink(self):
        """Run Strategy B and return the Strategy A-compatible tuple output."""

        logger.info("Starting Strategy B epoch-aware blink detection pipeline.")
        prepared = self.prepare_epoch_data()
        valid_epoch_indices = get_valid_epoch_indices(self.epoch)
        result = run_epoch_blink_pipeline_mne(
            epochs=self.epoch,
            prepared=prepared,
            params=self.params,
            valid_epoch_indices=valid_epoch_indices,
            annot_label=self.annot_label,
            visualize=self.viz_data,
            n_jobs=self.n_jobs,
            use_multiprocessing=self.use_multiprocessing,
            mne_half_window_s=self.mne_half_window_s,
            mne_l_freq=self.mne_l_freq,
            mne_h_freq=self.mne_h_freq,
            mne_thresh=self.mne_thresh,
        )
        self.epoch = result.epochs
        self.last_result = result
        return (
            result.annotations,
            result.channel,
            result.n_good_blinks,
            result.blink_table,
            result.fig_data,
            result.selected_channel,
            result.epochs,
        )


__all__ = [
    "BlinkDetectorEpochStrategyB",
    "PreparedEpochDetectionInput",
    "prepare_epoch_detection_input",
    "run_epoch_blink_pipeline_mne",
]
