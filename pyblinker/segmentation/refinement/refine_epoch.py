"""Per-epoch blink refinement orchestration."""

from __future__ import annotations

from typing import Any, Dict, List

import mne
import numpy as np

from .bounds import _compute_epoch_blink_bounds
from .ear import _append_ear_refinements, _refine_ear_blinks_for_epoch
from .eeg import _append_peak_refinements


def _refine_epoch_ear(
    row_data: Dict[str, Any],
    *,
    epoch_index: int,
    data_ear: np.ndarray | None,
    blink_starts: List[int],
    blink_ends: List[int],
    sfreq: float,
    n_samp_epoch: int,
    segment_config: dict,
) -> None:
    if data_ear is None:
        return

    seg_raw = data_ear[epoch_index]
    if seg_raw.ndim != 2 or seg_raw.shape[0] != 1:
        raise ValueError(
            f"EAR refinement expects a single channel, but epoch {epoch_index} contains shape {seg_raw.shape}."
        )
    seg = seg_raw.reshape(-1)
    refinements = _refine_ear_blinks_for_epoch(
        seg,
        blink_starts,
        blink_ends,
        sfreq,
        segment_config,
    )
    _append_ear_refinements(row_data, refinements, sfreq, n_samp_epoch)


def _refine_epoch_peak_modality(
    row_data: Dict[str, Any],
    *,
    epoch_index: int,
    data_modality: np.ndarray | None,
    modality_config: dict | None,
    blink_starts: List[int],
    blink_ends: List[int],
    sfreq: float,
    n_samp_epoch: int,
    modalities: str,
) -> None:
    if data_modality is None:
        return

    seg_raw = data_modality[epoch_index]
    if seg_raw.ndim != 2 or seg_raw.shape[0] != 1:
        raise ValueError(
            f"{modalities.upper()} refinement expects a single channel, but epoch {epoch_index} contains shape {seg_raw.shape}."
        )
    seg = seg_raw.reshape(-1)
    _append_peak_refinements(
        row_data,
        seg,
        blink_starts,
        blink_ends,
        sfreq,
        modalities,
        n_samp_epoch,
        modality_config,
    )


def _refine_epoch_modalities(
    *,
    epoch_index: int,
    epoch_len: float,
    epochs: mne.Epochs,
    sfreq: float,
    n_samp_epoch: int,
    blink_onsets_sec: np.ndarray,
    blink_durs_sec: np.ndarray,
    data_ear: np.ndarray | None,
    data_eeg: np.ndarray | None,
    data_eog: np.ndarray | None,
    have_ear: bool,
    have_eeg: bool,
    have_eog: bool,
    segment_config: dict,
) -> Dict[str, Any]:
    """Refine blink metadata for a single epoch across modalities."""

    epoch_start_samp = int(epochs.events[epoch_index, 0])
    epoch_start_sec = epoch_start_samp / sfreq
    epoch_end_sec = epoch_start_sec + epoch_len

    blink_starts, blink_ends = _compute_epoch_blink_bounds(
        blink_onsets_sec,
        blink_durs_sec,
        epoch_start_sec,
        epoch_end_sec,
        sfreq,
        n_samp_epoch,
    )

    row_data: Dict[str, Any] = {
        "blink_onset": np.nan,
        "blink_duration": np.nan,
        "n_blinks": 0,
    }
    n_blinks = len(blink_starts)
    row_data["n_blinks"] = n_blinks
    if n_blinks == 0:
        return row_data

    coarse_onsets: List[float] = []
    coarse_durations: List[float] = []
    for sr, er in zip(blink_starts, blink_ends):
        onset_sec_rel = sr / sfreq
        duration_sec_rel = max(0.0, (er - sr) / sfreq)
        coarse_onsets.append(onset_sec_rel)
        coarse_durations.append(duration_sec_rel)

    if coarse_onsets:
        row_data["blink_onset"] = coarse_onsets
        row_data["blink_duration"] = coarse_durations

    if have_ear and data_ear is not None:
        _refine_epoch_ear(
            row_data,
            epoch_index=epoch_index,
            data_ear=data_ear,
            blink_starts=blink_starts,
            blink_ends=blink_ends,
            sfreq=sfreq,
            n_samp_epoch=n_samp_epoch,
            segment_config=segment_config,
        )

    if have_eeg and data_eeg is not None:
        _refine_epoch_peak_modality(
            row_data,
            epoch_index=epoch_index,
            data_modality=data_eeg,
            modality_config=segment_config.get("eeg"),
            blink_starts=blink_starts,
            blink_ends=blink_ends,
            sfreq=sfreq,
            n_samp_epoch=n_samp_epoch,
            modalities="eeg",
        )

    if have_eog and data_eog is not None:
        _refine_epoch_peak_modality(
            row_data,
            epoch_index=epoch_index,
            data_modality=data_eog,
            modality_config=segment_config.get("eog"),
            blink_starts=blink_starts,
            blink_ends=blink_ends,
            sfreq=sfreq,
            n_samp_epoch=n_samp_epoch,
            modalities="eog",
        )

    return row_data


__all__ = ["_refine_epoch_modalities"]
