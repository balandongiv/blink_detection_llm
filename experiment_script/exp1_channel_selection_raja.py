"""Experiment 1 (Raja): channel-selection ablation — full 3-stage pipeline per group.

For each channel-selection group (all / frontal / central / parietal / occipital /
posterior / frontal hemispheres / single frontal channels) the complete Stage A->B->C
pipeline is run on that subset, for both the median and mean Stage-B centre, and
evaluated on Stage-A epoch selection and downstream event detection.  A butterfly
report (per-subject + all-subject TP/FN/FP blink-region waveforms) is produced for
visual inspection.  Channels come from ``brain_region_raja.yaml`` (EGI HydroCel
indices, resolved to ``E1…E128``).

Full sweep::

    python experiment_script/exp1_channel_selection_raja.py --out-dir runs/exp1_channel_raja

Quick smoke test::

    python experiment_script/exp1_channel_selection_raja.py --max-sessions 1 --n-epochs 8 --no-single-frontal --no-multithread
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

from experiment_script.butterfly_report import build_channel_selection_report
from experiment_script.channel_ablation_utils import (
    DEFAULT_CENTER_METHODS,
    condition_summary_rows,
    print_condition_summary,
    run_channel_ablation,
    write_csv,
)
from tutorial.tutorial_utils import (
    DEFAULT_CAO_REGION_YAML,
    DEFAULT_RAJA_REGION_YAML,
    discover_raja_pairs,
    setup_tutorial_logging,
)

logger = logging.getLogger(__name__)

DATASET              = "raja"
RAJA_REGION_YAML     = DEFAULT_RAJA_REGION_YAML
RAJA_ANNOTATION_BASE = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
RAJA_PROCESSED_BASE  = Path(r"D:\dataset\drowsy_driving_raja_processed")

EPOCH_DURATION_S = 30.0
STD_THRESHOLD    = 1.5
WINDOW_S         = 0.25


def _csv_list(value: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in value.split(",") if x.strip())


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--max-sessions", type=int, default=None)
    p.add_argument("--n-epochs", type=int, default=None)
    p.add_argument("--rules", type=_csv_list, default=("any",),
                   help="Aggregation rules: any,min2,min3 (default: any).")
    p.add_argument("--center-methods", type=_csv_list, default=DEFAULT_CENTER_METHODS,
                   help="Stage-B centres (default: median,mean).")
    p.add_argument("--butterfly-groups", type=_csv_list, default=("all", "frontal", "posterior"),
                   help="Groups to render in the butterfly report (default: all,frontal,posterior).")
    p.add_argument("--no-single-frontal", action="store_true")
    p.add_argument("--no-report", action="store_true",
                   help="Skip the butterfly HTML report.")
    p.add_argument("--no-multithread", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    setup_tutorial_logging()

    pairs = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    if args.max_sessions is not None:
        pairs = pairs[: args.max_sessions]
    logger.info("Raja sessions: %d", len(pairs))
    if not pairs:
        print("No Raja sessions found.")
        return

    butterfly_groups = None if args.no_report else tuple(args.butterfly_groups)
    metrics, morph, errors = run_channel_ablation(
        pairs,
        region_yaml=RAJA_REGION_YAML,
        raja_region_yaml=RAJA_REGION_YAML,
        cao_region_yaml=DEFAULT_CAO_REGION_YAML,
        epoch_duration_s=float(args.epoch_duration_s),
        std_threshold=STD_THRESHOLD,
        center_methods=tuple(args.center_methods),
        rules=tuple(args.rules),
        n_epochs=args.n_epochs,
        include_single_frontal=not args.no_single_frontal,
        butterfly_groups=butterfly_groups,
        window_s=WINDOW_S,
        use_multithread=not args.no_multithread,
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

        if morph:
            report = build_channel_selection_report(morph, window_s=WINDOW_S,
                                                    title=f"Exp1 Channel Selection — {DATASET}")
            report_path = out_dir / f"exp1_channel_selection_{DATASET}_butterfly.html"
            report.save(str(report_path), overwrite=True, open_browser=False)
            print(f"  Butterfly report -> {report_path}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
