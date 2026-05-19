"""Helper utilities for preparing sample evaluation datasets."""

from __future__ import annotations

from pathlib import Path

import mne
from mne.export import export_raw

__all__ = ["ensure_edf_file"]


def ensure_edf_file(edf_path: Path) -> Path:
    """Ensure the tutorial EDF file exists, converting from MNE sample data if needed."""
    if edf_path.exists():
        return edf_path

    print("[setup] EDF file missing; converting from MNE sample dataset")
    sample_data_folder = Path(mne.datasets.sample.data_path())
    raw_file = sample_data_folder / "MEG" / "sample" / "sample_audvis_filt-0-40_raw.fif"
    if not raw_file.exists():
        raise FileNotFoundError(f"Sample FIF file not found: {raw_file}")

    edf_path.parent.mkdir(parents=True, exist_ok=True)
    raw = mne.io.read_raw_fif(raw_file.as_posix(), preload=True, verbose="ERROR")
    export_raw(edf_path.as_posix(), raw, fmt="edf", physical_range="auto")
    print(f"[setup] Exported EDF to {edf_path}")
    return edf_path
