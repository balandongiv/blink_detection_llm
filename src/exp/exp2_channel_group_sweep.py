"""Shared per-session worker for the exp2 per-dataset channel-group sweep scripts.

Run order:
  1. exp2_a_strategy_comparison_cao2018.py / exp2_a_strategy_comparison_raja.py
     collect per-session rows.
  2. exp2_write_results() writes the exp2 per-dataset result artifacts.
  3. update_exp2_latex.py reads both datasets' results CSVs to build the
     manuscript's per-channel-group comparison table.

Both scripts call run_strategy_comparison_session_sweep() (below), which dispatches
process_one_session() — every exp2 condition (BLINKER-concat, MNE-annot, Proposed-Mean,
Proposed-Med — the runner functions live in src/exp/exp2_strategy_conditions.py, but the
active condition list and detector parameters are owned by the calling script, passed in
via session_kwargs["conditions"] / session_kwargs["detector_settings"]) on every selected
channel-selection group for one session — to a ProcessPoolExecutor (or runs it
in-process when n_jobs=1), mirroring src/exp/session_worker.py's role for the exp1
channel-selection scripts. process_one_session is called directly by name (never
through a generic Callable parameter or functools.partial) so debugger step-into /
IDE go-to-definition on that call lands here.
"""

from __future__ import annotations
import pandas as pd
import logging
import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np

from blink_evaluation import evaluate_channels
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import (
    load_brain_region_channels,
    load_brain_region_map,
    resolve_channel_names,
)
from src.utils.channel_ablation_utils import build_selection_groups, write_csv
from src.utils.experiment_utils import load_gt_annotations_for_pair
from src.utils.session_sweep import resolve_n_jobs, split_cached_and_todo, store_session_result
from src.exp.exp2_strategy_conditions import _CONDITION_RUNNERS

logger = logging.getLogger(__name__)

# Only the Proposed variants have a center method worth recording; the baselines don't.
_CENTER_METHOD = {"Proposed-Mean": "mean", "Proposed-Med": "median"}


def _run_one_group_all_conditions(
    pair: dict,
    group_name: str,
    group_chs: list[str],
    *,
    epoch_duration_s: float,
    filter_low: float,
    filter_high: float,
    resample_rate: float,
    conditions: list[str],
    detector_settings: dict,
) -> tuple[list[dict], list[str]]:
    """Run every exp2 condition on one (session, channel group); one row per channel."""
    rows: list[dict] = []
    errs: list[str] = []
    try:
        raw = mne.io.read_raw_fif(str(pair["fif"]), preload=True, verbose="ERROR")
        raw.pick(sorted(group_chs))

        epochs = mne.make_fixed_length_epochs(
            raw, duration=epoch_duration_s, preload=True, verbose="ERROR"
        )
        valid_epoch_indices = list(range(len(epochs)))
        if not valid_epoch_indices:
            return rows, errs

        prepared = prepare_epoch_detection_input(
            epochs, pick_types_options={"eeg": True},
            filter_low=filter_low, filter_high=filter_high, resample_rate=resample_rate,
        )
        gt_annotations = load_gt_annotations_for_pair(pair, epoch_duration_s, valid_epoch_indices)
        n_channels = len(prepared.channel_names)

        for cond in conditions:
            try:
                ch_results = _CONDITION_RUNNERS[cond](prepared, valid_epoch_indices, detector_settings)
                center = _CENTER_METHOD.get(cond, "n/a")
                scored = evaluate_channels(
                    ch_results, gt_annotations, epoch_duration=epoch_duration_s
                )
                em = scored.best_eval_result.event_metrics

                rows.append({
                        "dataset": pair["dataset"], "session": pair["name"],
                        "selection": group_name, "condition": cond, "center_method": center,
                        "n_channels_used": n_channels,
                        "best_channel": scored.best_channel,
                        "tp": em.tp, "fp": em.fp, "fn": em.fn,
                        "precision": em.precision, "recall": em.recall, "f1": em.f1,
                    })
            except Exception as exc:  # noqa: BLE001
                errs.append(f"ERROR  {pair['name']} [{group_name}] {cond}: {exc}")

    except Exception as exc:  # noqa: BLE001
        errs.append(f"ERROR  {pair['name']} [{group_name}] (load): {exc}")

    return rows, errs


def process_one_session(
    pair: dict,
    *,
    groups_filter: set[str] | None,
    session_kwargs: dict,
) -> tuple[str, list[dict], list[str]]:
    """Worker: run every selected channel group x condition for one session.

    Picklable, top-level — safe to dispatch to a ProcessPoolExecutor.  Returns
    (session_name, metric_rows, error_messages).
    """
    region_yaml = session_kwargs["region_yaml"]
    region_map = load_brain_region_map(region_yaml)
    brain_channels = load_brain_region_channels(region_yaml)

    raw_meta = mne.io.read_raw_fif(str(pair["fif"]), preload=False, verbose="ERROR")
    available = resolve_channel_names(brain_channels, raw_meta.ch_names)
    groups = build_selection_groups(region_map, available, include_single_frontal=True)
    if groups_filter is not None:
        groups = {name: chs for name, chs in groups.items() if name in groups_filter}
    all_rows: list[dict] = []
    all_errs: list[str] = []
    for group_name, group_chs in groups.items():
        rows, errs = _run_one_group_all_conditions(
            pair, group_name, group_chs,
            epoch_duration_s=session_kwargs["epoch_duration_s"],
            filter_low=session_kwargs["filter_low"],
            filter_high=session_kwargs["filter_high"],
            resample_rate=session_kwargs["resample_rate"],
            conditions=session_kwargs["conditions"],
            detector_settings=session_kwargs["detector_settings"],
        )
        all_rows.extend(rows)
        all_errs.extend(errs)

    return pair["name"], all_rows, all_errs


def run_strategy_comparison_session_sweep(
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
    are skipped (loaded from cache) unless ``overwrite`` is True.
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


def _summary_by_condition(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (condition, selection, channel_in_group)."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["condition"], r["selection"], r.get("channel_in_group", "unknown"))].append(r)

    def _mean(bucket: list[dict], key: str) -> float:
        vals = [b[key] for b in bucket if key in b and isinstance(b[key], (int, float))]
        return float(np.mean(vals)) if vals else float("nan")

    out: list[dict] = []
    for (cond, sel, ch), bucket in buckets.items():
        out.append({
            "dataset": dataset_label,
            "condition": cond,
            "selection": sel,
            "channel_in_group": ch,
            "n_sessions": len(bucket),
            "det_precision": _mean(bucket, "precision"),
            "det_recall": _mean(bucket, "recall"),
            "det_f1": _mean(bucket, "f1"),
        })
    cond_order = {c: i for i, c in enumerate(dict.fromkeys(r["condition"] for r in records))}
    out.sort(key=lambda r: (cond_order.get(r["condition"], 99), r["selection"], r["channel_in_group"]))
    return out


def exp2_write_results(
    *,
    out_dir: Path,
    dataset: str,
    all_metrics: list[dict],
    errors: list[str],
    epoch_duration_s: float,
    groups_run: set[str] | None,
    n_sessions: int,
) -> None:
    """Coerce ``all_metrics``, then write the exp2 per-dataset results CSV, summary CSV,
    summary.json, and print the summary table.

    Shared by exp2_a_strategy_comparison_cao2018.py and exp2_a_strategy_comparison_raja.py
    so the two scripts produce identically-shaped outputs, and so
    update_exp2_latex.py's input schema stays stable.
    """

    df = pd.DataFrame(all_metrics)
    df.to_csv(
        out_dir / f"exp2_strategy_comparison_{dataset}_results.csv",
        index=False,
        )
    print(df)
    print(f"\nResults written to: {out_dir}")


__all__ = ["process_one_session", "run_strategy_comparison_session_sweep", "exp2_write_results"]
