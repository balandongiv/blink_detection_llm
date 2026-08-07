"""Shared per-session worker for the exp4 per-dataset boundary-tolerance sweep scripts.

Run order:
  1. exp4_a_boundary_tolerance_cao2018.py / exp4_a_boundary_tolerance_raja.py
     collect per-session rows across every IoU threshold.
  2. exp4_write_results() writes the exp4 per-dataset result artifacts.

Both scripts call run_boundary_tolerance_session_sweep() (below), which dispatches
process_one_session() — Proposed-Med is detected ONCE per (session, channel group)
via pyblinker.double_thresholding.blink_position_strategy_dbo, then the SAME
channel_results are re-scored at every IoU threshold in iou_thresholds (cheap sweep,
no re-detection) — to a ProcessPoolExecutor (or runs it in-process when n_jobs=1),
mirroring src/exp/exp2_channel_group_sweep.py's role for the exp2 scripts.
process_one_session is called directly by name (never through a generic Callable
parameter or functools.partial) so debugger step-into / IDE go-to-definition on
that call lands here.
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
from pyblinker.double_thresholding import blink_position_strategy_dbo

from blink_evaluation import evaluate_channels
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import (
    load_brain_region_channels,
    load_brain_region_map,
    resolve_channel_names,
)
from src.utils.channel_ablation_utils import build_selection_groups
from src.utils.experiment_utils import load_gt_annotations_for_pair
from src.utils.session_sweep import resolve_n_jobs, split_cached_and_todo, store_session_result

logger = logging.getLogger(__name__)


def _run_one_group(
    pair: dict,
    group_name: str,
    group_chs: list[str],
    *,
    epoch_duration_s: float,
    filter_low: float,
    filter_high: float,
    resample_rate: float,
    center_method: str,
    std_threshold: float,
    min_flagged_epochs: int,
    autoreject_random_state: int,
    iou_thresholds: list[float],
) -> tuple[list[dict], list[str]]:
    """Detect once on one (session, channel group); re-score at every IoU threshold."""
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

        setting = {
            "autoreject_random_state": autoreject_random_state,
            "std_threshold": std_threshold,
            "center_method": center_method,
            "min_flagged_epochs": min_flagged_epochs,
            "verbose": False,
        }
        channel_results = blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)

        for iou in iou_thresholds:
            try:
                scored = evaluate_channels(
                    channel_results, gt_annotations,
                    epoch_duration=epoch_duration_s, iou_threshold=iou,
                )
                for rec in scored.lane_summary.to_dict("records"):
                    rows.append({
                        "dataset": pair["dataset"], "session": pair["name"],
                        "selection": group_name, "center_method": center_method,
                        "iou_threshold": float(iou), "n_channels_used": n_channels,
                        **rec,
                    })
            except Exception as exc:  # noqa: BLE001
                errs.append(f"ERROR  {pair['name']} [{group_name}] iou={iou}: {exc}")

    except Exception as exc:  # noqa: BLE001
        errs.append(f"ERROR  {pair['name']} [{group_name}] (load): {exc}")

    return rows, errs


def process_one_session(
    pair: dict,
    *,
    groups_filter: set[str] | None,
    session_kwargs: dict,
) -> tuple[str, list[dict], list[str]]:
    """Worker: run every selected channel group, re-scored at every IoU threshold.

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
        rows, errs = _run_one_group(
            pair, group_name, group_chs,
            epoch_duration_s=session_kwargs["epoch_duration_s"],
            filter_low=session_kwargs["filter_low"],
            filter_high=session_kwargs["filter_high"],
            resample_rate=session_kwargs["resample_rate"],
            center_method=session_kwargs["center_method"],
            std_threshold=session_kwargs["std_threshold"],
            min_flagged_epochs=session_kwargs["min_flagged_epochs"],
            autoreject_random_state=session_kwargs["autoreject_random_state"],
            iou_thresholds=session_kwargs["iou_thresholds"],
        )
        all_rows.extend(rows)
        all_errs.extend(errs)

    return pair["name"], all_rows, all_errs


def run_boundary_tolerance_session_sweep(
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
    cached CSV covers every IoU threshold, so resume is all-or-nothing per
    session, not per (session, threshold).
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


def _summary_by_iou(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (iou_threshold, selection, channel)."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["iou_threshold"], r["selection"], r["channel"])].append(r)

    def _mean(bucket: list[dict], key: str) -> float:
        vals = [float(b[key]) for b in bucket if key in b and b[key] != ""]
        return float(np.mean(vals)) if vals else float("nan")

    out: list[dict] = []
    for (iou, sel, ch), bucket in buckets.items():
        out.append({
            "dataset": dataset_label,
            "iou_threshold": float(iou),
            "selection": sel,
            "channel": ch,
            "n_sessions": len(bucket),
            "precision": _mean(bucket, "precision"),
            "recall": _mean(bucket, "recall"),
            "f1": _mean(bucket, "f1"),
        })
    out.sort(key=lambda r: (r["iou_threshold"], r["selection"], r["channel"]))
    return out


def exp4_write_results(
    *,
    out_dir: Path,
    dataset: str,
    all_metrics: list[dict],
    errors: list[str],
    groups_run: set[str] | None,
    n_sessions: int,
) -> None:
    """Coerce ``all_metrics``, then write the exp4 per-dataset results CSV, summary CSV,
    summary.json, and print the IoU-summary table.

    Shared by exp4_a_boundary_tolerance_cao2018.py and exp4_a_boundary_tolerance_raja.py
    so the two scripts produce identically-shaped outputs.
    """
    df = pd.DataFrame(all_metrics)
    df.to_csv(out_dir / f"exp4_boundary_tolerance_{dataset}_results.csv", index=False)

    summary_rows = _summary_by_iou(all_metrics, dataset)
    pd.DataFrame(summary_rows).to_csv(
        out_dir / f"exp4_boundary_tolerance_{dataset}_summary.csv", index=False
    )

    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp4_boundary_tolerance_{dataset}",
        "groups_run": sorted(groups_run) if groups_run else None,
        "n_sessions": int(n_sessions),
        "n_rows": int(len(all_metrics)),
        "n_errors": int(len(errors)),
    }, indent=2), encoding="utf-8")

    header = (f"{'iou':>5}  {'selection':<16}  {'channel':<10}  "
              f"{'P':>7}  {'R':>7}  {'F1':>7}  {'N':>3}")
    print(f"\n{header}")
    print("-" * len(header))
    for r in summary_rows:
        print(f"{r['iou_threshold']:>5.2f}  {r['selection']:<16}  {r['channel']:<10}  "
              f"{r['precision']:>7.4f}  {r['recall']:>7.4f}  {r['f1']:>7.4f}  {r['n_sessions']:>3}")
    print(f"\nResults written to: {out_dir}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


__all__ = ["process_one_session", "run_boundary_tolerance_session_sweep", "exp4_write_results"]
