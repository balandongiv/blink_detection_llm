"""Experiment 3 (Cao2018): epoch-duration sensitivity, best-channel groups from exp1.

Replaces the old exp3_epoch_duration.py / run_exp3_cao2018.py. For every epoch
duration in ``epoch_durations_s`` (experiment_script/setup/exp3_epoch_duration.yaml),
runs the complete Stage A->B->C pipeline (src/utils/channel_ablation_utils.py, the
same engine exp1 uses) on each channel-selection group in ``--groups`` (default:
the best channels/regions from exp1, per the yaml), for both the median and mean
Stage-B centre. Tests whether the proposed pipeline is stable under the epoch-
length choice, since blink physiology does not depend on it.

Configuration is read entirely from experiment_script/setup/exp3_epoch_duration.yaml
— no experiment parameter is hardcoded in this script.
Output CSVs go to runs/exp3_cao/ by default.

Resume support
--------------
Each session's rows (covering every epoch duration) are cached under
``<out-dir>/sessions/`` (see src/utils/session_sweep.py). Re-running the same
command skips sessions that already have a cached CSV; pass ``--overwrite`` to
force a full recompute.

Full sweep::

    python experiment_script/exp3_a_epoch_duration_cao2018.py --out-dir runs/exp3_cao

Quick smoke test::

    python experiment_script/exp3_a_epoch_duration_cao2018.py --max-sessions 1 --n-jobs 1
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Limit per-process BLAS/OpenMP threads so the process pool (--n-jobs) scales
# cleanly across CPUs without oversubscription.  Must run before numpy/mne import.
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.exp.exp3_epoch_duration_sweep import exp3_write_results, run_epoch_duration_session_sweep
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, load_exp_config
from src.utils.dataset_discovery import discover_cao_pairs
from src.utils.experiment_utils import csv_list as _csv_list, setup_tutorial_logging

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp3_epoch_duration.yaml")
_PATH_CFG = load_exp_config(EXP_SETUP_DIR / "exp_path.yaml")
_CAO = get_cao_paths()

CAO_REGION_YAML  = _CAO["brain_region_yaml"]
CAO_DATASET_ROOT = _CAO["dataset_root"]
DEFAULT_OUT_DIR  = REPO_ROOT / Path(_PATH_CFG["out_dirs"]["exp3"]["cao2018"])

EPOCH_DURATIONS_S          = list(_EXP_CFG["epoch_durations_s"])
REFERENCE_EPOCH_DURATION_S = float(_EXP_CFG["reference_epoch_duration_s"])

# This script is the authority for the sweep parameters — the shared worker in
# src/exp/exp3_epoch_duration_sweep.py takes these as explicit session_kwargs
# rather than reading the yaml itself.
SWEEP_SETTINGS = {
    "std_threshold":           float(_EXP_CFG["std_threshold"]),
    "filter_low":              float(_EXP_CFG["filter_low"]),
    "filter_high":             float(_EXP_CFG["filter_high"]),
    "resample_rate":           float(_EXP_CFG["resample_rate"]),
    "center_methods":          tuple(_EXP_CFG["center_methods"]),
    "autoreject_random_state": int(_EXP_CFG["autoreject_random_state"]),
}

DEFAULT_GROUPS = ",".join(_EXP_CFG["groups"]["cao2018"])


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                   help="Output directory (default: %(default)s).")
    p.add_argument("--overwrite", action="store_true",
                   help="Re-run sessions that already have a cached result CSV "
                        "(default: skip them and resume).")
    p.add_argument("--max-sessions", type=int, default=None,
                   help="Limit to the first N discovered sessions (None = all).")
    p.add_argument("--n-jobs", type=int, default=20,
                   help="Worker processes for the session sweep (default: %(default)s "
                        "— kept modest to avoid Windows handle exhaustion).")
    p.add_argument("--groups", type=_csv_list, default=DEFAULT_GROUPS,
                   help="Comma-separated channel-selection groups to sweep "
                        "(default from experiment_script/setup/exp3_epoch_duration.yaml: "
                        "%(default)s).")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    setup_tutorial_logging()

    pairs = discover_cao_pairs(CAO_DATASET_ROOT)
    if not pairs:
        print("No Cao2018 sessions found — check paths.yaml.")
        return

    logger.info("Cao2018 sessions discovered: %d", len(pairs))
    if args.max_sessions is not None:
        pairs = pairs[:args.max_sessions]
        logger.info("--max-sessions=%d → limiting to %d session(s)", args.max_sessions, len(pairs))

    groups_filter = set(args.groups) if args.groups else None
    session_kwargs = dict(
        region_yaml=CAO_REGION_YAML,
        epoch_durations_s=EPOCH_DURATIONS_S,
        **SWEEP_SETTINGS,
    )
    logger.info("groups_filter = %s", sorted(groups_filter) if groups_filter is not None else "all")
    logger.info("session_kwargs = %s", session_kwargs)
    logger.info("out_dir = %s  overwrite=%s  n_jobs=%s", args.out_dir, args.overwrite, args.n_jobs)

    out_dir: Path = args.out_dir
    all_metrics, errors = run_epoch_duration_session_sweep(
        pairs, out_dir,
        overwrite=args.overwrite, n_jobs=args.n_jobs,
        groups_filter=groups_filter, session_kwargs=session_kwargs,
    )

    exp3_write_results(
        out_dir=out_dir,
        dataset="cao2018",
        all_metrics=all_metrics,
        errors=errors,
        reference_epoch_duration_s=REFERENCE_EPOCH_DURATION_S,
        groups_run=groups_filter,
        n_sessions=len(pairs),
    )


if __name__ == "__main__":
    main()
