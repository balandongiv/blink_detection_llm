"""Centralized dataset path and shared evaluation parameters.

Two modes:
- **dev**: internal Raja FIF + annotation CSV (not in repo)
- **batch**: public sample-data FIF + annotation CSV (in repo under ``sample_data/``)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# ── Shared evaluation parameters ──────────────────────────────────────────────
EPOCH_DURATION_S: float = 60.0
PEAK_SIDE_TOLERANCE_S: float = 0.01
FILTER_LOW: float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE: float | None = None


@dataclass(frozen=True)
class DatasetPaths:
    """Resolved FIF and annotation CSV paths for one dataset mode."""

    fif_path: Path
    csv_path: Path
    is_raw: bool = True
    """True if ``fif_path`` is a raw recording; False if it is already epoched."""


# ── Development dataset (internal Raja — not in repo) ─────────────────────────
DEV_DATASET = DatasetPaths(
    fif_path=Path(
        r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933"
        r"\seg_data_raw\eeg_eog_raw.fif"
    ),
    csv_path=Path(
        r"D:\dataset\drowsy_driving_raja\human_label_annotation\S1"
        r"\S01_20170519_043933\ear_eog.csv"
    ),
    is_raw=True,
)

# ── Batch dataset (public sample data — in repo) ──────────────────────────────
BATCH_DATASET = DatasetPaths(
    fif_path=REPO_ROOT / "sample_data" / "dev_epo.fif",
    csv_path=REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv",
    is_raw=False,  # already-epoched FIF
)

__all__ = [
    "BATCH_DATASET",
    "DEV_DATASET",
    "DatasetPaths",
    "EPOCH_DURATION_S",
    "FILTER_HIGH",
    "FILTER_LOW",
    "PEAK_SIDE_TOLERANCE_S",
    "REPO_ROOT",
    "RESAMPLE_RATE",
]
