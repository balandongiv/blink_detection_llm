"""Pipeline helpers and output types shared across multiple strategy packages.

These utilities were previously duplicated (with identical bodies) in
strategy_a/epoch_blink_pipeline.py, strategy_b/epoch_blink_pipeline_b.py,
and strategy_c/autoreject_utils.py.  Centralising them here removes those
copies and makes the shared contract explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

import mne
import numpy as np
import pandas as pd

from pyblinker.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.common.epoch_io import normalize_blink_table


@dataclass
class EpochBlinkDetectionOutput:
    """Structured output from the legacy six-step epoch-mode detector.

    Returned by Strategy A's ``run_epoch_blink_pipeline`` and Strategy B's
    ``run_epoch_blink_pipeline_mne``.
    """

    annotations: mne.Annotations
    channel: str | None
    n_good_blinks: int
    blink_table: pd.DataFrame
    fig_data: list[object]
    selected_channel: pd.DataFrame
    epochs: mne.Epochs
    valid_epoch_indices: list[int]


def empty_annotations() -> mne.Annotations:
    """Return an empty MNE Annotations object."""
    return mne.Annotations(onset=[], duration=[], description=[])


def finalize_blink_table(
    blink_table: pd.DataFrame,
    *,
    epochs: mne.Epochs,
    prepared: PreparedEpochDetectionInput,
) -> pd.DataFrame:
    """Normalize and enrich a mapped blink table with epoch-selection metadata.

    Adds ``epoch_selection`` (the MNE selection index) and, when available,
    ``epoch_id`` from ``epochs.metadata``.
    """
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


def build_epoch_boundaries(
    valid_epoch_count: int,
    epoch_length_samples: int,
) -> list[tuple[int, int]]:
    """Return concatenated-signal sample boundaries for each valid epoch.

    Parameters
    ----------
    valid_epoch_count:
        Number of valid epochs (``len(valid_epoch_indices)``).
    epoch_length_samples:
        Number of samples in one epoch.

    Returns
    -------
    list[tuple[int, int]]
        List of ``(start_sample, end_sample)`` pairs, one per valid epoch.
    """
    return [
        (
            idx * epoch_length_samples,
            (idx + 1) * epoch_length_samples,
        )
        for idx in range(valid_epoch_count)
    ]


def build_signal_by_epoch(
    prepared: PreparedEpochDetectionInput,
    ch_idx: int,
) -> dict[int, np.ndarray]:
    """Build the ``signal_by_epoch`` dict for one channel.

    Maps every epoch index (0 … n_epochs-1) to its 1-D filtered signal array.
    """
    return {
        epoch_idx: prepared.data[epoch_idx, ch_idx, :].astype(float)
        for epoch_idx in range(prepared.data.shape[0])
    }


__all__ = [
    "EpochBlinkDetectionOutput",
    "build_epoch_boundaries",
    "build_signal_by_epoch",
    "empty_annotations",
    "finalize_blink_table",
]
