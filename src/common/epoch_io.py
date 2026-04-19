"""Metadata and long-table export helpers for epoch-mode detection."""

from __future__ import annotations

import json

import pandas as pd


def normalize_blink_table(blink_table: pd.DataFrame) -> pd.DataFrame:
    """Return a consistently ordered long-form blink table."""

    if blink_table.empty:
        return blink_table.copy().reset_index(drop=True)
    sort_cols = [col for col in ("epoch_index", "blink_onset", "blink_duration") if col in blink_table.columns]
    return blink_table.sort_values(sort_cols).reset_index(drop=True)


def _json_float_list(values) -> str:
    payload = [float(value) for value in values]
    return json.dumps(payload, separators=(",", ":"))


def attach_epoch_blink_metadata(
    epochs,
    blink_table: pd.DataFrame,
    candidate_channel: str | None,
    valid_epoch_indices: list[int],
) -> pd.DataFrame:
    """Attach epoch-level blink outputs in JSON-list form."""

    n_epochs = len(epochs)
    metadata = (
        epochs.metadata.copy().reset_index(drop=True)
        if isinstance(epochs.metadata, pd.DataFrame)
        else pd.DataFrame(index=range(n_epochs))
    )
    metadata = metadata.reindex(range(n_epochs)).reset_index(drop=True)

    metadata["blink_onset"] = "[]"
    metadata["blink_duration"] = "[]"
    metadata["blink_count"] = 0
    metadata["candidate_channel"] = candidate_channel
    metadata["valid_epoch"] = [idx in set(valid_epoch_indices) for idx in range(n_epochs)]

    if not blink_table.empty:
        for epoch_index, group in blink_table.groupby("epoch_index", sort=True):
            ordered = group.sort_values("blink_onset")
            metadata.at[int(epoch_index), "blink_onset"] = _json_float_list(
                ordered["blink_onset"].tolist()
            )
            metadata.at[int(epoch_index), "blink_duration"] = _json_float_list(
                ordered["blink_duration"].tolist()
            )
            metadata.at[int(epoch_index), "blink_count"] = int(len(ordered))

    epochs.metadata = metadata
    return metadata


__all__ = ["attach_epoch_blink_metadata", "normalize_blink_table"]
