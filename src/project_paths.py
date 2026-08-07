"""Load machine-specific dataset paths and per-experiment config from YAML files.

Machine paths live in ``paths.yaml`` at the repo root (git-ignored).
Copy ``paths.yaml.example`` to ``paths.yaml`` and edit for your machine.

Per-experiment parameters live in companion YAML files under
experiment_script/setup/, e.g. ``experiment_script/setup/exp1_channel_selection.yaml``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_vars(node, scope: dict):
    """Recursively substitute ``${key}`` in string values with scope[key].

    Lets a YAML file define one top-level scalar (e.g. ``out_dir``) and
    reference it from nested values (e.g. ``${out_dir}/exp1_channel_raja``)
    so there is a single place to change a shared path.
    """
    if isinstance(node, dict):
        return {k: _resolve_vars(v, scope) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_vars(v, scope) for v in node]
    if isinstance(node, str):
        def _sub(match: re.Match) -> str:
            key = match.group(1)
            if key not in scope:
                raise KeyError(f"Unknown variable '${{{key}}}' referenced in YAML (no top-level '{key}' key)")
            return str(scope[key])
        return _VAR_PATTERN.sub(_sub, node)
    return node

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
    """Load per-experiment parameters from a companion YAML file.

    If the ``BLINK_YAML_VARIANT`` environment variable is set (e.g. by
    experiment_script/_run_all_experiments.py for a std=3.0 re-run) and a
    sibling ``<stem>_<variant>.yaml`` exists next to *exp_yaml*, that variant
    is loaded instead — letting the orchestrator swap configs for every
    experiment script via one env var rather than patching script source.
    """
    variant = os.environ.get("BLINK_YAML_VARIANT")
    if variant:
        variant_yaml = exp_yaml.with_name(f"{exp_yaml.stem}_{variant}{exp_yaml.suffix}")
        if variant_yaml.exists():
            exp_yaml = variant_yaml

    if not exp_yaml.exists():
        raise FileNotFoundError(
            f"Experiment config not found: {exp_yaml}\n"
            "Each experiment script expects a companion .yaml file with the same stem."
        )
    with exp_yaml.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return _resolve_vars(cfg, cfg)


__all__ = [
    "REPO_ROOT",
    "EXP_SETUP_DIR",
    "load_paths",
    "get_raja_paths",
    "get_cao_paths",
    "load_exp_config",
]
