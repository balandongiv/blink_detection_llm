"""Run Exp 8 (Raja) — long-blink analysis — no argparse needed.

Just press the Play button in IntelliJ IDEA.

What this experiment tests
--------------------------
Separately reports detection precision/recall/F1 for:

  * Normal blinks  — ground-truth duration < LONG_THRESHOLD_S (0.5 s)
  * Long blinks    — ground-truth duration >= LONG_THRESHOLD_S (0.5 s)

Detection is run once with the full pipeline (Proposed-Med, frontal channels).
The matched events are then split by the ground-truth blink duration.

Method:
  1. Run evaluate_channels → get TP matches and FN events (each with duration_gt).
  2. For FP counts, we know total predicted = TP + FP.
  3. Split TPs into normal/long by match.duration_gt.
  4. Split FNs into normal/long by fn_event.duration_gt.
  5. FPs are not split (we don't know if a false positive corresponds to a normal
     or long blink ground-truth event), so they are reported at the session level.

Configuration is read from experiment_script/setup/exp8_long_blink_analysis.yaml.
Output CSVs go to runs/exp8_raja/.

How to change settings
-----------------------
  LONG_THRESHOLD_S  — duration split point in seconds (default 0.5)
  GROUPS_TO_RUN     — best channels from Exp 1 (Raja)
  HEARTBEAT_EVERY_S — Telegram heartbeat interval (default 900 s)

Resume support
--------------
Each session has one CSV file (rows for normal/long categories together).
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

OUT_DIR = Path("runs/exp8_raja")
OVERWRITE = False
MAX_SESSIONS = None
N_JOBS = 16  # 16 of 24 logical threads (i7-13700F)
HEARTBEAT_EVERY_S = 900

# Duration split point in seconds.
LONG_THRESHOLD_S = 0.5

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
    build_selection_groups, write_csv,
)
from blink_evaluation import evaluate_channels, load_annotation_as_reference
from blink_evaluation.io import annotations_to_events
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import (
    load_brain_region_channels, load_brain_region_map, resolve_channel_names,
)
from src.strategy_dbo_drop.core import blink_position_strategy_dbo_drop
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_raja_pairs, load_gt_annotations_for_pair, setup_tutorial_logging,
)
import mne

logger = logging.getLogger(__name__)

_CFG = load_exp_config(EXP_SETUP_DIR / "exp8_long_blink_analysis.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
EPOCH_DURATION_S = float(_CFG.get("epoch_duration_s", 30.0))
LONG_THRESHOLD_S = float(_CFG.get("long_threshold_s", LONG_THRESHOLD_S))
STD_THRESHOLD    = float(_CFG.get("std_threshold", 3.5))
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))
CENTER_METHOD    = "median"


def _session_csv(out_dir: Path, session_name: str) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}.csv"


def _write_session_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: return
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
        fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)


def _resolve_n_jobs(n_tasks: int) -> int:
    n = max(1, int(N_JOBS)) if N_JOBS is not None else max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(n, n_tasks))


def _metrics_from_counts(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {"det_tp": tp, "det_fp": fp, "det_fn": fn,
            "det_precision": precision, "det_recall": recall, "det_f1": f1}


def _process_one_session(pair: dict) -> tuple[str, list[dict], list[str]]:
    """Worker: run detection for each group, split results by blink duration."""
    region_yaml = RAJA_REGION_YAML if pair["dataset"] == "raja" else CAO_REGION_YAML
    region_map = load_brain_region_map(region_yaml)
    brain_channels = load_brain_region_channels(region_yaml)
    raw_meta = mne.io.read_raw_fif(str(pair["fif"]), preload=False, verbose="ERROR")
    available = resolve_channel_names(brain_channels, raw_meta.ch_names)
    groups = build_selection_groups(region_map, available, include_single_frontal=True)
    if GROUPS_TO_RUN is not None:
        groups = {n: chs for n, chs in groups.items() if n in GROUPS_TO_RUN}

    rows, errs = [], []

    for group_name, group_chs in groups.items():
        try:
            raw_g = mne.io.read_raw_fif(str(pair["fif"]), preload=True, verbose="ERROR")
            raw_g.pick(sorted(group_chs))

            epochs = mne.make_fixed_length_epochs(
                raw_g, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
            )
            valid_epoch_indices = list(range(len(epochs)))
            if not valid_epoch_indices:
                continue

            prepared = prepare_epoch_detection_input(
                epochs, pick_types_options={"eeg": True},
                filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
            )
            gt_annotations = load_gt_annotations_for_pair(
                pair, EPOCH_DURATION_S, valid_epoch_indices
            )
            n_channels = len(prepared.channel_names)

            setting = {
                "autoreject_random_state": 42,
                "std_threshold": STD_THRESHOLD,
                "center_method": CENTER_METHOD,
                "min_flagged_epochs": 1,
                "verbose": False,
            }
            ch_results = blink_position_strategy_dbo_drop(
                prepared, valid_epoch_indices, setting=setting
            )

            # Evaluate each channel individually.
            gt_events = annotations_to_events(gt_annotations, "blink")
            n_gt_total  = len(gt_events)
            n_gt_normal = sum(1 for e in gt_events
                              if e.duration is not None and e.duration < LONG_THRESHOLD_S)
            n_gt_long   = sum(1 for e in gt_events
                              if e.duration is not None and e.duration >= LONG_THRESHOLD_S)

            for ch_result in ch_results:
                channel_name = ch_result["channel"]
                scored = evaluate_channels(
                    [ch_result], gt_annotations, epoch_duration=EPOCH_DURATION_S
                )
                if scored.best_eval_result is None:
                    continue

                res   = scored.best_eval_result
                tps   = res.true_positives
                fps   = res.false_positives
                fns   = res.false_negatives

                n_predicted = len(tps) + len(fps)

                normal_tp = sum(1 for m in tps
                                if m.duration_gt is not None and m.duration_gt < LONG_THRESHOLD_S)
                long_tp   = sum(1 for m in tps
                                if m.duration_gt is not None and m.duration_gt >= LONG_THRESHOLD_S)
                normal_fn = sum(1 for e in fns
                                if e.duration_gt is not None and e.duration_gt < LONG_THRESHOLD_S)
                long_fn   = sum(1 for e in fns
                                if e.duration_gt is not None and e.duration_gt >= LONG_THRESHOLD_S)

                total_fp = len(fps)

                base = {
                    "dataset": pair["dataset"], "session": pair["name"],
                    "selection": group_name, "center_method": CENTER_METHOD,
                    "channel_in_group": channel_name,
                    "n_channels_used": n_channels,
                    "long_threshold_s": LONG_THRESHOLD_S,
                    "n_gt_total": n_gt_total,
                    "n_gt_normal": n_gt_normal, "n_gt_long": n_gt_long,
                    "total_fp": total_fp, "n_predicted": n_predicted,
                }

                em = res.event_metrics
                rows.append({
                    **base, "blink_category": "all",
                    **_metrics_from_counts(em.tp, em.fp, em.fn),
                })
                rows.append({
                    **base, "blink_category": "normal",
                    **_metrics_from_counts(normal_tp, total_fp, normal_fn),
                })
                rows.append({
                    **base, "blink_category": "long",
                    **_metrics_from_counts(long_tp, total_fp, long_fn),
                })

        except Exception as exc:  # noqa: BLE001
            errs.append(f"ERROR  {pair['name']} [{group_name}]: {exc}")

    return pair["name"], rows, errs


def _send_telegram(message: str) -> None:
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
            f"[Exp8 Raja] Heartbeat  {done}/{n_total}  "
            f"Elapsed {elapsed/60:.1f}min  ETA {eta_s/60:.1f}min"
        )


def condition_summary_rows_blink_cat(records, dataset_label):
    """Macro-average metrics per (blink_category, selection, channel_in_group)."""
    from collections import defaultdict
    import numpy as np
    buckets = defaultdict(list)
    for r in records:
        ch = r.get("channel_in_group", r.get("best_channel", "unknown"))
        buckets[(r["blink_category"], r["selection"], ch)].append(r)
    out = []
    for (cat, sel, ch), bucket in buckets.items():
        def m(k):
            vals = [b[k] for b in bucket if k in b and isinstance(b[k], (int, float))]
            return float(np.mean(vals)) if vals else float("nan")
        out.append({
            "dataset": dataset_label, "blink_category": cat, "selection": sel,
            "channel_in_group": ch,
            "n_sessions": len(bucket),
            "det_precision": m("det_precision"), "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    cat_order = {"all": 0, "normal": 1, "long": 2}
    out.sort(key=lambda r: (cat_order.get(r["blink_category"], 9), r["selection"], r["channel_in_group"]))
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
        cp = _session_csv(out_dir, pair["name"])
        if not OVERWRITE and cp.is_file():
            with cp.open(encoding="utf-8") as fh:
                all_metrics.extend(list(csv.DictReader(fh)))
        else:
            todo.append(pair)

    progress = {"done": 0, "latest": ""}
    start_time = time.time()
    stop_evt = threading.Event()
    if todo:
        threading.Thread(target=_heartbeat_thread,
                         args=(stop_evt, progress, len(todo), start_time),
                         daemon=True).start()

    def _store(name, rows, errs):
        errors.extend(errs)
        if rows:
            _write_session_csv(_session_csv(out_dir, name), rows)
            all_metrics.extend(rows)
        progress["done"] += 1; progress["latest"] = name
        logger.info("done %s -> %d rows", name, len(rows))

    if todo:
        n_jobs = _resolve_n_jobs(len(todo))
        if n_jobs == 1:
            for pair in todo: _store(*_process_one_session(pair))
        else:
            with ProcessPoolExecutor(max_workers=n_jobs) as ex:
                fut_map = {ex.submit(_process_one_session, p): p["name"] for p in todo}
                for fut in as_completed(fut_map):
                    name = fut_map[fut]
                    try: _store(*fut.result())
                    except Exception as exc:
                        errors.append(f"ERROR {name}: {exc}"); progress["done"] += 1

    stop_evt.set()
    if not all_metrics:
        print("No metrics."); return

    numeric_keys = {
        "long_threshold_s", "n_gt_total", "n_gt_normal", "n_gt_long",
        "total_fp", "n_predicted", "n_channels_used",
        "det_tp", "det_fp", "det_fn", "det_precision", "det_recall", "det_f1",
    }
    coerced = []
    for r in all_metrics:
        row = dict(r)
        for k in numeric_keys:
            if k in row and isinstance(row[k], str):
                try: row[k] = float(row[k])
                except ValueError: pass
        coerced.append(row)

    write_csv(out_dir / f"exp8_long_blink_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows_blink_cat(coerced, DATASET)
    write_csv(out_dir / f"exp8_long_blink_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp8_long_blink_{DATASET}", "long_threshold_s": LONG_THRESHOLD_S,
        "epoch_duration_s": EPOCH_DURATION_S, "groups_run": sorted(GROUPS_TO_RUN),
        "n_sessions": len(pairs), "n_rows": len(coerced), "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print(f"LONG BLINK ANALYSIS — {DATASET.upper()}  (threshold={LONG_THRESHOLD_S}s)")
    print("=" * 80)
    print(f"{'category':<8}  {'selection':<16}  "
          f"{'det_P':>7}  {'det_R':>7}  {'det_F1':>7}  {'N':>3}")
    print("-" * 80)
    for r in summary_rows:
        print(f"{r['blink_category']:<8}  {r['selection']:<16}  "
              f"{r['det_precision']:>7.4f}  {r['det_recall']:>7.4f}  "
              f"{r['det_f1']:>7.4f}  {r['n_sessions']:>3}")

    if errors:
        print(f"\n{len(errors)} error(s):", *errors[:5], sep="\n  ")

    elapsed_min = (time.time() - start_time) / 60
    from experiment_script.exp_tg_report import per_group_telegram_message, send_telegram_chunked as _stc
    _tg8r = per_group_telegram_message(
        tag="[Exp8 Raja] COMPLETE",
        summary_rows=summary_rows,
        param_col="blink_category",
        param_fmt=lambda v: str(v),
        ref_val="all",
        center_method=None,
        errors=errors,
        elapsed_min=elapsed_min,
        n_sessions=len(pairs),
        n_tasks=None,
    )
    _stc(REPO_ROOT, _tg8r)
    print(f"\nResults written to: {out_dir}  ({elapsed_min:.1f} min)")


if __name__ == "__main__":
    main()
