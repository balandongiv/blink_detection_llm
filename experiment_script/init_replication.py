"""Initialise a fresh "from factory" replication run.

Some users replicate the whole study from scratch. They must NOT write into the
canonical ``runs_second_iteration/`` folder (it backs the published manuscript).
This script creates a fresh runs folder instead and tells you how to point the
pipeline at it (via the ``BLINK_RUNS_DIR`` env var).

Usage (from repo root, inside conda env double_threshold_algo):

  python experiment_script/init_replication.py my_run
        -> use a user-chosen fresh folder 'my_run/'

  python experiment_script/init_replication.py
        -> auto-create 'runs_replica_<timestamp>/' (with a warning)

After running, EXPORT the printed variable in the same shell, then proceed with
Stage 1 of REPLICATION_GUIDE.md (run_exp1_*.py, ...). Without the export, the
pipeline falls back to the canonical 'runs_second_iteration/'.
"""
from __future__ import annotations

import sys

try:
    from runs_dir import make_fresh_runs_dir
except ImportError:  # imported as a package member
    from experiment_script.runs_dir import make_fresh_runs_dir


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else None
    make_fresh_runs_dir(name)


if __name__ == "__main__":
    main()
