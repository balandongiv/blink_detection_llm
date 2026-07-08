"""Dataset discovery helpers: locate sessions with matching fif/csv pairs.

Import this module after REPO_ROOT has been added to sys.path.
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def _cao_yaml_status_is_complete(session_dir: Path) -> bool:
    """Return True if Cao2018Viewer.yaml exists and status == 'Complete'."""
    yaml_path = session_dir / "Cao2018Viewer.yaml"
    if not yaml_path.is_file():
        return False
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("status", "") == "Complete"


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
