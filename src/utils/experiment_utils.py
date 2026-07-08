"""Shared utilities for experiment scripts (formerly tutorial/tutorial_utils.py).

Import this module after REPO_ROOT has been added to sys.path.
"""
from __future__ import annotations

import csv
import logging
from functools import partial
from pathlib import Path

import mne
import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_default_region_yamls() -> tuple[Path, Path]:
    """Load brain-region YAML paths from paths.yaml; fall back to repo-relative defaults."""
    try:
        from src.project_paths import get_raja_paths, get_cao_paths
        return (
            get_raja_paths()["brain_region_yaml"],
            get_cao_paths()["brain_region_yaml"],
        )
    except FileNotFoundError:
        return (
            REPO_ROOT / "brain_region_raja.yaml",
            REPO_ROOT / "brain_region_cao2018.yaml",
        )


DEFAULT_RAJA_REGION_YAML, DEFAULT_CAO_REGION_YAML = _load_default_region_yamls()


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_tutorial_logging(level: int = logging.INFO) -> None:
    """Configure basic console logging for tutorial/experiment scripts."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
        force=True,  # ensure logs show up even if another library configured logging earlier
    )


def log_run_config(dest_logger: logging.Logger, args, **extra) -> None:
    """Log every parsed CLI argument (and any extra derived config) at INFO level.

    Called right after ``argparse.parse_args()`` so the exact configuration of a
    run — every flag, whether explicitly passed or defaulted — is always visible
    in the log, not just the handful of values a script happens to print later.
    """
    dest_logger.info("Run configuration:")
    for key, value in vars(args).items():
        dest_logger.info("  --%-18s = %r", key.replace("_", "-"), value)
    for key, value in extra.items():
        dest_logger.info("  %-20s = %r", key, value)


# ---------------------------------------------------------------------------
# Valid-epoch indices (health-based screening)
# ---------------------------------------------------------------------------

def get_valid_cao_epoch_indices(
    epoch_health_path: Path | None,
    epoch_duration_s: float,
    n_epochs: int,
    *,
    health_drop_threshold: int = 3,
) -> list[int]:
    """Return Cao2018 valid analysis epochs from 30s epoch_health.csv.

    An analysis epoch is dropped if any overlapping 30s health sub-epoch has
    health <= ``health_drop_threshold``. Missing health files fall back to all
    epochs, matching tutorial 22.
    """
    if epoch_health_path is None or not epoch_health_path.is_file():
        return list(range(n_epochs))

    df = pd.read_csv(epoch_health_path)
    required = {"epoch_start_s", "epoch_end_s", "health"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"epoch_health.csv missing columns: {missing}")

    df["health"] = pd.to_numeric(df["health"], errors="coerce")
    valid: list[int] = []
    for i in range(n_epochs):
        epoch_start = i * float(epoch_duration_s)
        epoch_end = (i + 1) * float(epoch_duration_s)
        overlapping = df[
            (df["epoch_start_s"] < epoch_end) & (df["epoch_end_s"] > epoch_start)
        ]
        if overlapping.empty or (overlapping["health"] > health_drop_threshold).all():
            valid.append(i)
    return valid


# ---------------------------------------------------------------------------
# Raw data loaders
# ---------------------------------------------------------------------------

def load_raja_raw(fif_path: Path, brain_region_yaml: Path) -> mne.io.BaseRaw:
    """Load a Raja-dataset .fif file, selecting brain-region channels."""
    from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
    brain_channels = load_brain_region_channels(brain_region_yaml)
    return load_raw_with_brain_channels(fif_path, brain_channels)


def load_cao_raw(fif_path: Path, brain_region_yaml: Path | None = None) -> mne.io.BaseRaw:
    """Load a Cao2018 .fif file.

    When *brain_region_yaml* is given, only the resolved brain-region channels
    are retained (the channel-selection refactor); when ``None`` the full
    recording is returned (legacy behaviour used by tutorial 22).
    """
    if brain_region_yaml is None:
        return mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
    brain_channels = load_brain_region_channels(brain_region_yaml)
    return load_raw_with_brain_channels(fif_path, brain_channels)


def make_dataset_loaders(
    raja_region_yaml: Path | None = None,
    cao_region_yaml: Path | None = None,
) -> dict:
    """Return ``{dataset_name: load_fn}`` for supported datasets.

    Each loader accepts a single *fif_path* and returns an ``mne.io.BaseRaw``.

    Parameters
    ----------
    raja_region_yaml:
        Brain-region config for the Raja loader.  Defaults to
        :data:`DEFAULT_RAJA_REGION_YAML`.  (Legacy single-positional callers that
        pass the old ``brain_region.yaml`` still work via channel-name
        resolution.)
    cao_region_yaml:
        Brain-region config for the Cao2018 loader.  ``None`` keeps the legacy
        all-channel behaviour; pass :data:`DEFAULT_CAO_REGION_YAML` to restrict
        Cao2018 detection to its blink-region channels.
    """
    raja_region_yaml = raja_region_yaml or DEFAULT_RAJA_REGION_YAML
    return {
        "raja":      partial(load_raja_raw, brain_region_yaml=raja_region_yaml),
        "cao2018":   partial(load_cao_raw, brain_region_yaml=cao_region_yaml),
    }


# ---------------------------------------------------------------------------
# Per-pair valid-epoch indices and ground-truth annotations
# ---------------------------------------------------------------------------

def valid_epoch_indices_for_pair(
    pair: dict,
    epochs: mne.Epochs,
    epoch_duration_s: float,
) -> list[int]:
    """Return valid (non-dropped) epoch indices for *pair*.

    When ``epoch_health`` is present in the pair dict (cao2018 or raja), epochs
    are filtered by the health CSV.  Otherwise falls back to the generic
    flat-epoch validity check.
    """
    from src.common.bad_epochs import get_valid_epoch_indices
    if pair.get("epoch_health"):
        return get_valid_cao_epoch_indices(
            pair["epoch_health"],
            epoch_duration_s,
            len(epochs),
        )
    if pair["dataset"] == "cao2018":
        return get_valid_cao_epoch_indices(None, epoch_duration_s, len(epochs))
    return get_valid_epoch_indices(epochs)


def load_gt_annotations_for_pair(
    pair: dict,
    epoch_duration_s: float,
    valid_epoch_indices: list[int] | None = None,
):
    """Load per-dataset ground-truth blink annotations for the event evaluator.

    Cao2018 annotations are restricted to *valid_epoch_indices* (when supplied)
    so that blinks inside health-dropped epochs do not inflate false negatives;
    Raja annotations use the standard loader.
    """
    from blink_evaluation import (
        enrich_absolute_times,
        load_annotation_as_reference,
        load_ground_truth_annotations,
    )
    from blink_evaluation.io import dataframe_to_annotations

    if pair["dataset"] != "cao2018":
        return load_ground_truth_annotations(pair["csv"], epoch_duration_s)

    ground_truth_raw = load_annotation_as_reference(pair["csv"], epoch_duration_s)
    if valid_epoch_indices is not None:
        ground_truth_raw = ground_truth_raw[
            ground_truth_raw["epoch_index"].isin(valid_epoch_indices)
        ].reset_index(drop=True)
    ground_truth_df = enrich_absolute_times(ground_truth_raw, epoch_duration_s)
    return dataframe_to_annotations(ground_truth_df)


# ---------------------------------------------------------------------------
# Waveform extraction (morphological analysis)
# ---------------------------------------------------------------------------

def extract_window(
    signal_by_epoch: dict,
    epoch_index: int,
    onset_s: float,
    duration_s: float,
    sfreq: float,
    window_s: float,
) -> np.ndarray | None:
    """Extract a symmetric window centred on the peak of a blink event.

    Returns a 1D array of length ``2 * int(window_s * sfreq)``, or None if
    the epoch signal is unavailable or the window falls outside the signal.
    """
    epoch_signal = signal_by_epoch.get(int(epoch_index))
    if epoch_signal is None or len(epoch_signal) == 0:
        return None

    start_samp = int(round(onset_s * sfreq))
    end_samp   = int(round((onset_s + duration_s) * sfreq))
    start_samp = max(0, min(start_samp, len(epoch_signal) - 1))
    end_samp   = max(start_samp, min(end_samp, len(epoch_signal)))

    if end_samp <= start_samp:
        return None

    event_signal = epoch_signal[start_samp:end_samp]
    peak_local   = int(np.argmax(np.abs(event_signal)))
    peak_samp    = start_samp + peak_local

    half      = int(round(window_s * sfreq))
    win_start = peak_samp - half
    win_end   = peak_samp + half

    if win_start < 0 or win_end > len(epoch_signal):
        return None
    return epoch_signal[win_start:win_end].copy()


# ---------------------------------------------------------------------------
# Small shared helpers duplicated across experiment_script/exp*.py scripts
# ---------------------------------------------------------------------------

def csv_list(value: str) -> tuple[str, ...]:
    """Parse a comma-separated CLI argument into a tuple of trimmed strings."""
    return tuple(x.strip() for x in value.split(",") if x.strip())


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write *rows* (list of flat dicts, common keys) to *path* as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
