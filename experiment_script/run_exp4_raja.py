"""Run Exp 4 (Raja) — boundary-tolerance (IoU threshold) sweep — no argparse needed.

Just press the Play button in IntelliJ IDEA.

What this experiment tests
--------------------------
Blink boundary annotation is inherently uncertain: different annotators locate onset
and offset slightly differently.  A detector whose F1 score is highly sensitive to
the matching tolerance is fragile in practice.

This experiment evaluates Proposed-Med (the best centre method from Exp 2) at five
intersection-over-union (IoU) thresholds: {0.0, 0.1, 0.2, 0.3, 0.5}.

Detection is run ONCE per (session, group, centre_method).  Then evaluate_channels
is called with each of the 5 IoU thresholds — no recomputation of the EEG signal.
This makes the sweep efficient: 5 evaluation passes, 1 detection pass.

Configuration is read from experiment_script/setup/exp4_boundary_tolerance.yaml.
Output CSVs go to runs/exp4_raja/.

How to change settings
-----------------------
  IOU_THRESHOLDS    — list of IoU values to test
  GROUPS_TO_RUN     — best channels from Exp 1 (Raja)
  N_JOBS            — None → all cores minus 1; 1 → serial (debug)

Resume support
--------------
Each session has one CSV file (containing rows for all IoU thresholds).
Set OVERWRITE = False to skip sessions that already have a result CSV.

Output columns (beyond Exp1 baseline)
--------------------------------------
  iou_threshold  — IoU threshold used for the event-matching step
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

# ---------------------------------------------------------------------------
# *** User-facing settings — edit these ***
# ---------------------------------------------------------------------------

OUT_DIR = Path("runs/exp4_raja")

OVERWRITE = False

MAX_SESSIONS = None

N_JOBS = 16  # 16 of 24 logical threads (i7-13700F)

# IoU thresholds to sweep.
IOU_THRESHOLDS = [0.0, 0.1, 0.2, 0.3, 0.5]

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
    build_selection_groups,
    selection_group_names,
    _stage_a_metrics,
    write_csv,
    RULE_MIN_VOTES,
    DEFAULT_RULES,
)
from blink_evaluation import evaluate_channels, load_annotation_as_reference
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import (
    load_brain_region_channels,
    load_brain_region_map,
    load_raw_with_brain_channels,
    resolve_channel_names,
)
from src.strategy_dbo_drop.core import blink_position_strategy_dbo_drop
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_raja_pairs,
    load_gt_annotations_for_pair,
    valid_epoch_indices_for_pair,
    setup_tutorial_logging,
)
import mne

logger = logging.getLogger(__name__)

_CFG = load_exp_config(EXP_SETUP_DIR / "exp4_boundary_tolerance.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
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
    """Worker: run detection once per group; evaluate at multiple IoU thresholds.

    Returns (session_name, rows_with_iou_column, errors).
    For each (group, center_method, iou_threshold) combination, one row is produced.
    """
    region_yaml = RAJA_REGION_YAML if pair["dataset"] == "raja" else CAO_REGION_YAML
    region_map = load_brain_region_map(region_yaml)
    brain_channels = load_brain_region_channels(region_yaml)
    raw = load_raw_with_brain_channels(pair["fif"], brain_channels)

    groups = build_selection_groups(
        region_map, list(raw.ch_names), include_single_frontal=True,
    )
    if GROUPS_TO_RUN is not None:
        groups = {name: chs for name, chs in groups.items() if name in GROUPS_TO_RUN}

    rows: list[dict] = []
    errs: list[str] = []

    for group_name, group_chs in groups.items():
        try:
            # Pick only this group's channels.
            raw_g = raw.copy().pick(sorted(group_chs))
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
            blink_global = {int(i) for i in gt_raw["epoch_index"].unique()}
            gt_annotations = load_gt_annotations_for_pair(
                pair, EPOCH_DURATION_S, valid_epoch_indices
            )

            # Run detection once per center_method (only the configured one from YAML).
            for center in [CENTER_METHOD]:
                setting = {
                    "autoreject_random_state": 42,
                    "std_threshold": STD_THRESHOLD,
                    "center_method": center,
                    "min_flagged_epochs": 1,
                    "verbose": False,
                }
                channel_results = blink_position_strategy_dbo_drop(
                    prepared, valid_epoch_indices, setting=setting
                )
                flagged_global = (
                    list(channel_results[0]["flagged_valid_epoch_indices"])
                    if channel_results else []
                )
                stage_a = _stage_a_metrics(
                    set(flagged_global), blink_global, valid_epoch_indices
                )
                n_channels = len(prepared.channel_names)

                # Evaluate each channel individually at each IoU threshold.
                for iou in IOU_THRESHOLDS:
                    for ch_result in channel_results:
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
                            "rule": "any",
                            "center_method": center,
                            "iou_threshold": iou,
                            "channel_in_group": channel_name,
                            "condition": f"{group_name}|any|{center}|iou{iou}|{channel_name}",
                            "n_channels_used": n_channels,
                            "n_valid": len(valid_epoch_indices),
                            **stage_a,
                            "det_tp": em.tp,
                            "det_fp": em.fp,
                            "det_fn": em.fn,
                            "det_precision": em.precision,
                            "det_recall": em.recall,
                            "det_f1": em.f1,
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


def condition_summary_rows_iou(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (iou_threshold, selection, channel_in_group, center_method)."""
    from collections import defaultdict
    import numpy as np
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        ch = r.get("channel_in_group", r.get("best_channel", "unknown"))
        key = (r.get("iou_threshold", 0.1), r["selection"], ch, r["center_method"])
        buckets[key].append(r)
    out: list[dict] = []
    for (iou, selection, ch, center), bucket in buckets.items():
        def m(k: str) -> float:
            vals = [b[k] for b in bucket if k in b and isinstance(b[k], (int, float))]
            return float(np.mean(vals)) if vals else float("nan")
        out.append({
            "dataset": dataset_label,
            "iou_threshold": iou,
            "selection": selection,
            "channel_in_group": ch,
            "center_method": center,
            "n_sessions": len(bucket),
            "det_precision": m("det_precision"),
            "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    out.sort(key=lambda r: (float(r["iou_threshold"]), r["selection"], r["channel_in_group"]))
    return out


def main() -> None:
    start_time = time.time()
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

    numeric_keys = {
        "iou_threshold", "stageA_tp", "stageA_fp", "stageA_fn", "stageA_tn",
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

    write_csv(out_dir / f"exp4_boundary_tolerance_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows_iou(coerced, DATASET)
    write_csv(out_dir / f"exp4_boundary_tolerance_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp4_boundary_tolerance_{DATASET}",
        "epoch_duration_s": EPOCH_DURATION_S,
        "std_threshold": STD_THRESHOLD,
        "center_method": CENTER_METHOD,
        "iou_thresholds": IOU_THRESHOLDS,
        "groups_run": sorted(GROUPS_TO_RUN),
        "n_sessions": len(pairs),
        "n_rows": len(coerced),
        "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print(f"BOUNDARY TOLERANCE (IoU SWEEP) — {DATASET.upper()}")
    print("=" * 80)
    print(f"{'iou':>5}  {'selection':<16}  {'centre':<6}  "
          f"{'det_P':>7}  {'det_R':>7}  {'det_F1':>7}  {'N':>3}")
    print("-" * 80)
    for r in summary_rows:
        print(f"{r['iou_threshold']:>5.2f}  {r['selection']:<16}  {r['center_method']:<6}  "
              f"{r['det_precision']:>7.4f}  {r['det_recall']:>7.4f}  {r['det_f1']:>7.4f}  "
              f"{r['n_sessions']:>3}")
    print("=" * 80)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)

    print(f"\nResults written to: {out_dir}")
    from experiment_script.exp_tg_report import per_group_telegram_message, send_telegram_chunked as _stc
    _tg4r = per_group_telegram_message(
        tag="[Exp4 Raja] COMPLETE",
        summary_rows=summary_rows,
        param_col="iou_threshold",
        param_fmt=lambda v: f"iou{float(v):.1f}",
        ref_val=0.1,
        center_method=None,
        errors=errors,
        elapsed_min=(time.time() - start_time) / 60,
        n_sessions=len(pairs),
        n_tasks=len(pairs) * len(IOU_THRESHOLDS),
    )
    _stc(REPO_ROOT, _tg4r)


if __name__ == "__main__":
    main()
