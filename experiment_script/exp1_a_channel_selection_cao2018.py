"""Experiment 1 (Cao2018): channel-selection ablation — full 3-stage pipeline per group.

Run order:
  1. Run this script first to generate the exp1 per-session results.
  2. This script calls exp1_write_results(), which writes the exp1 results
     CSV, summary CSV, and summary.json.
  3. Run exp1_step_b_get_best_region_channel.py afterwards to pick the top 4
     channels and top 4 region groups from those summary CSVs.

For each channel-selection group (all / frontal / central / parietal / occipital /
posterior / frontal hemispheres / single frontal channels) the complete Stage A->B->C
pipeline is run on that subset, for both the median and mean Stage-B centre, and
evaluated on Stage-A epoch selection and downstream event detection.
Channels come from the brain_region_yaml specified in paths.yaml.

Config files:
  paths.yaml                               — machine-specific dataset paths
  experiment_script/exp1_channel_selection_cao2018.yaml  — experiment parameters

Resume support
--------------
Each session's rows are cached under ``<out-dir>/sessions/`` (see
src/utils/session_sweep.py). Re-running the same command skips sessions that
already have a cached CSV; pass ``--overwrite`` to force a full recompute.

Full sweep::

    python experiment_script/exp1_a_channel_selection_cao2018.py --out-dir runs/exp1_channel_cao

Quick smoke test::

    python experiment_script/exp1_a_channel_selection_cao2018.py --max-sessions 1 --n-jobs 1
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

from src.exp.session_worker import exp1_write_results, run_channel_selection_session_sweep
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from src.utils.dataset_discovery import discover_cao_pairs
from src.utils.experiment_utils import csv_list as _csv_list, log_run_config, setup_tutorial_logging

logger = logging.getLogger(__name__)

_EXP_YAML_PATH = EXP_SETUP_DIR / (Path(__file__).stem + ".yaml")
_PATHS_YAML = EXP_SETUP_DIR / "exp_path.yaml"
print(f"[exp1_channel_selection_cao2018] loading exp config from: {_EXP_YAML_PATH}")
_EXP_CFG = load_exp_config(_EXP_YAML_PATH)
print(f"[exp1_channel_selection_cao2018] exp config values: {_EXP_CFG}")
print(f"[exp1_channel_selection_cao2018] loading path defaults from: {_PATHS_YAML}")
_PATH_CFG = load_exp_config(_PATHS_YAML)
print(f"[exp1_channel_selection_cao2018] path config values: {_PATH_CFG}")
_CAO     = get_cao_paths()
print(f"[exp1_channel_selection_cao2018] cao paths: {_CAO}")


DATASET          = _EXP_CFG["dataset"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
CAO_DATASET_ROOT = _CAO["dataset_root"]
EPOCH_DURATION_S = float(_EXP_CFG["epoch_duration_s"])
STD_THRESHOLD    = float(_EXP_CFG["std_threshold"])
FILTER_LOW       = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_EXP_CFG.get("resample_rate", 100.0))
DEFAULT_OUT_DIR  = REPO_ROOT / Path(_PATH_CFG["cao2018_out_dir"])


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--std-threshold", type=float, default=STD_THRESHOLD,
                   help="Stage-B k multiplier for MAD (default: %(default)s).")
    p.add_argument("--center-methods", type=_csv_list, default="median,mean",
                   help="Stage-B centres (default: median,mean).")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                   help="Output directory (default from setup/exp1_channel_selection_paths.yaml: %(default)s).")
    p.add_argument("--overwrite", action="store_true", default=True,
                   help="Re-run sessions that already have a cached result CSV "
                        "(default: skip them and resume).")
    p.add_argument("--max-sessions", type=int, default=None,
                   help="Limit to the first N discovered sessions (None = all).")
    p.add_argument("--n-jobs", type=int, default=10,
                   help="Worker processes for the session sweep (default: cpu_count - 1).")

    p.add_argument("--groups", type=_csv_list, default="all",
                   help="Comma-separated channel-selection groups to run "
                        "(default: all groups, e.g. all,frontal,frontal_left,...).")

    p.add_argument("--use-epoch-health", action="store_true", default=False,
                   help="Exclude low-health epochs (epoch_health.csv) before scoring.")
    p.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Enable extra per-session logging.",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    setup_tutorial_logging()
    log_run_config(
        logger, args,
        dataset=DATASET,
        cao_region_yaml=CAO_REGION_YAML,
        cao_dataset_root=CAO_DATASET_ROOT,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        exp_setup_yaml=EXP_SETUP_DIR / (Path(__file__).stem + ".yaml"),
    )

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
        std_threshold=float(args.std_threshold),
        center_methods=tuple(args.center_methods),
        autoreject_random_state=42,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        use_epoch_health=args.use_epoch_health,
        verbose=args.verbose,
    )
    logger.info("groups_filter = %s", sorted(groups_filter) if groups_filter is not None else "all")
    logger.info("session_kwargs = %s", session_kwargs)
    logger.info("out_dir = %s  overwrite=%s  n_jobs=%s", args.out_dir, args.overwrite, args.n_jobs)

    out_dir: Path = args.out_dir
    all_metrics, errors = run_channel_selection_session_sweep(
        pairs, out_dir,
        overwrite=args.overwrite, n_jobs=args.n_jobs,
        groups_filter=groups_filter, session_kwargs=session_kwargs,
    )

    exp1_write_results(
        out_dir=out_dir,
        dataset=DATASET,
        all_metrics=all_metrics,
        errors=errors,
        epoch_duration_s=float(args.epoch_duration_s),
        resample_rate=RESAMPLE_RATE,
        use_epoch_health=args.use_epoch_health,
        groups_filter=groups_filter,
        n_sessions=len(pairs),
    )


if __name__ == "__main__":
    main()
