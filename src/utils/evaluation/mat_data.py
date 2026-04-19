"""Utilities for working with MAT recordings in tutorials and evaluation flows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping

import mne
import numpy as np
import pandas as pd


def ensure_mat_file(path: Path, url: str) -> Path:
    """Download a MAT dataset once and return its local path."""

    from src.utils.download import download_once

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[download] {url} → {path}")
        download_once(url, path)
    return path


def load_raw_from_mat(path: Path, sfreq: float | None = None) -> mne.io.BaseRaw:
    """Load a MAT recording into an MNE ``Raw`` instance."""

    from src.utils.mat_edf import load_mat_to_mne

    raw = load_mat_to_mne(path.as_posix(), sfreq_default=sfreq)
    sampling_rate = float(raw.info.get("sfreq", np.nan))
    if not np.isfinite(sampling_rate):
        raise RuntimeError("Loaded MAT file is missing a valid sampling rate")
    return raw


def parse_channel_spec(spec: str) -> list[str]:
    """Convert ranges like ``"1-3"`` or ``"1,2,3"`` into channel names."""

    spec = spec.strip()
    if "-" in spec:
        start_str, end_str = spec.split("-", 1)
        start, end = int(start_str), int(end_str)
        if start > end:
            start, end = end, start
        indices = range(start, end + 1)
    else:
        indices = [int(part) for part in spec.replace(" ", "").split(",") if part]
    return [f"CH{idx}" for idx in indices]


def pick_channels(raw: mne.io.BaseRaw, channels: Iterable[str]) -> mne.io.BaseRaw:
    """Return a copy of ``raw`` containing only the requested channels."""

    channels = list(channels)
    missing = [ch for ch in channels if ch not in raw.ch_names]
    if missing:
        raise ValueError(f"Missing required channels: {missing}")

    to_drop = [ch for ch in raw.ch_names if ch not in channels]
    if not to_drop:
        return raw.copy()
    return raw.copy().drop_channels(to_drop)


def load_manual_annotations_csv(
    csv_path: Path,
    *,
    column_aliases: Mapping[str, tuple[str, ...]] | None = None,
) -> pd.DataFrame:
    """Load manual annotations (seconds) from a CSV file."""

    if not csv_path.exists():
        raise FileNotFoundError(f"Manual annotation CSV not found: {csv_path}")

    aliases = column_aliases or {
        "onset_sec": ("onset_sec", "onset"),
        "duration_sec": ("duration_sec", "duration"),
        "description": ("description", "label"),
    }

    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file {csv_path} has no header row")
        lower_map = {name.lower(): name for name in reader.fieldnames}

        def _resolve(key: str) -> str:
            for candidate in aliases[key]:
                lowered = candidate.lower()
                if lowered in lower_map:
                    return lower_map[lowered]
            raise KeyError(f"Missing columns {aliases[key]!r} in {csv_path}")

        onset_key = _resolve("onset_sec")
        duration_key = _resolve("duration_sec")
        desc_key = _resolve("description")

        rows = [
            {
                "onset_sec": float(row[onset_key]),
                "duration_sec": float(row[duration_key]),
                "description": str(row[desc_key]),
            }
            for row in reader
        ]

    df = pd.DataFrame(rows, columns=["onset_sec", "duration_sec", "description"])
    if df.empty:
        raise ValueError(f"Manual annotations CSV {csv_path} contains no rows")
    return df


def annotations_to_event_table(
    annotations: pd.DataFrame, sampling_rate_hz: float
) -> pd.DataFrame:
    """Convert onset/duration annotations into a 1-based blink interval table."""

    from . import similarity

    if sampling_rate_hz <= 0:
        raise ValueError("Sampling rate must be positive to build event table")

    onset_samples = np.rint(
        annotations["onset_sec"].to_numpy(dtype=float) * sampling_rate_hz
    ).astype(int)
    duration_samples = np.rint(
        annotations["duration_sec"].to_numpy(dtype=float) * sampling_rate_hz
    ).astype(int)
    duration_samples = np.maximum(duration_samples, 1)

    start_zero_based = np.maximum(onset_samples, 0)
    end_zero_based_exclusive = start_zero_based + duration_samples

    event_df = pd.DataFrame(
        {
            "start_blink": start_zero_based + 1,
            "end_blink": end_zero_based_exclusive,
        }
    )
    event_df = event_df.sort_values("start_blink", kind="mergesort", ignore_index=True)
    similarity.validate_event_table(event_df)
    return event_df


def dataframe_to_annotations(df: pd.DataFrame) -> mne.Annotations:
    """Convert an annotations DataFrame into :class:`mne.Annotations`."""

    return mne.Annotations(
        onset=df["onset_sec"].to_numpy(dtype=float),
        duration=df["duration_sec"].to_numpy(dtype=float),
        description=df["description"].astype(str).tolist(),
    )


def read_annotations_as_mne(csv_path: Path) -> mne.Annotations:
    """Convenience wrapper to load annotations CSV into MNE structure."""

    df = load_manual_annotations_csv(csv_path)
    return dataframe_to_annotations(df)


def save_annotations_csv(annotations: mne.Annotations, out_csv: Path) -> None:
    """Save annotations to a CSV file compatible with ``load_manual_annotations_csv``."""

    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["onset_sec", "duration_sec", "description"])
        for onset, duration, desc in zip(
            annotations.onset,
            annotations.duration,
            annotations.description,
            strict=False,
        ):
            writer.writerow([onset, duration, desc])
