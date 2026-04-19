"""Helpers for preparing segmentation settings and epoch data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import mne
import numpy as np


def _prepare_segmentation_config(
    segmentation_type: Optional[dict],
) -> Dict[str, Any]:
    """Return a defensive copy of the segmentation settings."""

    config: Dict[str, Any] = dict(segmentation_type or {})
    for modality, modality_config in list(config.items()):
        if isinstance(modality_config, dict):
            config[modality] = dict(modality_config)
    return config


def _is_noop_segmentation(modality_config: Dict[str, Any]) -> bool:
    """Return True when segmentation is explicitly disabled for a modality."""

    seg_type = modality_config.get("seg_type")
    if isinstance(seg_type, str):
        return not seg_type.strip()
    if isinstance(seg_type, Sequence) and not isinstance(seg_type, str):
        return len(seg_type) == 0
    return False


def _modality_enabled(segment_config: Dict[str, Any], modality: str) -> bool:
    """Return True when a modality should be refined."""

    modality_config = segment_config.get(modality)
    if not isinstance(modality_config, dict):
        return False
    if _is_noop_segmentation(modality_config):
        return False

    channel_value = modality_config.get("channel")
    if channel_value is None:
        return False
    if isinstance(channel_value, str):
        return bool(channel_value.strip())
    if isinstance(channel_value, Sequence) and not isinstance(channel_value, str):
        return len(channel_value) > 0
    return False


@dataclass
class EpochPreparationResult:
    """Container for epoch-level data and modality picks."""

    epochs: mne.Epochs
    sfreq: float
    n_epochs: int
    n_samp_epoch: int
    data_ear: np.ndarray | None
    data_eeg: np.ndarray | None
    data_eog: np.ndarray | None
    have_ear: bool
    have_eeg: bool
    have_eog: bool
    blink_onsets_sec: np.ndarray
    blink_durs_sec: np.ndarray


def _resolve_single_channel_pick(
    raw: mne.io.BaseRaw,
    config: Dict[str, Any],
    modality: str,
    *,
    required: bool,
) -> int | None:
    """Validate and return the index for a single modality channel."""

    channel_value = (config or {}).get("channel")
    if channel_value is None or (
        isinstance(channel_value, str) and not channel_value.strip()
    ):
        if required:
            raise ValueError(
                f"{modality.upper()} refinement requires a single channel set via segmentation config."
            )
        return None

    if isinstance(channel_value, Sequence) and not isinstance(channel_value, str):
        if len(channel_value) != 1:
            raise ValueError(
                f"{modality.upper()} refinement expects exactly one channel, but got {len(channel_value)} entries."
            )
        channel_name = str(channel_value[0])
    else:
        channel_name = str(channel_value)

    picks = [idx for idx, name in enumerate(raw.ch_names) if name == channel_name]
    if not picks:
        raise ValueError(
            f"Configured {modality.upper()} channel '{channel_name}' not found in raw data."
        )
    if len(picks) > 1:
        raise ValueError(
            f"{modality.upper()} refinement expects a single channel, but multiple matches were found for "
            f"'{channel_name}'."
        )
    return picks[0]


def _prepare_epochs_and_modalities(
    raw: mne.io.BaseRaw,
    *,
    epoch_len: float,
    blink_label: str | None,
    segment_config: Dict[str, Any],
) -> EpochPreparationResult:
    """Create epochs, resolve modality channels, and filter annotations."""

    events = mne.make_fixed_length_events(raw, duration=epoch_len)
    sfreq = float(raw.info["sfreq"])
    epochs = mne.Epochs(
        raw,
        events,
        tmin=0.0,
        tmax=epoch_len - 1.0 / sfreq,
        baseline=None,
        preload=True,
        verbose=False,
    )

    have_ear = _modality_enabled(segment_config, "ear")
    have_eeg = _modality_enabled(segment_config, "eeg")
    have_eog = _modality_enabled(segment_config, "eog")

    ear_idx = (
        _resolve_single_channel_pick(
            raw, segment_config.get("ear", {}), "ear", required=True
        )
        if have_ear
        else None
    )
    eeg_idx = (
        _resolve_single_channel_pick(
            raw, segment_config.get("eeg", {}), "eeg", required=False
        )
        if have_eeg
        else None
    )
    eog_idx = (
        _resolve_single_channel_pick(
            raw, segment_config.get("eog", {}), "eog", required=False
        )
        if have_eog
        else None
    )

    data_ear = (
        epochs.get_data(picks=[ear_idx]) if have_ear and ear_idx is not None else None
    )
    data_eeg = (
        epochs.get_data(picks=[eeg_idx]) if have_eeg and eeg_idx is not None else None
    )
    data_eog = (
        epochs.get_data(picks=[eog_idx]) if have_eog and eog_idx is not None else None
    )

    n_epochs = len(epochs)
    n_samp_epoch = (
        epochs.get_data(picks=[0]).shape[-1]
        if epochs.info["nchan"] > 0
        else int(round(epoch_len * sfreq))
    )

    ann = raw.annotations
    if blink_label is None:
        sel = np.ones(len(ann), dtype=bool)
    else:
        sel = np.array(
            [(str(d).lower() == blink_label.lower()) for d in ann.description],
            dtype=bool,
        )

    blink_onsets_sec = np.array(ann.onset)[sel]
    blink_durs_sec = np.array(ann.duration)[sel]

    return EpochPreparationResult(
        epochs=epochs,
        sfreq=sfreq,
        n_epochs=n_epochs,
        n_samp_epoch=n_samp_epoch,
        data_ear=data_ear,
        data_eeg=data_eeg,
        data_eog=data_eog,
        have_ear=have_ear,
        have_eeg=have_eeg,
        have_eog=have_eog,
        blink_onsets_sec=blink_onsets_sec,
        blink_durs_sec=blink_durs_sec,
    )


__all__ = [
    "EpochPreparationResult",
    "_is_noop_segmentation",
    "_modality_enabled",
    "_prepare_epochs_and_modalities",
    "_prepare_segmentation_config",
    "_resolve_single_channel_pick",
]
