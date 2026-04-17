"""Strategy C single-channel autoreject threshold learning."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

from pyblinker.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.common.epochs import build_stage1_epochs


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


def _learn_global_threshold(
    stage1_data: np.ndarray,
    *,
    channel_names: tuple[str, ...],
    sfreq: float,
    random_state: int,
) -> float:
    epochs = build_stage1_epochs(
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
    stage1_threshold_scope: str,
    autoreject_method: str,
    stage1_scan_scale: float = 1.0,
    autoreject_random_state: int = 42,
    autoreject_augment: bool = False,
) -> SimpleNamespace:
    """Compute per-channel autoreject thresholds for stage-1 scanning.

    Parameters
    ----------
    prepared:
        Pre-processed epoch data.
    valid_epoch_indices:
        Indices of epochs to include in threshold estimation.
    stage1_threshold_scope:
        ``"per_channel"`` or ``"global"``.
    autoreject_method:
        Autoreject estimation method (e.g. ``"bayesian_optimization"``).
    stage1_scan_scale:
        Multiplicative factor applied to raw thresholds to produce
        ``scan_thresholds``. Caller is responsible for computing this
        from method/scope/rescale policy. Default ``1.0`` means no scaling.
    autoreject_random_state:
        Random seed forwarded to autoreject.
    autoreject_augment:
        Whether to use data augmentation in autoreject.

    Returns
    -------
    SimpleNamespace
        Fields: ``channel_names``, ``raw_thresholds``, ``scan_thresholds``,
        ``global_threshold``, ``threshold_learning_api``,
        ``threshold_scope``, ``autoreject_method``, ``scan_scale``.
    """
    channel_names = tuple(prepared.channel_names)
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
            scan_scale=float(stage1_scan_scale),
        )

    channel_indices = [prepared.channel_names.index(channel) for channel in channel_names]
    data = prepared.data[valid_indices][:, channel_indices, :]

    if stage1_threshold_scope == "global":
        global_threshold = _learn_global_threshold(
            data,
            channel_names=channel_names,
            sfreq=prepared.sfreq,
            random_state=autoreject_random_state,
        )
        raw_thresholds = {channel: global_threshold for channel in channel_names}
        threshold_learning_api = "get_rejection_threshold"
    else:
        epochs = build_stage1_epochs(
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
        raw_thresholds = {channel: float(thresholds[channel]) for channel in channel_names}
        global_threshold = None
        threshold_learning_api = "compute_thresholds"

    scan_thresholds = {
        channel: float(raw_thresholds[channel]) * float(stage1_scan_scale)
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
        scan_scale=float(stage1_scan_scale),
    )


__all__ = [
    "learn_strategy_c_thresholds",
]
