"""Strategy C single-channel blink detection with autoreject thresholds."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import mne
import numpy as np
import pandas as pd

from pyblinker.blinker.get_blink_positions import get_blink_position_with_threshold
from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_channel import map_concatenated_blinks_to_epochs
from pyblinker.common.epoch_input import (
    PreparedEpochDetectionInput,
    prepare_epoch_detection_input,
)
from pyblinker.common.epoch_io import attach_epoch_blink_metadata
from pyblinker.common.pipeline_utils import (
    build_epoch_boundaries,
    build_signal_by_epoch,
    empty_annotations,
    finalize_blink_table,
)
from pyblinker.utils.annotation_utils import create_annotation


def _ensure_autoreject_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    candidates = (
        repo_root / "autoreject",
        repo_root.parent / "find_blink_epoch_worktree" / "autoreject",
    )
    for candidate in candidates:
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


_ensure_autoreject_path()

from autoreject import compute_thresholds, get_rejection_threshold  # noqa: E402


def _build_stage1_epochs(
    stage1_data: np.ndarray,
    *,
    channel_names: tuple[str, ...],
    sfreq: float,
) -> mne.Epochs:
    info = mne.create_info(
        list(channel_names),
        sfreq=float(sfreq),
        ch_types=["eeg"] * len(channel_names),
    )
    return mne.EpochsArray(stage1_data, info, verbose="ERROR")

def _learn_global_threshold(
    stage1_data: np.ndarray,
    *,
    channel_names: tuple[str, ...],
    sfreq: float,
    random_state: int,
) -> float:
    epochs = _build_stage1_epochs(
        stage1_data,
        channel_names=channel_names,
        sfreq=sfreq,
    )
    reject = get_rejection_threshold(
        epochs,
        random_state=int(random_state),
        ch_types="eeg",
        cv=min(5, int(stage1_data.shape[0])),
        verbose=False,
    )
    return float(reject["eeg"])


def _learn_thresholds(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    channel_names: tuple[str, ...],
    stage1_threshold_scope: str,
    autoreject_method: str,
    autoreject_random_state: int,
    autoreject_augment: bool,
) -> tuple[dict[str, float], float | None, str]:
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)
    if len(valid_indices) == 0:
        return {channel: 0.0 for channel in channel_names}, None, "none"

    channel_indices = [prepared.channel_names.index(channel) for channel in channel_names]
    data = prepared.data[valid_indices][:, channel_indices, :]

    if stage1_threshold_scope == "global":
        global_threshold = _learn_global_threshold(
            data,
            channel_names=channel_names,
            sfreq=prepared.sfreq,
            random_state=autoreject_random_state,
        )
        thresholds = {channel: global_threshold for channel in channel_names}
        return thresholds, global_threshold, "get_rejection_threshold"

    epochs = _build_stage1_epochs(
        data,
        channel_names=channel_names,
        sfreq=prepared.sfreq,
    )
    thresholds = compute_thresholds(
        epochs,
        method=autoreject_method,
        random_state=int(autoreject_random_state),
        augment=bool(autoreject_augment),
        verbose=False,
        n_jobs=1,
    )
    return (
        {channel: float(thresholds[channel]) for channel in channel_names},
        None,
        "compute_thresholds",
    )

def channel_results_strategy_c(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    stage1_threshold_scope: str,
    autoreject_method: str,
    blink_params: dict | None = None,
    stage1_channels: tuple[str, ...] | list[str] | None = None,
    stage1_rescale_threshold: bool = True,
    no_backbone_sentinel: tuple[str, ...] = ("__NO_BACKBONE__",),
    stage1_threshold_scales: dict[str, float] | None = None,
    autoreject_random_state: int = 42,
    autoreject_augment: bool = False,
    **blink_param_overrides,
) -> list[dict]:
    params = BlinkDetector._build_detector_params(blink_params, dict(blink_param_overrides))
    params["sfreq"] = float(prepared.sfreq)

    selected_channels = (
        tuple(stage1_channels) if stage1_channels is not None else no_backbone_sentinel
    )
    if selected_channels == no_backbone_sentinel:
        channel_names = tuple(prepared.channel_names)
    else:
        channel_names = tuple(
            channel for channel in selected_channels if channel in prepared.channel_names
        )
        if not channel_names:
            if prepared.channel_names:
                channel_names = tuple(prepared.channel_names)
            else:
                raise ValueError("Strategy C needs at least one EEG channel after preprocessing.")
    thresholds, _global_threshold, _api = _learn_thresholds(
        prepared,
        valid_epoch_indices,
        channel_names=channel_names,
        stage1_threshold_scope=stage1_threshold_scope,
        autoreject_method=autoreject_method,
        autoreject_random_state=autoreject_random_state,
        autoreject_augment=autoreject_augment,
    )

    threshold_scales = (
            {key: float(value) for key, value in stage1_threshold_scales.items()})


    if stage1_threshold_scope == "global":
        scan_scale = float(threshold_scales["global"])
    elif autoreject_method == "bayesian_optimization":
        scan_scale = float(threshold_scales["bayesian_optimization"])
    else:
        scan_scale = float(threshold_scales["random_search"])
    epoch_boundaries = build_epoch_boundaries(
        len(valid_epoch_indices),
        prepared.epoch_length_samples,
    )
    min_blink_frames = float(params["min_event_len"] * params["sfreq"])
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)

    results: list[dict] = []
    for channel in channel_names:
        channel_index = prepared.channel_names.index(channel)
        concatenated_signal = prepared.data[valid_indices, channel_index, :].reshape(-1)
        raw_threshold = float(thresholds[channel])
        scan_threshold = raw_threshold * float(scan_scale)
        df_positions = get_blink_position_with_threshold(
            params,
            blink_component=concatenated_signal,
            threshold=scan_threshold,
            ch=channel,
            progress_bar=False,
            min_blink_frames=min_blink_frames,
        )
        mapped_candidates = map_concatenated_blinks_to_epochs(
            df_positions,
            channel=channel,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )
        mapped_candidates["candidate_source"] = "channel_threshold"
        mapped_candidates["raw_threshold"] = raw_threshold
        mapped_candidates["scan_threshold"] = scan_threshold
        results.append(
            {
                "channel": channel,
                "df_positions": df_positions,
                "mapped_candidates": mapped_candidates,
                "signal_by_epoch": build_signal_by_epoch(prepared, channel_index),
                "raw_threshold": raw_threshold,
                "scan_threshold": scan_threshold,
                "candidate_source": "channel_threshold",
            }
        )
    return results


def run_stage1_candidate_scan(
    detector,
    *,
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
):
    if detector.stage1_channels == detector.no_backbone_sentinel:
        channel_names = tuple(prepared.channel_names)
    else:
        channel_names = tuple(
            channel for channel in detector.stage1_channels if channel in prepared.channel_names
        )
        if not channel_names:
            if prepared.channel_names:
                channel_names = tuple(prepared.channel_names)
            else:
                raise ValueError("Strategy C needs at least one EEG channel after preprocessing.")
    thresholds, global_threshold, threshold_learning_api = _learn_thresholds(
        prepared,
        valid_epoch_indices,
        channel_names=channel_names,
        stage1_threshold_scope=detector.stage1_threshold_scope,
        autoreject_method=detector.autoreject_method,
        autoreject_random_state=detector.autoreject_random_state,
        autoreject_augment=detector.autoreject_augment,
    )
    if not detector.stage1_rescale_threshold:
        scan_scale = 1.0
    else:
        threshold_scales = {
            key: float(value) for key, value in detector.stage1_threshold_scales.items()
        }
        if detector.stage1_threshold_scope == "global":
            scan_scale = float(threshold_scales["global"])
        elif detector.autoreject_method == "bayesian_optimization":
            scan_scale = float(threshold_scales["bayesian_optimization"])
        else:
            scan_scale = float(threshold_scales["random_search"])
    epoch_boundaries = build_epoch_boundaries(
        len(valid_epoch_indices),
        prepared.epoch_length_samples,
    )
    min_blink_frames = float(detector.params["min_event_len"] * float(prepared.sfreq))
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)

    detections: list[SimpleNamespace] = []
    for channel in channel_names:
        channel_index = prepared.channel_names.index(channel)
        signal = prepared.data[valid_indices, channel_index, :].reshape(-1).astype(float)
        raw_threshold = float(thresholds[channel])
        scan_threshold = raw_threshold * float(scan_scale)
        positions = get_blink_position_with_threshold(
            detector.params,
            blink_component=signal,
            threshold=scan_threshold,
            ch=channel,
            progress_bar=False,
            min_blink_frames=min_blink_frames,
        )
        mapped = map_concatenated_blinks_to_epochs(
            positions,
            channel=channel,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )
        mapped["candidate_source"] = "channel_threshold"
        mapped["raw_threshold"] = raw_threshold
        mapped["scan_threshold"] = scan_threshold
        detections.append(
            SimpleNamespace(
                channel=channel,
                signal=signal,
                threshold=scan_threshold,
                candidate_source="channel_threshold",
                positions=positions,
                mapped_candidates=mapped,
                raw_threshold=raw_threshold,
            )
        )

    summary_rows: list[dict[str, object]] = []
    for detection in detections:
        summary_rows.append(
            {
                "ch": detection.channel,
                "channel": detection.channel,
                "candidate_source": detection.candidate_source,
                "raw_threshold": float(detection.raw_threshold),
                "scan_threshold": float(detection.threshold),
                "raw_candidate_count": int(len(detection.positions)),
                "mapped_candidate_count": int(len(detection.mapped_candidates)),
                "number_good_blinks": int(len(detection.mapped_candidates)),
            }
        )
    if summary_rows:
        summary = (
            pd.DataFrame(summary_rows)
            .sort_values(
                ["mapped_candidate_count", "raw_candidate_count", "channel"],
                ascending=[False, False, True],
            )
            .reset_index(drop=True)
        )
    else:
        summary = pd.DataFrame()
    candidate_frames = [
        detection.mapped_candidates
        for detection in detections
        if not detection.mapped_candidates.empty
    ]

    detector.stage1_threshold_scope_ = detector.stage1_threshold_scope
    detector.stage1_autoreject_method_ = detector.autoreject_method
    detector.stage1_threshold_learning_api_ = threshold_learning_api
    detector.stage1_channel_names_ = channel_names
    detector.stage1_backbone_channels_ = ()
    detector.stage1_global_threshold_ = global_threshold
    detector.stage1_thresholds_ = thresholds
    detector.stage1_backbone_signal_ = None
    detector.stage1_candidates_ = (
        pd.concat(candidate_frames, ignore_index=True, sort=False)
        if candidate_frames
        else pd.DataFrame(
            columns=[
                "epoch_index",
                "channel",
                "blink_onset",
                "blink_duration",
                "start_blink",
                "end_blink",
                "candidate_source",
                "raw_threshold",
                "scan_threshold",
            ]
        )
    )
    detector.stage1_rescue_candidates_ = pd.DataFrame()
    detector.stage1_channel_summary_ = summary
    detector.stage1_representative_channels_ = summary.head(3).copy()

    return SimpleNamespace(
        epoch_boundaries=epoch_boundaries,
        backbone_signal=None,
        thresholds=thresholds,
        channel_names=channel_names,
        global_threshold=global_threshold,
        threshold_learning_api=threshold_learning_api,
        candidate_lanes=detections,
        detections=detections,
    )


def get_blink(detector):
    if detector._prepared is None:
        detector._prepared = prepare_epoch_detection_input(
            detector.epoch,
            pick_types_options=detector.pick_types_options,
            filter_low=detector.filter_low,
            filter_high=detector.filter_high,
            resample_rate=detector.resample_rate,
        )
    prepared = detector._prepared
    detector.params["sfreq"] = float(prepared.sfreq)

    valid_epoch_indices = get_valid_epoch_indices(detector.epoch)
    stage1 = run_stage1_candidate_scan(
        detector,
        prepared=prepared,
        valid_epoch_indices=valid_epoch_indices,
    )
    summary = detector.stage1_channel_summary_.copy()

    if summary.empty:
        annotations = empty_annotations()
        blink_table = finalize_blink_table(
            pd.DataFrame(),
            epochs=detector.epoch,
            prepared=prepared,
        )
        selected_channel = pd.DataFrame(
            columns=[
                "ch",
                "channel",
                "candidate_source",
                "raw_threshold",
                "scan_threshold",
                "raw_candidate_count",
                "mapped_candidate_count",
                "number_good_blinks",
            ]
        )
        result = SimpleNamespace(
            annotations=annotations,
            channel="",
            n_good_blinks=0,
            blink_table=blink_table,
            fig_data=[],
            selected_channel=selected_channel,
            epochs=detector.epoch,
            valid_epoch_indices=valid_epoch_indices,
        )
        detector.last_result = result
        return annotations, "", 0, blink_table, [], selected_channel, detector.epoch

    selected_row = summary.iloc[[0]].copy()
    selected_channel_name = str(selected_row.iloc[0]["channel"])
    selected_detection = next(
        detection for detection in stage1.detections if detection.channel == selected_channel_name
    )

    if selected_detection.positions.empty:
        annotations = empty_annotations()
    else:
        annotations = create_annotation(
            selected_detection.positions,
            float(prepared.sfreq),
            detector.annot_label,
        )

    blink_table = finalize_blink_table(
        selected_detection.mapped_candidates,
        epochs=detector.epoch,
        prepared=prepared,
    )
    attach_epoch_blink_metadata(
        detector.epoch,
        blink_table,
        selected_channel_name,
        valid_epoch_indices,
    )

    selected_channel = selected_row.copy()
    selected_channel["strategy_c_candidate_source"] = selected_channel["candidate_source"]
    selected_channel["strategy_c_detection_threshold"] = selected_channel["scan_threshold"]
    selected_channel["strategy_c_raw_threshold"] = selected_channel["raw_threshold"]
    selected_channel["strategy_c_stage1_threshold_scope"] = detector.stage1_threshold_scope_
    selected_channel["strategy_c_stage1_threshold_learning_api"] = (
        detector.stage1_threshold_learning_api_
    )
    selected_channel["strategy_c_autoreject_method"] = detector.stage1_autoreject_method_
    selected_channel["strategy_c_stage1_candidate_count"] = selected_channel[
        "raw_candidate_count"
    ]

    result = SimpleNamespace(
        annotations=annotations,
        channel=selected_channel_name,
        n_good_blinks=int(len(blink_table)),
        blink_table=blink_table,
        fig_data=[],
        selected_channel=selected_channel,
        epochs=detector.epoch,
        valid_epoch_indices=valid_epoch_indices,
    )
    detector.last_result = result
    return (
        annotations,
        selected_channel_name,
        int(len(blink_table)),
        blink_table,
        [],
        selected_channel,
        detector.epoch,
    )


def epoch_detection_strategy_c_autoreject(
    epoch: mne.Epochs,
    visualize: bool = False,
    annot_label: str | None = None,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    n_jobs: int = 1,
    use_multiprocessing: bool = False,
    pick_types_options: dict | None = None,
    blink_params: dict | None = None,
    *,
    stage1_threshold_scope: str,
    autoreject_method: str,
    stage1_channels: tuple[str, ...] | list[str] | None = None,
    stage1_rescale_threshold: bool = True,
    no_backbone_sentinel: tuple[str, ...] = ("__NO_BACKBONE__",),
    stage1_threshold_scales: dict[str, float] | None = None,
    autoreject_random_state: int = 42,
    autoreject_augment: bool = False,
    **blink_param_overrides,
):
    clean_overrides = dict(blink_param_overrides)
    for ignored_key in _IGNORED_TEMPLATE_ARGS:
        clean_overrides.pop(ignored_key, None)

    detector = SimpleNamespace(
        epoch=epoch.copy(),
        viz_data=bool(visualize),
        annot_label=annot_label or "blink",
        filter_low=float(filter_low),
        filter_high=float(filter_high),
        resample_rate=resample_rate,
        n_jobs=int(n_jobs),
        use_multiprocessing=bool(use_multiprocessing),
        pick_types_options=pick_types_options or {"eeg": True},
        stage1_channels=tuple(stage1_channels) if stage1_channels is not None else no_backbone_sentinel,
        stage1_threshold_scope=stage1_threshold_scope,
        stage1_rescale_threshold=bool(stage1_rescale_threshold),
        no_backbone_sentinel=tuple(no_backbone_sentinel),
        stage1_threshold_scales=(
            {key: float(value) for key, value in stage1_threshold_scales.items()}
            if stage1_threshold_scales is not None
            else {
                "random_search": 0.08,
                "bayesian_optimization": 0.12,
                "global": 0.005,
            }
        ),
        autoreject_random_state=int(autoreject_random_state),
        autoreject_method=autoreject_method,
        autoreject_augment=bool(autoreject_augment),
        params=BlinkDetector._build_detector_params(blink_params, clean_overrides),
        _prepared=None,
        last_result=None,
        stage1_threshold_scope_="",
        stage1_autoreject_method_="",
        stage1_threshold_learning_api_="",
        stage1_channel_names_=(),
        stage1_backbone_channels_=(),
        stage1_global_threshold_=None,
        stage1_thresholds_={},
        stage1_backbone_signal_=None,
        stage1_candidates_=pd.DataFrame(
            columns=[
                "epoch_index",
                "channel",
                "blink_onset",
                "blink_duration",
                "start_blink",
                "end_blink",
                "candidate_source",
                "raw_threshold",
                "scan_threshold",
            ]
        ),
        stage1_rescue_candidates_=pd.DataFrame(),
        stage1_channel_summary_=pd.DataFrame(),
        stage1_representative_channels_=pd.DataFrame(),
    )
    detector.run_stage1_candidate_scan = (
        lambda *, prepared, valid_epoch_indices: run_stage1_candidate_scan(
            detector,
            prepared=prepared,
            valid_epoch_indices=valid_epoch_indices,
        )
    )
    detector.get_blink = lambda: get_blink(detector)
    return detector


EpochDetectionStrategyCAutoreject = epoch_detection_strategy_c_autoreject
Stage1CandidateLane = SimpleNamespace
Stage1CandidateDetection = SimpleNamespace
Stage1CandidateEvaluation = SimpleNamespace
Stage1ScanResult = SimpleNamespace
StrategyCAutorejectResult = SimpleNamespace


__all__ = [
    "EpochDetectionStrategyCAutoreject",
    "Stage1CandidateDetection",
    "Stage1CandidateEvaluation",
    "Stage1CandidateLane",
    "Stage1ScanResult",
    "StrategyCAutorejectResult",
    "channel_results_strategy_c",
    "epoch_detection_strategy_c_autoreject",
    "run_stage1_candidate_scan",
]
