"""Shared per-session worker for the exp8 per-dataset long-blink-recall sweep scripts.

Per session, per channel-selection group: prepares the group's channel subset once,
then runs every detector condition (BLINKER-concat, MNE-annot, Proposed-Mean,
Proposed-Med — src/exp/exp2_strategy_conditions.py, the exp2 single source of
truth for condition definitions) on it, and re-scores each condition's detections
against three ground-truth subsets — all blinks, normal (< long_threshold_s), and
long (>= long_threshold_s) — via blink_evaluation.evaluate_channels(). Recall is the
primary metric: false positives are inflated for any single subset since a
detection matching the *other* duration type still counts against it, so
precision/F1 for the normal/long rows should not be read as independent of one
another.

Run order:
  1. exp8_a_long_blink_analysis_cao2018.py / exp8_a_long_blink_analysis_raja.py
     collect per-session rows across every condition x channel group x blink
     category (all/normal/long).
  2. exp8_write_results() writes the exp8 per-dataset result artifacts.

Both scripts call run_long_blink_session_sweep() (below), which dispatches
process_one_session() to a ProcessPoolExecutor (or runs it in-process when
n_jobs=1), mirroring src/exp/exp2_channel_group_sweep.py's role for the exp2
scripts. process_one_session is called directly by name (never through a
generic Callable parameter or functools.partial) so debugger step-into / IDE
go-to-definition on that call lands here.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import mne
import numpy as np
import pandas as pd

from blink_evaluation import evaluate_channels
from src.common.epoch_input import prepare_epoch_detection_input
from src.exp.exp2_strategy_conditions import _CONDITION_RUNNERS
from src.io.eeg_channels import (
    load_brain_region_channels,
    load_brain_region_map,
    resolve_channel_names,
)
from src.utils.channel_ablation_utils import build_selection_groups
from src.utils.condition_runner_utils import annotations_from_reference, reference_dataframe
from src.utils.session_sweep import resolve_n_jobs, split_cached_and_todo, store_session_result

logger = logging.getLogger(__name__)


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
    long_threshold_s: float,
) -> tuple[list[dict], list[str]]:
    """Run every exp8 condition on one (session, channel group); score against
    all/normal/long ground-truth subsets."""
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
        n_channels = len(prepared.channel_names)

        ref = reference_dataframe(pair, epoch_duration_s)
        ref = ref[ref["epoch_index"].isin(valid_epoch_indices)].reset_index(drop=True)
        is_long = ref["blink_duration"] >= long_threshold_s
        ref_normal, ref_long = ref[~is_long], ref[is_long]
        n_normal_gt, n_long_gt = int((~is_long).sum()), int(is_long.sum())

        gt_by_category = {
            "all":    annotations_from_reference(ref,        epoch_duration_s),
            "normal": annotations_from_reference(ref_normal, epoch_duration_s),
            "long":   annotations_from_reference(ref_long,   epoch_duration_s),
        }

        for cond in conditions:
            try:
                ch_results = _CONDITION_RUNNERS[cond](prepared, valid_epoch_indices, detector_settings)
                for category, gt in gt_by_category.items():
                    scored = evaluate_channels(
                        ch_results, gt, epoch_duration=epoch_duration_s
                    )
                    em = scored.best_eval_result.event_metrics
                    rows.append({
                        "dataset": pair["dataset"], "session": pair["name"],
                        "selection": group_name, "condition": cond, "blink_category": category,
                        "n_channels_used": n_channels,
                        "n_normal_gt": n_normal_gt, "n_long_gt": n_long_gt,
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
    """Worker: run every selected channel group x condition x blink category for
    one session.

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
            long_threshold_s=session_kwargs["long_threshold_s"],
        )
        all_rows.extend(rows)
        all_errs.extend(errs)

    return pair["name"], all_rows, all_errs


def run_long_blink_session_sweep(
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


def _summary_by_condition_category(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (condition, blink_category, selection, channel_in_group)."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["condition"], r["blink_category"], r["selection"], r["best_channel"])].append(r)

    def _mean(bucket: list[dict], key: str) -> float:
        vals = [float(b[key]) for b in bucket if key in b and b[key] != ""]
        return float(np.mean(vals)) if vals else float("nan")

    out: list[dict] = []
    for (cond, category, sel, ch), bucket in buckets.items():
        out.append({
            "dataset": dataset_label,
            "condition": cond,
            "blink_category": category,
            "selection": sel,
            "channel": ch,
            "n_sessions": len(bucket),
            "precision": _mean(bucket, "precision"),
            "recall": _mean(bucket, "recall"),
            "f1": _mean(bucket, "f1"),
        })
    out.sort(key=lambda r: (r["condition"], r["blink_category"], r["selection"], r["channel"]))
    return out


def exp8_write_results(
    *,
    out_dir: Path,
    dataset: str,
    all_metrics: list[dict],
    errors: list[str],
    long_threshold_s: float,
    groups_run: set[str] | None,
    n_sessions: int,
) -> None:
    """Coerce ``all_metrics``, then write the exp8 per-dataset results CSV, summary CSV,
    summary.json, and print the recall-by-category table.

    Shared by exp8_a_long_blink_analysis_cao2018.py and
    exp8_a_long_blink_analysis_raja.py so the two scripts produce identically-
    shaped outputs.
    """
    df = pd.DataFrame(all_metrics)
    df.to_csv(out_dir / f"exp8_long_blink_{dataset}_results.csv", index=False)

    summary_rows = _summary_by_condition_category(all_metrics, dataset)
    pd.DataFrame(summary_rows).to_csv(
        out_dir / f"exp8_long_blink_{dataset}_summary.csv", index=False
    )

    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp8_long_blink_{dataset}",
        "long_threshold_s": float(long_threshold_s),
        "groups_run": sorted(groups_run) if groups_run else None,
        "n_sessions": int(n_sessions),
        "n_rows": int(len(all_metrics)),
        "n_errors": int(len(errors)),
    }, indent=2), encoding="utf-8")

    header = (f"{'condition':<16}  {'category':<7}  {'selection':<16}  {'channel':<10}  "
              f"{'P':>7}  {'R':>7}  {'F1':>7}  {'N':>3}")
    print(f"\n{header}")
    print("-" * len(header))
    for r in summary_rows:
        print(f"{r['condition']:<16}  {r['blink_category']:<7}  {r['selection']:<16}  "
              f"{r['channel']:<10}  {r['precision']:>7.4f}  {r['recall']:>7.4f}  "
              f"{r['f1']:>7.4f}  {r['n_sessions']:>3}")
    print(f"\nResults written to: {out_dir}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


__all__ = ["process_one_session", "run_long_blink_session_sweep", "exp8_write_results"]
