"""Annotation-to-epoch normalization and absolute-time enrichment utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_annotation_as_reference(
    csv_path: Path,
    epoch_duration: float,
) -> pd.DataFrame:
    """Convert a CSV of absolute-onset annotations into epoch-relative blink references.

    The CSV must have ``onset`` and ``duration`` columns (in seconds).
    Returns a DataFrame with columns: epoch_index, blink_onset, blink_duration.
    """
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    rows: list[dict] = []
    for _, row in df.iterrows():
        onset_abs = float(row["onset"])
        duration = float(row["duration"])
        epoch_index = int(onset_abs // epoch_duration)
        rows.append(
            {
                "epoch_index": epoch_index,
                "blink_onset": onset_abs - epoch_index * epoch_duration,
                "blink_duration": duration,
            }
        )
    return pd.DataFrame(rows, columns=["epoch_index", "blink_onset", "blink_duration"])


def enrich_absolute_times(frame: pd.DataFrame, epoch_duration: float) -> pd.DataFrame:
    """Add ``absolute_onset_s`` and ``absolute_offset_s`` columns from epoch-relative timings.

    Requires ``epoch_index``, ``blink_onset``, and ``blink_duration`` columns.
    These enriched columns are expected by :func:`~pyblinker.analysis.false_negative_analysis.collect_false_negatives`.
    """
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    out["absolute_onset_s"] = (
        out["epoch_index"].astype(float) * epoch_duration
        + out["blink_onset"].astype(float)
    )
    out["absolute_offset_s"] = out["absolute_onset_s"] + out["blink_duration"].astype(float)
    return out


__all__ = [
    "enrich_absolute_times",
    "load_annotation_as_reference",
]
