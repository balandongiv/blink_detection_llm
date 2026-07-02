"""Experiment 1 (Raja): channel-selection ablation — full 3-stage pipeline per group.

For each channel-selection group (all / frontal / central / parietal / occipital /
posterior / frontal hemispheres / single frontal channels) the complete Stage A->B->C
pipeline is run on that subset, for both the median and mean Stage-B centre, and
evaluated on Stage-A epoch selection and downstream event detection.
Channels come from the brain_region_yaml specified in paths.yaml.

Config files:
  paths.yaml                              — machine-specific dataset paths
  experiment_script/exp1_channel_selection_raja.yaml  — experiment parameters

Resume support
--------------
Each session's rows are cached under ``<out-dir>/sessions/`` (see
src/utils/session_sweep.py). Re-running the same command skips sessions that
already have a cached CSV; pass ``--overwrite`` to force a full recompute.

Full sweep::

    python experiment_script/exp1_channel_selection_raja.py --out-dir runs/exp1_channel_raja

Quick smoke test::

    python experiment_script/exp1_channel_selection_raja.py --max-sessions 1 --n-jobs 1
"""

from __future__ import annotations

import argparse
import functools
import json
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

from experiment_script.channel_ablation_utils import (
    DEFAULT_CENTER_METHODS,
    run_one_session,
    selection_group_names,
    write_csv,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from src.utils.dataset_discovery import discover_raja_pairs
from src.utils.experiment_utils import csv_list as _csv_list, log_run_config, setup_tutorial_logging
from src.utils.session_sweep import run_session_sweep

logger = logging.getLogger(__name__)

_EXP_CFG  = load_exp_config(EXP_SETUP_DIR / (Path(__file__).stem + ".yaml"))
_RAJA     = get_raja_paths()
_CAO      = get_cao_paths()

DATASET              = _EXP_CFG["dataset"]
RAJA_REGION_YAML     = _RAJA["brain_region_yaml"]
CAO_REGION_YAML      = _CAO["brain_region_yaml"]
RAJA_ANNOTATION_BASE = _RAJA["annotation_base"]
RAJA_PROCESSED_BASE  = _RAJA["processed_base"]
EPOCH_DURATION_S     = float(_EXP_CFG["epoch_duration_s"])
STD_THRESHOLD        = float(_EXP_CFG["std_threshold"])
FILTER_LOW           = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH          = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE        = float(_EXP_CFG.get("resample_rate", 100.0))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--std-threshold", type=float, default=STD_THRESHOLD,
                   help="Stage-B k multiplier for MAD (default: %(default)s).")
    p.add_argument("--center-methods", type=_csv_list, default=DEFAULT_CENTER_METHODS,
                   help="Stage-B centres (default: median,mean).")
    p.add_argument("--out-dir", type=Path, default=REPO_ROOT / "runsX" / "exp1_channel_raja",
                   help="Output directory (default: %(default)s).")
    p.add_argument("--overwrite", action="store_true", default=True,
                   help="Re-run sessions that already have a cached result CSV "
                        "(default: skip them and resume).")
    p.add_argument("--max-sessions", type=int, default=1,
                   help="Limit to the first N discovered sessions (None = all).")
    p.add_argument("--n-jobs", type=int, default=None,
                   help="Worker processes for the session sweep (default: cpu_count - 1).")
    p.add_argument("--groups", type=_csv_list, default="frontal_left",
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


def _process_one_session(
    pair: dict,
    *,
    groups_filter: set[str] | None,
    session_kwargs: dict,
) -> tuple[str, list[dict], list[str]]:
    """Worker: run every selected channel group for one session.

    Picklable, top-level — safe to dispatch to a ProcessPoolExecutor.  Returns
    (session_name, metric_rows, error_messages).
    """
    group_names = selection_group_names(
        pair,
        region_yaml=session_kwargs["region_yaml"],
        groups_filter=groups_filter,
    )
    rows: list[dict] = []
    errs: list[str] = []
    for group in group_names:
        try:
            rows.extend(run_one_session(pair, groups_filter={group}, **session_kwargs))
        except Exception as exc:  # noqa: BLE001
            errs.append(f"ERROR  {pair['name']} [{group}]: {exc}")
    return pair["name"], rows, errs


def main() -> None:
    args = _parse_args()
    setup_tutorial_logging()
    log_run_config(
        logger, args,
        dataset=DATASET,
        raja_region_yaml=RAJA_REGION_YAML,
        raja_annotation_base=RAJA_ANNOTATION_BASE,
        raja_processed_base=RAJA_PROCESSED_BASE,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        exp_setup_yaml=EXP_SETUP_DIR / (Path(__file__).stem + ".yaml"),
    )

    pairs = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    if not pairs:
        print("No Raja sessions found — check paths.yaml.")
        return

    logger.info("Raja sessions discovered: %d", len(pairs))
    if args.max_sessions is not None:
        pairs = pairs[:args.max_sessions]
        logger.info("--max-sessions=%d → limiting to %d session(s)", args.max_sessions, len(pairs))

    groups_filter = set(args.groups) if args.groups else None
    session_kwargs = dict(
        region_yaml=RAJA_REGION_YAML,
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

    worker = functools.partial(
        _process_one_session, groups_filter=groups_filter, session_kwargs=session_kwargs,
    )

    out_dir: Path = args.out_dir
    all_metrics, errors = run_session_sweep(
        pairs, out_dir, worker, overwrite=args.overwrite, n_jobs=args.n_jobs,
    )

    if not all_metrics:
        print("No metrics collected.")
        for e in errors:
            print(e)
        return

    # Re-cast numeric fields from str when rows were read back from existing CSVs.
    numeric_keys = {
        "raw_candidate_count", "mapped_candidate_count", "n_channels_used", "n_valid",
        "tp", "fp", "fn", "precision", "recall", "f1",
    }
    coerced: list[dict] = []
    for r in all_metrics:
        row = dict(r)
        for k in numeric_keys:
            if k in row and isinstance(row[k], str):
                try:
                    row[k] = float(row[k])
                except ValueError:
                    pass
        coerced.append(row)

    write_csv(out_dir / f"exp1_channel_selection_{DATASET}_results.csv", coerced)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp1_channel_selection_{DATASET}",
        "epoch_duration_s": float(args.epoch_duration_s),
        "resample_rate": RESAMPLE_RATE,
        "use_epoch_health": args.use_epoch_health,
        "groups_run": sorted(groups_filter) if groups_filter is not None else "all",
        "metric_primary": "f1 per (selection, channel, centre)",
        "n_sessions": len(pairs),
        "n_rows": len(coerced),
        "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)

    print(f"\nResults written to: {out_dir}")


if __name__ == "__main__":
    main()
