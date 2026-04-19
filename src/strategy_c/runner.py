"""Strategy C runner: threshold-driven per-channel blink region scanning."""

from __future__ import annotations

from types import SimpleNamespace

import mne
import numpy as np
import pandas as pd

from src.analysis.lane_evaluation import LaneScoringResult
from src.blinker.get_blink_positions import scan_threshold_crossings_kleifges
from src.blinker.pyblinker import BlinkDetector
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import (
    PreparedEpochDetectionInput,
    prepare_epoch_detection_input,
)
from src.common.epoch_io import attach_epoch_blink_metadata
from src.common.pipeline_utils import (
    build_epoch_boundaries,
    build_signal_by_epoch,
    empty_annotations,
    finalize_blink_table,
)
from src.config.strategy_c_defaults import (
    validate_strategy_c_options,
)
from src.evaluation_runner import score_channel_results
from src.matching.blink_matching import enrich_absolute_times
from src.utils.annotation_utils import create_annotation

from .single_channel_autoreject import learn_strategy_c_thresholds


def scan_strategy_c_channels(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    blink_params: dict | None = None,
    threshold_scope: str,
    autoreject_method: str,
    scan_scale: float = 1.0,
    autoreject_random_state: int = 42,
    autoreject_augment: bool = False,
    **blink_param_overrides,
) -> tuple[list[dict], SimpleNamespace]:
    params = BlinkDetector._build_detector_params(blink_params, dict(blink_param_overrides))
    params["sfreq"] = float(prepared.sfreq)

    threshold_result = learn_strategy_c_thresholds(
        prepared,
        valid_epoch_indices,
        stage1_threshold_scope=threshold_scope,
        autoreject_method=autoreject_method,
        stage1_scan_scale=scan_scale,
        autoreject_random_state=autoreject_random_state,
        autoreject_augment=autoreject_augment,
    )

    epoch_boundaries = build_epoch_boundaries(
        len(valid_epoch_indices),
        prepared.epoch_length_samples,
    )
    min_blink_frames = float(params["min_event_len"] * params["sfreq"])
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)
    results: list[dict] = []
    for channel in threshold_result.channel_names:
        channel_index = prepared.channel_names.index(channel)
        concatenated_signal = prepared.data[valid_indices, channel_index, :].reshape(-1)
        raw_threshold = float(threshold_result.raw_thresholds[channel])
        scan_threshold = float(threshold_result.scan_thresholds[channel])
        start_blinks, end_blinks = scan_threshold_crossings_kleifges(
            concatenated_signal,
            float(scan_threshold),
            min_blink_frames,
            progress_bar=False,
            channel_name=channel,
        )

        df_positions = pd.DataFrame({"start_blink": start_blinks, "end_blink": end_blinks})
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
    return results, threshold_result


def channel_results_strategy_c(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    blink_params: dict | None = None,
    threshold_scope: str,
    autoreject_method: str,
    scan_scale: float = 1.0,
    autoreject_random_state: int = 42,
    autoreject_augment: bool = False,
    **blink_param_overrides,
) -> list[dict]:
    results, _threshold_result = scan_strategy_c_channels(
        prepared,
        valid_epoch_indices,
        blink_params=blink_params,
        threshold_scope=threshold_scope,
        autoreject_method=autoreject_method,
        scan_scale=scan_scale,
        autoreject_random_state=autoreject_random_state,
        autoreject_augment=autoreject_augment,
        **blink_param_overrides,
    )
    return results


def blink_position_strategy_c(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    setting: dict | None = None,
    **kwargs,
) -> list[dict]:
    """Return Strategy C per-channel blink results in the standard format."""
    options = dict(setting or {})
    options.update(kwargs)
    return channel_results_strategy_c(prepared, valid_epoch_indices, **options)


def _build_stage1_summary(channel_results: list[dict]) -> pd.DataFrame:
    summary_rows: list[dict[str, object]] = []
    for result in channel_results:
        summary_rows.append(
            {
                "ch": result["channel"],
                "channel": result["channel"],
                "candidate_source": result["candidate_source"],
                "raw_threshold": float(result["raw_threshold"]),
                "scan_threshold": float(result["scan_threshold"]),
                "raw_candidate_count": int(len(result["df_positions"])),
                "mapped_candidate_count": int(len(result["mapped_candidates"])),
                "number_good_blinks": int(len(result["mapped_candidates"])),
            }
        )
    if not summary_rows:
        return pd.DataFrame(columns=[
            "ch", "channel", "candidate_source", "raw_threshold", "scan_threshold",
            "raw_candidate_count", "mapped_candidate_count", "number_good_blinks",
        ])
    return (
        pd.DataFrame(summary_rows)
        .sort_values(
            ["mapped_candidate_count", "raw_candidate_count", "channel"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )


def run_stage1_candidate_scan(
    detector,
    *,
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
):
    channel_results, threshold_result = scan_strategy_c_channels(
        prepared,
        valid_epoch_indices,
        blink_params=detector.params,
        threshold_scope=detector.stage1_threshold_scope,
        autoreject_method=detector.autoreject_method,
        scan_scale=detector.stage1_scan_scale,
        autoreject_random_state=detector.autoreject_random_state,
        autoreject_augment=detector.autoreject_augment,
    )

    detections: list[SimpleNamespace] = []
    for result in channel_results:
        detections.append(
            SimpleNamespace(
                channel=result["channel"],
                signal=np.concatenate(
                    [
                        result["signal_by_epoch"][epoch_index]
                        for epoch_index in valid_epoch_indices
                    ]
                ).astype(float)
                if valid_epoch_indices
                else np.array([], dtype=float),
                threshold=float(result["scan_threshold"]),
                candidate_source=result["candidate_source"],
                positions=result["df_positions"],
                mapped_candidates=result["mapped_candidates"],
                raw_threshold=float(result["raw_threshold"]),
            )
        )

    summary = _build_stage1_summary(channel_results)
    candidate_frames = [
        detection.mapped_candidates
        for detection in detections
        if not detection.mapped_candidates.empty
    ]

    detector.stage1_threshold_scope_ = threshold_result.stage1_threshold_scope
    detector.stage1_autoreject_method_ = threshold_result.autoreject_method
    detector.stage1_threshold_learning_api_ = threshold_result.threshold_learning_api
    detector.stage1_channel_names_ = threshold_result.channel_names
    detector.stage1_backbone_channels_ = ()
    detector.stage1_global_threshold_ = threshold_result.global_threshold
    detector.stage1_thresholds_ = dict(threshold_result.raw_thresholds)
    detector.stage1_scan_thresholds_ = dict(threshold_result.scan_thresholds)
    detector.stage1_backbone_signal_ = None
    detector.stage1_candidates_ = (
        pd.concat(candidate_frames, ignore_index=True, sort=False)
        if candidate_frames
        else pd.DataFrame(columns=[
            "epoch_index", "channel", "blink_onset", "blink_duration",
            "start_blink", "end_blink", "candidate_source",
            "raw_threshold", "scan_threshold",
        ])
    )
    detector.stage1_rescue_candidates_ = pd.DataFrame()
    detector.stage1_channel_summary_ = summary
    detector.stage1_representative_channels_ = summary.head(3).copy()

    return SimpleNamespace(
        thresholds=dict(threshold_result.raw_thresholds),
        scan_thresholds=dict(threshold_result.scan_thresholds),
        channel_names=threshold_result.channel_names,
        global_threshold=threshold_result.global_threshold,
        threshold_learning_api=threshold_result.threshold_learning_api,
        candidate_lanes=detections,
        detections=detections,
        channel_results=channel_results,
    )


def _empty_selected_channel_summary() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "ch", "channel", "candidate_source", "raw_threshold", "scan_threshold",
        "raw_candidate_count", "mapped_candidate_count", "number_good_blinks",
    ])


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
        selected_channel = _empty_selected_channel_summary()
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
    stage1_scan_scale: float = 1.0,
    autoreject_random_state: int = 42,
    autoreject_augment: bool = False,
    **blink_param_overrides,
):
    clean_overrides = dict(blink_param_overrides)
    for ignored_key in {"threshold_scope", "autoreject_method"}:
        clean_overrides.pop(ignored_key, None)

    method, scope = validate_strategy_c_options(
        autoreject_method=autoreject_method,
        stage1_threshold_scope=stage1_threshold_scope,
    )

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
        stage1_threshold_scope=scope,
        stage1_scan_scale=float(stage1_scan_scale),
        autoreject_random_state=int(autoreject_random_state),
        autoreject_method=method,
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
        stage1_scan_thresholds_={},
        stage1_backbone_signal_=None,
        stage1_candidates_=pd.DataFrame(columns=[
            "epoch_index", "channel", "blink_onset", "blink_duration",
            "start_blink", "end_blink", "candidate_source",
            "raw_threshold", "scan_threshold",
        ]),
        stage1_rescue_candidates_=pd.DataFrame(),
        stage1_channel_summary_=pd.DataFrame(),
        stage1_representative_channels_=pd.DataFrame(),
    )
    detector.params["sfreq"] = float(epoch.info["sfreq"])
    detector._get_stage1_scan_threshold_scale = lambda: detector.stage1_scan_scale
    detector.run_stage1_candidate_scan = (
        lambda *, prepared, valid_epoch_indices: run_stage1_candidate_scan(
            detector,
            prepared=prepared,
            valid_epoch_indices=valid_epoch_indices,
        )
    )
    detector.get_blink = lambda: get_blink(detector)
    return detector


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

    method, scope = validate_strategy_c_options(
        autoreject_method=autoreject_method,
        stage1_threshold_scope="per_channel",
    )
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=None,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = blink_position_strategy_c(
        prepared,
        valid_epoch_indices,
        setting={
            "threshold_scope": scope,
            "scan_scale": 1.0,
            "autoreject_random_state": autoreject_random_state,
            "autoreject_method": method,
        },
    )
    ground_truth = enrich_absolute_times(ground_truth_raw, epoch_duration)
    return score_channel_results(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


__all__ = [
    "blink_position_strategy_c",
    "channel_results_strategy_c",
    "epoch_detection_strategy_c_autoreject",
    "get_blink",
    "run_stage1_candidate_scan",
    "run_strategy_c",
]
