"""Shared per-session worker for the exp5 per-dataset n_min-sensitivity sweep scripts.

Run order:
  1. exp5_a_nmin_sensitivity_cao2018.py / exp5_a_nmin_sensitivity_raja.py
     collect per-session rows across every min_flagged_epochs (n_min) value.
  2. exp5_write_results() writes the exp5 per-dataset result artifacts.

Both scripts call run_nmin_session_sweep() (below), which dispatches
process_one_session() — every n_min value x channel-selection group for one
session, via src.utils.channel_ablation_utils.run_one_session (the same Stage
A->B->C ablation engine exp1/exp3 use; called directly, not through
run_channel_ablation, because that wrapper does not plumb min_flagged_epochs
through) — to a ProcessPoolExecutor (or runs it in-process when n_jobs=1),
mirroring src/exp/exp3_epoch_duration_sweep.py's role for the exp3 scripts.
process_one_session is called directly by name (never through a generic
Callable parameter or functools.partial) so debugger step-into / IDE go-to-
definition on that call lands here.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.channel_ablation_utils import run_one_session, selection_group_names
from src.utils.session_sweep import resolve_n_jobs, split_cached_and_todo, store_session_result

logger = logging.getLogger(__name__)


def process_one_session(
    pair: dict,
    *,
    groups_filter: set[str] | None,
    session_kwargs: dict,
) -> tuple[str, list[dict], list[str]]:
    """Worker: run every n_min value x selected channel group for one session.

    Picklable, top-level — safe to dispatch to a ProcessPoolExecutor.  Returns
    (session_name, metric_rows, error_messages).
    """
    region_yaml = session_kwargs["region_yaml"]
    group_names = selection_group_names(pair, region_yaml=region_yaml, groups_filter=groups_filter)

    all_rows: list[dict] = []
    all_errs: list[str] = []
    for nmin in session_kwargs["nmin_values"]:
        for group in group_names:
            try:
                rows = run_one_session(
                    pair,
                    region_yaml=region_yaml,
                    epoch_duration_s=session_kwargs["epoch_duration_s"],
                    std_threshold=session_kwargs["std_threshold"],
                    center_methods=(session_kwargs["center_method"],),
                    autoreject_random_state=session_kwargs["autoreject_random_state"],
                    filter_low=session_kwargs["filter_low"],
                    filter_high=session_kwargs["filter_high"],
                    resample_rate=session_kwargs["resample_rate"],
                    use_epoch_health=False,
                    groups_filter={group},
                    verbose=False,
                    min_flagged_epochs=int(nmin),
                )
                for r in rows:
                    r["min_flagged_epochs"] = int(nmin)
                all_rows.extend(rows)
            except Exception as exc:  # noqa: BLE001
                all_errs.append(f"ERROR  {pair['name']} [{group}] nmin={nmin}: {exc}")

    return pair["name"], all_rows, all_errs


def run_nmin_session_sweep(
    pairs: list[dict],
    out_dir: Path,
    *,
    overwrite: bool = False,
    n_jobs: int | None = None,
    **worker_kwargs,
) -> tuple[list[dict], list[str]]:
    """Run ``process_one_session`` (above) over *pairs*, resume-aware.

    Calls ``process_one_session`` directly by name — defined in this same
    module, right above — never through a generic ``Callable`` parameter,
    ``functools.partial``, or any other indirection, so a debugger's "step
    into" and an IDE's "go to definition" on the call below always land in
    the real implementation.

    Sessions whose per-session CSV already exists under ``out_dir/sessions/``
    are skipped (loaded from cache) unless ``overwrite`` is True. A session's
    cached CSV covers every n_min value, so resume is all-or-nothing per
    session, not per (session, n_min).
    """
    all_metrics, todo = split_cached_and_todo(pairs, out_dir, overwrite)
    errors: list[str] = []

    if todo:
        jobs = resolve_n_jobs(len(todo), n_jobs)
        logger.info("Running %d session(s) with n_jobs=%d (of %d cpus)",
                    len(todo), jobs, os.cpu_count() or 1)
        if jobs == 1:
            for pair in todo:
                name, rows, errs = process_one_session(pair, **worker_kwargs)
                store_session_result(out_dir, name, rows, errs,
                                      all_metrics=all_metrics, errors=errors)
        else:
            with ProcessPoolExecutor(max_workers=jobs) as ex:
                fut_map = {
                    ex.submit(process_one_session, pair, **worker_kwargs): pair["name"]
                    for pair in todo
                }
                for fut in as_completed(fut_map):
                    name = fut_map[fut]
                    try:
                        _, rows, errs = fut.result()
                        store_session_result(out_dir, name, rows, errs,
                                              all_metrics=all_metrics, errors=errors)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("ERROR  %s: %s", name, exc)
                        errors.append(f"ERROR  {name}: {exc}")

    return all_metrics, errors


def _summary_by_nmin(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (min_flagged_epochs, selection, channel)."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["min_flagged_epochs"], r["selection"], r["channel"])].append(r)

    def _mean(bucket: list[dict], key: str) -> float:
        vals = [float(b[key]) for b in bucket if key in b and b[key] != ""]
        return float(np.mean(vals)) if vals else float("nan")

    out: list[dict] = []
    for (nmin, sel, ch), bucket in buckets.items():
        out.append({
            "dataset": dataset_label,
            "min_flagged_epochs": int(nmin),
            "selection": sel,
            "channel": ch,
            "n_sessions": len(bucket),
            "precision": _mean(bucket, "precision"),
            "recall": _mean(bucket, "recall"),
            "f1": _mean(bucket, "f1"),
        })
    out.sort(key=lambda r: (r["min_flagged_epochs"], r["selection"], r["channel"]))
    return out


def exp5_write_results(
    *,
    out_dir: Path,
    dataset: str,
    all_metrics: list[dict],
    errors: list[str],
    groups_run: set[str] | None,
    n_sessions: int,
) -> None:
    """Coerce ``all_metrics``, then write the exp5 per-dataset results CSV, summary CSV,
    summary.json, and print the n_min-summary table.

    Shared by exp5_a_nmin_sensitivity_cao2018.py and exp5_a_nmin_sensitivity_raja.py
    so the two scripts produce identically-shaped outputs.
    """
    df = pd.DataFrame(all_metrics)
    df.to_csv(out_dir / f"exp5_nmin_sensitivity_{dataset}_results.csv", index=False)

    summary_rows = _summary_by_nmin(all_metrics, dataset)
    pd.DataFrame(summary_rows).to_csv(
        out_dir / f"exp5_nmin_sensitivity_{dataset}_summary.csv", index=False
    )

    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp5_nmin_sensitivity_{dataset}",
        "groups_run": sorted(groups_run) if groups_run else None,
        "n_sessions": int(n_sessions),
        "n_rows": int(len(all_metrics)),
        "n_errors": int(len(errors)),
    }, indent=2), encoding="utf-8")

    header = (f"{'n_min':>5}  {'selection':<16}  {'channel':<10}  "
              f"{'P':>7}  {'R':>7}  {'F1':>7}  {'N':>3}")
    print(f"\n{header}")
    print("-" * len(header))
    for r in summary_rows:
        print(f"{r['min_flagged_epochs']:>5}  {r['selection']:<16}  {r['channel']:<10}  "
              f"{r['precision']:>7.4f}  {r['recall']:>7.4f}  {r['f1']:>7.4f}  {r['n_sessions']:>3}")
    print(f"\nResults written to: {out_dir}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


__all__ = ["process_one_session", "run_nmin_session_sweep", "exp5_write_results"]
