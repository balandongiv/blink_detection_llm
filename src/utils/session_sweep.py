"""Resume-aware, crash-safe session-sweep helpers shared by the concrete sweep runners.

Each experiment family (exp1 channel-selection, exp2 strategy-comparison, ...) owns a
concrete ``run_<family>_session_sweep()`` function, defined right next to its worker
(``process_one_session``) — see ``src/exp/session_worker.py`` and
``src/exp/exp2_channel_group_sweep.py``. Those runners call their worker directly by
name (module-level function reference, never a generic ``Callable`` parameter,
``functools.partial``, lambda, or dict/getattr-based lookup), so a debugger's "step
into" and an IDE's "go to definition" on the worker call always land in the real
implementation instead of some indirection layer.

This module holds only the small, worker-agnostic pieces those concrete runners
share: per-session CSV caching (crash-safe, atomic writes) and job-count resolution.
It intentionally has no knowledge of any specific worker.
"""
from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def session_csv_path(out_dir: Path, session_name: str) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}.csv"


def write_session_csv(path: Path, rows: list[dict]) -> None:
    """Write a session's rows atomically (temp file -> fsync -> os.replace).

    Power-outage safety: the final CSV appears only after a complete write, so a
    crash mid-write never leaves a partial file that resume would mistake for a
    finished session.  A leftover ``*.tmp`` from a crash is simply ignored on
    resume (only the final path is checked) and overwritten on the next attempt.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    # Build fieldnames as union of all row keys (preserving first-seen order)
    # so that rows with different schemas can coexist without DictWriter raising ValueError.
    all_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=all_keys, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)  # atomic on Windows and POSIX


def resolve_n_jobs(n_tasks: int, n_jobs: int | None) -> int:
    """Number of worker processes: n_jobs, or most cores when None, capped at n_tasks.

    Debugging note: pass ``n_jobs=1`` to keep a sweep entirely in the current
    process (no ``ProcessPoolExecutor``) so breakpoints inside the worker
    function actually fire — most debuggers cannot attach to the subprocess
    pool used when this resolves above 1.
    """
    if n_jobs is not None:
        n = max(1, int(n_jobs))
    else:
        n = max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(n, n_tasks))


def split_cached_and_todo(
    pairs: list[dict], out_dir: Path, overwrite: bool,
) -> tuple[list[dict], list[dict]]:
    """Return ``(cached_metric_rows, todo_pairs)``.

    A session whose per-session CSV already exists under ``out_dir/sessions/``
    is treated as cached (its rows are loaded from disk) unless ``overwrite``
    is True, in which case it's added to ``todo_pairs`` for a full recompute.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cached: list[dict] = []
    todo: list[dict] = []
    for pair in pairs:
        csv_path = session_csv_path(out_dir, pair["name"])
        if not overwrite and csv_path.is_file():
            logger.info("SKIP (cached): %s", pair["name"])
            with csv_path.open(encoding="utf-8") as fh:
                cached.extend(list(csv.DictReader(fh)))
        else:
            todo.append(pair)
    return cached, todo


def store_session_result(
    out_dir: Path,
    name: str,
    rows: list[dict],
    errs: list[str],
    *,
    all_metrics: list[dict],
    errors: list[str],
) -> None:
    """Append *rows*/*errs* to the running accumulators and cache *rows* to disk."""
    errors.extend(errs)
    if rows:
        write_session_csv(session_csv_path(out_dir, name), rows)
        all_metrics.extend(rows)
    logger.info("done %s -> %d rows%s", name, len(rows),
                f"  ({len(errs)} err)" if errs else "")


__all__ = [
    "session_csv_path",
    "write_session_csv",
    "resolve_n_jobs",
    "split_cached_and_todo",
    "store_session_result",
]
