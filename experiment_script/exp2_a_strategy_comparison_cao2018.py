"""Experiment 2 (Cao2018): per-channel strategy-comparison sweep, all_channel gate.

Replaces the old run_exp2_cao2018.py. Compares the same four conditions defined in
src/exp/exp2_strategy_conditions.py (BLINKER-concat, MNE-annot, Proposed-Mean, Proposed-Med), on the
same "all_channel" gate (all 32 EEG channels) recorded in
channel_group_selection.yaml — but reports every individual channel's metrics
(not just the session's best channel), which is what feeds
update_exp2_latex.py's per-channel manuscript table. ``--groups`` can widen the
sweep to other channel-selection groups if needed.

Configuration is read from experiment_script/setup/exp2_strategy_comparison.yaml.
Output CSVs go to runs/exp2_cao/ by default.

Resume support
--------------
Each session's rows are cached under ``<out-dir>/sessions/`` (see
src/utils/session_sweep.py). Re-running the same command skips sessions that
already have a cached CSV; pass ``--overwrite`` to force a full recompute.

Full sweep::

    python experiment_script/exp2_a_strategy_comparison_cao2018.py --out-dir runs/exp2_cao

Quick smoke test::

    python experiment_script/exp2_a_strategy_comparison_cao2018.py --max-sessions 1 --n-jobs 1
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

from src.exp.exp2_channel_group_sweep import exp2_write_results, run_strategy_comparison_session_sweep
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, load_exp_config
from src.utils.dataset_discovery import discover_cao_pairs
from src.utils.experiment_utils import csv_list as _csv_list, setup_tutorial_logging

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp2_strategy_comparison.yaml")
_CAO = get_cao_paths()

CAO_REGION_YAML  = _CAO["brain_region_yaml"]
CAO_DATASET_ROOT = _CAO["dataset_root"]
EPOCH_DURATION_S = float(_EXP_CFG.get("epoch_duration_s", 30.0))
FILTER_LOW       = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = int(_EXP_CFG.get("resample_rate", 100))
DEFAULT_OUT_DIR  = REPO_ROOT / "runs" / "exp2_cao"

# all_channel = every EEG channel (32 for Cao2018), matching channel_group_selection.yaml's
# gate so exp2 stays on the same channel set as exp1/exp2's other scripts.
DEFAULT_GROUPS = "all_channel"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                   help="Output directory (default: %(default)s).")
    p.add_argument("--overwrite", action="store_true",
                   help="Re-run sessions that already have a cached result CSV "
                        "(default: skip them and resume).")
    p.add_argument("--max-sessions", type=int, default=5,
                   help="Limit to the first N discovered sessions (None = all).")
    p.add_argument("--n-jobs", type=int, default=5,
                   help="Worker processes for the session sweep (default: %(default)s "
                        "— kept modest to avoid Windows handle exhaustion).")
    p.add_argument("--groups", type=_csv_list, default=DEFAULT_GROUPS,
                   help="Comma-separated channel-selection groups to sweep "
                        "(default: all_channel — all 32 EEG channels, per "
                        "channel_group_selection.yaml).")
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
        epoch_duration_s=float(args.epoch_duration_s),
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    logger.info("groups_filter = %s", sorted(groups_filter) if groups_filter is not None else "all")
    logger.info("session_kwargs = %s", session_kwargs)
    logger.info("out_dir = %s  overwrite=%s  n_jobs=%s", args.out_dir, args.overwrite, args.n_jobs)

    out_dir: Path = args.out_dir
    all_metrics, errors = run_strategy_comparison_session_sweep(
        pairs, out_dir,
        overwrite=args.overwrite, n_jobs=args.n_jobs,
        groups_filter=groups_filter, session_kwargs=session_kwargs,
    )

    exp2_write_results(
        out_dir=out_dir,
        dataset="cao2018",
        all_metrics=all_metrics,
        errors=errors,
        epoch_duration_s=float(args.epoch_duration_s),
        groups_run=groups_filter,
        n_sessions=len(pairs),
    )


if __name__ == "__main__":
    main()
