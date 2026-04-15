"""Epoch-aware blink detection that reuses the legacy six-step logic."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

import mne
import numpy as np
import pandas as pd

from pyblinker.blinker.legacy_eeglab_filter import legacy_blinker_bandpass
from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.logging import get_logger
from pyblinker.utils.annotation_utils import create_annotation
from pyblinker.viz.viz_pd import viz_complete_blink_prop

from .bad_epoch_utils import get_valid_epoch_indices
from .epoch_channel_processor import process_concatenated_epoch_channel
from .epoch_metadata_export import attach_epoch_blink_metadata, normalize_blink_table
from .epoch_result_aggregation import (
    get_selected_channel_result,
    select_candidate_channel_from_results,
)

logger = get_logger(__name__)


@dataclass
class PreparedEpochDetectionInput:
    """Cached, preprocessed epoch data ready for per-channel concatenation."""

    data: np.ndarray
    channel_names: tuple[str, ...]
    sfreq: float
    epoch_length_samples: int
    selection: np.ndarray


@dataclass
class EpochBlinkDetectionOutput:
    """Structured output from the epoch-mode detector."""

    annotations: mne.Annotations
    channel: str | None
    n_good_blinks: int
    blink_table: pd.DataFrame
    fig_data: list[object]
    selected_channel: pd.DataFrame
    epochs: mne.Epochs
    valid_epoch_indices: list[int]


def _resample_epoch_array(
    data: np.ndarray,
    *,
    orig_sfreq: float,
    target_sfreq: float,
) -> np.ndarray:
    if np.isclose(orig_sfreq, target_sfreq):
        return data
    ratio = (
        Fraction(str(target_sfreq)).limit_denominator(1000)
        / Fraction(str(orig_sfreq)).limit_denominator(1000)
    ).limit_denominator(1000)
    return mne.filter.resample(
        data,
        up=ratio.numerator,
        down=ratio.denominator,
        axis=-1,
        verbose="ERROR",
    )


def prepare_epoch_detection_input(
    epochs: mne.Epochs,
    *,
    pick_types_options: dict | None = None,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
) -> PreparedEpochDetectionInput:
    """Load, pick, filter, and optionally resample epoch data once."""

    epochs.load_data()
    print("Total epochs:", len(epochs))
    pick_options = pick_types_options or {"eeg": True}
    picks = mne.pick_types(epochs.info, **pick_options)
    if picks.size == 0:
        raise ValueError("No channels matched the requested pick_types_options.")

    channel_names = tuple(epochs.ch_names[pick] for pick in picks)
    raw_data = epochs.get_data(picks=picks)
    orig_sfreq = float(epochs.info["sfreq"])
    target_sfreq = orig_sfreq if resample_rate in (None, 0) else float(resample_rate)

    processed_epochs: list[np.ndarray] = []
    for epoch_data in raw_data:
        filtered = legacy_blinker_bandpass(
            epoch_data,
            sfreq=orig_sfreq,
            low_cutoff_hz=float(filter_low),
            high_cutoff_hz=float(filter_high),
        )
        processed = _resample_epoch_array(
            filtered,
            orig_sfreq=orig_sfreq,
            target_sfreq=target_sfreq,
        )
        processed_epochs.append(np.asarray(processed, dtype=np.float64))

    prepared = np.stack(processed_epochs, axis=0) if processed_epochs else raw_data[:, :, :0]
    gg=PreparedEpochDetectionInput(
        data=prepared,
        channel_names=channel_names,
        sfreq=float(target_sfreq),
        epoch_length_samples=int(prepared.shape[-1]),
        selection=np.asarray(epochs.selection, dtype=int).copy(),
        )
    return gg


def _channel_task_payload(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    params: dict,
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
            }
        )
    return tasks


def _run_channel_task(task: dict[str, object]):
    return process_concatenated_epoch_channel(**task)


def _empty_annotations() -> mne.Annotations:
    return mne.Annotations(onset=[], duration=[], description=[])


def _execute_channel_tasks(
    tasks: list[dict[str, object]],
    *,
    max_workers: int,
    use_multiprocessing: bool,
):
    del max_workers, use_multiprocessing

    results = []
    for task in tasks:
        results.append(_run_channel_task(task))
    return results


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


def run_epoch_blink_pipeline(
    *,
    epochs: mne.Epochs,
    prepared: PreparedEpochDetectionInput,
    params: dict,
    valid_epoch_indices: list[int],
    annot_label: str | None = None,
    visualize: bool = False,
    n_jobs: int = 2,
    use_multiprocessing: bool = True,
) -> EpochBlinkDetectionOutput:
    """Run the epoch-aware detector from prepared inputs and valid indices."""

    epochs_out = epochs.copy()
    effective_jobs = 1 # max(2, int(n_jobs))

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

    tasks = _channel_task_payload(prepared, valid_epoch_indices, params)
    results = _execute_channel_tasks(
        tasks,
        max_workers=effective_jobs,
        use_multiprocessing=use_multiprocessing,
    )

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


class BlinkDetectorEpoch:
    """Epoch-aware detector that excludes bad epochs before blink computation."""

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
        self._prepared: PreparedEpochDetectionInput | None = None
        self.last_result: EpochBlinkDetectionOutput | None = None

    def prepare_epoch_data(self) -> PreparedEpochDetectionInput:
        """Preprocess epoch data once and cache it for repeated runs."""

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
        """Run the epoch-aware pipeline and return metadata plus long-form output."""

        logger.info("Starting epoch-aware blink detection pipeline.")
        prepared = self.prepare_epoch_data()
        valid_epoch_indices = get_valid_epoch_indices(self.epoch)
        result = run_epoch_blink_pipeline(
            epochs=self.epoch,
            prepared=prepared,
            params=self.params,
            valid_epoch_indices=valid_epoch_indices,
            annot_label=self.annot_label,
            visualize=self.viz_data,
            n_jobs=self.n_jobs,
            use_multiprocessing=self.use_multiprocessing,
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
    "BlinkDetectorEpoch",
    "EpochBlinkDetectionOutput",
    "PreparedEpochDetectionInput",
    "prepare_epoch_detection_input",
    "run_epoch_blink_pipeline",
]
