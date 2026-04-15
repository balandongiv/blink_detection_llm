"""Strategy C single-channel autoreject threshold learning."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import mne
import numpy as np

from pyblinker.common.epoch_input import PreparedEpochDetectionInput

DEFAULT_STAGE1_THRESHOLD_SCALES = {
    "random_search": 0.08,
    "bayesian_optimization": 0.12,
    "global": 0.005,
}
DEFAULT_NO_BACKBONE_SENTINEL = ("__NO_BACKBONE__",)


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


def resolve_stage1_channels(
    prepared: PreparedEpochDetectionInput,
    *,
    stage1_channels: tuple[str, ...] | list[str] | None = None,
    no_backbone_sentinel: tuple[str, ...] = DEFAULT_NO_BACKBONE_SENTINEL,
) -> tuple[str, ...]:
    selected_channels = (
        tuple(stage1_channels) if stage1_channels is not None else tuple(no_backbone_sentinel)
    )
    if selected_channels == tuple(no_backbone_sentinel):
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
    return channel_names


def get_stage1_scan_scale(
    *,
    stage1_threshold_scope: str,
    autoreject_method: str,
    stage1_rescale_threshold: bool = True,
    stage1_threshold_scales: dict[str, float] | None = None,
) -> float:
    if not stage1_rescale_threshold:
        return 1.0

    threshold_scales = dict(DEFAULT_STAGE1_THRESHOLD_SCALES)
    if stage1_threshold_scales is not None:
        threshold_scales.update(
            {key: float(value) for key, value in stage1_threshold_scales.items()}
        )

    if stage1_threshold_scope == "global":
        return float(threshold_scales["global"])
    if autoreject_method == "bayesian_optimization":
        return float(threshold_scales["bayesian_optimization"])
    return float(threshold_scales["random_search"])


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


def learn_strategy_c_thresholds(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    stage1_channels: tuple[str, ...] | list[str] | None = None,
    no_backbone_sentinel: tuple[str, ...] = DEFAULT_NO_BACKBONE_SENTINEL,
    stage1_threshold_scope: str,
    autoreject_method: str,
    stage1_rescale_threshold: bool = True,
    stage1_threshold_scales: dict[str, float] | None = None,
    autoreject_random_state: int = 42,
    autoreject_augment: bool = False,
) -> SimpleNamespace:
    channel_names = resolve_stage1_channels(
        prepared,
        stage1_channels=stage1_channels,
        no_backbone_sentinel=no_backbone_sentinel,
    )
    scan_scale = get_stage1_scan_scale(
        stage1_threshold_scope=stage1_threshold_scope,
        autoreject_method=autoreject_method,
        stage1_rescale_threshold=stage1_rescale_threshold,
        stage1_threshold_scales=stage1_threshold_scales,
    )
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)

    if len(valid_indices) == 0:
        raw_thresholds = {channel: 0.0 for channel in channel_names}
        return SimpleNamespace(
            channel_names=channel_names,
            raw_thresholds=raw_thresholds,
            scan_thresholds={channel: 0.0 for channel in channel_names},
            global_threshold=None,
            threshold_learning_api="none",
            stage1_threshold_scope=stage1_threshold_scope,
            autoreject_method=autoreject_method,
            scan_scale=float(scan_scale),
        )

    channel_indices = [prepared.channel_names.index(channel) for channel in channel_names]
    stage1_data = prepared.data[valid_indices][:, channel_indices, :]

    if stage1_threshold_scope == "global":
        global_threshold = _learn_global_threshold(
            stage1_data,
            channel_names=channel_names,
            sfreq=prepared.sfreq,
            random_state=autoreject_random_state,
        )
        raw_thresholds = {channel: global_threshold for channel in channel_names}
        threshold_learning_api = "get_rejection_threshold"
    else:
        epochs = _build_stage1_epochs(
            stage1_data,
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
        raw_thresholds = {channel: float(thresholds[channel]) for channel in channel_names}
        global_threshold = None
        threshold_learning_api = "compute_thresholds"

    scan_thresholds = {
        channel: float(raw_thresholds[channel]) * float(scan_scale)
        for channel in channel_names
    }
    return SimpleNamespace(
        channel_names=channel_names,
        raw_thresholds=raw_thresholds,
        scan_thresholds=scan_thresholds,
        global_threshold=global_threshold,
        threshold_learning_api=threshold_learning_api,
        stage1_threshold_scope=stage1_threshold_scope,
        autoreject_method=autoreject_method,
        scan_scale=float(scan_scale),
    )


StrategyCThresholdResult = SimpleNamespace


__all__ = [
    "DEFAULT_NO_BACKBONE_SENTINEL",
    "DEFAULT_STAGE1_THRESHOLD_SCALES",
    "StrategyCThresholdResult",
    "get_stage1_scan_scale",
    "learn_strategy_c_thresholds",
    "resolve_stage1_channels",
]
