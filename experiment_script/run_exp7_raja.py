"""Run Exp 7 (Raja) — epoch-health filter effect — no argparse needed.

Just press the Play button in IntelliJ IDEA.

What this experiment tests
--------------------------
Compares two conditions:

  * use_epoch_health=False  — all epochs are used (baseline, matches Exp 1)
  * use_epoch_health=True   — only epochs passing the epoch-health filter are used

The epoch-health filter (``epoch_health.csv``) excludes low-quality epochs based
on signal quality metrics.  This experiment tests whether filtering improves or
degrades detection performance.

Configuration is read from experiment_script/setup/exp7_epoch_health_effect.yaml.
Output CSVs go to runs/exp7_raja/.

How to change settings
-----------------------
  USE_EPOCH_HEALTH_OPTIONS — [True, False] (run both conditions)
  GROUPS_TO_RUN            — best channels from Exp 1 (Raja)
  HEARTBEAT_EVERY_S        — Telegram heartbeat interval (default 900 s)

Resume support
--------------
Each (session, use_epoch_health) combination has its own CSV:
  runs/exp7_raja/sessions/<session>__health<0_or_1>.csv

Output columns (beyond Exp1 baseline)
--------------------------------------
  use_epoch_health  — True/False flag
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

OUT_DIR = Path("runs/exp7_raja")
OVERWRITE = False
MAX_SESSIONS = None
N_JOBS = 16  # 16 of 24 logical threads (i7-13700F)
HEARTBEAT_EVERY_S = 900

# Both conditions: with and without epoch-health filtering.
USE_EPOCH_HEALTH_OPTIONS = [False, True]

GROUPS_TO_RUN = {
    "single:E22", "single:E9", "single:E3", "single:E23",
    "frontal", "frontal_left", "frontal_right",
}

DATASET = "raja"

# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiment_script.channel_ablation_utils import (
    run_one_session, selection_group_names, write_csv,
    DEFAULT_CENTER_METHODS, DEFAULT_RULES,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

logger = logging.getLogger(__name__)

_CFG = load_exp_config(EXP_SETUP_DIR / "exp7_epoch_health_effect.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
EPOCH_DURATION_S = float(_CFG.get("epoch_duration_s", 30.0))
STD_THRESHOLD    = float(_CFG.get("std_threshold", 3.5))
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))


def _session_csv(out_dir, session_name, use_health):
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}__health{int(use_health)}.csv"


def _write_session_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: return
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
        fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)


def _resolve_n_jobs(n_tasks):
    n = max(1, int(N_JOBS)) if N_JOBS is not None else max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(n, n_tasks))


def _process_one_task(task):
    pair, use_health = task
    kw = dict(
        raja_region_yaml=RAJA_REGION_YAML, cao_region_yaml=CAO_REGION_YAML,
        epoch_duration_s=EPOCH_DURATION_S, std_threshold=STD_THRESHOLD,
        center_methods=DEFAULT_CENTER_METHODS, rules=DEFAULT_RULES,
        autoreject_random_state=42, filter_low=FILTER_LOW, filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE, include_single_frontal=True,
        use_epoch_health=use_health, verbose=False,
    )
    groups = selection_group_names(
        pair, raja_region_yaml=RAJA_REGION_YAML, cao_region_yaml=CAO_REGION_YAML,
        include_single_frontal=True, groups_filter=GROUPS_TO_RUN,
    )
    rows, errs = [], []
    for group in groups:
        try:
            raw_rows = run_one_session(pair, groups_filter={group}, **kw)
            for r in raw_rows:
                r["use_epoch_health"] = use_health
            rows.extend(raw_rows)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"ERROR  {pair['name']} [{group}] health={use_health}: {exc}")
    return pair["name"], use_health, rows, errs


def _send_telegram(message):
    import urllib.parse, urllib.request
    token_path = REPO_ROOT / "bot_telegram.md"
    if not token_path.exists(): return
    token = token_path.read_text(encoding="utf-8").strip()
    data = urllib.parse.urlencode({"chat_id": "7784180158", "text": message}).encode()
    try: urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=10)
    except Exception: pass


def _heartbeat_thread(stop_event, progress, n_total, start_time):
    while not stop_event.wait(HEARTBEAT_EVERY_S):
        done = progress.get("done", 0)
        elapsed = time.time() - start_time
        eta_s = (elapsed / done * (n_total - done)) if done > 0 else float("nan")
        _send_telegram(
            f"[Exp7 Raja] Heartbeat  {done}/{n_total}  "
            f"Elapsed {elapsed/60:.1f}min  ETA {eta_s/60:.1f}min"
        )


def condition_summary_rows_health(records, dataset_label):
    """Macro-average per (use_epoch_health, selection, channel_in_group, center_method)."""
    from collections import defaultdict
    import numpy as np
    buckets = defaultdict(list)
    for r in records:
        health_val = r.get("use_epoch_health", False)
        if isinstance(health_val, str):
            health_val = health_val.lower() == "true"
        ch = r.get("channel_in_group", r.get("best_channel", "unknown"))
        buckets[(bool(health_val), r["selection"], ch, r["center_method"])].append(r)
    out = []
    for (health, sel, ch, center), bucket in buckets.items():
        def m(k):
            vals = [b[k] for b in bucket if k in b and isinstance(b[k], (int, float))]
            return float(np.mean(vals)) if vals else float("nan")
        out.append({
            "dataset": dataset_label, "use_epoch_health": health, "selection": sel,
            "channel_in_group": ch, "center_method": center, "n_sessions": len(bucket),
            "det_precision": m("det_precision"), "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    out.sort(key=lambda r: (r["use_epoch_health"], r["selection"], r["channel_in_group"]))
    return out


def main():
    setup_tutorial_logging()
    out_dir = REPO_ROOT / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = discover_raja_pairs(_RAJA["annotation_base"], _RAJA["processed_base"])
    if not pairs:
        print("No Raja sessions found."); return
    if MAX_SESSIONS is not None:
        pairs = pairs[:MAX_SESSIONS]

    all_metrics, errors = [], []
    todo = []
    for pair in pairs:
        for use_health in USE_EPOCH_HEALTH_OPTIONS:
            cp = _session_csv(out_dir, pair["name"], use_health)
            if not OVERWRITE and cp.is_file():
                with cp.open(encoding="utf-8") as fh:
                    all_metrics.extend(list(csv.DictReader(fh)))
            else:
                todo.append((pair, use_health))

    progress = {"done": 0, "latest": ""}
    start_time = time.time()
    stop_evt = threading.Event()
    if todo:
        threading.Thread(target=_heartbeat_thread,
                         args=(stop_evt, progress, len(todo), start_time),
                         daemon=True).start()

    def _store(name, use_health, rows, errs):
        errors.extend(errs)
        if rows:
            _write_session_csv(_session_csv(out_dir, name, use_health), rows)
            all_metrics.extend(rows)
        progress["done"] += 1; progress["latest"] = f"{name} health={use_health}"

    if todo:
        n_jobs = _resolve_n_jobs(len(todo))
        if n_jobs == 1:
            for task in todo: _store(*_process_one_task(task))
        else:
            with ProcessPoolExecutor(max_workers=n_jobs) as ex:
                fut_map = {ex.submit(_process_one_task, t): t for t in todo}
                for fut in as_completed(fut_map):
                    try: _store(*fut.result())
                    except Exception as exc: errors.append(f"ERROR: {exc}"); progress["done"] += 1

    stop_evt.set()
    if not all_metrics:
        print("No metrics."); return

    numeric_keys = {
        "pct_flagged", "n_flagged", "n_blink_epochs",
        "n_channels_used", "n_valid", "det_tp", "det_fp", "det_fn",
        "det_precision", "det_recall", "det_f1",
    }
    coerced = []
    for r in all_metrics:
        row = dict(r)
        for k in numeric_keys:
            if k in row and isinstance(row[k], str):
                try: row[k] = float(row[k])
                except ValueError: pass
        # Normalise use_epoch_health to Python bool
        if "use_epoch_health" in row and isinstance(row["use_epoch_health"], str):
            row["use_epoch_health"] = row["use_epoch_health"].lower() == "true"
        coerced.append(row)

    write_csv(out_dir / f"exp7_epoch_health_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows_health(coerced, DATASET)
    write_csv(out_dir / f"exp7_epoch_health_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp7_epoch_health_{DATASET}", "epoch_duration_s": EPOCH_DURATION_S,
        "groups_run": sorted(GROUPS_TO_RUN),
        "n_sessions": len(pairs), "n_rows": len(coerced), "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    elapsed_min = (time.time() - start_time) / 60
    from experiment_script.exp_tg_report import per_group_telegram_message, send_telegram_chunked as _stc
    _tg7r = per_group_telegram_message(
        tag="[Exp7 Raja] COMPLETE",
        summary_rows=summary_rows,
        param_col="use_epoch_health",
        param_fmt=lambda v: f"health={v}",
        ref_val="False",
        center_method="median",
        errors=errors,
        elapsed_min=elapsed_min,
        n_sessions=len(pairs),
        n_tasks=len(pairs) * len(USE_EPOCH_HEALTH_OPTIONS),
    )
    _stc(REPO_ROOT, _tg7r)
    print(f"\nResults written to: {out_dir}  ({elapsed_min:.1f} min)")


if __name__ == "__main__":
    main()
