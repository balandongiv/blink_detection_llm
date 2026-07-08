"""Stage-A channel-group selection gate for downstream experiments (exp2..exp8).

Experiment 1 (channel selection) decides which Stage-A channel group is best; the
winner is recorded in ``channel_group_selection.yaml`` at the repo root. The
downstream experiments call :func:`apply_stage_a_channel_group` right after
preparing a session, which subsets the prepared montage to the approved group.

The YAML is a HARD-APPROVAL GATE: the default group is ``"all"`` (no change), and
selecting any other group requires ``approved_by`` to be set in the YAML — otherwise
:func:`load_group_for_dataset` raises, so an unapproved group can never silently
take effect. ``exp1_channel_selection_*`` deliberately does NOT call this (it must
see the full montage to compare every group).
"""

from __future__ import annotations

import logging
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from src.utils.channel_ablation_utils import build_selection_groups
from src.common.epoch_input import PreparedEpochDetectionInput
from src.io.eeg_channels import load_brain_region_map
from src.project_paths import get_cao_paths, get_raja_paths

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANNEL_GROUP_YAML = REPO_ROOT / "channel_group_selection.yaml"

# Region config used to resolve a group name to actual channels, per dataset.
_REGION_YAML_BY_DATASET = {
    "raja": get_raja_paths()["brain_region_yaml"],
    "cao2018": get_cao_paths()["brain_region_yaml"],
}

# Track datasets already warned about (so the all-channels warning fires once each).
_WARNED_ALL_CHANNELS: set[str] = set()


@lru_cache(maxsize=4)
def _load_config(path_str: str) -> dict:
    path = Path(path_str)
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_group_for_dataset(dataset: str, *, yaml_path: Path = CHANNEL_GROUP_YAML) -> str:
    """Return the approved Stage-A group for *dataset* (default ``"all"``).

    Raises ``ValueError`` if a non-``"all"`` group is selected without
    ``approved_by`` being filled in the YAML (the hard-approval gate).
    """
    cfg = _load_config(str(yaml_path))
    group = str((cfg.get("stage_a_channel_group") or {}).get(dataset, "all"))
    if group != "all" and not cfg.get("approved_by"):
        raise ValueError(
            f"{yaml_path.name} selects Stage-A group '{group}' for dataset "
            f"'{dataset}', but 'approved_by' is empty. A non-'all' group requires "
            f"explicit human/agent approval — set 'approved_by' and 'approved_date'."
        )
    return group


def apply_stage_a_channel_group(
    prepared: PreparedEpochDetectionInput,
    dataset: str,
    *,
    yaml_path: Path = CHANNEL_GROUP_YAML,
) -> PreparedEpochDetectionInput:
    """Subset *prepared* to the approved Stage-A group for *dataset*.

    Returns *prepared* unchanged when the group is ``"all"`` or the dataset has no
    region config (e.g. murat2018), so the default is a true no-op.
    """
    group = load_group_for_dataset(dataset, yaml_path=yaml_path)
    region_yaml = _REGION_YAML_BY_DATASET.get(dataset)
    if group == "all" or region_yaml is None:
        if dataset not in _WARNED_ALL_CHANNELS:
            _WARNED_ALL_CHANNELS.add(dataset)
            logger.warning(
                "Stage-A is using ALL channels for '%s' — no channel group is selected in "
                "%s (group='all'). Run exp1 (channel selection), then record the winning "
                "group and 'approved_by' in %s to restrict Stage A to the chosen montage.",
                dataset, yaml_path.name, yaml_path.name,
            )
        return prepared

    channel_names = list(prepared.channel_names)
    groups = build_selection_groups(
        load_brain_region_map(region_yaml), channel_names, include_single_frontal=True
    )
    if group not in groups:
        raise ValueError(
            f"Stage-A group '{group}' not available for {dataset}. "
            f"Available: {sorted(groups)}"
        )
    keep = set(groups[group])
    idx = np.array([i for i, ch in enumerate(channel_names) if ch in keep], dtype=int)
    if idx.size == 0:
        raise ValueError(f"Stage-A group '{group}' resolved to 0 channels for {dataset}.")
    logger.info("Stage-A channel group '%s' (%s) → %d/%d channels",
                group, dataset, idx.size, len(channel_names))
    return replace(
        prepared,
        data=prepared.data[:, idx, :],
        channel_names=tuple(channel_names[i] for i in idx),
    )


__all__ = ["CHANNEL_GROUP_YAML", "load_group_for_dataset", "apply_stage_a_channel_group"]
