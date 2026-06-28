"""Run Exp 1 (Raja) — channel-selection ablation — no argparse needed.

Just press the Play button in IntelliJ IDEA.

Configuration is read from experiment_script/setup/exp1_channel_selection_raja.yaml.
Output CSVs go to runs/exp1_channel_raja/.

Resume support
--------------
Set OVERWRITE = False  (the default) to skip sessions whose per-session CSV
already exists.  Set OVERWRITE = True to re-run everything from scratch.

Choosing which channel groups to run
-------------------------------------
Edit GROUPS_TO_RUN below.  The group names map to the conditions in
experiment_script/extende_experiment.md as follows:

  Group name (code)          Markdown label
  ─────────────────────────  ──────────────────────────────
  "all"                      All channels (baseline)
  "frontal"                  FL_FR  — frontal bilateral
  "frontal_left"             FL     — frontal left
  "frontal_right"            FR     — frontal right
  "central"                  CL_CR  — central bilateral
  "central_left"             CL     — central left
  "central_right"            CR     — central right
  "parietal"                 PL_PR  — parietal bilateral
  "parietal_left"            PL     — parietal left
  "parietal_right"           PR     — parietal right
  "occipital"                OR_OL  — occipital bilateral
  "occipital_left"           OL     — occipital left
  "occipital_right"          OR     — occipital right
  "posterior"                PL_PR_OR_OL — posterior bilateral
  "single:Fp1"               Single-channel: Fp1
  "single:Fp2"               Single-channel: Fp2
  "single:AF3"               Single-channel: AF3
  "single:AF4"               Single-channel: AF4
  ... (one entry per frontal electrode present in the recording)

  Note: the midline (NA) condition is intentionally not built — it would require
  adding a midline region key to brain_region_raja.yaml, which also folds those
  channels into the "all" baseline.

Examples
--------
Run ALL conditions (default):
    GROUPS_TO_RUN = None

Run only the "all channels" baseline:
    GROUPS_TO_RUN = {"all"}

Run the full frontal block (FL, FR, FL_FR):
    GROUPS_TO_RUN = {"frontal_left", "frontal_right", "frontal"}

Run every single-frontal-channel condition only:
    GROUPS_TO_RUN = {"single:Fp1", "single:Fp2", "single:AF3", "single:AF4",
                     "single:F3", "single:F4", "single:F7", "single:F8"}

Run only the regional group conditions (no single-channel sweep):
    GROUPS_TO_RUN = {"all", "frontal", "frontal_left", "frontal_right",
                     "central", "parietal", "occipital", "posterior"}
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Limit per-process BLAS/OpenMP threads so the process pool (N_JOBS below) scales
# cleanly across CPUs without oversubscription.  Must run before numpy/mne import.
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

# ---------------------------------------------------------------------------
# *** User-facing settings — edit these ***
# ---------------------------------------------------------------------------

# Output directory (relative to repo root).
OUT_DIR = Path("runs/exp1_channel_raja")

# Resume control. Leave False for power-outage / interruption resume: sessions
# that already have a complete per-session CSV are skipped, so re-running the same
# command simply continues where it stopped and never overwrites finished work.
# Set True ONLY for a deliberate full recompute (e.g. after changing GROUPS_TO_RUN).
OVERWRITE = False

# Quick-check limit: process only the first N discovered sessions.
# None  → all sessions (the real sweep).  1 → fast single-session smoke test.
MAX_SESSIONS = None

# CPU parallelism for the sweep: number of worker processes (one session each).
# None → use most cores (cpu_count - 1).  1 → serial (easiest to debug).
N_JOBS = 8  # Reduced to avoid Windows handle exhaustion

# Which channel groups to run.
# None              → run every group (all conditions from extende_experiment.md).
# set of strings   → run only those group names (see docstring mapping table above).
#
# Common recipes (uncomment one):
# GROUPS_TO_RUN = None                                          # ALL conditions
# GROUPS_TO_RUN = {"all"}                                       # baseline only
# GROUPS_TO_RUN = {"frontal_left"}                             # FL only
GROUPS_TO_RUN = None                                          # ALL conditions
# GROUPS_TO_RUN = {"all", "frontal", "frontal_left", "frontal_right",
#                  "central", "parietal", "occipital", "posterior"}  # regional only (no singles)
# GROUPS_TO_RUN = {"single:Fp1", "single:Fp2"}                 # specific single channels
# GROUPS_TO_RUN: set[str] | None = None

# ---------------------------------------------------------------------------
# Repo root on sys.path
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiment_script.channel_ablation_utils import (
    condition_summary_rows,
    print_condition_summary,
    run_one_session,
    selection_group_names,
    write_csv,
    DEFAULT_CENTER_METHODS,
    DEFAULT_RULES,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config from yaml
# ---------------------------------------------------------------------------

_CFG = load_exp_config(EXP_SETUP_DIR / "exp1_channel_selection_raja.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

DATASET          = _CFG["dataset"]
RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
EPOCH_DURATION_S = float(_CFG["epoch_duration_s"])
STD_THRESHOLD    = float(_CFG["std_threshold"])
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))


def _session_csv(out_dir: Path, session_name: str) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}.csv"


def _write_session_csv(path: Path, rows: list[dict]) -> None:
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
    # so that rows with different schemas (e.g. with/without stageA_* fields)
    # can coexist without DictWriter raising ValueError.
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


# Shared per-call parameters.  Each run_one_session call processes ONE group only;
# the worker below loops over a session's groups.  Module-level so it is available
# in the spawned worker processes on Windows.
_SESSION_KWARGS = dict(
    raja_region_yaml=RAJA_REGION_YAML,
    cao_region_yaml=CAO_REGION_YAML,
    epoch_duration_s=EPOCH_DURATION_S,
    std_threshold=STD_THRESHOLD,
    center_methods=DEFAULT_CENTER_METHODS,
    rules=DEFAULT_RULES,
    autoreject_random_state=42,
    filter_low=FILTER_LOW,
    filter_high=FILTER_HIGH,
    resample_rate=RESAMPLE_RATE,
    include_single_frontal=True,  # build single-channel groups; GROUPS_TO_RUN filters
    use_epoch_health=False,
    verbose=False,
)


def _resolve_n_jobs(n_tasks: int) -> int:
    """Number of worker processes: N_JOBS, or most cores when None, capped at n_tasks."""
    if N_JOBS is not None:
        n = max(1, int(N_JOBS))
    else:
        n = max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(n, n_tasks))


def _process_one_session(pair: dict) -> tuple[str, list[dict], list[str]]:
    """Worker: run every selected channel group for one session.

    Picklable, top-level — safe to dispatch to a ProcessPoolExecutor.  Returns
    (session_name, metric_rows, error_messages).
    """
    group_names = selection_group_names(
        pair,
        raja_region_yaml=RAJA_REGION_YAML,
        cao_region_yaml=CAO_REGION_YAML,
        include_single_frontal=True,
        groups_filter=GROUPS_TO_RUN,
    )
    rows: list[dict] = []
    errs: list[str] = []
    for group in group_names:
        try:
            rows.extend(run_one_session(pair, groups_filter={group}, **_SESSION_KWARGS))
        except Exception as exc:  # noqa: BLE001
            errs.append(f"ERROR  {pair['name']} [{group}]: {exc}")
    return pair["name"], rows, errs


def main() -> None:
    setup_tutorial_logging()
    out_dir = REPO_ROOT / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = discover_raja_pairs(_RAJA["annotation_base"], _RAJA["processed_base"])
    if not pairs:
        print("No Raja sessions found — check paths.yaml.")
        return

    logger.info("Raja sessions discovered: %d", len(pairs))
    if MAX_SESSIONS is not None:
        pairs = pairs[:MAX_SESSIONS]
        logger.info("MAX_SESSIONS=%d → limiting to %d session(s)", MAX_SESSIONS, len(pairs))

    all_metrics: list[dict] = []
    errors: list[str] = []

    # Resume: load already-finished sessions from cache; queue the rest.
    todo: list[dict] = []
    for pair in pairs:
        csv_path = _session_csv(out_dir, pair["name"])
        if not OVERWRITE and csv_path.is_file():
            logger.info("SKIP (cached): %s", pair["name"])
            with csv_path.open(encoding="utf-8") as fh:
                all_metrics.extend(list(csv.DictReader(fh)))
        else:
            todo.append(pair)

    def _store(name: str, rows: list[dict], errs: list[str]) -> None:
        errors.extend(errs)
        if rows:
            _write_session_csv(_session_csv(out_dir, name), rows)
            all_metrics.extend(rows)
        logger.info("done %s -> %d rows%s", name, len(rows),
                    f"  ({len(errs)} err)" if errs else "")

    if todo:
        n_jobs = _resolve_n_jobs(len(todo))
        logger.info("Running %d session(s) with n_jobs=%d (of %d cpus)",
                    len(todo), n_jobs, os.cpu_count() or 1)
        if n_jobs == 1:
            for pair in todo:
                _store(*_process_one_session(pair))
        else:
            with ProcessPoolExecutor(max_workers=n_jobs) as ex:
                fut_map = {ex.submit(_process_one_session, pair): pair["name"]
                           for pair in todo}
                for fut in as_completed(fut_map):
                    name = fut_map[fut]
                    try:
                        _store(*fut.result())
                    except Exception as exc:  # noqa: BLE001
                        logger.error("ERROR  %s: %s", name, exc)
                        errors.append(f"ERROR  {name}: {exc}")

    if not all_metrics:
        print("No metrics collected.")
        for e in errors:
            print(e)
        return

    # Re-cast numeric fields from str when rows were read back from existing CSVs.
    numeric_keys = {
        "stageA_tp", "stageA_fp", "stageA_fn", "stageA_tn",
        "stageA_precision", "stageA_recall", "stageA_f1", "stageA_fpr",
        "pct_flagged", "n_flagged", "n_blink_epochs", "n_channels_used",
        "n_valid", "det_tp", "det_fp", "det_fn",
        "det_precision", "det_recall", "det_f1",
    }
    coerced: list[dict] = []
    for r in all_metrics:
        row = dict(r)
        for k in numeric_keys:
            if k in row and isinstance(row[k], str):
                try:
                    row[k] = float(row[k])
                except ValueError:
                    pass
        coerced.append(row)

    write_csv(out_dir / f"exp1_channel_selection_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows(coerced, DATASET)
    write_csv(out_dir / f"exp1_channel_selection_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp1_channel_selection_{DATASET}",
        "epoch_duration_s": EPOCH_DURATION_S,
        "resample_rate": RESAMPLE_RATE,
        "groups_run": sorted(GROUPS_TO_RUN) if GROUPS_TO_RUN is not None else "all",
        "metric_primary": "det_f1 + stageA_f1 per (selection, rule, centre)",
        "n_sessions": len(pairs),
        "n_rows": len(coerced),
        "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print_condition_summary(coerced, DATASET)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)

    print(f"\nResults written to: {out_dir}")


if __name__ == "__main__":
    main()
