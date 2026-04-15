"""Shared epoch/context utilities for blink feature extractors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Set

import mne
import pandas as pd

from .constants import infer_modality
from .utils.style_windows import available_styles
from ..utils.epoch_utils import resolve_channels


@dataclass(frozen=True)
class EpochContext:
    """Common per-run context shared by feature-family compute loops."""

    epochs: mne.Epochs
    sfreq: float
    ch_names: List[str]
    modality_by_channel: Dict[str, str]
    metadata_cols: Sequence[str] | None
    index: pd.Index
    n_epochs: int
    n_times: int


def build_epoch_context(
    epochs: mne.Epochs,
    picks: str | Sequence[str] | None,
    *,
    default=None,
) -> EpochContext:
    """Resolve channels and precompute common epoch-level metadata."""

    ch_names = resolve_channels(epochs, picks, default=default)
    sfreq = float(epochs.info["sfreq"])
    n_epochs = len(epochs)
    index = (
        epochs.metadata.index
        if isinstance(epochs.metadata, pd.DataFrame)
        else pd.RangeIndex(n_epochs)
    )

    if n_epochs == 0:
        n_times = 0
    else:
        n_times = int(epochs.get_data(picks=[ch_names[0]]).shape[-1])

    modality_by_channel = {ch: infer_modality(ch, epochs.info) for ch in ch_names}
    metadata_cols = (
        tuple(epochs.metadata.columns)
        if isinstance(epochs.metadata, pd.DataFrame)
        else None
    )

    return EpochContext(
        epochs=epochs,
        sfreq=sfreq,
        ch_names=ch_names,
        modality_by_channel=modality_by_channel,
        metadata_cols=metadata_cols,
        index=index,
        n_epochs=n_epochs,
        n_times=n_times,
    )


def available_styles_by_modality(
    metadata_cols: Sequence[str] | None,
    modalities: Set[str],
    *,
    include_eeg_for_eog: bool = True,
) -> Dict[str, Set[str]]:
    """Return detected style names per modality with optional EEG→EOG merge."""

    eeg_styles = available_styles(metadata_cols, "eeg")
    out: Dict[str, Set[str]] = {}
    for mod in modalities:
        styles = available_styles(metadata_cols, mod)
        if include_eeg_for_eog and mod == "eog" and eeg_styles:
            styles = styles | eeg_styles
        out[mod] = styles
    return out


def get_metadata_row(epochs: mne.Epochs, ei: int) -> pd.Series:
    """Return per-epoch metadata row or an empty fallback series."""

    if isinstance(epochs.metadata, pd.DataFrame):
        return epochs.metadata.iloc[ei]
    return pd.Series(dtype=float)


def empty_feature_frame(index: pd.Index, columns: Sequence[str]) -> pd.DataFrame:
    """Return a typed empty output frame for feature extractors."""

    return pd.DataFrame(index=index, columns=list(columns), dtype=float)


# def frame_from_records(
#     records: list[dict[str, float]],
#     *,
#     index: pd.Index,
#     columns: Sequence[str] | None = None,
# ) -> pd.DataFrame:
#     """Build a DataFrame from epoch records with optional explicit columns."""
#
#     if columns is None:
#         return pd.DataFrame.from_records(records, index=index)
#     return pd.DataFrame.from_records(records, index=index, columns=list(columns))
