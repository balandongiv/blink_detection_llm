"""Run Exp 3 (Cao2018) — epoch-duration sensitivity — no argparse needed.

Just press the Play button in IntelliJ IDEA.

What this experiment tests
--------------------------
Tests whether the pipeline produces stable detection performance when the epoch
grid is changed.  The same set of best channels (from Exp 1) is used; only the
epoch duration varies across {10, 20, 30, 40, 50, 60, 120} seconds.

The 30-second duration is the reference (selected by the experimental design).
A robust detector should show similar det_f1 across durations.

Configuration is read from experiment_script/setup/exp3_epoch_duration.yaml.
Output CSVs go to runs/exp3_cao/.

How to change settings
-----------------------
  EPOCH_DURATIONS       — list of durations to sweep (seconds)
  REFERENCE_EPOCH_DUR_S — reference duration (30 s)
  GROUPS_TO_RUN         — best channels from Exp 1 (Cao2018)
  HEARTBEAT_EVERY_S     — Telegram heartbeat interval in seconds (default 900)

Resume support
--------------
Each (session, epoch_duration) combination has its own CSV:
  runs/exp3_cao/sessions/<session>__<N>s.csv

Output columns (beyond Exp1 baseline)
--------------------------------------
  epoch_duration_s  — epoch length used for this row
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

# ---------------------------------------------------------------------------
# *** User-facing settings — edit these ***
# ---------------------------------------------------------------------------

OUT_DIR = Path("runs/exp3_cao")

OVERWRITE = False

MAX_SESSIONS = None

N_JOBS = 8  # Reduced to avoid Windows handle exhaustion

# Telegram heartbeat interval in seconds (900 = 15 minutes).
HEARTBEAT_EVERY_S = 900

# Epoch durations to sweep (seconds).  30 is the reference.
EPOCH_DURATIONS = [10, 20, 30, 40, 50, 60, 120]

REFERENCE_EPOCH_DUR_S = 30.0

# Fixed best channels from Exp 1 (Cao2018).
GROUPS_TO_RUN = {
    "single:FP1", "single:FP2",
    "frontal", "frontal_left", "frontal_right",
}

DATASET = "cao2018"

# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiment_script.channel_ablation_utils import (
    run_one_session,
    selection_group_names,
    write_csv,
    DEFAULT_CENTER_METHODS,
    DEFAULT_RULES,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import discover_cao_pairs, setup_tutorial_logging

logger = logging.getLogger(__name__)

_CFG = load_exp_config(EXP_SETUP_DIR / "exp3_epoch_duration.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
CAO_DATASET_ROOT = _CAO["dataset_root"]
STD_THRESHOLD    = float(_CFG["std_threshold"])
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))


def _session_csv(out_dir: Path, session_name: str, epoch_duration_s: float) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    dur  = int(epoch_duration_s)
    return out_dir / "sessions" / f"{safe}__{dur}s.csv"


def _write_session_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _resolve_n_jobs(n_tasks: int) -> int:
    if N_JOBS is not None:
        n = max(1, int(N_JOBS))
    else:
        n = max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(n, n_tasks))


def _process_one_task(task: tuple[dict, float]) -> tuple[str, float, list[dict], list[str]]:
    """Worker: run every selected channel group for one (session, epoch_duration) task."""
    pair, epoch_duration_s = task

    session_kwargs = dict(
        raja_region_yaml=RAJA_REGION_YAML,
        cao_region_yaml=CAO_REGION_YAML,
        epoch_duration_s=epoch_duration_s,
        std_threshold=STD_THRESHOLD,
        center_methods=DEFAULT_CENTER_METHODS,
        rules=DEFAULT_RULES,
        autoreject_random_state=42,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        include_single_frontal=True,
        use_epoch_health=False,
        verbose=False,
    )

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
            raw_rows = run_one_session(pair, groups_filter={group}, **session_kwargs)
            for r in raw_rows:
                r["epoch_duration_s"] = epoch_duration_s
            rows.extend(raw_rows)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"ERROR  {pair['name']} [{group}] {epoch_duration_s}s: {exc}")
    return pair["name"], epoch_duration_s, rows, errs


def _send_telegram(message: str) -> None:
    import urllib.parse
    import urllib.request
    token_path = REPO_ROOT / "bot_telegram.md"
    if not token_path.exists():
        return
    token = token_path.read_text(encoding="utf-8").strip()
    chat_id = "7784180158"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception:  # noqa: BLE001
        pass


def _send_telegram_chunked(message: str) -> None:
    """Send Telegram message, splitting into <=4000-char chunks if needed."""
    import urllib.parse
    import urllib.request
    token_path = REPO_ROOT / "bot_telegram.md"
    if not token_path.exists():
        return
    token = token_path.read_text(encoding="utf-8").strip()
    chat_id = "7784180158"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": chunk}).encode()
        try:
            urllib.request.urlopen(url, data=data, timeout=10)
        except Exception:  # noqa: BLE001
            pass


def _heartbeat_thread(
    stop_event: threading.Event,
    progress: dict,
    n_total: int,
    start_time: float,
) -> None:
    while not stop_event.wait(HEARTBEAT_EVERY_S):
        done = progress.get("done", 0)
        elapsed = time.time() - start_time
        eta_s = (elapsed / done * (n_total - done)) if done > 0 else float("nan")
        eta_min = eta_s / 60 if eta_s == eta_s else -1
        msg = (
            f"[Exp3 Cao2018] Heartbeat\n"
            f"  Progress: {done}/{n_total} tasks\n"
            f"  Elapsed:  {elapsed/60:.1f} min\n"
            f"  ETA:      {eta_min:.1f} min\n"
            f"  Latest:   {progress.get('latest', '?')}"
        )
        _send_telegram(msg)


def condition_summary_rows_with_duration(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (epoch_duration_s, selection, channel_in_group, rule, centre_method)."""
    from collections import defaultdict
    import numpy as np
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        ch = r.get("channel_in_group", r.get("best_channel", "unknown"))
        key = (r.get("epoch_duration_s", "?"), r["selection"], ch, r["rule"], r["center_method"])
        buckets[key].append(r)
    out: list[dict] = []
    for (dur, selection, ch, rule, center), bucket in buckets.items():
        def m(k: str) -> float:
            vals = [b[k] for b in bucket if k in b and isinstance(b[k], (int, float))]
            return float(np.mean(vals)) if vals else float("nan")
        out.append({
            "dataset": dataset_label,
            "epoch_duration_s": dur,
            "selection": selection,
            "channel_in_group": ch,
            "rule": rule, "center_method": center,
            "n_sessions": len(bucket),
            "det_precision": m("det_precision"),
            "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    out.sort(key=lambda r: (float(r["epoch_duration_s"]), r["selection"], r["channel_in_group"], r["rule"]))
    return out


def main() -> None:
    setup_tutorial_logging()
    out_dir = REPO_ROOT / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = discover_cao_pairs(CAO_DATASET_ROOT)
    if not pairs:
        print("No Cao2018 sessions found — check paths.yaml.")
        return

    logger.info("Cao2018 sessions discovered: %d", len(pairs))
    if MAX_SESSIONS is not None:
        pairs = pairs[:MAX_SESSIONS]

    all_metrics: list[dict] = []
    errors: list[str] = []

    todo: list[tuple[dict, float]] = []
    for pair in pairs:
        for dur in EPOCH_DURATIONS:
            csv_path = _session_csv(out_dir, pair["name"], float(dur))
            if not OVERWRITE and csv_path.is_file():
                logger.info("SKIP (cached): %s @%ds", pair["name"], dur)
                with csv_path.open(encoding="utf-8") as fh:
                    all_metrics.extend(list(csv.DictReader(fh)))
            else:
                todo.append((pair, float(dur)))

    progress = {"done": 0, "latest": ""}
    start_time = time.time()
    stop_evt = threading.Event()
    if todo:
        hb = threading.Thread(
            target=_heartbeat_thread,
            args=(stop_evt, progress, len(todo), start_time),
            daemon=True,
        )
        hb.start()

    def _store(name: str, dur: float, rows: list[dict], errs: list[str]) -> None:
        errors.extend(errs)
        if rows:
            _write_session_csv(_session_csv(out_dir, name, dur), rows)
            all_metrics.extend(rows)
        progress["done"] += 1
        progress["latest"] = f"{name}@{int(dur)}s"
        logger.info("done %s@%ds -> %d rows%s", name, int(dur), len(rows),
                    f"  ({len(errs)} err)" if errs else "")

    if todo:
        n_jobs = _resolve_n_jobs(len(todo))
        logger.info("Running %d tasks with n_jobs=%d (of %d cpus)",
                    len(todo), n_jobs, os.cpu_count() or 1)
        if n_jobs == 1:
            for task in todo:
                _store(*_process_one_task(task))
        else:
            with ProcessPoolExecutor(max_workers=n_jobs) as ex:
                fut_map = {ex.submit(_process_one_task, task): task for task in todo}
                for fut in as_completed(fut_map):
                    task = fut_map[fut]
                    try:
                        _store(*fut.result())
                    except Exception as exc:  # noqa: BLE001
                        name = task[0]["name"]
                        dur = task[1]
                        logger.error("ERROR  %s@%ds: %s", name, dur, exc)
                        errors.append(f"ERROR  {name}@{dur}s: {exc}")
                        progress["done"] += 1

    stop_evt.set()

    if not all_metrics:
        print("No metrics collected.")
        for e in errors:
            print(e)
        return

    numeric_keys = {
        "epoch_duration_s", "stageA_tp", "stageA_fp", "stageA_fn", "stageA_tn",
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

    write_csv(out_dir / f"exp3_epoch_duration_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows_with_duration(coerced, DATASET)
    write_csv(out_dir / f"exp3_epoch_duration_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp3_epoch_duration_{DATASET}",
        "epoch_durations": EPOCH_DURATIONS,
        "reference_epoch_duration_s": REFERENCE_EPOCH_DUR_S,
        "std_threshold": STD_THRESHOLD,
        "groups_run": sorted(GROUPS_TO_RUN),
        "n_sessions": len(pairs),
        "n_rows": len(coerced),
        "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print(f"EPOCH DURATION SENSITIVITY — {DATASET.upper()}  (reference={REFERENCE_EPOCH_DUR_S}s)")
    print("=" * 80)
    print(f"{'dur_s':>5}  {'selection':<16}  {'centre':<6}  "
          f"{'det_P':>7}  {'det_R':>7}  {'det_F1':>7}  {'N':>3}")
    print("-" * 80)
    for r in summary_rows:
        ref_marker = " *" if float(r["epoch_duration_s"]) == REFERENCE_EPOCH_DUR_S else ""
        print(f"{r['epoch_duration_s']:>5}{ref_marker:<2}  {r['selection']:<16}  "
              f"{r['center_method']:<6}  "
              f"{r['det_precision']:>7.4f}  {r['det_recall']:>7.4f}  {r['det_f1']:>7.4f}  "
              f"{r['n_sessions']:>3}")
    print("=" * 80)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)

    elapsed_min = (time.time() - start_time) / 60
    print(f"\nResults written to: {out_dir}  ({elapsed_min:.1f} min)")

    # Telegram: per-channel, per-duration breakdown + inversion check.
    ref_dur = REFERENCE_EPOCH_DUR_S
    median_rows = [r for r in summary_rows if r.get("center_method") == "median"]
    combined_sels = [s for s in ["frontal", "frontal_left", "frontal_right"]
                     if any(r["selection"] == s for r in median_rows)]
    single_sels   = sorted({r["selection"] for r in median_rows
                             if r["selection"].startswith("single:")})

    def _tg_block3c(sels, label):
        parts = [label]
        for sel in sels:
            channels = sorted({r["channel_in_group"] for r in median_rows if r["selection"] == sel})
            parts.append(f"  [{sel}]")
            for ch in channels:
                rows_ch = sorted(
                    [r for r in median_rows if r["selection"] == sel and r["channel_in_group"] == ch],
                    key=lambda r: float(r["epoch_duration_s"])
                )
                dur_parts = []
                for r in rows_ch:
                    dur = int(float(r["epoch_duration_s"]))
                    ref_mark = "*" if float(r["epoch_duration_s"]) == ref_dur else ""
                    dur_parts.append(f"{dur}s{ref_mark}:{r['det_f1']:.3f}")
                parts.append(f"    ch={ch}: {' '.join(dur_parts)}")
        return "\n".join(parts)

    # Inversions: any individual channel beat frontal's best channel at ref duration?
    ref_frontal_rows3c = [r for r in median_rows
                          if r["selection"] == "frontal"
                          and float(r["epoch_duration_s"]) == ref_dur]
    ref_frontal_best3c = max((float(r["det_f1"]) for r in ref_frontal_rows3c), default=None)
    inv_lines3c = []
    if ref_frontal_best3c is not None:
        for sel in single_sels:
            for ch_row in [r for r in median_rows
                           if r["selection"] == sel
                           and float(r["epoch_duration_s"]) == ref_dur]:
                if float(ch_row["det_f1"]) >= ref_frontal_best3c:
                    inv_lines3c.append(
                        f"  {sel}/{ch_row['channel_in_group']} "
                        f"F1={float(ch_row['det_f1']):.4f} >= frontal_best {ref_frontal_best3c:.4f}"
                    )

    tg_parts3c = [
        f"[Exp3 Cao2018] COMPLETE",
        f"Sessions: {len(pairs)}  Tasks: {len(pairs)*len(EPOCH_DURATIONS)}"
        f"  Errors: {len(errors)}  Elapsed: {elapsed_min:.1f} min",
        f"Reference: {int(ref_dur)}s (*=ref dur)",
        "", _tg_block3c(combined_sels, "=== Combined channel groups (per channel) ==="),
    ]
    if single_sels:
        tg_parts3c += ["", _tg_block3c(single_sels, "=== Single channels ===")]
    if inv_lines3c:
        tg_parts3c += ["", "*** INVERSIONS: single ch F1 >= best frontal channel at ref dur ***"] + inv_lines3c
    else:
        tg_parts3c.append("\nNo inversions: frontal leads all single channels at reference duration.")
    _send_telegram_chunked("\n".join(tg_parts3c))


if __name__ == "__main__":
    main()
