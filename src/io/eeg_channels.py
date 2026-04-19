"""EEG I/O helpers for loading channel configuration and raw FIF data."""

from __future__ import annotations

from pathlib import Path

import mne
import yaml


def load_brain_region_channels(yaml_path: Path) -> list[str]:
    """Return a flat list of EEG channel names from a brain-region YAML config."""
    with yaml_path.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    channels: list[str] = []
    for region_channels in config["eeg_regions"].values():
        channels.extend(region_channels)
    return channels


def load_raw_with_brain_channels(
    fif_path: Path,
    brain_channels: list[str],
) -> mne.io.BaseRaw:
    """Load a FIF file and retain only channels that appear in brain_channels."""
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    available = [ch for ch in brain_channels if ch in raw.ch_names]
    raw.pick(available)
    return raw


__all__ = [
    "load_brain_region_channels",
    "load_raw_with_brain_channels",
]
