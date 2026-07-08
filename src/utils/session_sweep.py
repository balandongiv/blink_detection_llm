"""Resume-aware, multiprocess sweep over sessions with atomic per-session CSV caching.

Shared by the exp1 channel-selection scripts (and any future sweep that needs
crash-safe resume): each session's rows are cached to its own CSV under
``out_dir/sessions/`` so an interrupted run can be restarted without redoing
already-finished sessions or corrupting a partially written file.
"""
from __future__ import annotations

import csv
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

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
    """Number of worker processes: n_jobs, or most cores when None, capped at n_tasks."""
    if n_jobs is not None:
        n = max(1, int(n_jobs))
    else:
        n = max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(n, n_tasks))


def run_session_sweep(
    pairs: list[dict],
    out_dir: Path,
    process_one_session: Callable[[dict], tuple[str, list[dict], list[str]]],
    *,
    overwrite: bool = False,
    n_jobs: int | None = None,
) -> tuple[list[dict], list[str]]:
    """Run *process_one_session* over *pairs* with resume + crash-safe caching.

    ``process_one_session`` must be a picklable top-level callable (or a
    ``functools.partial`` wrapping one) — it is dispatched to a
    ``ProcessPoolExecutor`` and must not depend on parent-process state that
    isn't explicitly passed in.  It receives one *pair* and returns
    ``(session_name, metric_rows, error_messages)``.

    Sessions whose per-session CSV already exists under ``out_dir/sessions/``
    are skipped (loaded from cache) unless ``overwrite`` is True.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    all_metrics: list[dict] = []
    errors: list[str] = []

    todo: list[dict] = []
    for pair in pairs:
        csv_path = session_csv_path(out_dir, pair["name"])
        if not overwrite and csv_path.is_file():
            logger.info("SKIP (cached): %s", pair["name"])
            with csv_path.open(encoding="utf-8") as fh:
                all_metrics.extend(list(csv.DictReader(fh)))
        else:
            todo.append(pair)

    def _store(name: str, rows: list[dict], errs: list[str]) -> None:
        errors.extend(errs)
        if rows:
            write_session_csv(session_csv_path(out_dir, name), rows)
            all_metrics.extend(rows)
        logger.info("done %s -> %d rows%s", name, len(rows),
                    f"  ({len(errs)} err)" if errs else "")

    if todo:
        jobs = resolve_n_jobs(len(todo), n_jobs)
        logger.info("Running %d session(s) with n_jobs=%d (of %d cpus)",
                    len(todo), jobs, os.cpu_count() or 1)
        if jobs == 1:
            for pair in todo:
                _store(*process_one_session(pair))
        else:
            with ProcessPoolExecutor(max_workers=jobs) as ex:
                fut_map = {ex.submit(process_one_session, pair): pair["name"]
                           for pair in todo}
                for fut in as_completed(fut_map):
                    name = fut_map[fut]
                    try:
                        _store(*fut.result())
                    except Exception as exc:  # noqa: BLE001
                        logger.error("ERROR  %s: %s", name, exc)
                        errors.append(f"ERROR  {name}: {exc}")

    return all_metrics, errors
