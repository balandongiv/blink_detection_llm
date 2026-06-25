"""Shared utilities for tutorial strategy comparison and experiment scripts.

Import this module from tutorial scripts after REPO_ROOT has been added to sys.path.
"""
from __future__ import annotations

import logging
from functools import partial
from pathlib import Path

import mne
import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]


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
    """Configure basic console logging for tutorial scripts."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
        force=True,  # ensure logs show up even if another library configured logging earlier
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _murat_yaml_status_is_completed(subject_dir: Path) -> bool:
    """Return True if Murat2018Viewer.yaml exists and status == 'Completed'."""
    yaml_path = subject_dir / "Murat2018Viewer.yaml"
    if not yaml_path.is_file():
        return False
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("status", "") == "Completed"


def _cao_yaml_status_is_complete(session_dir: Path) -> bool:
    """Return True if Cao2018Viewer.yaml exists and status == 'Complete'."""
    yaml_path = session_dir / "Cao2018Viewer.yaml"
    if not yaml_path.is_file():
        return False
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("status", "") == "Complete"


# ---------------------------------------------------------------------------
# Dataset discovery
# ---------------------------------------------------------------------------

def discover_raja_pairs(
    annotation_base_dir: Path,
    processed_base_dir: Path,
) -> list[dict]:
    """Return Raja sessions with VideoFrameViewers.yaml status == 'complete_eeg'.

    Returns dicts with keys: dataset, name, fif, csv.
    """
    pairs: list[dict] = []
    for yaml_path in sorted(annotation_base_dir.rglob("VideoFrameViewers.yaml")):
        with yaml_path.open("r", encoding="utf-8") as fh:
            info = yaml.safe_load(fh)
        if (info or {}).get("status") != "complete_eeg":
            continue
        session_dir = yaml_path.parent
        rel = session_dir.relative_to(annotation_base_dir)
        csv_path = session_dir / "ear_eog.csv"
        fif_path = processed_base_dir / rel / "seg_data_raw" / "eeg_eog_raw.fif"
        if not csv_path.exists():
            logger.debug("skip — CSV not found: %s", csv_path)
            continue
        if not fif_path.exists():
            logger.debug("skip — FIF not found: %s", fif_path)
            continue
        epoch_health = session_dir / "epoch_health.csv"
        pairs.append({
            "dataset":      "raja",
            "name":         str(rel).replace("\\", "/"),
            "fif":          fif_path,
            "csv":          csv_path,
            "epoch_health": epoch_health if epoch_health.is_file() else None,
        })
    return pairs


def discover_murat_pairs(
    dataset_root: Path,
    use_yaml_filter: bool = False,
) -> list[dict]:
    """Return murat_2018 subjects that have both <id>.fif and <id>.csv.

    When *use_yaml_filter* is True, additionally requires that
    Murat2018Viewer.yaml reports ``status: Completed``.

    Returns dicts with keys: dataset, name, fif, csv.
    """
    pairs: list[dict] = []
    skipped_yaml: list[str] = []
    for subject_dir in sorted(dataset_root.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name
        fif = subject_dir / f"{sid}.fif"
        csv = subject_dir / f"{sid}.csv"
        if not (fif.is_file() and csv.is_file()):
            continue
        if use_yaml_filter and not _murat_yaml_status_is_completed(subject_dir):
            skipped_yaml.append(sid)
            continue
        pairs.append({
            "dataset": "murat2018",
            "name":    sid,
            "fif":     fif,
            "csv":     csv,
        })
    if skipped_yaml:
        logger.info(
            "[yaml-filter] skipped %d subject(s) with status != Completed: %s",
            len(skipped_yaml),
            ", ".join(skipped_yaml),
        )
    return pairs


def discover_cao_pairs(
    dataset_root: Path,
    use_yaml_filter: bool = True,
) -> list[dict]:
    """Return Cao2018 Complete sessions with matching fif/csv files.

    Directory layout is ``dataset_root/<subject_id>/<session_id>/`` and data
    files are named ``<subject_id_lower>_<session_id>.fif/.csv``.  Returned
    dicts include ``epoch_health`` when ``epoch_health.csv`` is present.
    """
    pairs: list[dict] = []
    skipped_status: list[str] = []
    skipped_missing: list[str] = []

    for subject_dir in sorted(dataset_root.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name
        sid_lower = sid.lower()
        for session_dir in sorted(subject_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            session_id = session_dir.name
            label = f"{sid}/{session_id}"

            if use_yaml_filter and not _cao_yaml_status_is_complete(session_dir):
                skipped_status.append(label)
                continue

            fif = session_dir / f"{sid_lower}_{session_id}.fif"
            csv = session_dir / f"{sid_lower}_{session_id}.csv"
            if not (fif.is_file() and csv.is_file()):
                skipped_missing.append(label)
                continue

            epoch_health = session_dir / "epoch_health.csv"
            pairs.append({
                "dataset":      "cao2018",
                "name":         label,
                "fif":          fif,
                "csv":          csv,
                "epoch_health": epoch_health if epoch_health.is_file() else None,
            })

    if skipped_status:
        logger.info(
            "[yaml-filter] skipped %d Cao2018 session(s) with status != Complete: %s",
            len(skipped_status),
            ", ".join(skipped_status),
        )
    if skipped_missing:
        logger.info(
            "[files] skipped %d Cao2018 session(s) missing fif or csv: %s",
            len(skipped_missing),
            ", ".join(skipped_missing),
        )
    return pairs


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


def load_murat_raw(fif_path: Path) -> mne.io.BaseRaw:
    """Load a murat_2018 .fif file (all channels)."""
    return mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")


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
        # "murat2018": load_murat_raw,
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
    Raja/Murat annotations use the standard loader.
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


def _event_peak_time(row, epoch_signal: np.ndarray, sfreq: float) -> float:
    onset_s = float(row["blink_onset"])
    duration_s = float(row["blink_duration"])
    start_samp = int(round(onset_s * sfreq))
    end_samp = int(round((onset_s + duration_s) * sfreq))
    start_samp = max(0, min(start_samp, len(epoch_signal) - 1))
    end_samp = max(start_samp + 1, min(end_samp, len(epoch_signal)))
    event_signal = epoch_signal[start_samp:end_samp]
    peak_local = int(np.argmax(np.abs(event_signal)))
    return (start_samp + peak_local) / float(sfreq)


def _events_overlap(left, right) -> bool:
    left_start = float(left["blink_onset"])
    left_end = left_start + float(left["blink_duration"])
    right_start = float(right["blink_onset"])
    right_end = right_start + float(right["blink_duration"])
    return max(left_start, right_start) < min(left_end, right_end)


def match_events(
    predicted,
    ground_truth,
    signal_by_epoch: dict,
    sfreq: float,
    peak_side_tolerance_s: float | None = None,
) -> tuple[list[int], list[int], list[int]]:
    """Greedily match predicted and ground-truth events within each epoch."""
    predicted = predicted.reset_index(drop=True)
    ground_truth = ground_truth.reset_index(drop=True)

    matched_pred: set[int] = set()
    matched_gt: set[int] = set()

    epoch_indices = sorted(
        set(predicted["epoch_index"].tolist()) | set(ground_truth["epoch_index"].tolist())
    )

    for epoch_index in epoch_indices:
        pred_group = predicted[predicted["epoch_index"] == epoch_index]
        gt_group = ground_truth[ground_truth["epoch_index"] == epoch_index]
        unmatched_gt = set(gt_group.index.tolist())
        epoch_signal = np.asarray(signal_by_epoch.get(int(epoch_index), []), dtype=float)

        for pred_index, pred_row in pred_group.sort_values("blink_onset").iterrows():
            best_gt_index = None
            for gt_index in list(unmatched_gt):
                gt_row = gt_group.loc[gt_index]
                if not _events_overlap(pred_row, gt_row):
                    continue
                if peak_side_tolerance_s is not None and len(epoch_signal) > 0:
                    pred_peak = _event_peak_time(pred_row, epoch_signal, sfreq)
                    gt_peak = _event_peak_time(gt_row, epoch_signal, sfreq)
                    if abs(pred_peak - gt_peak) > peak_side_tolerance_s:
                        continue
                best_gt_index = gt_index
                break
            if best_gt_index is not None:
                matched_pred.add(pred_index)
                matched_gt.add(best_gt_index)
                unmatched_gt.remove(best_gt_index)

    tp_pred = list(matched_pred)
    fp_pred = [i for i in predicted.index if i not in matched_pred]
    fn_gt = [i for i in ground_truth.index if i not in matched_gt]
    return tp_pred, fp_pred, fn_gt
