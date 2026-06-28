"""Run Exp 5 (Raja) — min-flagged-epochs sensitivity — no argparse needed.

Just press the Play button in IntelliJ IDEA.

What this experiment tests
--------------------------
The ``min_flagged_epochs`` parameter controls the minimum number of suspicious
epochs required to proceed with threshold estimation in Stage B.  If too few
epochs are flagged by Stage A, the threshold cannot be reliably estimated, so
the pipeline falls back to using all valid epochs.

This experiment sweeps min_flagged_epochs across {1, 2, 3, 5} using the best
channel groups from Exp 1 (Raja) and the median centre (best from Exp 2).

Configuration is read from experiment_script/setup/exp5_nmin_sensitivity.yaml.
Output CSVs go to runs/exp5_raja/.

How to change settings
-----------------------
  NMIN_VALUES       — values of min_flagged_epochs to test
  GROUPS_TO_RUN     — best channels from Exp 1 (Raja)
  HEARTBEAT_EVERY_S — Telegram heartbeat interval in seconds (default 900)

Resume support
--------------
Each (session, nmin) combination has its own CSV:
  runs/exp5_raja/sessions/<session>__nmin<N>.csv

Output columns (beyond Exp1 baseline)
--------------------------------------
  min_flagged_epochs  — value used for this row
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

OUT_DIR = Path("runs/exp5_raja")

OVERWRITE = False

MAX_SESSIONS = None

N_JOBS = 16  # 16 of 24 logical threads (i7-13700F)

HEARTBEAT_EVERY_S = 900

# Values of min_flagged_epochs to sweep.
NMIN_VALUES = [1, 2, 3, 5]

# Fixed best channels from Exp 1 (Raja).
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
    run_one_session,
    selection_group_names,
    write_csv,
    DEFAULT_RULES,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

logger = logging.getLogger(__name__)

_CFG = load_exp_config(EXP_SETUP_DIR / "exp5_nmin_sensitivity.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
EPOCH_DURATION_S = float(_CFG.get("epoch_duration_s", 30.0))
STD_THRESHOLD    = float(_CFG["std_threshold"])
CENTER_METHOD    = str(_CFG.get("center_method", "median"))
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))


def _session_csv(out_dir: Path, session_name: str, nmin: int) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}__nmin{nmin}.csv"


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


def _process_one_task(task: tuple[dict, int]) -> tuple[str, int, list[dict], list[str]]:
    """Worker: run all groups for one (session, min_flagged_epochs) combination."""
    pair, nmin = task

    session_kwargs = dict(
        raja_region_yaml=RAJA_REGION_YAML,
        cao_region_yaml=CAO_REGION_YAML,
        epoch_duration_s=EPOCH_DURATION_S,
        std_threshold=STD_THRESHOLD,
        center_methods=(CENTER_METHOD,),
        rules=DEFAULT_RULES,
        autoreject_random_state=42,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        include_single_frontal=True,
        use_epoch_health=False,
        verbose=False,
        min_flagged_epochs=nmin,
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
                r["min_flagged_epochs"] = nmin
            rows.extend(raw_rows)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"ERROR  {pair['name']} [{group}] nmin={nmin}: {exc}")
    return pair["name"], nmin, rows, errs


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


def _heartbeat_thread(stop_event, progress, n_total, start_time):
    while not stop_event.wait(HEARTBEAT_EVERY_S):
        done = progress.get("done", 0)
        elapsed = time.time() - start_time
        eta_s = (elapsed / done * (n_total - done)) if done > 0 else float("nan")
        eta_min = eta_s / 60 if eta_s == eta_s else -1
        _send_telegram(
            f"[Exp5 Raja] Heartbeat\n"
            f"  Progress: {done}/{n_total}  Elapsed: {elapsed/60:.1f} min  ETA: {eta_min:.1f} min\n"
            f"  Latest: {progress.get('latest', '?')}"
        )


def condition_summary_rows_nmin(records, dataset_label):
    """Macro-average per (min_flagged_epochs, selection, channel_in_group, center_method)."""
    from collections import defaultdict
    import numpy as np
    buckets = defaultdict(list)
    for r in records:
        ch = r.get("channel_in_group", r.get("best_channel", "unknown"))
        buckets[(r.get("min_flagged_epochs", 1), r["selection"], ch, r["center_method"])].append(r)
    out = []
    for (nmin, sel, ch, center), bucket in buckets.items():
        def m(k):
            vals = [b[k] for b in bucket if k in b and isinstance(b[k], (int, float))]
            return float(np.mean(vals)) if vals else float("nan")
        out.append({
            "dataset": dataset_label, "min_flagged_epochs": nmin,
            "selection": sel, "channel_in_group": ch, "center_method": center,
            "n_sessions": len(bucket),
            "det_precision": m("det_precision"), "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    out.sort(key=lambda r: (int(r["min_flagged_epochs"]), r["selection"], r["channel_in_group"]))
    return out


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

    all_metrics: list[dict] = []
    errors: list[str] = []

    todo: list[tuple[dict, int]] = []
    for pair in pairs:
        for nmin in NMIN_VALUES:
            csv_path = _session_csv(out_dir, pair["name"], nmin)
            if not OVERWRITE and csv_path.is_file():
                logger.info("SKIP (cached): %s nmin=%d", pair["name"], nmin)
                with csv_path.open(encoding="utf-8") as fh:
                    all_metrics.extend(list(csv.DictReader(fh)))
            else:
                todo.append((pair, nmin))

    progress = {"done": 0, "latest": ""}
    start_time = time.time()
    stop_evt = threading.Event()
    if todo:
        threading.Thread(target=_heartbeat_thread,
                         args=(stop_evt, progress, len(todo), start_time),
                         daemon=True).start()

    def _store(name, nmin, rows, errs):
        errors.extend(errs)
        if rows:
            _write_session_csv(_session_csv(out_dir, name, nmin), rows)
            all_metrics.extend(rows)
        progress["done"] += 1
        progress["latest"] = f"{name} nmin={nmin}"
        logger.info("done %s nmin=%d -> %d rows", name, nmin, len(rows))

    if todo:
        n_jobs = _resolve_n_jobs(len(todo))
        logger.info("Running %d tasks with n_jobs=%d", len(todo), n_jobs)
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
                        errors.append(f"ERROR {task}: {exc}")
                        progress["done"] += 1

    stop_evt.set()

    if not all_metrics:
        print("No metrics collected.")
        return

    numeric_keys = {
        "min_flagged_epochs", "stageA_tp", "stageA_fp", "stageA_fn", "stageA_tn",
        "stageA_precision", "stageA_recall", "stageA_f1", "stageA_fpr",
        "pct_flagged", "n_flagged", "n_blink_epochs", "n_channels_used", "n_valid",
        "det_tp", "det_fp", "det_fn", "det_precision", "det_recall", "det_f1",
    }
    coerced = []
    for r in all_metrics:
        row = dict(r)
        for k in numeric_keys:
            if k in row and isinstance(row[k], str):
                try:
                    row[k] = float(row[k])
                except ValueError:
                    pass
        coerced.append(row)

    write_csv(out_dir / f"exp5_nmin_sensitivity_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows_nmin(coerced, DATASET)
    write_csv(out_dir / f"exp5_nmin_sensitivity_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp5_nmin_sensitivity_{DATASET}",
        "epoch_duration_s": EPOCH_DURATION_S, "center_method": CENTER_METHOD,
        "nmin_values": NMIN_VALUES, "groups_run": sorted(GROUPS_TO_RUN),
        "n_sessions": len(pairs), "n_rows": len(coerced), "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print("\n" + "=" * 75)
    print(f"MIN-FLAGGED-EPOCHS SENSITIVITY — {DATASET.upper()}")
    print("=" * 75)
    for r in summary_rows:
        print(f"  nmin={r['min_flagged_epochs']}  {r['selection']:<16}  "
              f"P={r['det_precision']:.4f}  R={r['det_recall']:.4f}  F1={r['det_f1']:.4f}")

    if errors:
        print(f"\n{len(errors)} error(s):", *errors[:5], sep="\n  ")

    elapsed_min = (time.time() - start_time) / 60
    from experiment_script.exp_tg_report import per_group_telegram_message, send_telegram_chunked as _stc
    _tg5r = per_group_telegram_message(
        tag="[Exp5 Raja] COMPLETE",
        summary_rows=summary_rows,
        param_col="min_flagged_epochs",
        param_fmt=lambda v: f"nmin{int(float(v))}",
        ref_val=1,
        center_method="median",
        errors=errors,
        elapsed_min=elapsed_min,
        n_sessions=len(pairs),
        n_tasks=len(pairs) * len(NMIN_VALUES),
    )
    _stc(REPO_ROOT, _tg5r)
    print(f"\nResults written to: {out_dir}  ({elapsed_min:.1f} min)")


if __name__ == "__main__":
    main()
