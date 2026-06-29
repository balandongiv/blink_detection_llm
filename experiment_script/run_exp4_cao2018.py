"""Run Exp 4 (Cao2018) — boundary-tolerance (IoU threshold) sweep — no argparse needed.

Just press the Play button in IntelliJ IDEA.

What this experiment tests
--------------------------
Evaluates how detection F1 changes as the event-matching IoU threshold varies.
Detection is run ONCE per (session, group); then evaluate_channels is called with
each of the 5 IoU thresholds — no recomputation of the EEG signal.

IoU thresholds: {0.0, 0.1, 0.2, 0.3, 0.5}

Configuration is read from experiment_script/setup/exp4_boundary_tolerance.yaml.
Output CSVs go to runs/exp4_cao/.

How to change settings
-----------------------
  IOU_THRESHOLDS    — list of IoU values to test
  GROUPS_TO_RUN     — best channels from Exp 1 (Cao2018)
  HEARTBEAT_EVERY_S — Telegram heartbeat interval in seconds (default 900)

Resume support
--------------
Each session has one CSV file (all IoU threshold rows stored together).

Output columns (beyond Exp1 baseline)
--------------------------------------
  iou_threshold  — IoU threshold used for event-matching
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

OUT_DIR = Path("runs/exp4_cao")

OVERWRITE = False

MAX_SESSIONS = None

N_JOBS = 16  # 16 of 24 logical threads (i7-13700F)

HEARTBEAT_EVERY_S = 900

# IoU thresholds to sweep.
IOU_THRESHOLDS = [0.0, 0.1, 0.2, 0.3, 0.5]

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
    build_selection_groups,
    write_csv,
    _stage_a_metrics,
)
from blink_evaluation import evaluate_channels, load_annotation_as_reference
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import (
    load_brain_region_channels,
    load_brain_region_map,
    resolve_channel_names,
)
from pyblinker.double_thresholding import blink_position_strategy_dbo
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs,
    load_gt_annotations_for_pair,
    setup_tutorial_logging,
)
import mne

logger = logging.getLogger(__name__)

_CFG = load_exp_config(EXP_SETUP_DIR / "exp4_boundary_tolerance.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
CAO_DATASET_ROOT = _CAO["dataset_root"]
EPOCH_DURATION_S = float(_CFG["epoch_duration_s"])
STD_THRESHOLD    = float(_CFG["std_threshold"])
CENTER_METHOD    = str(_CFG.get("center_method", "median"))
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))


def _session_csv(out_dir: Path, session_name: str) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}.csv"


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


def _process_one_session(pair: dict) -> tuple[str, list[dict], list[str]]:
    """Worker: run detection once per group; evaluate at multiple IoU thresholds."""
    region_yaml = RAJA_REGION_YAML if pair["dataset"] == "raja" else CAO_REGION_YAML
    region_map = load_brain_region_map(region_yaml)
    brain_channels = load_brain_region_channels(region_yaml)
    raw = mne.io.read_raw_fif(str(pair["fif"]), preload=False, verbose="ERROR")
    available = resolve_channel_names(brain_channels, raw.ch_names)
    groups = build_selection_groups(region_map, available, include_single_frontal=True)
    if GROUPS_TO_RUN is not None:
        groups = {n: chs for n, chs in groups.items() if n in GROUPS_TO_RUN}

    rows: list[dict] = []
    errs: list[str] = []

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

            gt_raw = load_annotation_as_reference(pair["csv"], EPOCH_DURATION_S)
            if pair["dataset"] == "cao2018":
                gt_raw = gt_raw[gt_raw["epoch_index"].isin(valid_epoch_indices)].reset_index(drop=True)
            blink_global = {int(i) for i in gt_raw["epoch_index"].unique()}
            gt_annotations = load_gt_annotations_for_pair(
                pair, EPOCH_DURATION_S, valid_epoch_indices
            )

            setting = {
                "autoreject_random_state": 42,
                "std_threshold": STD_THRESHOLD,
                "center_method": CENTER_METHOD,
                "min_flagged_epochs": 1,
                "verbose": False,
            }
            ch_results = blink_position_strategy_dbo(
                prepared, valid_epoch_indices, setting=setting
            )
            flagged_global = (
                list(ch_results[0]["flagged_valid_epoch_indices"]) if ch_results else []
            )
            stage_a = _stage_a_metrics(set(flagged_global), blink_global, valid_epoch_indices)
            n_channels = len(prepared.channel_names)

            for iou in IOU_THRESHOLDS:
                for ch_result in ch_results:
                    channel_name = ch_result["channel"]
                    scored = evaluate_channels(
                        [ch_result], gt_annotations,
                        epoch_duration=EPOCH_DURATION_S,
                        iou_threshold=iou,
                    )
                    em = scored.best_eval_result.event_metrics
                    rows.append({
                        "dataset": pair["dataset"],
                        "session": pair["name"],
                        "selection": group_name,
                        "center_method": CENTER_METHOD,
                        "iou_threshold": iou,
                        "channel_in_group": channel_name,
                        "n_channels_used": n_channels,
                        "n_valid": len(valid_epoch_indices),
                        **stage_a,
                        "det_tp": em.tp, "det_fp": em.fp, "det_fn": em.fn,
                        "det_precision": em.precision, "det_recall": em.recall, "det_f1": em.f1,
                    })

        except Exception as exc:  # noqa: BLE001
            errs.append(f"ERROR  {pair['name']} [{group_name}]: {exc}")

    return pair["name"], rows, errs


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
            f"[Exp4 Cao2018] Heartbeat\n"
            f"  Progress: {done}/{n_total} sessions\n"
            f"  Elapsed:  {elapsed/60:.1f} min  ETA: {eta_min:.1f} min\n"
            f"  Latest:   {progress.get('latest', '?')}"
        )


def condition_summary_rows_iou(records, dataset_label):
    """Macro-average metrics per (iou_threshold, selection, channel_in_group)."""
    from collections import defaultdict
    import numpy as np
    buckets = defaultdict(list)
    for r in records:
        ch = r.get("channel_in_group", r.get("best_channel", "unknown"))
        buckets[(r.get("iou_threshold", 0.1), r["selection"], ch)].append(r)
    out = []
    for (iou, sel, ch), bucket in buckets.items():
        def m(k):
            vals = [b[k] for b in bucket if k in b and isinstance(b[k], (int, float))]
            return float(np.mean(vals)) if vals else float("nan")
        out.append({
            "dataset": dataset_label, "iou_threshold": iou, "selection": sel,
            "channel_in_group": ch,
            "n_sessions": len(bucket),
            "det_precision": m("det_precision"), "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    out.sort(key=lambda r: (float(r["iou_threshold"]), r["selection"], r["channel_in_group"]))
    return out


def main() -> None:
    import threading
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

    todo = []
    for pair in pairs:
        csv_path = _session_csv(out_dir, pair["name"])
        if not OVERWRITE and csv_path.is_file():
            logger.info("SKIP (cached): %s", pair["name"])
            with csv_path.open(encoding="utf-8") as fh:
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
        progress["done"] += 1
        progress["latest"] = name
        logger.info("done %s -> %d rows", name, len(rows))

    if todo:
        n_jobs = _resolve_n_jobs(len(todo))
        logger.info("Running %d session(s) with n_jobs=%d", len(todo), n_jobs)
        if n_jobs == 1:
            for pair in todo:
                _store(*_process_one_session(pair))
        else:
            with ProcessPoolExecutor(max_workers=n_jobs) as ex:
                fut_map = {ex.submit(_process_one_session, pair): pair["name"] for pair in todo}
                for fut in as_completed(fut_map):
                    name = fut_map[fut]
                    try:
                        _store(*fut.result())
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"ERROR  {name}: {exc}")
                        progress["done"] += 1

    stop_evt.set()

    if not all_metrics:
        print("No metrics collected.")
        return

    numeric_keys = {
        "iou_threshold", "stageA_tp", "stageA_fp", "stageA_fn", "stageA_tn",
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

    write_csv(out_dir / f"exp4_boundary_tolerance_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows_iou(coerced, DATASET)
    write_csv(out_dir / f"exp4_boundary_tolerance_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp4_boundary_tolerance_{DATASET}",
        "epoch_duration_s": EPOCH_DURATION_S, "center_method": CENTER_METHOD,
        "iou_thresholds": IOU_THRESHOLDS, "groups_run": sorted(GROUPS_TO_RUN),
        "n_sessions": len(pairs), "n_rows": len(coerced), "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print("\n" + "=" * 75)
    print(f"BOUNDARY TOLERANCE (IoU SWEEP) — {DATASET.upper()}")
    print("=" * 75)
    for r in summary_rows:
        print(f"  iou={r['iou_threshold']:.2f}  {r['selection']:<16}  "
              f"P={r['det_precision']:.4f}  R={r['det_recall']:.4f}  F1={r['det_f1']:.4f}")

    if errors:
        print(f"\n{len(errors)} error(s):", *errors, sep="\n  ")

    elapsed_min = (time.time() - start_time) / 60
    from experiment_script.exp_tg_report import per_group_telegram_message, send_telegram_chunked as _stc
    _tg4c = per_group_telegram_message(
        tag="[Exp4 Cao2018] COMPLETE",
        summary_rows=summary_rows,
        param_col="iou_threshold",
        param_fmt=lambda v: f"iou{float(v):.1f}",
        ref_val=0.1,
        center_method=None,
        errors=errors,
        elapsed_min=elapsed_min,
        n_sessions=len(pairs),
        n_tasks=len(pairs) * len(IOU_THRESHOLDS),
    )
    _stc(REPO_ROOT, _tg4c)
    print(f"\nResults written to: {out_dir}  ({elapsed_min:.1f} min)")


if __name__ == "__main__":
    main()
