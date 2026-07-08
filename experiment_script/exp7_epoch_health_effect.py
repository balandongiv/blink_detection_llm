"""Experiment 7: effect of excluding low-health epochs, for every detector.

Motivation
----------
Both corpora ship an ``epoch_health`` annotation (Cao2018 via ``epoch_health.csv``;
Raja via the same file beside ``ear_eog.csv``).  The main pipeline *excludes*
low-health epochs before detection.  Exclusion is a preprocessing choice, not part
of any detector — so a fair benchmark must show how much it actually changes the
reported numbers, and whether it helps the proposed method more (or less) than the
baselines.  If excluding health-flagged epochs mostly removes noisy segments, every
detector should improve; if it mainly removes hard-but-real blinks, recall falls.

Design
------
For each session the full pipeline is run twice under identical settings, varying
only the epoch set fed to detection + evaluation:

* ``health_on``  — keep only epochs with assigned health >= ``--min-health``
  (Cao2018: drop if any overlapping 30 s sub-epoch is unhealthy); GT restricted to
  the kept epochs so blinks in dropped epochs are not counted as misses.
* ``health_off`` — use all epochs; GT over all epochs.

This is run for all five conditions (BLINKER-concat, MNE-annot, DBO, Proposed-Mean,
Proposed-Med) on Raja + Cao2018, and the per-condition on-vs-off delta is reported.

Reuse of prior results
----------------------
The ``health_on`` side is, by construction, *exactly* the main comparison (exp1
already runs the same five conditions on the health-filtered epoch set).  Pass
``--reuse-exp1-csv runs/exp1_strategy_30s/exp41_strategy_comparison_results.csv`` to
take the ``health_on`` numbers straight from exp1 and only compute the ``health_off``
side here — roughly halving the work (the expensive DBO/Proposed detections on the
kept epochs are not repeated).

Outputs (with --out-dir): per-(session,condition,mode) results CSV + per-(dataset,
condition) on/off summary CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.condition_runner_utils import (
    CONDITIONS,
    annotations_from_reference,
    prepare_session,
    reference_dataframe,
    run_condition,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from src.utils.dataset_discovery import discover_cao_pairs, discover_raja_pairs
from src.utils.experiment_utils import (
    get_valid_cao_epoch_indices,
    setup_tutorial_logging,
    write_csv as _write_csv,
)

from pyblinker.epoch_detection import assign_epoch_health, get_valid_epoch_indices_by_health

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp7_epoch_health_effect.yaml")
_RAJA    = get_raja_paths()
_CAO     = get_cao_paths()

RAJA_ANNOTATION_BASE = _RAJA["annotation_base"]
RAJA_PROCESSED_BASE  = _RAJA["processed_base"]
CAO_DATASET_ROOT     = _CAO["dataset_root"]

EPOCH_DURATION_S = float(_EXP_CFG.get("epoch_duration_s", 30.0))
MIN_HEALTH       = int(_EXP_CFG.get("min_health", 3))


def _raja_health_path(pair: dict) -> Path | None:
    candidate = pair["csv"].parent / "epoch_health.csv"
    return candidate if candidate.is_file() else None


def health_valid_indices(pair: dict, n_epochs: int, epoch_duration_s: float, min_health: int) -> list[int]:
    """Health-filtered valid epoch indices for the dataset (fallback: all epochs)."""
    if pair["dataset"] == "cao2018":
        return get_valid_cao_epoch_indices(
            pair.get("epoch_health"), epoch_duration_s, n_epochs,
            health_drop_threshold=min_health,
        )
    health_path = _raja_health_path(pair)
    if health_path is None:
        return list(range(n_epochs))
    df = pd.read_csv(health_path)
    df["health"] = pd.to_numeric(df["health"], errors="coerce")
    health_values = assign_epoch_health(df, epoch_duration_s, n_epochs)
    return get_valid_epoch_indices_by_health(health_values, min_health)


def run_one_pair(pair: dict, conditions: list[str], epoch_duration_s: float,
                 min_health: int, n_epochs: int | None,
                 reuse_on: dict | None = None) -> list[dict]:
    epochs, prepared = prepare_session(pair, epoch_duration_s, n_epochs=n_epochs)
    n_total = len(epochs)
    ref_df = reference_dataframe(pair, epoch_duration_s)
    valid_on = sorted(set(health_valid_indices(pair, n_total, epoch_duration_s, min_health)))

    records: list[dict] = []

    # health_off — always computed here (all epochs).
    valid_off = list(range(n_total))
    gt_off = annotations_from_reference(
        ref_df[ref_df["epoch_index"].isin(set(valid_off))], epoch_duration_s
    )
    for condition in conditions:
        m, _, _ = run_condition(prepared, valid_off, gt_off, condition, epoch_duration_s)
        records.append({
            "dataset": pair["dataset"], "session": pair["name"],
            "condition": condition, "health_mode": "health_off",
            "n_total": n_total, "n_valid": len(valid_off), "source": "computed", **m,
        })

    # health_on — reuse exp1 when available (identical pipeline), else compute.
    reused = reuse_on or {}
    can_reuse = all((pair["dataset"], pair["name"], c) in reused for c in conditions)
    if can_reuse:
        for condition in conditions:
            m = reused[(pair["dataset"], pair["name"], condition)]
            records.append({
                "dataset": pair["dataset"], "session": pair["name"],
                "condition": condition, "health_mode": "health_on",
                "n_total": n_total, "n_valid": len(valid_on),
                "source": "reused_exp1", **m,
            })
            # (keys aligned with computed records below via the shared 'source' field)
    elif valid_on:
        gt_on = annotations_from_reference(
            ref_df[ref_df["epoch_index"].isin(set(valid_on))], epoch_duration_s
        )
        for condition in conditions:
            m, _, _ = run_condition(prepared, valid_on, gt_on, condition, epoch_duration_s)
            records.append({
                "dataset": pair["dataset"], "session": pair["name"],
                "condition": condition, "health_mode": "health_on",
                "n_total": n_total, "n_valid": len(valid_on), "source": "computed", **m,
            })
    else:
        logger.warning("no health-valid epochs for %s — health_on skipped", pair["name"])
    return records


def _summary_rows(records: list[dict]) -> list[dict]:
    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["dataset"], r["condition"], r["health_mode"])].append(r)

    def macro(rows, key):
        return sum(x[key] for x in rows) / len(rows) if rows else 0.0

    out: list[dict] = []
    seen = set()
    for (dataset, condition, _mode) in buckets:
        if (dataset, condition) in seen:
            continue
        seen.add((dataset, condition))
        on = buckets.get((dataset, condition, "health_on"), [])
        off = buckets.get((dataset, condition, "health_off"), [])
        out.append({
            "dataset": dataset, "condition": condition,
            "n_sessions": max(len(on), len(off)),
            "mean_n_total": macro(off or on, "n_total"),
            "mean_n_valid_on": macro(on, "n_valid"),
            "on_precision": macro(on, "precision"), "off_precision": macro(off, "precision"),
            "on_recall": macro(on, "recall"), "off_recall": macro(off, "recall"),
            "on_f1": macro(on, "f1"), "off_f1": macro(off, "f1"),
            "delta_f1_on_minus_off": macro(on, "f1") - macro(off, "f1"),
        })
    order = {c: i for i, c in enumerate(CONDITIONS)}
    out.sort(key=lambda r: (r["dataset"], order.get(r["condition"], 99)))
    return out


def _print_summary(rows: list[dict]) -> None:
    header = (f"{'dataset':<8}  {'condition':<14}  {'N':>3}  "
              f"{'on_F1':>7}  {'off_F1':>7}  {'ΔF1':>7}  "
              f"{'on_R':>7}  {'off_R':>7}  {'on_P':>7}  {'off_P':>7}  "
              f"{'kept/tot':>10}")
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print("EXP7 — EFFECT OF EXCLUDING LOW-HEALTH EPOCHS  (health_on vs health_off)")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)
    prev = None
    for r in rows:
        if prev and r["dataset"] != prev:
            print(sep)
        prev = r["dataset"]
        kept = f"{r['mean_n_valid_on']:.0f}/{r['mean_n_total']:.0f}"
        print(f"{r['dataset']:<8}  {r['condition']:<14}  {r['n_sessions']:>3}  "
              f"{r['on_f1']:>7.4f}  {r['off_f1']:>7.4f}  {r['delta_f1_on_minus_off']:>+7.4f}  "
              f"{r['on_recall']:>7.4f}  {r['off_recall']:>7.4f}  "
              f"{r['on_precision']:>7.4f}  {r['off_precision']:>7.4f}  {kept:>10}")
    print(f"{'=' * len(header)}\n")


def _load_exp1_reuse(csv_path: Path) -> dict:
    """Load exp1 results CSV → {(dataset, session, condition): metrics} for reuse."""
    reuse: dict = {}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["dataset"], row["session"], row["condition"])
            reuse[key] = {
                "best_channel": row.get("best_channel", ""),
                "tp": int(float(row["tp"])), "fp": int(float(row["fp"])),
                "fn": int(float(row["fn"])),
                "precision": float(row["precision"]),
                "recall": float(row["recall"]), "f1": float(row["f1"]),
            }
    return reuse



def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch-duration-s", type=float, default=EPOCH_DURATION_S)
    p.add_argument("--min-health", type=int, default=MIN_HEALTH)
    p.add_argument("--conditions", type=lambda s: [x.strip() for x in s.split(",") if x.strip()],
                   default=CONDITIONS, help="Subset of conditions (default: all five).")
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--reuse-exp1-csv", type=Path, default=None,
                   help="exp1 results CSV; its rows are reused for the health_on side "
                        "so only health_off is computed here.")
    p.add_argument("--max-sessions", type=int, default=None,
                   help="Limit sessions per dataset (quick runs).")
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

    reuse_on = None
    if args.reuse_exp1_csv is not None:
        if not args.reuse_exp1_csv.is_file():
            raise SystemExit(f"--reuse-exp1-csv not found: {args.reuse_exp1_csv}")
        reuse_on = _load_exp1_reuse(args.reuse_exp1_csv)
        logger.info("Reusing exp1 health_on results from %s (%d rows)",
                    args.reuse_exp1_csv, len(reuse_on))

    records: list[dict] = []
    errors: list[str] = []
    for pair in pairs:
        logger.info("running  %s …", pair["name"])
        try:
            records.extend(run_one_pair(
                pair, args.conditions, float(args.epoch_duration_s),
                int(args.min_health), args.n_epochs, reuse_on=reuse_on,
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
        _write_csv(out_dir / "exp7_epoch_health_effect_results.csv", records)
        _write_csv(out_dir / "exp7_epoch_health_effect_summary.csv", summary)
        (out_dir / "summary.json").write_text(json.dumps({
            "experiment": "exp7_epoch_health_effect",
            "epoch_duration_s": float(args.epoch_duration_s),
            "min_health": int(args.min_health),
            "metric_primary": "delta_f1_on_minus_off per (dataset, condition)",
            "n_rows": len(records),
        }, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
