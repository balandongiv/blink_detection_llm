"""Single source of truth for *which* runs folder the pipeline reads/writes.

The whole pipeline keys off ONE environment variable, ``BLINK_RUNS_DIR``:

  * unset  -> the canonical manuscript folder ``runs_second_iteration`` (default;
              existing behaviour is unchanged).
  * set    -> that folder name, used by every experiment runner *and* every
              extraction script, so a fresh run stays internally consistent.

For a fresh "from factory" replication, do NOT write into
``runs_second_iteration`` (it backs the published manuscript). Instead mint a new
folder with :func:`make_fresh_runs_dir` (or run
``python experiment_script/init_replication.py``) and export ``BLINK_RUNS_DIR``.

This module is importable both as a sibling (``from runs_dir import ...`` when a
script is run directly) and as a package member
(``from experiment_script.runs_dir import ...``).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENV_VAR = "BLINK_RUNS_DIR"
CANONICAL = "runs_second_iteration"


def runs_dir_name(default: str = CANONICAL) -> str:
    """Folder *name* the pipeline should use (env override or default)."""
    return os.environ.get(ENV_VAR, default).strip() or default


def get_runs_dir(default: str = CANONICAL, *, create: bool = False) -> Path:
    """Absolute path to the runs folder (env override or default)."""
    p = REPO / runs_dir_name(default)
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def make_fresh_runs_dir(name: str | None = None, *, prefix: str = "runs_replica") -> Path:
    """Create a fresh runs folder for a from-scratch replication, with a warning.

    * ``name`` given  -> use that folder (a user-chosen fresh folder).
    * ``name`` None   -> auto-create ``<prefix>_<YYYYMMDD_HHMMSS>``.

    Never silently reuses the canonical manuscript folder; prints how to point the
    pipeline at the new folder via ``BLINK_RUNS_DIR``.
    """
    auto = name is None
    if auto:
        name = f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}"
    if name == CANONICAL:
        print(f"WARNING: '{CANONICAL}' is the canonical manuscript folder; refusing to "
              f"treat it as a fresh run. Choose another name.", file=sys.stderr)
        return REPO / name

    p = REPO / name
    not_empty = p.exists() and any(p.iterdir())
    p.mkdir(parents=True, exist_ok=True)

    bar = "=" * 72
    print(bar)
    print(f"WARNING: {'auto-created' if auto else 'using fresh'} runs folder  ->  {name}/")
    if not_empty:
        print(f"  CAUTION: '{name}/' already existed and is NOT empty; existing result")
        print(f"           files may be reused or overwritten.")
    print(f"  The canonical manuscript results in '{CANONICAL}/' were NOT touched.")
    print(f"  Point the ENTIRE pipeline (runners + extraction) at this folder by setting:")
    print(f"     bash/zsh   :  export {ENV_VAR}={name}")
    print(f"     PowerShell :  $env:{ENV_VAR}='{name}'")
    print(f"  Then run exp1..exp8, exp1_get_best_region_channel.py, and")
    print(f"  reproduce_manuscript.py build in that same shell.")
    print(bar)
    return p


__all__ = ["ENV_VAR", "CANONICAL", "REPO", "runs_dir_name", "get_runs_dir", "make_fresh_runs_dir"]
