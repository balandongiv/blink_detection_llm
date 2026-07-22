"""Shared per-session worker for the exp3 per-dataset epoch-duration sweep scripts.

Run order:
  1. exp3_a_epoch_duration_cao2018.py / exp3_a_epoch_duration_raja.py
     collect per-session rows across every epoch duration.
  2. exp3_write_results() writes the exp3 per-dataset result artifacts.
  3. exp3_b_plot_epoch_duration.py reads both datasets' results CSVs to plot
     macro-F1 stability across epoch durations.

Both scripts call run_epoch_duration_session_sweep() (below), which dispatches
process_one_session() — every epoch duration x channel-selection group for one
session, via src.utils.channel_ablation_utils.run_channel_ablation (the same
Stage A->B->C ablation engine exp1 uses) — to a ProcessPoolExecutor (or runs it
in-process when n_jobs=1), mirroring src/exp/exp2_channel_group_sweep.py's role
for the exp2 scripts. process_one_session is called directly by name (never
through a generic Callable parameter or functools.partial) so debugger step-into /
IDE go-to-definition on that call lands here.
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

from src.utils.channel_ablation_utils import run_channel_ablation
from src.utils.session_sweep import resolve_n_jobs, split_cached_and_todo, store_session_result

logger = logging.getLogger(__name__)


def process_one_session(
    pair: dict,
    *,
    groups_filter: set[str] | None,
    session_kwargs: dict,
) -> tuple[str, list[dict], list[str]]:
    """Worker: run every epoch duration x selected channel group for one session.

    Picklable, top-level — safe to dispatch to a ProcessPoolExecutor.  Returns
    (session_name, metric_rows, error_messages).
    """
    all_rows: list[dict] = []
    all_errs: list[str] = []
    for epoch_duration_s in session_kwargs["epoch_durations_s"]:
        rows, errs = run_channel_ablation(
            [pair],
            region_yaml=session_kwargs["region_yaml"],
            epoch_duration_s=float(epoch_duration_s),
            std_threshold=session_kwargs["std_threshold"],
            center_methods=session_kwargs["center_methods"],
            autoreject_random_state=session_kwargs["autoreject_random_state"],
            filter_low=session_kwargs["filter_low"],
            filter_high=session_kwargs["filter_high"],
            resample_rate=session_kwargs["resample_rate"],
            groups_filter=groups_filter,
            use_multithread=False,
            verbose=False,
        )
        for r in rows:
            r["epoch_duration_s"] = float(epoch_duration_s)
        all_rows.extend(rows)
        all_errs.extend(errs)

    return pair["name"], all_rows, all_errs


def run_epoch_duration_session_sweep(
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

    Pass ``n_jobs=1`` to keep everything in this process while stepping
    through the worker in a debugger; any ``n_jobs`` that resolves above 1
    dispatches to ``ProcessPoolExecutor`` worker subprocesses that most
    debuggers cannot attach to, so breakpoints inside the worker won't fire.

    Sessions whose per-session CSV already exists under ``out_dir/sessions/``
    are skipped (loaded from cache) unless ``overwrite`` is True. A session's
    cached CSV covers every epoch duration, so resume is all-or-nothing per
    session, not per (session, duration).
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


def _summary_by_duration(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (epoch_duration_s, selection, channel, center_method)."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["epoch_duration_s"], r["selection"], r["channel"], r["center_method"])].append(r)

    def _mean(bucket: list[dict], key: str) -> float:
        vals = [float(b[key]) for b in bucket if key in b and b[key] != ""]
        return float(np.mean(vals)) if vals else float("nan")

    out: list[dict] = []
    for (dur, sel, ch, center), bucket in buckets.items():
        out.append({
            "dataset": dataset_label,
            "epoch_duration_s": float(dur),
            "selection": sel,
            "channel": ch,
            "center_method": center,
            "n_sessions": len(bucket),
            "precision": _mean(bucket, "precision"),
            "recall": _mean(bucket, "recall"),
            "f1": _mean(bucket, "f1"),
        })
    out.sort(key=lambda r: (r["epoch_duration_s"], r["selection"], r["channel"], r["center_method"]))
    return out


def exp3_write_results(
    *,
    out_dir: Path,
    dataset: str,
    all_metrics: list[dict],
    errors: list[str],
    reference_epoch_duration_s: float,
    groups_run: set[str] | None,
    n_sessions: int,
) -> None:
    """Coerce ``all_metrics``, then write the exp3 per-dataset results CSV, summary CSV,
    summary.json, and print the duration-summary table.

    Shared by exp3_a_epoch_duration_cao2018.py and exp3_a_epoch_duration_raja.py
    so the two scripts produce identically-shaped outputs, and so
    exp3_b_plot_epoch_duration.py's input schema stays stable.
    """
    df = pd.DataFrame(all_metrics)
    df.to_csv(out_dir / f"exp3_epoch_duration_{dataset}_results.csv", index=False)

    summary_rows = _summary_by_duration(all_metrics, dataset)
    pd.DataFrame(summary_rows).to_csv(
        out_dir / f"exp3_epoch_duration_{dataset}_summary.csv", index=False
    )

    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp3_epoch_duration_{dataset}",
        "reference_epoch_duration_s": float(reference_epoch_duration_s),
        "groups_run": sorted(groups_run) if groups_run else None,
        "n_sessions": int(n_sessions),
        "n_rows": int(len(all_metrics)),
        "n_errors": int(len(errors)),
    }, indent=2), encoding="utf-8")

    header = (f"{'dur_s':>6}  {'selection':<16}  {'channel':<10}  {'centre':<7}  "
              f"{'P':>7}  {'R':>7}  {'F1':>7}  {'N':>3}")
    print(f"\n{header}")
    print("-" * len(header))
    for r in summary_rows:
        marker = " *" if float(r["epoch_duration_s"]) == float(reference_epoch_duration_s) else ""
        print(f"{r['epoch_duration_s']:>6.0f}{marker:<2} {r['selection']:<16}  {r['channel']:<10}  "
              f"{r['center_method']:<7}  {r['precision']:>7.4f}  {r['recall']:>7.4f}  "
              f"{r['f1']:>7.4f}  {r['n_sessions']:>3}")
    print(f"\nResults written to: {out_dir}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


__all__ = ["process_one_session", "run_epoch_duration_session_sweep", "exp3_write_results"]
