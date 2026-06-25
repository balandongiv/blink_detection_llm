"""Experiment 1 (Cao2018): channel-selection ablation — full 3-stage pipeline per group.

For each channel-selection group (all / frontal / central / parietal / occipital /
posterior / frontal hemispheres / single frontal channels) the complete Stage A->B->C
pipeline is run on that subset, for both the median and mean Stage-B centre, and
evaluated on Stage-A epoch selection and downstream event detection.
Channels come from the brain_region_yaml specified in paths.yaml.
Cao2018 analysis epochs are filtered by ``epoch_health.csv`` as in the main experiments.

Config files:
  paths.yaml                               — machine-specific dataset paths
  experiment_script/exp1_channel_selection_cao2018.yaml  — experiment parameters

Full sweep::

    python experiment_script/exp1_channel_selection_cao2018.py --out-dir runs/exp1_channel_cao

Quick smoke test::

    python experiment_script/exp1_channel_selection_cao2018.py --max-sessions 1 --n-epochs 8 --no-single-frontal --no-multithread
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiment_script.channel_ablation_utils import (
    DEFAULT_CENTER_METHODS,
    condition_summary_rows,
    print_condition_summary,
    run_channel_ablation,
    write_csv,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import discover_cao_pairs, setup_tutorial_logging

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / (Path(__file__).stem + ".yaml"))
_RAJA    = get_raja_paths()
_CAO     = get_cao_paths()

DATASET          = _EXP_CFG["dataset"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_DATASET_ROOT = _CAO["dataset_root"]
EPOCH_DURATION_S = float(_EXP_CFG["epoch_duration_s"])
STD_THRESHOLD    = float(_EXP_CFG["std_threshold"])
FILTER_LOW       = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_EXP_CFG.get("resample_rate", 100.0))


def _csv_list(value: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in value.split(",") if x.strip())


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--max-sessions", type=int, default=None)
    p.add_argument("--n-epochs", type=int, default=None)
    p.add_argument("--std-threshold", type=float, default=STD_THRESHOLD,
                   help="Stage-B k multiplier for MAD (default: %(default)s).")
    p.add_argument("--rules", type=_csv_list, default=("any",),
                   help="Aggregation rules: any,min2,min3 (default: any).")
    p.add_argument("--center-methods", type=_csv_list, default=DEFAULT_CENTER_METHODS,
                   help="Stage-B centres (default: median,mean).")
    p.add_argument("--no-single-frontal", action="store_true")
    p.add_argument("--no-multithread", action="store_true", default=False)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    setup_tutorial_logging()

    pairs = discover_cao_pairs(CAO_DATASET_ROOT)
    if args.max_sessions is not None:
        pairs = pairs[: args.max_sessions]
    logger.info("Cao2018 sessions: %d", len(pairs))
    if not pairs:
        print("No Cao2018 sessions found.")
        return

    metrics, errors = run_channel_ablation(
        pairs,
        raja_region_yaml=RAJA_REGION_YAML,
        cao_region_yaml=CAO_REGION_YAML,
        epoch_duration_s=float(args.epoch_duration_s),
        std_threshold=float(args.std_threshold),
        center_methods=tuple(args.center_methods),
        rules=tuple(args.rules),
        resample_rate=RESAMPLE_RATE,
        n_epochs=args.n_epochs,
        include_single_frontal=not args.no_single_frontal,
        use_multithread=args.no_multithread,
        verbose=True,
    )

    if not metrics:
        print("No records collected.")
        for e in errors:
            print(e)
        return

    print_condition_summary(metrics, DATASET)

    if args.out_dir is not None:
        out_dir: Path = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        write_csv(out_dir / f"exp1_channel_selection_{DATASET}_results.csv", metrics)
        write_csv(out_dir / f"exp1_channel_selection_{DATASET}_summary.csv",
                  condition_summary_rows(metrics, DATASET))
        (out_dir / "summary.json").write_text(json.dumps({
            "experiment": f"exp1_channel_selection_{DATASET}",
            "epoch_duration_s": float(args.epoch_duration_s),
            "metric_primary": "det_f1 + stageA_f1 per (selection, rule, centre)",
            "n_rows": len(metrics),
        }, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
