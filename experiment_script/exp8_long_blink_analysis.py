"""Experiment 8: long-blink (drowsiness closure) detection, for every detector.

Motivation
----------
Classical blink detectors (BLINKER, MNE amplitude annotation) are tuned to the
sharp, ~150-400 ms waveform of a spontaneous blink.  Long eye closures
(>= 500 ms; PERCLOS microsleep, Wierwille & Ellsworth 1994) have a wide plateau
that violates those shape assumptions and tends to be rejected.  For a driving-
safety application the long closures are the *most important* events, so a method
is only useful if its recall does not collapse on them.  This analysis quantifies,
per detector, the recall gap between normal and long blinks — extending the
single-pipeline diagnostic in ``tutorial/14_pyblinker_long_blink_analysis.py`` to
all five conditions on Raja + Cao2018.

Design
------
Per session the standard valid-epoch pipeline is run once per condition; the
resulting detections are scored separately against three ground-truth subsets:
all blinks, normal (< ``--long-threshold-s``) and long (>= threshold).  Recall is
the primary metric (false positives are inflated for any single subset, as a
detection that matches the *other* type counts against it).

Outputs (with --out-dir): per-(session,condition) results CSV + per-(dataset,
condition) normal-vs-long recall summary CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels
from experiment_script.condition_runner_utils import (
    CONDITIONS,
    annotations_from_reference,
    prepare_session,
    reference_dataframe,
    run_condition,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs,
    discover_raja_pairs,
    setup_tutorial_logging,
    valid_epoch_indices_for_pair,
)

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp8_long_blink_analysis.yaml")
_RAJA    = get_raja_paths()
_CAO     = get_cao_paths()

RAJA_ANNOTATION_BASE = _RAJA["annotation_base"]
RAJA_PROCESSED_BASE  = _RAJA["processed_base"]
CAO_DATASET_ROOT     = _CAO["dataset_root"]

EPOCH_DURATION_S = float(_EXP_CFG.get("epoch_duration_s", 30.0))
LONG_THRESHOLD_S = float(_EXP_CFG.get("long_threshold_s", 0.5))


def _recall(scored) -> dict:
    em = scored.best_eval_result.event_metrics
    return {"tp": em.tp, "fp": em.fp, "fn": em.fn,
            "precision": em.precision, "recall": em.recall, "f1": em.f1,
            "best_channel": scored.best_channel}


def run_one_pair(pair: dict, conditions: list[str], epoch_duration_s: float,
                 long_threshold_s: float, n_epochs: int | None) -> list[dict]:
    epochs, prepared = prepare_session(pair, epoch_duration_s, n_epochs=n_epochs)
    valid = valid_epoch_indices_for_pair(pair, epochs, epoch_duration_s)
    if not valid:
        return []
    valid_set = set(valid)

    ref = reference_dataframe(pair, epoch_duration_s)
    ref = ref[ref["epoch_index"].isin(valid_set)].reset_index(drop=True)
    is_long = ref["blink_duration"] >= long_threshold_s
    ref_normal, ref_long = ref[~is_long], ref[is_long]

    gt_all    = annotations_from_reference(ref,        epoch_duration_s)
    gt_normal = annotations_from_reference(ref_normal, epoch_duration_s)
    gt_long   = annotations_from_reference(ref_long,   epoch_duration_s)

    records: list[dict] = []
    for condition in conditions:
        _, channel_results, scored_all = run_condition(
            prepared, valid, gt_all, condition, epoch_duration_s
        )
        m_all = _recall(scored_all)
        m_norm = _recall(evaluate_channels(channel_results, gt_normal, epoch_duration=epoch_duration_s))
        m_long = _recall(evaluate_channels(channel_results, gt_long, epoch_duration=epoch_duration_s))
        records.append({
            "dataset": pair["dataset"], "session": pair["name"], "condition": condition,
            "n_normal_gt": int((~is_long).sum()), "n_long_gt": int(is_long.sum()),
            "all_precision": m_all["precision"], "all_recall": m_all["recall"], "all_f1": m_all["f1"],
            "normal_recall": m_norm["recall"], "long_recall": m_long["recall"],
            "recall_drop": m_norm["recall"] - m_long["recall"],
            "best_channel": m_all["best_channel"],
        })
    return records


def _summary_rows(records: list[dict]) -> list[dict]:
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["dataset"], r["condition"])].append(r)

    def macro(rows, key):
        return sum(x[key] for x in rows) / len(rows) if rows else 0.0

    out: list[dict] = []
    for (dataset, condition), rows in buckets.items():
        out.append({
            "dataset": dataset, "condition": condition, "n_sessions": len(rows),
            "n_normal_gt": sum(r["n_normal_gt"] for r in rows),
            "n_long_gt": sum(r["n_long_gt"] for r in rows),
            "all_f1": macro(rows, "all_f1"),
            "normal_recall": macro(rows, "normal_recall"),
            "long_recall": macro(rows, "long_recall"),
            "recall_drop": macro(rows, "recall_drop"),
        })
    order = {c: i for i, c in enumerate(CONDITIONS)}
    out.sort(key=lambda r: (r["dataset"], order.get(r["condition"], 99)))
    return out


def _print_summary(rows: list[dict]) -> None:
    header = (f"{'dataset':<8}  {'condition':<14}  {'N':>3}  "
              f"{'nNorm':>6}  {'nLong':>6}  {'all_F1':>7}  "
              f"{'norm_R':>7}  {'long_R':>7}  {'R_drop':>8}")
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print(f"EXP8 — LONG-BLINK RECALL  (long >= {LONG_THRESHOLD_S}s)  per detector")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)
    prev = None
    for r in rows:
        if prev and r["dataset"] != prev:
            print(sep)
        prev = r["dataset"]
        print(f"{r['dataset']:<8}  {r['condition']:<14}  {r['n_sessions']:>3}  "
              f"{r['n_normal_gt']:>6}  {r['n_long_gt']:>6}  {r['all_f1']:>7.4f}  "
              f"{r['normal_recall']:>7.4f}  {r['long_recall']:>7.4f}  {r['recall_drop']:>+8.4f}")
    print(f"{'=' * len(header)}\n")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--long-threshold-s", type=float, default=LONG_THRESHOLD_S)
    p.add_argument("--conditions", type=lambda s: [x.strip() for x in s.split(",") if x.strip()],
                   default=CONDITIONS, help="Subset of conditions (default: all five).")
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--max-sessions", type=int, default=None)
    p.add_argument("--n-epochs", type=int, default=None)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    setup_tutorial_logging()

    raja = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    cao = discover_cao_pairs(CAO_DATASET_ROOT)
    if args.max_sessions is not None:
        raja, cao = raja[: args.max_sessions], cao[: args.max_sessions]
    pairs = raja + cao
    logger.info("Raja=%d  Cao2018=%d  conditions=%s", len(raja), len(cao), args.conditions)
    if not pairs:
        print("No sessions found.")
        return

    records: list[dict] = []
    errors: list[str] = []
    for pair in pairs:
        logger.info("running  %s …", pair["name"])
        try:
            records.extend(run_one_pair(
                pair, args.conditions, float(args.epoch_duration_s),
                float(args.long_threshold_s), args.n_epochs,
            ))
        except Exception as exc:  # noqa: BLE001
            logger.error("%s: %s", pair["name"], exc)
            errors.append(f"ERROR  {pair['name']}: {exc}")

    if not records:
        print("No records collected.")
        for e in errors:
            print(e)
        return

    summary = _summary_rows(records)
    _print_summary(summary)

    if args.out_dir is not None:
        out_dir: Path = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_csv(out_dir / "exp8_long_blink_results.csv", records)
        _write_csv(out_dir / "exp8_long_blink_summary.csv", summary)
        (out_dir / "summary.json").write_text(json.dumps({
            "experiment": "exp8_long_blink_analysis",
            "epoch_duration_s": float(args.epoch_duration_s),
            "long_threshold_s": float(args.long_threshold_s),
            "metric_primary": "long_recall + recall_drop per (dataset, condition)",
            "n_rows": len(records),
        }, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
