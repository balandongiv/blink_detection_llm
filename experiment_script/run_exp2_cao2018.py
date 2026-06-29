"""Run Exp 2 (Cao2018) — full strategy comparison — no argparse needed.

Just press the Play button in IntelliJ IDEA.

What this experiment tests
--------------------------
Using the best channel groups identified in Exp 1, this experiment compares FOUR
detection conditions on Cao2018:

  * BLINKER-concat  — naive concatenation with Kleifges/BLINKER threshold
  * MNE-annot       — MNE annotate_amplitude routine (community baseline)
  * Proposed-Mean   — three-stage pipeline with mean + std threshold
  * Proposed-Med    — three-stage pipeline with median + MAD threshold (primary)

All four conditions run on the SAME best-channel subsets from Exp 1 (frontal
and best single channels).  This makes the comparison fair: any difference is
due to the algorithm, not the channels.

Configuration is read from experiment_script/setup/exp2_strategy_comparison.yaml.
Output CSVs go to runs/exp2_cao/.

How to change settings
-----------------------
  GROUPS_TO_RUN     — best channels from Exp 1 (Cao2018)
  N_JOBS            — None → all cores minus 1; 1 → serial (debug)
  HEARTBEAT_EVERY_S — Telegram heartbeat interval in seconds (default 900 = 15 min)

Resume support
--------------
Set OVERWRITE = False to skip sessions that already have a result CSV.

Output columns
--------------
  condition         — "BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"
  selection         — channel group name (e.g. "frontal", "single:Fp1")
  det_precision, det_recall, det_f1 — event-level detection metrics
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

OUT_DIR = Path("runs/exp2_cao")

OVERWRITE = False

MAX_SESSIONS = None

N_JOBS = 8  # Reduced from None to avoid Windows handle exhaustion with many workers

# Telegram heartbeat interval in seconds (900 = 15 minutes).
HEARTBEAT_EVERY_S = 900

# Fixed best channels from Exp 1 (Cao2018).
GROUPS_TO_RUN = {
    "single:FP1", "single:FP2",
    "frontal", "frontal_left", "frontal_right",
}

# Which conditions to run (all 4 by default).
CONDITIONS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]

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
from src.strategy_nathanael_mne.runner import blink_position_strategy_nathanael
from pyblinker.strategies import kleifges_strategy
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs,
    load_gt_annotations_for_pair,
    setup_tutorial_logging,
)
import mne

logger = logging.getLogger(__name__)

_CFG = load_exp_config(EXP_SETUP_DIR / "exp2_strategy_comparison.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
CAO_DATASET_ROOT = _CAO["dataset_root"]
EPOCH_DURATION_S = float(_CFG["epoch_duration_s"])
STD_THRESHOLD    = float(_CFG["std_threshold"])
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))

MNE_HALF_WINDOW_S = 0.10

# Ordered list of selections for Telegram report (combined groups first, then singles).
CAO_SELECTION_ORDER = [
    "frontal", "frontal_left", "frontal_right",
    "single:FP1", "single:FP2",
]


def _session_csv(out_dir: Path, session_name: str) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}.csv"


def _write_session_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    # Union of all keys across all rows: BLINKER/MNE-annot rows lack stageA_* while
    # Proposed rows have them — must use the superset so DictWriter doesn't choke.
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
    os.replace(tmp, path)


def _resolve_n_jobs(n_tasks: int) -> int:
    if N_JOBS is not None:
        n = max(1, int(N_JOBS))
    else:
        n = max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(n, n_tasks))


def _run_one_group_all_conditions(
    pair: dict,
    group_name: str,
    group_chs: list[str],
) -> tuple[list[dict], list[str]]:
    """Run all CONDITIONS on one (pair, channel group) combination."""
    rows: list[dict] = []
    errs: list[str] = []

    try:
        raw_g = mne.io.read_raw_fif(str(pair["fif"]), preload=True, verbose="ERROR")
        raw_g.pick(sorted(group_chs))

        epochs = mne.make_fixed_length_epochs(
            raw_g, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
        )
        valid_epoch_indices = list(range(len(epochs)))
        if not valid_epoch_indices:
            return rows, errs

        prepared = prepare_epoch_detection_input(
            epochs, pick_types_options={"eeg": True},
            filter_low=FILTER_LOW, filter_high=FILTER_HIGH, resample_rate=RESAMPLE_RATE,
        )

        gt_raw = load_annotation_as_reference(pair["csv"], EPOCH_DURATION_S)
        if pair["dataset"] == "cao2018":
            gt_raw = gt_raw[gt_raw["epoch_index"].isin(valid_epoch_indices)].reset_index(drop=True)
        gt_annotations = load_gt_annotations_for_pair(
            pair, EPOCH_DURATION_S, valid_epoch_indices
        )
        blink_global = {int(i) for i in gt_raw["epoch_index"].unique()}
        n_channels = len(prepared.channel_names)

        def _eval_per_channel(ch_results: list, cond: str, center: str,
                              extra: dict | None = None) -> list[dict]:
            """Evaluate each channel individually; return one row per channel."""
            per_ch_rows = []
            for ch_result in ch_results:
                channel_name = ch_result["channel"]
                scored = evaluate_channels(
                    [ch_result], gt_annotations, epoch_duration=EPOCH_DURATION_S
                )
                em = scored.best_eval_result.event_metrics
                row = {
                    "dataset": pair["dataset"], "session": pair["name"],
                    "selection": group_name, "condition": cond, "center_method": center,
                    "n_channels_used": n_channels, "channel_in_group": channel_name,
                    "det_tp": em.tp, "det_fp": em.fp, "det_fn": em.fn,
                    "det_precision": em.precision, "det_recall": em.recall, "det_f1": em.f1,
                }
                if extra:
                    row.update(extra)
                per_ch_rows.append(row)
            return per_ch_rows

        for cond in CONDITIONS:
            try:
                if cond == "BLINKER-concat":
                    ch_results = kleifges_strategy(prepared, valid_epoch_indices)
                    rows.extend(_eval_per_channel(ch_results, cond, "n/a"))
                elif cond == "MNE-annot":
                    ch_results = blink_position_strategy_nathanael(
                        prepared, valid_epoch_indices, half_window_s=MNE_HALF_WINDOW_S,
                        l_freq=FILTER_LOW, h_freq=FILTER_HIGH, thresh=None,
                    )
                    rows.extend(_eval_per_channel(ch_results, cond, "n/a"))
                elif cond in ("Proposed-Mean", "Proposed-Med"):
                    center = "mean" if cond == "Proposed-Mean" else "median"
                    setting = {
                        "autoreject_random_state": 42,
                        "std_threshold": STD_THRESHOLD,
                        "center_method": center,
                        "min_flagged_epochs": 1,
                        "verbose": False,
                    }
                    ch_results = blink_position_strategy_dbo(
                        prepared, valid_epoch_indices, setting=setting
                    )
                    flagged_global = (
                        list(ch_results[0]["flagged_valid_epoch_indices"]) if ch_results else []
                    )
                    stage_a = _stage_a_metrics(
                        set(flagged_global), blink_global, valid_epoch_indices
                    )
                    rows.extend(_eval_per_channel(ch_results, cond, center, extra=stage_a))
            except Exception as exc:  # noqa: BLE001
                errs.append(f"ERROR  {pair['name']} [{group_name}] {cond}: {exc}")

    except Exception as exc:  # noqa: BLE001
        errs.append(f"ERROR  {pair['name']} [{group_name}] (load): {exc}")

    return rows, errs


def _process_one_session(pair: dict) -> tuple[str, list[dict], list[str]]:
    """Worker: run all conditions × groups for one session."""
    region_yaml = RAJA_REGION_YAML if pair["dataset"] == "raja" else CAO_REGION_YAML
    region_map = load_brain_region_map(region_yaml)
    brain_channels = load_brain_region_channels(region_yaml)

    raw_meta = mne.io.read_raw_fif(str(pair["fif"]), preload=False, verbose="ERROR")
    available = resolve_channel_names(brain_channels, raw_meta.ch_names)
    groups = build_selection_groups(
        region_map, available, include_single_frontal=True,
    )
    if GROUPS_TO_RUN is not None:
        groups = {n: chs for n, chs in groups.items() if n in GROUPS_TO_RUN}

    all_rows: list[dict] = []
    all_errs: list[str] = []
    for group_name, group_chs in groups.items():
        rows, errs = _run_one_group_all_conditions(pair, group_name, group_chs)
        all_rows.extend(rows)
        all_errs.extend(errs)

    return pair["name"], all_rows, all_errs


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


def _send_telegram_chunked(message: str, chunk_size: int = 4000) -> None:
    """Send a long Telegram message in chunks of at most chunk_size characters."""
    lines = message.split("\n")
    chunk: list[str] = []
    current_len = 0
    for line in lines:
        if current_len + len(line) + 1 > chunk_size and chunk:
            _send_telegram("\n".join(chunk))
            chunk = []
            current_len = 0
        chunk.append(line)
        current_len += len(line) + 1
    if chunk:
        _send_telegram("\n".join(chunk))


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
            f"[Exp2 Cao2018] Heartbeat\n"
            f"  Progress: {done}/{n_total} sessions\n"
            f"  Elapsed:  {elapsed/60:.1f} min\n"
            f"  ETA:      {eta_min:.1f} min\n"
            f"  Latest:   {progress.get('latest', '?')}"
        )
        _send_telegram(msg)


def _summary_by_condition(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average metrics per (condition, selection, channel_in_group)."""
    from collections import defaultdict
    import numpy as np
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        ch = r.get("channel_in_group", r.get("best_channel", "unknown"))
        buckets[(r["condition"], r["selection"], ch)].append(r)
    out: list[dict] = []
    for (cond, sel, ch), bucket in buckets.items():
        def m(k: str) -> float:
            vals = [b[k] for b in bucket if k in b and isinstance(b[k], (int, float))]
            return float(np.mean(vals)) if vals else float("nan")
        out.append({
            "dataset": dataset_label,
            "condition": cond,
            "selection": sel,
            "channel_in_group": ch,
            "n_sessions": len(bucket),
            "det_precision": m("det_precision"),
            "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    cond_order = {c: i for i, c in enumerate(CONDITIONS)}
    out.sort(key=lambda r: (cond_order.get(r["condition"], 99), r["selection"], r["channel_in_group"]))
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

    todo: list[dict] = []
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
        hb = threading.Thread(
            target=_heartbeat_thread,
            args=(stop_evt, progress, len(todo), start_time),
            daemon=True,
        )
        hb.start()

    def _store(name: str, rows: list[dict], errs: list[str]) -> None:
        errors.extend(errs)
        if rows:
            _write_session_csv(_session_csv(out_dir, name), rows)
            all_metrics.extend(rows)
        progress["done"] += 1
        progress["latest"] = name
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
                        progress["done"] += 1

    stop_evt.set()

    if not all_metrics:
        print("No metrics collected.")
        for e in errors:
            print(e)
        return

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

    write_csv(out_dir / f"exp2_strategy_comparison_{DATASET}_results.csv", coerced)
    summary_rows = _summary_by_condition(coerced, DATASET)
    write_csv(out_dir / f"exp2_strategy_comparison_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp2_strategy_comparison_{DATASET}",
        "epoch_duration_s": EPOCH_DURATION_S,
        "std_threshold": STD_THRESHOLD,
        "conditions": CONDITIONS,
        "groups_run": sorted(GROUPS_TO_RUN),
        "n_sessions": len(pairs),
        "n_rows": len(coerced),
        "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print("\n" + "=" * 90)
    print(f"STRATEGY COMPARISON — {DATASET.upper()}")
    print("=" * 90)
    print(f"{'condition':<14}  {'selection':<16}  "
          f"{'det_P':>7}  {'det_R':>7}  {'det_F1':>7}  {'N':>3}")
    print("-" * 90)
    for r in summary_rows:
        print(f"{r['condition']:<14}  {r['selection']:<16}  "
              f"{r['det_precision']:>7.4f}  {r['det_recall']:>7.4f}  "
              f"{r['det_f1']:>7.4f}  {r['n_sessions']:>3}")
    print("=" * 90)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)

    elapsed_min = (time.time() - start_time) / 60
    print(f"\nResults written to: {out_dir}  ({elapsed_min:.1f} min)")

    # Build a per-channel Telegram summary.
    msg_parts = [
        f"[Exp2 Cao2018] COMPLETE",
        f"Sessions: {len(pairs)}  Rows: {len(coerced)}  Errors: {len(errors)}",
        f"Elapsed: {elapsed_min:.1f} min",
        "",
        "=== Per-selection per-channel results (Proposed-Med | BLINKER-concat) ===",
    ]
    for sel in CAO_SELECTION_ORDER:
        sel_rows = [r for r in summary_rows if r["selection"] == sel]
        if not sel_rows:
            continue
        channels = sorted(set(r["channel_in_group"] for r in sel_rows))
        msg_parts.append(f"\n[{sel}]")
        for ch in channels:
            ch_rows = {r["condition"]: r for r in sel_rows if r["channel_in_group"] == ch}
            prop = ch_rows.get("Proposed-Med")
            blink = ch_rows.get("BLINKER-concat")
            prop_f1 = f"{prop['det_f1']:.3f}" if prop else "N/A"
            blink_f1 = f"{blink['det_f1']:.3f}" if blink else "N/A"
            inv = " [INVERSION]" if (prop and blink and float(blink['det_f1']) > float(prop['det_f1'])) else ""
            msg_parts.append(f"  ch={ch}: Proposed-Med={prop_f1}  BLINKER={blink_f1}{inv}")
    _send_telegram_chunked("\n".join(msg_parts))


if __name__ == "__main__":
    main()
