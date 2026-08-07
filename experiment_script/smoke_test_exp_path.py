"""Smoke test: read experiment_script/setup/exp_path.yaml and create every out_dir.

Verifies that ${out_dir} interpolation resolves correctly end-to-end and that
each resulting path is creatable, without running any actual experiment.

Usage:
    python experiment_script/smoke_test_exp_path.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.project_paths import EXP_SETUP_DIR, load_exp_config

_PATHS_YAML = EXP_SETUP_DIR / "exp_path.yaml"


def main() -> None:
    print(f"[smoke_test_exp_path] loading: {_PATHS_YAML}")
    cfg = load_exp_config(_PATHS_YAML)

    out_dirs = cfg.get("out_dirs", {})
    if not out_dirs:
        raise SystemExit("No 'out_dirs' key found in exp_path.yaml")

    for exp_name, per_dataset in out_dirs.items():
        for dataset, rel_path in per_dataset.items():
            full_path = REPO_ROOT / Path(rel_path)
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  {exp_name}.{dataset}: {full_path}  [created/exists]")

    print("[smoke_test_exp_path] OK")


if __name__ == "__main__":
    main()
