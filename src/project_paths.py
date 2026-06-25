"""Load machine-specific dataset paths and per-experiment config from YAML files.

Machine paths live in ``paths.yaml`` at the repo root (git-ignored).
Copy ``paths.yaml.example`` to ``paths.yaml`` and edit for your machine.

Per-experiment parameters live in companion YAML files next to each script,
e.g. ``experiment_script/exp1_channel_selection_raja.yaml``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
_PATHS_YAML = REPO_ROOT / "paths.yaml"
EXP_SETUP_DIR = REPO_ROOT / "experiment_script" / "setup"


def load_paths(paths_yaml: Path | None = None) -> dict:
    """Load and return the raw paths.yaml dict."""
    p = paths_yaml or _PATHS_YAML
    if not p.exists():
        raise FileNotFoundError(
            f"paths.yaml not found at {p}.\n"
            "Copy paths.yaml.example to paths.yaml and fill in your local dataset paths."
        )
    with p.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_raja_paths(paths: dict | None = None) -> dict[str, Path]:
    """Return resolved Raja dataset paths.

    Keys: ``annotation_base``, ``processed_base``, ``brain_region_yaml``.
    """
    p = paths or load_paths()
    raja = p["raja"]
    return {
        "annotation_base": Path(raja["annotation_base"]),
        "processed_base": Path(raja["processed_base"]),
        "brain_region_yaml": (REPO_ROOT / raja["brain_region_yaml"]).resolve(),
    }


def get_cao_paths(paths: dict | None = None) -> dict[str, Path]:
    """Return resolved Cao2018 dataset paths.

    Keys: ``dataset_root``, ``brain_region_yaml``.
    """
    p = paths or load_paths()
    cao = p["cao2018"]
    return {
        "dataset_root": Path(cao["dataset_root"]),
        "brain_region_yaml": (REPO_ROOT / cao["brain_region_yaml"]).resolve(),
    }


def load_exp_config(exp_yaml: Path) -> dict:
    """Load per-experiment parameters from a companion YAML file."""
    if not exp_yaml.exists():
        raise FileNotFoundError(
            f"Experiment config not found: {exp_yaml}\n"
            "Each experiment script expects a companion .yaml file with the same stem."
        )
    with exp_yaml.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


__all__ = [
    "REPO_ROOT",
    "EXP_SETUP_DIR",
    "load_paths",
    "get_raja_paths",
    "get_cao_paths",
    "load_exp_config",
]
