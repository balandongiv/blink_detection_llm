"""Shared per-session worker and result-writing for the exp1 channel-selection scripts.

Run order:
  1. exp1_channel_selection_raja.py / exp1_channel_selection_cao2018.py
     collect per-session rows.
  2. exp1_write_results() writes the exp1 result artifacts.
  3. exp1_step_b_get_best_region_channel.py reads the summary CSVs and selects the
     top 4 single channels plus top 4 regional groups.

Both exp1_channel_selection_cao2018.py and exp1_channel_selection_raja.py run
every selected channel group for one session in a picklable, top-level
function so it can be dispatched to a ProcessPoolExecutor, then coerce the
collected rows and write a results CSV + summary CSV + summary.json in an
identical way. This module holds that single shared implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

from src.utils.channel_ablation_utils import run_one_session, selection_group_names, write_csv

NUMERIC_RESULT_KEYS = {
    "raw_candidate_count", "mapped_candidate_count", "n_channels_used", "n_valid",
    "tp", "fp", "fn", "precision", "recall", "f1",
}


def process_one_session(
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


def exp1_write_results(
    *,
    out_dir: Path,
    dataset: str,
    all_metrics: list[dict],
    errors: list[str],
    epoch_duration_s: float,
    resample_rate: float,
    use_epoch_health: bool,
    groups_filter: set[str] | None,
    n_sessions: int,
) -> None:
    """Coerce ``all_metrics``, then write the exp1 results CSV, summary CSV, and summary.json.

    Shared by exp1_channel_selection_cao2018.py and exp1_channel_selection_raja.py
    so the two scripts produce identically-shaped outputs.
    """
    if not all_metrics:
        print("No metrics collected.")
        for e in errors:
            print(e)
        return

    # Re-cast numeric fields from str when rows were read back from existing CSVs.
    coerced: list[dict] = []
    for r in all_metrics:
        row = dict(r)
        for k in NUMERIC_RESULT_KEYS:
            if k in row and isinstance(row[k], str):
                try:
                    row[k] = float(row[k])
                except ValueError:
                    pass
        coerced.append(row)

    results_csv = out_dir / f"exp1_channel_selection_{dataset}_results.csv"
    summary_csv = out_dir / f"exp1_channel_selection_{dataset}_summary.csv"
    write_csv(results_csv, coerced)

    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in coerced:
        key = (
            str(row.get("dataset", dataset)),
            str(row.get("selection", "")),
            str(row.get("channel", "")),
            str(row.get("center_method", "")),
        )
        grouped[key].append(row)

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else float("nan")

    def _num(row: dict, key: str) -> float:
        val = row.get(key)
        return float(val) if isinstance(val, (int, float)) else float("nan")

    center_order = {"median": 0, "mean": 1}
    summary_rows: list[dict] = []
    for (group_dataset, selection, channel, center_method), rows in sorted(
        grouped.items(),
        key=lambda item: (
            item[0][0],
            item[0][1],
            center_order.get(item[0][3], 99),
            item[0][2],
        ),
    ):
        summary_rows.append({
            "dataset": group_dataset,
            "selection": selection,
            "channel": channel,
            "center_method": center_method,
            "n_sessions": len(rows),
            "mean_n_channels": _mean([_num(r, "n_channels_used") for r in rows]),
            "precision": _mean([_num(r, "precision") for r in rows]),
            "recall": _mean([_num(r, "recall") for r in rows]),
            "f1": _mean([_num(r, "f1") for r in rows]),
        })

    write_csv(summary_csv, summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp1_channel_selection_{dataset}",
        "epoch_duration_s": float(epoch_duration_s),
        "resample_rate": resample_rate,
        "use_epoch_health": use_epoch_health,
        "groups_run": sorted(groups_filter) if groups_filter is not None else "all",
        "metric_primary": "f1 per (selection, channel, centre)",
        "n_sessions": n_sessions,
        "n_rows": len(coerced),
        "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)

    print(f"\nResults written to: {out_dir}")


__all__ = ["process_one_session", "exp1_write_results"]
