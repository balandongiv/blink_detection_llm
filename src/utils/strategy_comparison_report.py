"""Console reporting for the exp2 strategy-comparison scripts.

Per-session table, per-condition summary table, and the summary rows written
to the summary CSV — split out of the experiment script so it stays focused
on running conditions and collecting results.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

__all__ = ["print_per_session_table", "print_summary_table", "summary_rows"]


def print_per_session_table(results: list[dict], dataset_name: str, conditions: list[str]) -> None:
    """Print per-session metrics for *dataset_name* grouped by session."""
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: (r["session"], conditions.index(r["condition"])))

    W_sess = max(len(r["session"]) for r in rows)
    W_sess = max(W_sess, 8)
    W_cond = 14
    header = (
        f"{'session':<{W_sess}}  {'condition':<{W_cond}}  "
        f"{'tp':>5}  {'fp':>5}  {'fn':>5}  "
        f"{'precision':>10}  {'recall':>8}  {'f1':>8}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"PER-SESSION RESULTS - {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    prev_session = None
    for r in rows:
        if prev_session and r["session"] != prev_session:
            print(sep)
        prev_session = r["session"]
        print(
            f"{r['session']:<{W_sess}}  {r['condition']:<{W_cond}}  "
            f"{r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  "
            f"{r['precision']:>10.4f}  {r['recall']:>8.4f}  {r['f1']:>8.4f}"
        )
    print(f"{'=' * len(header)}\n")


def summary_rows(results: list[dict], dataset_name: str, conditions: list[str]) -> list[dict]:
    """Return micro/macro metrics per condition for *dataset_name* (or 'all')."""
    rows = results if dataset_name == "all" else [
        r for r in results if r["dataset"] == dataset_name
    ]
    if not rows:
        return []

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r["condition"]].append(r)

    out: list[dict] = []
    for cond in conditions:
        if cond not in buckets:
            continue
        bucket = buckets[cond]
        total_tp = sum(r["tp"] for r in bucket)
        total_fp = sum(r["fp"] for r in bucket)
        total_fn = sum(r["fn"] for r in bucket)
        micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                    if (micro_p + micro_r) > 0 else 0.0)
        macro_p  = float(np.mean([r["precision"] for r in bucket]))
        macro_r  = float(np.mean([r["recall"]    for r in bucket]))
        macro_f1 = float(np.mean([r["f1"]        for r in bucket]))
        out.append({
            "dataset": dataset_name,
            "condition": cond,
            "n_sessions": int(len(bucket)),
            "tp": int(total_tp),
            "fp": int(total_fp),
            "fn": int(total_fn),
            "micro_precision": float(micro_p),
            "micro_recall": float(micro_r),
            "micro_f1": float(micro_f1),
            "macro_precision": float(macro_p),
            "macro_recall": float(macro_r),
            "macro_f1": float(macro_f1),
        })
    return out


def print_summary_table(results: list[dict], dataset_name: str, conditions: list[str]) -> None:
    """Print macro-F1 and micro-F1 per condition for *dataset_name* (or 'all')."""
    rows = summary_rows(results, dataset_name, conditions)
    if not rows:
        return

    header = (
        f"{'condition':<14}  {'N':>5}  "
        f"{'TP':>7}  {'FP':>7}  {'FN':>7}  "
        f"{'micro_P':>8}  {'micro_R':>8}  {'micro_F1':>8}  "
        f"{'macro_P':>8}  {'macro_R':>8}  {'macro_F1':>8}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"SUMMARY - {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for row in rows:
        print(
            f"{row['condition']:<14}  {row['n_sessions']:>5}  "
            f"{row['tp']:>7}  {row['fp']:>7}  {row['fn']:>7}  "
            f"{row['micro_precision']:>8.4f}  {row['micro_recall']:>8.4f}  {row['micro_f1']:>8.4f}  "
            f"{row['macro_precision']:>8.4f}  {row['macro_recall']:>8.4f}  {row['macro_f1']:>8.4f}"
        )
    print(f"{'=' * len(header)}\n")
