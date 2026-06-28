"""Shared Telegram reporting helpers for Exp3–8.

Call ``per_group_telegram_message()`` at the end of each experiment's main()
to produce a message that covers:
  - Combined channel groups (frontal, frontal_left, frontal_right)
  - Single-channel groups (single:*)
  - Inversions: channel groups where a single channel outperforms frontal
    at the reference parameter value.

Usage example (Exp3 epoch-duration sweep)::

    from experiment_script.exp_tg_report import per_group_telegram_message, send_telegram_chunked
    msg = per_group_telegram_message(
        tag="[Exp3 Raja] COMPLETE",
        summary_rows=summary_rows,    # list[dict] with keys: selection, det_f1, ...
        param_col="epoch_duration_s", # column that identifies the swept parameter
        param_fmt=lambda v: f"{int(float(v))}s",
        ref_val=30.0,                 # reference value (starred in output)
        center_method="median",       # filter rows by center_method; None = no filter
        errors=errors,
        elapsed_min=elapsed_min,
        n_sessions=len(pairs),
        n_tasks=len(pairs) * len(EPOCH_DURATIONS),
    )
    send_telegram_chunked(REPO_ROOT, msg)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

import numpy as np


def _macro(vals: list[float]) -> float:
    return float(np.mean(vals)) if vals else float("nan")


def per_group_telegram_message(
    *,
    tag: str,
    summary_rows: list[dict],
    param_col: str,
    param_fmt: Callable[[Any], str],
    ref_val: Any,
    center_method: str | None = None,
    errors: list,
    elapsed_min: float,
    n_sessions: int,
    n_tasks: int | None = None,
) -> str:
    """Build a Telegram message with full per-channel-group breakdown.

    Parameters
    ----------
    tag : str
        Message header, e.g. "[Exp3 Raja] COMPLETE".
    summary_rows : list[dict]
        Macro-averaged rows from the experiment summary CSV.
        Must contain keys: ``selection``, ``det_f1``, ``det_precision``,
        ``det_recall``, and ``param_col``.
    param_col : str
        Name of the column holding the swept parameter (e.g. "epoch_duration_s").
    param_fmt : callable
        Function that converts a param value to a short display string.
    ref_val : Any
        The reference/baseline value of the swept parameter.
    center_method : str or None
        If given, only rows with ``center_method == center_method`` are shown.
    errors : list
        List of error strings accumulated during the run.
    elapsed_min : float
        Total elapsed minutes.
    n_sessions : int
        Number of EEG sessions processed.
    n_tasks : int or None
        Total number of tasks (sessions × param values). None if same as n_sessions.
    """
    if center_method is not None:
        rows = [r for r in summary_rows if r.get("center_method") == center_method]
    else:
        rows = list(summary_rows)

    # Collect all selections present in the rows.
    all_sels: set[str] = {r["selection"] for r in rows}
    combined_sels = [s for s in ["frontal", "frontal_left", "frontal_right"] if s in all_sels]
    single_sels   = sorted(s for s in all_sels if s.startswith("single:"))

    def _block(sels: list[str], header: str) -> str:
        lines = [header]
        for sel in sels:
            sel_rows = sorted(
                [r for r in rows if r["selection"] == sel],
                key=lambda r: str(r.get(param_col, "")),
            )
            cells: list[str] = []
            for r in sel_rows:
                pv = r.get(param_col, "?")
                is_ref = _values_equal(pv, ref_val)
                label = param_fmt(pv) + ("*" if is_ref else "")
                f1 = r.get("det_f1", float("nan"))
                try:
                    f1 = float(f1)
                except (TypeError, ValueError):
                    f1 = float("nan")
                cells.append(f"{label}:{f1:.3f}")
            lines.append(f"  {sel:<16}: {' '.join(cells)}")
        return "\n".join(lines)

    # Inversions: single channel that matches or beats frontal at reference param value.
    ref_frontal_f1: float = float("nan")
    for r in rows:
        if r["selection"] == "frontal" and _values_equal(r.get(param_col), ref_val):
            try:
                ref_frontal_f1 = float(r["det_f1"])
            except (TypeError, ValueError):
                pass
            break

    inv_lines: list[str] = []
    if not np.isnan(ref_frontal_f1):
        for sel in single_sels:
            for r in rows:
                if r["selection"] == sel and _values_equal(r.get(param_col), ref_val):
                    try:
                        f1 = float(r["det_f1"])
                    except (TypeError, ValueError):
                        f1 = float("nan")
                    if not np.isnan(f1) and f1 >= ref_frontal_f1:
                        inv_lines.append(
                            f"  {sel}: F1={f1:.4f} >= frontal {ref_frontal_f1:.4f}"
                            f" (P={float(r.get('det_precision', float('nan'))):.3f}"
                            f" R={float(r.get('det_recall', float('nan'))):.3f})"
                        )
                    break

    task_str = f"  Tasks: {n_tasks}" if n_tasks is not None and n_tasks != n_sessions else ""
    header = (
        f"{tag}\n"
        f"Sessions: {n_sessions}{task_str}  Errors: {len(errors)}"
        f"  Elapsed: {elapsed_min:.1f} min\n"
        f"Reference param: {param_fmt(ref_val)} (*=ref)\n"
    )

    parts = [header]
    if combined_sels:
        parts.append(_block(combined_sels, "=== Combined channel groups ==="))
    if single_sels:
        parts.append(_block(single_sels, "=== Single channels ==="))

    if inv_lines:
        parts.append("*** INVERSIONS: single ch >= frontal at ref param ***")
        parts.extend(inv_lines)
    else:
        parts.append("No inversions: frontal leads all single channels at ref param.")

    return "\n".join(parts)


def send_telegram_chunked(repo_root, message: str) -> None:
    """Send message to Telegram, splitting at 4000-char boundaries."""
    import urllib.parse, urllib.request
    from pathlib import Path
    token_path = Path(repo_root) / "bot_telegram.md"
    if not token_path.exists():
        return
    token = token_path.read_text(encoding="utf-8").strip()
    chat_id = "7784180158"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": chunk}).encode()
        try:
            urllib.request.urlopen(url, data=data, timeout=10)
        except Exception:
            pass


def _values_equal(a: Any, b: Any) -> bool:
    """Compare param values with type coercion (handles str vs float)."""
    try:
        return abs(float(str(a)) - float(str(b))) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)
