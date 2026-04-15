"""Strategy C detector with autoreject-learned channel thresholds."""

from __future__ import annotations

from pathlib import Path
import sys

import mne
import numpy as np
import pandas as pd

from pyblinker.blink_features.waveform_features.extract_blink_properties import (
    BlinkProperties,
)
from pyblinker.blinker.fit_blink import FitBlinks
from pyblinker.blinker.get_blink_positions import (
    get_blink_position,
    get_blink_position_with_threshold,
)
from pyblinker.blinker.get_representative_channel import (
    channel_selection,
    filter_blink_amplitude_ratios,
    filter_good_blinks,
    filter_good_ratio,
)
from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (
    PreparedEpochDetectionInput,
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_a.epoch_channel_processor import (
    map_concatenated_blinks_to_epochs,
)
from pyblinker.epoch_detection_strategy_a.epoch_metadata_export import (
    attach_epoch_blink_metadata,
)
from pyblinker.logging import get_logger
from pyblinker.utils.annotation_utils import create_annotation
from pyblinker.utils.statistics_utils import get_blink_statistic, get_good_blink_mask
from pyblinker.viz.viz_pd import viz_complete_blink_prop

from .autoreject_constants import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    AUTOREJECT_RANDOM_SEARCH,
    CONSENSUS_CHANNEL_NAME,
    DEFAULT_AUTOREJECT_METHOD,
    DEFAULT_STAGE1_THRESHOLD_SCOPE,
    DEFAULT_STRATEGY_C_CHANNELS,
    IGNORED_TEMPLATE_ARGS,
    SEED_RESCUE_CHANNEL,
    STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE,
    STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE,
    STAGE1_RANDOM_SCAN_THRESHOLD_SCALE,
    THRESHOLD_SCOPE_GLOBAL,
    THRESHOLD_SCOPE_PER_CHANNEL,
)
from .autoreject_types import (
    Stage1CandidateDetection,
    Stage1CandidateEvaluation,
    Stage1CandidateLane,
    Stage1ScanResult,
    StrategyCAutorejectResult,
)
from .autoreject_utils import (
    _build_epoch_boundaries,
    _cluster_seed_events,
    _dedup_union,
    _empty_annotations,
    _empty_candidate_table,
    _finalize_blink_table,
    _is_cluster_already_covered,
    normalize_autoreject_method,
    normalize_stage1_threshold_scope,
)


logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VENDORED_AUTOREJECT = _REPO_ROOT / "autoreject"
if str(_VENDORED_AUTOREJECT) not in sys.path:
    sys.path.insert(0, str(_VENDORED_AUTOREJECT))

from autoreject import compute_thresholds, get_rejection_threshold  # noqa: E402


class EpochDetectionStrategyCAutoreject:
    """Autoreject-backed Strategy C detector for the first-5-epoch benchmark."""

    def __init__(
        self,
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
        stage1_channels: tuple[str, ...] | list[str] | None = None,
        stage1_threshold_scope: str = DEFAULT_STAGE1_THRESHOLD_SCOPE,
        stage1_rescale_threshold: bool = True,
        autoreject_random_state: int = 42,
        autoreject_method: str = DEFAULT_AUTOREJECT_METHOD,
        autoreject_augment: bool = False,
        **blink_param_overrides,
    ) -> None:
        self.epoch = epoch.copy()
        self.viz_data = visualize
        self.annot_label = annot_label
        self.filter_low = float(filter_low)
        self.filter_high = float(filter_high)
        self.resample_rate = resample_rate
        self.n_jobs = max(1, int(n_jobs))
        self.use_multiprocessing = use_multiprocessing
        self.pick_types_options = pick_types_options or {"eeg": True}
        clean_overrides = dict(blink_param_overrides)
        for ignored_key in IGNORED_TEMPLATE_ARGS:
            clean_overrides.pop(ignored_key, None)
        self.params = BlinkDetector._build_detector_params(
            blink_params,
            clean_overrides,
        )
        self.stage1_channels = tuple(stage1_channels or DEFAULT_STRATEGY_C_CHANNELS)
        self.stage1_threshold_scope = normalize_stage1_threshold_scope(stage1_threshold_scope)
        self.stage1_rescale_threshold = bool(stage1_rescale_threshold)
        self.autoreject_random_state = int(autoreject_random_state)
        self.autoreject_method = normalize_autoreject_method(autoreject_method)
        self.autoreject_augment = bool(autoreject_augment)
        self._prepared: PreparedEpochDetectionInput | None = None
        self.last_result: StrategyCAutorejectResult | None = None

        self.stage1_threshold_scope_: str = self.stage1_threshold_scope
        self.stage1_autoreject_method_: str = self.autoreject_method
        self.stage1_threshold_learning_api_: str = ""
        self.stage1_channel_names_: tuple[str, ...] = ()
        self.stage1_backbone_channels_: tuple[str, ...] = ()
        self.stage1_global_threshold_: float | None = None
        self.stage1_thresholds_: dict[str, float] = {}
        self.stage1_backbone_signal_: np.ndarray | None = None
        self.stage1_candidates_: pd.DataFrame = pd.DataFrame()
        self.stage1_rescue_candidates_: pd.DataFrame = pd.DataFrame()
        self.stage1_channel_summary_: pd.DataFrame = pd.DataFrame()
        self.stage1_representative_channels_: pd.DataFrame = pd.DataFrame()

    def _log_stage1_configuration(self) -> None:
        """Emit a concise debug summary of the configured Strategy C variant."""

        logger.debug(
            "Strategy C configuration: autoreject_method=%s, stage1_threshold_scope=%s, "
            "stage1_rescale_threshold=%s, stage1_channels=%s, autoreject_random_state=%d, "
            "autoreject_augment=%s",
            self.autoreject_method,
            self.stage1_threshold_scope,
            self.stage1_rescale_threshold,
            self.stage1_channels,
            self.autoreject_random_state,
            self.autoreject_augment,
        )

    def _log_stage1_resolution(
        self,
        *,
        channel_names: tuple[str, ...],
        thresholds: dict[str, float],
        backbone_signal: np.ndarray | None,
        threshold_learning_api: str,
        global_threshold: float | None,
    ) -> None:
        """Emit a debug summary after Stage 1 thresholds and lanes are resolved."""

        logger.debug(
            "Strategy C Stage 1 resolved: threshold_learning_api=%s, eligible_eeg_channels=%d, "
            "backbone_built=%s, backbone_channels=%s, stage1_rescale_threshold=%s, "
            "scan_threshold_scale=%s, global_threshold=%s",
            threshold_learning_api,
            len(channel_names),
            backbone_signal is not None,
            self.stage1_backbone_channels_,
            self.stage1_rescale_threshold,
            self._get_stage1_scan_threshold_scale(),
            global_threshold,
        )
        logger.debug("Strategy C Stage 1 thresholds: %s", thresholds)

    def _log_stage1_selection(
        self,
        *,
        selected_channel_name: str,
        selected_candidate_source: str,
        representative_channels: pd.DataFrame,
        stage1_candidates: pd.DataFrame,
        rescue_candidates: pd.DataFrame,
        n_good_blinks: int,
        n_pavr_passed: int,
    ) -> None:
        """Emit a debug summary for the selected Strategy C lane and outputs."""

        representative_names = (
            representative_channels["ch"].astype(str).tolist()
            if not representative_channels.empty and "ch" in representative_channels.columns
            else []
        )
        logger.debug(
            "Strategy C selection: selected_channel=%s, candidate_source=%s, "
            "representative_channels=%s, stage1_candidates=%d, rescue_candidates=%d, "
            "n_good_blinks=%d, n_pavr_passed=%d",
            selected_channel_name,
            selected_candidate_source,
            representative_names,
            len(stage1_candidates),
            len(rescue_candidates),
            n_good_blinks,
            n_pavr_passed,
        )

    def prepare_epoch_data(self) -> PreparedEpochDetectionInput:
        """Preprocess epoch data once and cache it for repeated Strategy C runs."""

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

    def _resolve_stage1_channel_names(
        self,
        prepared: PreparedEpochDetectionInput,
    ) -> tuple[str, ...]:
        if not prepared.channel_names:
            raise ValueError("Strategy C needs at least one EEG channel after preprocessing.")
        return tuple(prepared.channel_names)

    def _resolve_stage1_backbone_channels(
        self,
        prepared: PreparedEpochDetectionInput,
    ) -> tuple[str, ...]:
        return tuple(name for name in self.stage1_channels if name in prepared.channel_names)

    def get_channel_rejection_threshold(
        self,
        prepared: PreparedEpochDetectionInput,
        valid_epoch_indices: list[int],
    ) -> tuple[dict[str, float], tuple[str, ...], float | None, str]:
        """Learn Stage 1 channel rejection thresholds only."""

        channel_names = self._resolve_stage1_channel_names(prepared)
        channel_indices = [prepared.channel_names.index(channel) for channel in channel_names]
        stage1_data = prepared.data[np.asarray(valid_epoch_indices, dtype=int)][:, channel_indices, :]

        info = mne.create_info(
            list(channel_names),
            sfreq=float(prepared.sfreq),
            ch_types=["eeg"] * len(channel_names),
        )
        stage1_epochs = mne.EpochsArray(stage1_data, info, verbose="ERROR")
        global_threshold: float | None = None

        if self.stage1_threshold_scope == THRESHOLD_SCOPE_GLOBAL:
            if stage1_data.shape[0] < 2:
                global_threshold = float(np.max(np.ptp(stage1_data, axis=2)))
            else:
                reject = get_rejection_threshold(
                    stage1_epochs,
                    random_state=self.autoreject_random_state,
                    ch_types="eeg",
                    cv=min(5, int(stage1_data.shape[0])),
                    verbose=False,
                )
                global_threshold = float(reject["eeg"])
            thresholds = {channel: global_threshold for channel in channel_names}
            threshold_learning_api = "get_rejection_threshold"
        else:
            threshes = compute_thresholds(
                stage1_epochs,
                method=self.autoreject_method,
                random_state=self.autoreject_random_state,
                augment=self.autoreject_augment,
                verbose=False,
            )
            thresholds = {channel: float(threshes[channel]) for channel in channel_names}
            threshold_learning_api = "compute_thresholds"

        return thresholds, channel_names, global_threshold, threshold_learning_api

    def _build_stage1_backbone_signal(
        self,
        *,
        prepared: PreparedEpochDetectionInput,
        valid_epoch_indices: list[int],
        thresholds: dict[str, float],
        backbone_channels: tuple[str, ...],
    ) -> np.ndarray | None:
        """Build the weighted median backbone used when enough frontal channels survive."""

        if len(backbone_channels) < 2:
            return None

        valid_indices = np.asarray(valid_epoch_indices, dtype=int)
        backbone_indices = [prepared.channel_names.index(channel) for channel in backbone_channels]
        backbone_data = prepared.data[valid_indices][:, backbone_indices, :]
        threshold_vec = np.asarray(
            [thresholds[channel] for channel in backbone_channels],
            dtype=float,
        )
        threshold_vec = np.maximum(threshold_vec, np.finfo(float).eps)
        weighted = backbone_data / threshold_vec[np.newaxis, :, np.newaxis]
        return np.median(weighted, axis=1).reshape(-1)

    def _get_stage1_scan_threshold_scale(self) -> float:
        """Translate Stage 1 PTP rejection thresholds into scan thresholds."""

        if not self.stage1_rescale_threshold:
            return 1.0
        if self.stage1_threshold_scope == THRESHOLD_SCOPE_GLOBAL:
            return STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE
        if self.autoreject_method == AUTOREJECT_BAYESIAN_OPTIMIZATION:
            return STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE
        return STAGE1_RANDOM_SCAN_THRESHOLD_SCALE

    def rescale_threshold(
        self,
        *,
        prepared: PreparedEpochDetectionInput,
        valid_epoch_indices: list[int],
        thresholds: dict[str, float],
        backbone_signal: np.ndarray | None,
    ) -> list[Stage1CandidateLane]:
        """Translate autoreject thresholds into Stage 1 scan thresholds.

        By default this rescales autoreject PTP rejection thresholds into the lower scan
        thresholds used to seed blink candidates. When ``stage1_rescale_threshold`` is
        disabled, the raw autoreject threshold is used directly for each lane instead.
        """

        valid_indices = np.asarray(valid_epoch_indices, dtype=int)
        scan_threshold_scale = self._get_stage1_scan_threshold_scale()
        lanes: list[Stage1CandidateLane] = []

        for channel in prepared.channel_names:
            if channel not in thresholds:
                continue
            channel_index = prepared.channel_names.index(channel)
            signal = prepared.data[valid_indices, channel_index, :].reshape(-1)
            lanes.append(
                Stage1CandidateLane(
                    channel=channel,
                    signal=signal,
                    threshold=float(thresholds[channel]) * scan_threshold_scale,
                    candidate_source="channel_threshold",
                )
            )

        if backbone_signal is not None:
            lanes.append(
                Stage1CandidateLane(
                    channel=CONSENSUS_CHANNEL_NAME,
                    signal=backbone_signal,
                    threshold=scan_threshold_scale,
                    candidate_source="weighted_median_backbone",
                )
            )

        return lanes

    def _map_candidates(
        self,
        blink_df: pd.DataFrame,
        *,
        channel: str,
        valid_epoch_indices: list[int],
        epoch_boundaries: list[tuple[int, int]],
        sfreq: float,
    ) -> pd.DataFrame:
        return map_concatenated_blinks_to_epochs(
            blink_df,
            channel=channel,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=sfreq,
        )

    def run_stage1_candidate_scan(
        self,
        *,
        prepared: PreparedEpochDetectionInput,
        valid_epoch_indices: list[int],
    ) -> Stage1ScanResult:
        """Run the shared Stage 1 scan before any FitBlinks refinement."""

        epoch_boundaries = _build_epoch_boundaries(
            valid_epoch_count=len(valid_epoch_indices),
            epoch_length_samples=prepared.epoch_length_samples,
        )

        (
            thresholds,
            channel_names,
            global_threshold,
            threshold_learning_api,
        ) = self.get_channel_rejection_threshold(prepared, valid_epoch_indices)

        backbone_channels = self._resolve_stage1_backbone_channels(prepared)
        backbone_signal: np.ndarray | None = None
        self.stage1_backbone_channels_ = ()
        if len(backbone_channels) >= 2:
            backbone_signal = self._build_stage1_backbone_signal(
                prepared=prepared,
                valid_epoch_indices=valid_epoch_indices,
                thresholds=thresholds,
                backbone_channels=backbone_channels,
            )
            self.stage1_backbone_channels_ = backbone_channels
        self._log_stage1_resolution(
            channel_names=channel_names,
            thresholds=thresholds,
            backbone_signal=backbone_signal,
            threshold_learning_api=threshold_learning_api,
            global_threshold=global_threshold,
        )
        candidate_lanes = self.rescale_threshold(
            prepared=prepared,
            valid_epoch_indices=valid_epoch_indices,
            thresholds=thresholds,
            backbone_signal=backbone_signal,
        )
        detections = self._detect_stage1_candidate_positions(
            candidate_lanes,
            prepared=prepared,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
        )
        return Stage1ScanResult(
            epoch_boundaries=epoch_boundaries,
            backbone_signal=backbone_signal,
            thresholds=thresholds,
            channel_names=channel_names,
            global_threshold=global_threshold,
            threshold_learning_api=threshold_learning_api,
            candidate_lanes=candidate_lanes,
            detections=detections,
        )

    def _build_selective_rescue_lane(
        self,
        *,
        prepared: PreparedEpochDetectionInput,
        valid_epoch_indices: list[int],
        epoch_boundaries: list[tuple[int, int]],
        baseline: pd.DataFrame,
    ) -> pd.DataFrame:
        """Recover likely missed blinks with a narrow F7-only fallback detector."""

        if SEED_RESCUE_CHANNEL not in prepared.channel_names:
            return _empty_candidate_table()

        f7_index = prepared.channel_names.index(SEED_RESCUE_CHANNEL)
        epoch_signals = prepared.data[np.asarray(valid_epoch_indices, dtype=int), f7_index, :]
        f7_signal = epoch_signals.reshape(-1)

        seed_params = self.params.copy()
        seed_params["std_threshold"] = 1.3
        seed_params["min_event_len"] = 0.0
        seed_params["min_event_sep"] = 0.0
        seed_df = get_blink_position(
            seed_params,
            blink_component=f7_signal,
            ch=SEED_RESCUE_CHANNEL,
            progress_bar=False,
        )
        seed_mapped = self._map_candidates(
            seed_df,
            channel=SEED_RESCUE_CHANNEL,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )

        rescue_rows: list[pd.Series] = []
        for epoch_index, cluster in _cluster_seed_events(seed_mapped):
            if len(cluster) != 2:
                continue
            seed_span_s = float(cluster[-1]["blink_onset"]) - float(cluster[0]["blink_onset"])
            max_seed_duration_s = max(float(row["blink_duration"]) for row in cluster)
            if not (0.08 <= seed_span_s <= 0.15):
                continue
            if max_seed_duration_s >= 0.03:
                continue
            if _is_cluster_already_covered(epoch_index, cluster, baseline):
                continue

            cluster_center_s = float(
                np.mean(
                    [
                        float(row["blink_onset"]) + float(row["blink_duration"]) / 2.0
                        for row in cluster
                    ]
                )
            )
            local_start_s = max(0.0, cluster_center_s - 0.35)
            local_stop_s = min(
                prepared.epoch_length_samples / prepared.sfreq,
                cluster_center_s + 0.35,
            )
            epoch_offset = valid_epoch_indices.index(epoch_index)
            epoch_signal = epoch_signals[epoch_offset]
            local_start_sample = int(round(local_start_s * prepared.sfreq))
            local_stop_sample = int(round(local_stop_s * prepared.sfreq))
            local_signal = epoch_signal[local_start_sample:local_stop_sample]
            if local_signal.size == 0:
                continue

            # The seed pair suggests a local blink-shaped blind spot, so rerun a
            # stricter detector only inside a tight window around that cluster.
            rescue_params = self.params.copy()
            rescue_params["std_threshold"] = 0.4
            rescue_params["min_event_len"] = 0.03
            rescue_params["min_event_sep"] = 0.05
            local_df = get_blink_position(
                rescue_params,
                blink_component=local_signal,
                ch=SEED_RESCUE_CHANNEL,
                progress_bar=False,
            )
            if local_df.empty:
                continue

            local_df = local_df.copy()
            global_epoch_offset = epoch_index * prepared.epoch_length_samples
            local_df["start_blink"] += global_epoch_offset + local_start_sample
            local_df["end_blink"] += global_epoch_offset + local_start_sample
            local_df["candidate_source"] = "f7_selective_rescue"
            local_mapped = self._map_candidates(
                local_df,
                channel=SEED_RESCUE_CHANNEL,
                valid_epoch_indices=valid_epoch_indices,
                epoch_boundaries=epoch_boundaries,
                sfreq=prepared.sfreq,
            )
            if local_mapped.empty:
                continue

            for _, row in local_mapped.iterrows():
                duration_s = float(row["blink_duration"])
                center_delta_s = abs(
                    (float(row["blink_onset"]) + duration_s / 2.0) - cluster_center_s
                )
                if 0.15 <= duration_s <= 0.60 and center_delta_s <= 0.20:
                    rescue_rows.append(row)

        if not rescue_rows:
            return _empty_candidate_table()
        return pd.DataFrame(rescue_rows).reset_index(drop=True)

    def _detect_stage1_candidate_positions(
        self,
        candidate_lanes: list[Stage1CandidateLane],
        *,
        prepared: PreparedEpochDetectionInput,
        valid_epoch_indices: list[int],
        epoch_boundaries: list[tuple[int, int]],
    ) -> list[Stage1CandidateDetection]:
        min_blink_frames = float(self.params["min_event_len"] * self.params["sfreq"])
        detections: list[Stage1CandidateDetection] = []

        for lane in candidate_lanes:
            positions = get_blink_position_with_threshold(
                self.params,
                blink_component=lane.signal,
                threshold=lane.threshold,
                ch=lane.channel,
                progress_bar=False,
                min_blink_frames=min_blink_frames,
            ).copy()
            if positions.empty:
                positions["candidate_source"] = pd.Series(dtype="object")
            else:
                positions["candidate_source"] = lane.candidate_source

            mapped = self._map_candidates(
                positions,
                channel=lane.channel,
                valid_epoch_indices=valid_epoch_indices,
                epoch_boundaries=epoch_boundaries,
                sfreq=prepared.sfreq,
            )

            detections.append(
                Stage1CandidateDetection(
                    channel=lane.channel,
                    signal=lane.signal,
                    threshold=float(lane.threshold),
                    candidate_source=lane.candidate_source,
                    positions=positions,
                    mapped_candidates=mapped,
                )
            )

        return detections

    def _evaluate_stage1_candidates(
        self,
        detections: list[Stage1CandidateDetection],
    ) -> list[Stage1CandidateEvaluation]:
        evaluations: list[Stage1CandidateEvaluation] = []

        for detection in detections:
            fitblinks = FitBlinks(
                candidate_signal=detection.signal,
                df=detection.positions.copy(),
                params=self.params,
            )
            fitblinks.dprocess()
            fitted_df = fitblinks.frame_blinks.copy()

            blink_stats = get_blink_statistic(
                fitted_df,
                self.params["z_thresholds"],
                signal=detection.signal,
            )
            blink_stats["ch"] = detection.channel
            blink_stats["strategy_c_candidate_source"] = detection.candidate_source
            blink_stats["strategy_c_detection_threshold"] = float(detection.threshold)
            blink_stats["strategy_c_stage1_candidate_count"] = int(len(detection.positions))

            evaluations.append(
                Stage1CandidateEvaluation(
                    channel=detection.channel,
                    signal=detection.signal,
                    threshold=float(detection.threshold),
                    candidate_source=detection.candidate_source,
                    positions=detection.positions,
                    mapped_candidates=detection.mapped_candidates,
                    fitted_df=fitted_df,
                    stats=blink_stats,
                )
            )

        return evaluations

    def _shortlist_representative_channels(
        self,
        channel_summary: pd.DataFrame,
        *,
        top_n: int = 3,
    ) -> pd.DataFrame:
        if channel_summary.empty:
            return pd.DataFrame()

        shortlisted = filter_blink_amplitude_ratios(channel_summary.copy(), self.params)
        shortlisted = filter_good_blinks(shortlisted, self.params)
        shortlisted = filter_good_ratio(shortlisted, self.params)

        if "select" in shortlisted.columns and shortlisted["select"].any():
            shortlisted = shortlisted[shortlisted["select"]].copy()

        shortlisted = shortlisted.drop(columns=["status", "select"], errors="ignore")
        sort_spec = [
            ("number_good_blinks", False),
            ("good_ratio", False),
            ("blink_amp_ratio", False),
            ("number_blinks", False),
            ("ch", True),
        ]
        sort_columns = [column for column, _ in sort_spec if column in shortlisted.columns]
        if sort_columns:
            ascending = [ascending for column, ascending in sort_spec if column in sort_columns]
            shortlisted = shortlisted.sort_values(
                sort_columns,
                ascending=ascending,
                na_position="last",
            )
        return shortlisted.head(top_n).reset_index(drop=True)

    @staticmethod
    def _get_selected_stage1_evaluation(
        evaluations: list[Stage1CandidateEvaluation],
        selected: pd.DataFrame,
    ) -> Stage1CandidateEvaluation | None:
        if not evaluations:
            return None
        if selected.empty or "ch" not in selected.columns:
            return evaluations[0]
        selected_channel = str(selected.loc[0, "ch"])
        for evaluation in evaluations:
            if evaluation.channel == selected_channel:
                return evaluation
        return evaluations[0]

    def _annotate_quality_flags(
        self,
        fitted_df: pd.DataFrame,
        *,
        signal: np.ndarray,
        sfreq: float,
    ) -> tuple[pd.DataFrame, dict[str, float], int, int]:
        if fitted_df.empty:
            empty = fitted_df.copy()
            empty["strategy_c_good_mask"] = pd.Series(dtype=bool)
            empty["strategy_c_pavr_pass"] = pd.Series(dtype=bool)
            return empty, {}, 0, 0

        blink_stats = get_blink_statistic(
            fitted_df,
            self.params["z_thresholds"],
            signal=signal,
        )
        good_count = int(blink_stats.get("number_good_blinks", 0))

        try:
            _, good_df = get_good_blink_mask(
                fitted_df,
                blink_stats["best_median"],
                blink_stats["best_robust_std"],
                self.params["z_thresholds"],
            )
        except Exception:
            good_df = pd.DataFrame(columns=fitted_df.columns)

        good_pairs = {
            (int(row["start_blink"]), int(row["end_blink"]))
            for _, row in good_df.iterrows()
            if "start_blink" in row and "end_blink" in row
        }

        try:
            annotated = BlinkProperties(
                signal,
                fitted_df.copy(),
                sfreq,
                self.params,
            ).df
        except Exception:
            annotated = fitted_df.copy()

        annotated["strategy_c_good_mask"] = [
            (int(row["start_blink"]), int(row["end_blink"])) in good_pairs
            for _, row in annotated.iterrows()
        ]

        if {"pos_amp_vel_ratio_zero", "max_value"} <= set(annotated.columns):
            condition_1 = annotated["pos_amp_vel_ratio_zero"] < self.params["p_avr_threshold"]
            median = float(blink_stats.get("best_median", np.nan))
            robust_std = float(blink_stats.get("best_robust_std", np.nan))
            if np.isnan(median) or np.isnan(robust_std):
                annotated["strategy_c_pavr_pass"] = True
            else:
                condition_2 = annotated["max_value"] < (median - robust_std)
                annotated["strategy_c_pavr_pass"] = ~(condition_1 & condition_2)
        else:
            annotated["strategy_c_pavr_pass"] = True

        pavr_passed = int(annotated["strategy_c_pavr_pass"].sum())
        return annotated, blink_stats, good_count, pavr_passed

    def get_blink(self):
        """Run the Strategy C detector and return the Strategy A-compatible tuple."""

        logger.info("Starting Strategy C autoreject-aware epoch blink detection.")
        self._log_stage1_configuration()
        prepared = self.prepare_epoch_data()
        valid_epoch_indices = get_valid_epoch_indices(self.epoch)
        epochs_out = self.epoch.copy()

        stage1 = self.run_stage1_candidate_scan(
            prepared=prepared,
            valid_epoch_indices=valid_epoch_indices,
        )
        epoch_boundaries = stage1.epoch_boundaries
        backbone_signal = stage1.backbone_signal
        thresholds = stage1.thresholds
        channel_names = stage1.channel_names
        global_threshold = stage1.global_threshold
        threshold_learning_api = stage1.threshold_learning_api
        detections = stage1.detections
        evaluations = self._evaluate_stage1_candidates(detections)

        channel_summary = pd.DataFrame([evaluation.stats for evaluation in evaluations]).reset_index(
            drop=True
        )
        representative_channels = self._shortlist_representative_channels(
            channel_summary,
            top_n=3,
        )
        selected_channel = (
            channel_selection(channel_summary.copy(), self.params).reset_index(drop=True)
            if not channel_summary.empty
            else pd.DataFrame()
        )
        selected_evaluation = self._get_selected_stage1_evaluation(evaluations, selected_channel)
        if selected_evaluation is None:
            raise RuntimeError("Strategy C failed to produce any Stage 1 candidate lanes.")

        selected_signal = selected_evaluation.signal
        selected_channel_name = selected_evaluation.channel
        selected_candidate_source = selected_evaluation.candidate_source
        representative_channel_names = (
            set(representative_channels["ch"].astype(str).tolist())
            if not representative_channels.empty
            else {selected_channel_name}
        )
        representative_frames = [
            evaluation.mapped_candidates
            for evaluation in evaluations
            if evaluation.channel in representative_channel_names
        ]
        baseline_candidates = _dedup_union(*representative_frames)
        has_representative_backbone = any(
            evaluation.channel in representative_channel_names
            and evaluation.candidate_source == "weighted_median_backbone"
            for evaluation in evaluations
        )
        rescue_candidates = (
            self._build_selective_rescue_lane(
                prepared=prepared,
                valid_epoch_indices=valid_epoch_indices,
                epoch_boundaries=epoch_boundaries,
                baseline=baseline_candidates,
            )
            if has_representative_backbone
            else _empty_candidate_table()
        )
        stage1_candidates = _dedup_union(baseline_candidates, rescue_candidates)

        positions = (
            stage1_candidates.loc[:, ["start_blink", "end_blink", "candidate_source"]].copy()
            if not stage1_candidates.empty
            else pd.DataFrame(columns=["start_blink", "end_blink", "candidate_source"])
        )

        fitblinks = FitBlinks(
            candidate_signal=selected_signal,
            df=positions.copy(),
            params=self.params,
        )
        fitblinks.dprocess()
        fitted_df = fitblinks.frame_blinks.copy()

        if "candidate_source" not in fitted_df.columns and not positions.empty:
            source_lookup = positions.drop_duplicates(subset=["start_blink", "end_blink"])
            fitted_df = fitted_df.merge(
                source_lookup,
                on=["start_blink", "end_blink"],
                how="left",
            )

        annotated_df, blink_stats, n_good_blinks, n_pavr_passed = self._annotate_quality_flags(
            fitted_df,
            signal=selected_signal,
            sfreq=prepared.sfreq,
        )
        annotated_df["channel"] = selected_channel_name
        if "candidate_source" not in annotated_df.columns:
            annotated_df["candidate_source"] = (
                pd.Series(dtype="object")
                if annotated_df.empty
                else selected_candidate_source
            )
        if blink_stats:
            annotated_df["strategy_c_best_median"] = float(blink_stats.get("best_median", np.nan))
            annotated_df["strategy_c_best_robust_std"] = float(
                blink_stats.get("best_robust_std", np.nan)
            )

        mapped_blinks = self._map_candidates(
            annotated_df,
            channel=selected_channel_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )
        blink_table = _finalize_blink_table(
            mapped_blinks,
            epochs=epochs_out,
            prepared=prepared,
        )
        attach_epoch_blink_metadata(
            epochs_out,
            blink_table,
            candidate_channel=selected_channel_name,
            valid_epoch_indices=valid_epoch_indices,
        )

        annotations = (
            create_annotation(
                annotated_df,
                prepared.sfreq,
                self.annot_label if self.annot_label else "eye_blink",
            )
            if not annotated_df.empty
            else _empty_annotations()
        )

        if selected_channel.empty:
            selected_channel = pd.DataFrame([dict(selected_evaluation.stats)])
        else:
            selected_channel = selected_channel.copy()

        selected_channel["ch"] = selected_channel_name
        selected_channel["number_good_blinks"] = int(n_good_blinks)
        selected_channel["strategy_c_stage1_candidates"] = int(len(stage1_candidates))
        selected_channel["strategy_c_stage1_rescue_candidates"] = int(len(rescue_candidates))
        selected_channel["strategy_c_stage1_channels"] = ", ".join(channel_names)
        selected_channel["strategy_c_stage1_backbone_channels"] = ", ".join(
            self.stage1_backbone_channels_
        )
        selected_channel["strategy_c_stage1_backbone_built"] = backbone_signal is not None
        selected_channel["strategy_c_stage1_threshold_scope"] = self.stage1_threshold_scope
        selected_channel["strategy_c_stage1_threshold_learning_api"] = threshold_learning_api
        selected_channel["strategy_c_stage1_rescale_threshold"] = self.stage1_rescale_threshold
        selected_channel["strategy_c_stage1_scan_threshold_scale"] = (
            self._get_stage1_scan_threshold_scale()
        )
        selected_channel["strategy_c_stage1_global_threshold"] = (
            float(global_threshold) if global_threshold is not None else np.nan
        )
        selected_channel["strategy_c_autoreject_method"] = self.autoreject_method
        selected_channel["strategy_c_candidate_source"] = selected_candidate_source
        selected_channel["strategy_c_representative_channels"] = (
            ", ".join(representative_channels["ch"].astype(str).tolist())
            if not representative_channels.empty
            else selected_channel_name
        )
        selected_channel["strategy_c_representative_channel_count"] = int(
            len(representative_channels)
        )
        selected_channel["strategy_c_good_mask_passed"] = (
            int(annotated_df["strategy_c_good_mask"].sum())
            if "strategy_c_good_mask" in annotated_df.columns
            else 0
        )
        selected_channel["strategy_c_pavr_passed"] = int(n_pavr_passed)
        self._log_stage1_selection(
            selected_channel_name=selected_channel_name,
            selected_candidate_source=selected_candidate_source,
            representative_channels=representative_channels,
            stage1_candidates=stage1_candidates,
            rescue_candidates=rescue_candidates,
            n_good_blinks=int(n_good_blinks),
            n_pavr_passed=int(n_pavr_passed),
        )

        fig_data: list[object] = []
        if self.viz_data and not annotated_df.empty:
            fig_data = [
                viz_complete_blink_prop(selected_signal, row, prepared.sfreq)
                for _, row in annotated_df.iterrows()
            ]

        self.stage1_threshold_scope_ = self.stage1_threshold_scope
        self.stage1_autoreject_method_ = self.autoreject_method
        self.stage1_threshold_learning_api_ = threshold_learning_api
        self.stage1_channel_names_ = channel_names
        self.stage1_global_threshold_ = global_threshold
        self.stage1_thresholds_ = thresholds
        self.stage1_backbone_signal_ = backbone_signal
        self.stage1_candidates_ = stage1_candidates.copy()
        self.stage1_rescue_candidates_ = rescue_candidates.copy()
        self.stage1_channel_summary_ = channel_summary.copy()
        self.stage1_representative_channels_ = representative_channels.copy()

        result = StrategyCAutorejectResult(
            annotations=annotations,
            channel=selected_channel_name,
            n_good_blinks=int(n_good_blinks),
            blink_table=blink_table,
            fig_data=fig_data,
            selected_channel=selected_channel,
            epochs=epochs_out,
            valid_epoch_indices=list(valid_epoch_indices),
        )
        self.last_result = result
        self.epoch = result.epochs
        return (
            result.annotations,
            result.channel,
            result.n_good_blinks,
            result.blink_table,
            result.fig_data,
            result.selected_channel,
            result.epochs,
        )


epoch_detection_strategy_c_autoreject = EpochDetectionStrategyCAutoreject

__all__ = [
    "EpochDetectionStrategyCAutoreject",
    "epoch_detection_strategy_c_autoreject",
]
