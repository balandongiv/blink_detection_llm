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
import logging
from pathlib import Path
from collections import defaultdict

from src.utils.channel_ablation_utils import run_one_session, selection_group_names, write_csv

logger = logging.getLogger(__name__)

NUMERIC_RESULT_KEYS = {
    "raw_candidate_count", "mapped_candidate_count", "n_channels_used", "n_valid",
    "tp", "fp", "fn", "precision", "recall", "f1",
    "n_flagged", "used_all_epochs",
    "blink_region_threshold", "threshold_center", "threshold_dispersion",
}

# Grouping keys (dataset, selection, channel, center_method) plus columns that
# are per-session identifiers, non-scalar, or handled specially and so are not
# folded into the summary via SUM_KEYS/MEAN_KEYS below.
_SUMMARY_GROUP_KEYS = ("dataset", "selection", "channel", "center_method")
_SUMMARY_EXCLUDE_KEYS = {
    *_SUMMARY_GROUP_KEYS,
    "session", "condition", "flagged_valid_epoch_indices",
    "precision", "recall", "f1", "used_all_epochs",
}

# Event/epoch counts are additive across sessions (pooled totals), so the
# summary sums them rather than averaging.
_SUMMARY_SUM_KEYS = {
    "raw_candidate_count", "mapped_candidate_count",
    "tp", "fp", "fn", "n_valid", "n_flagged",
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

    # All remaining lane headers (blink_region_threshold, threshold_center,
    # threshold_dispersion, n_channels_used, ...) get carried into the summary
    # as per-group means, so the summary CSV mirrors whatever columns
    # ``run_one_session`` currently produces. Event/epoch counts are pooled
    # via SUM instead (see _SUMMARY_SUM_KEYS); precision/recall/f1 are
    # replaced below by explicit micro/macro variants since a plain mean or
    # sum of per-session ratios is not a meaningful aggregate.
    all_row_keys: list[str] = []
    seen_keys: set[str] = set()
    for row in coerced:
        for k in row.keys():
            if k not in seen_keys:
                all_row_keys.append(k)
                seen_keys.add(k)
    mean_keys = [
        k for k in all_row_keys
        if k not in _SUMMARY_EXCLUDE_KEYS and k not in _SUMMARY_SUM_KEYS
    ]
    sum_keys = [k for k in all_row_keys if k in _SUMMARY_SUM_KEYS]

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
        summary_row = {
            "dataset": group_dataset,
            "selection": selection,
            "channel": channel,
            "center_method": center_method,
            "n_sessions": len(rows),
        }
        for k in sum_keys:
            summary_row[k] = sum(_num(r, k) for r in rows)
        for k in mean_keys:
            summary_row[k] = _mean([_num(r, k) for r in rows])

        # Macro: unweighted mean of each session's own precision/recall/f1 —
        # every session counts equally regardless of how many blinks it has.
        summary_row["precision_macro"] = _mean([_num(r, "precision") for r in rows])
        summary_row["recall_macro"] = _mean([_num(r, "recall") for r in rows])
        summary_row["f1_macro"] = _mean([_num(r, "f1") for r in rows])

        # Micro: precision/recall/f1 recomputed from the pooled tp/fp/fn —
        # sessions with more blink events dominate the pooled counts.
        tp_sum = summary_row["tp"]
        fp_sum = summary_row["fp"]
        fn_sum = summary_row["fn"]
        precision_micro = tp_sum / (tp_sum + fp_sum) if (tp_sum + fp_sum) else float("nan")
        recall_micro = tp_sum / (tp_sum + fn_sum) if (tp_sum + fn_sum) else float("nan")
        f1_micro = (
            2 * precision_micro * recall_micro / (precision_micro + recall_micro)
            if (precision_micro + recall_micro)
            else float("nan")
        )
        summary_row["precision_micro"] = precision_micro
        summary_row["recall_micro"] = recall_micro
        summary_row["f1_micro"] = f1_micro

        # used_all_epochs should be identical across every session in a group
        # (it's a property of the Stage-B fallback rule, not the session
        # itself); surface a loud "MIXED" marker if that invariant ever
        # breaks instead of silently averaging booleans into a fraction.
        used_all_epochs_values = {r.get("used_all_epochs") for r in rows}
        if len(used_all_epochs_values) == 1:
            summary_row["used_all_epochs"] = used_all_epochs_values.pop()
        else:
            logger.warning(
                "used_all_epochs is not consistent across sessions for "
                "%s/%s/%s/%s: %s",
                group_dataset, selection, channel, center_method,
                used_all_epochs_values,
            )
            summary_row["used_all_epochs"] = "MIXED"

        summary_rows.append(summary_row)

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
