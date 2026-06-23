"""Experiment R2: event-level recall by ground-truth blink duration.

Inputs
------
- Raja FIF/CSV pairs discovered under ``D:\\dataset\\drowsy_driving_raja_processed``
  and ``D:\\dataset\\drowsy_driving_raja\\human_label_annotation_eeg``.
- Cao2018 FIF/CSV pairs discovered under
  ``D:\\dataset\\sustained_attention_driving`` with optional ``epoch_health.csv``.
- The four visible R2 strategy runners from
  ``experiment_script/exp2_strategy_comparison.py``.

Outputs on a full run
---------------------
- ``runs/extra_blink_type/recall_by_blink_type.csv``
- ``runs/extra_blink_type/cache/<dataset>/<condition>/<session>.json``
- ``runs/extra_blink_type/progress.json``
- ``writing/e_result/tab_blink_type_recall.tex``

Blink types are defined from ground-truth duration:
Normal = duration < 0.5 s; Long = duration >= 0.5 s.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime
from multiprocessing import cpu_count
from pathlib import Path
from typing import Iterable

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Local development checkouts sometimes expose blink_evaluation as a namespace
# package unless its src/ directory is on sys.path. Prefer installed packages,
# but add the sibling validation checkout when present.
_BLINK_EVAL_SRC = REPO_ROOT.parent / "blinker_pyblinker_validation" / "blink_evaluation" / "src"
if _BLINK_EVAL_SRC.is_dir() and str(_BLINK_EVAL_SRC) not in sys.path:
    sys.path.insert(0, str(_BLINK_EVAL_SRC))

from blink_evaluation import (  # noqa: E402
    build_events_masterlist_df,
    enrich_absolute_times,
    evaluate_channels,
    load_annotation_as_reference,
    load_ground_truth_annotations,
)
from blink_evaluation.io import dataframe_to_annotations  # noqa: E402
from src.common.bad_epochs import get_valid_epoch_indices  # noqa: E402
from src.common.epoch_input import prepare_epoch_detection_input  # noqa: E402
from tutorial.tutorial_utils import (  # noqa: E402
    discover_cao_pairs,
    discover_raja_pairs,
    get_valid_cao_epoch_indices,
    make_dataset_loaders,
    setup_tutorial_logging,
)

BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
RAJA_ANNOTATION_BASE = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
RAJA_PROCESSED_BASE = Path(r"D:\dataset\drowsy_driving_raja_processed")
CAO_DATASET_ROOT = Path(r"D:\dataset\sustained_attention_driving")

OUT_DIR = REPO_ROOT / "runs" / "extra_blink_type"
CACHE_ROOT = OUT_DIR / "cache"
PROGRESS_JSON = OUT_DIR / "progress.json"
SUMMARY_CSV = OUT_DIR / "recall_by_blink_type.csv"
TABLE_TEX = REPO_ROOT / "writing" / "e_result" / "tab_blink_type_recall.tex"

EPOCH_DURATION_S = 30.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = 100  # downsample to 100 Hz, matching the documented methodology
LONG_THRESHOLD_S = 0.5
VISIBLE_CONDITIONS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
BLINK_TYPES = ["Normal", "Long"]
DEFAULT_MAX_WORKERS = max(1, int(cpu_count() * 0.8))
WORKER_ENV = {
    "PYTHONIOENCODING": "utf-8",
    "NUMBA_DISABLE_JIT": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP41 = _load_module(
    "exp2_strategy_comparison_r2",
    REPO_ROOT / "experiment_script" / "exp2_strategy_comparison.py",
)


def _configure_exp41() -> None:
    EXP41.EPOCH_DURATION_S = EPOCH_DURATION_S
    EXP41.N_EPOCHS = None
    EXP41.VERBOSE = False
    EXP41.RUN_CONDITIONS = VISIBLE_CONDITIONS


def _init_worker() -> None:
    for name, value in WORKER_ENV.items():
        os.environ[name] = value
    os.environ.setdefault("_MNE_FAKE_HOME_DIR", str(REPO_ROOT / ".mne_fake_home"))
    os.environ.setdefault("NUMBA_CACHE_DIR", str(REPO_ROOT / ".numba_cache"))
    _configure_exp41()


def _safe_key(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    label = "_".join(str(p).replace("/", "_").replace("\\", "_").replace(" ", "_") for p in parts[-2:])
    return f"{label}_{digest}"


def _cache_path(dataset: str, session: str, condition: str) -> Path:
    return CACHE_ROOT / dataset / condition / f"{_safe_key(dataset, session, condition)}.json"


def _load_cache(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["condition", "blink_type", "n_blinks", "tp", "fn", "recall"])
        writer.writeheader()
        writer.writerows(rows)


def _gt_annotations(pair: dict, valid_epoch_indices: list[int] | None = None):
    if pair["dataset"] != "cao2018":
        return load_ground_truth_annotations(pair["csv"], EPOCH_DURATION_S)
    ground_truth_raw = load_annotation_as_reference(pair["csv"], EPOCH_DURATION_S)
    if valid_epoch_indices is not None:
        ground_truth_raw = ground_truth_raw[
            ground_truth_raw["epoch_index"].isin(valid_epoch_indices)
        ].reset_index(drop=True)
    return dataframe_to_annotations(enrich_absolute_times(ground_truth_raw, EPOCH_DURATION_S))


def _valid_indices(pair: dict, epochs) -> list[int]:
    if pair["dataset"] == "cao2018":
        return get_valid_cao_epoch_indices(pair.get("epoch_health"), EPOCH_DURATION_S, len(epochs))
    return get_valid_epoch_indices(epochs)


def _blink_type(duration: float) -> str:
    return "Long" if float(duration) >= LONG_THRESHOLD_S else "Normal"


def _extract_gt_event_records(scored, dataset: str, session: str, condition: str) -> list[dict]:
    result = scored.best_eval_result
    if result is None:
        raise RuntimeError("evaluate_channels returned no best_eval_result")
    master = build_events_masterlist_df(
        result.true_positives,
        result.false_positives,
        result.false_negatives,
    )
    records: list[dict] = []
    for row in master.to_dict(orient="records"):
        status = row.get("status")
        if status not in {"tp", "fn"}:
            continue
        duration = row.get("duration_gt")
        onset = row.get("onset_gt")
        idx = row.get("idx")
        if duration is None or onset is None or not math.isfinite(float(duration)):
            raise RuntimeError(
                f"Missing GT onset/duration for {dataset} {session} {condition} status={status}"
            )
        records.append(
            {
                "dataset": dataset,
                "session": session,
                "condition": condition,
                "best_channel": scored.best_channel,
                "gt_index": int(idx),
                "onset_gt": float(onset),
                "duration_gt": float(duration),
                "blink_type": _blink_type(float(duration)),
                "matched": status == "tp",
                "status": status,
            }
        )
    expected = int(result.event_metrics.tp) + int(result.event_metrics.fn)
    if len(records) != expected:
        raise RuntimeError(
            f"Per-GT record mismatch for {dataset} {session} {condition}: "
            f"got {len(records)}, expected tp+fn={expected}"
        )
    return records


def run_one_cell(pair: dict, condition: str) -> dict:
    _configure_exp41()
    start_s = time.perf_counter()
    load_fn = make_dataset_loaders(BRAIN_REGION_YAML)[pair["dataset"]]
    raw = load_fn(pair["fif"])
    epochs = mne.make_fixed_length_epochs(raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR")
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = _valid_indices(pair, epochs)
    channel_results = EXP41._CONDITION_RUNNERS[condition](prepared, valid_epoch_indices)
    gt = _gt_annotations(pair, valid_epoch_indices)
    scored = evaluate_channels(channel_results, gt, epoch_duration=EPOCH_DURATION_S)
    event_records = _extract_gt_event_records(scored, pair["dataset"], pair["name"], condition)
    em = scored.best_eval_result.event_metrics
    return {
        "dataset": pair["dataset"],
        "session": pair["name"],
        "condition": condition,
        "epoch_duration_s": EPOCH_DURATION_S,
        "best_channel": scored.best_channel,
        "tp": int(em.tp),
        "fn": int(em.fn),
        "recall": float(em.recall),
        "n_gt_events": len(event_records),
        "event_records": event_records,
        "wall_clock_s": time.perf_counter() - start_s,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def discover_pairs() -> list[dict]:
    # discover_raja_pairs signature is (annotation_base_dir, processed_base_dir);
    # Manager fix: the original author call had these two paths swapped, which
    # returned zero Raja sessions. Restored to match tcao2_full_rerun.py / exp40.
    raja_pairs = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    cao_pairs = discover_cao_pairs(CAO_DATASET_ROOT)
    return raja_pairs + cao_pairs


def _select_pairs(pairs: list[dict], args: argparse.Namespace) -> list[dict]:
    selected = pairs
    if args.dataset != "all":
        selected = [p for p in selected if p["dataset"] == args.dataset]
    if args.smoke_session is not None:
        raja = [p for p in selected if p["dataset"] == "raja"]
        if not raja:
            raise RuntimeError("No Raja sessions available for --smoke-session")
        idx = max(0, int(args.smoke_session) - 1)
        if idx >= len(raja):
            raise RuntimeError(f"--smoke-session {args.smoke_session} exceeds Raja session count {len(raja)}")
        selected = [raja[idx]]
    if args.limit is not None:
        selected = selected[: args.limit]
    return selected


def _progress_line(done: int, total: int, start_s: float) -> str:
    pct = (done / total * 100.0) if total else 100.0
    elapsed = max(0.0, time.perf_counter() - start_s)
    eta_s = elapsed / done * (total - done) if done and total > done else 0.0
    return f"blink-type: {done}/{total} [{pct:6.2f}%] ETA {eta_s / 60.0:.1f}m"


def _write_progress(rows: list[dict], total_tasks: int, max_workers: int, current: dict | None = None) -> None:
    payload = {
        "experiment": "blink_type_recall@30s",
        "tasks_total": total_tasks,
        "tasks_done": len(rows),
        "pct": round((len(rows) / total_tasks * 100.0) if total_tasks else 100.0, 3),
        "conditions": VISIBLE_CONDITIONS,
        "current": current or {},
        "max_workers": max_workers,
        "updated": datetime.now().isoformat(timespec="seconds"),
    }
    _atomic_write_json(PROGRESS_JSON, payload)


def aggregate(cells: Iterable[dict]) -> list[dict]:
    buckets: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"tp": 0, "fn": 0})
    for cell in cells:
        for event in cell["event_records"]:
            key = (event["condition"], event["blink_type"])
            if event["matched"]:
                buckets[key]["tp"] += 1
            else:
                buckets[key]["fn"] += 1
    rows: list[dict] = []
    for condition in VISIBLE_CONDITIONS:
        for blink_type in BLINK_TYPES:
            counts = buckets[(condition, blink_type)]
            n_blinks = counts["tp"] + counts["fn"]
            recall = counts["tp"] / n_blinks if n_blinks else 0.0
            rows.append(
                {
                    "condition": condition,
                    "blink_type": blink_type,
                    "n_blinks": n_blinks,
                    "tp": counts["tp"],
                    "fn": counts["fn"],
                    "recall": f"{recall:.10f}",
                }
            )
    return rows


def _latex_recall(value: float, best: float) -> str:
    text = f"{value:.4f}"
    return f"\\textbf{{{text}}}" if abs(value - best) < 5e-13 else text


def write_latex_table(summary_rows: list[dict]) -> None:
    by_condition_type = {
        (row["condition"], row["blink_type"]): row
        for row in summary_rows
    }
    normal_count = int(by_condition_type[(VISIBLE_CONDITIONS[0], "Normal")]["n_blinks"])
    long_count = int(by_condition_type[(VISIBLE_CONDITIONS[0], "Long")]["n_blinks"])
    best_normal = max(float(by_condition_type[(c, "Normal")]["recall"]) for c in VISIBLE_CONDITIONS)
    best_long = max(float(by_condition_type[(c, "Long")]["recall"]) for c in VISIBLE_CONDITIONS)
    lines = [
        "% Source: experiment_script/paper_blink_type_recall.py; runs/extra_blink_type/recall_by_blink_type.csv",
        "\\begin{table}[ht]",
        "  \\centering",
        "  \\caption{Extra analysis: event-level recall split by blink duration",
        "    (30\\,s epochs). Normal $=$ duration $<0.5$\\,s, Long $=$ duration $\\geq0.5$\\,s",
        "    (the long-closure threshold). Ground truth contains "
        f"{normal_count:,}".replace(",", "{,}") + " normal and",
        f"    {long_count:,}".replace(",", "{,}") + " long blinks across Raja and Cao2018. Best recall per column in \\textbf{bold}.}",
        "  \\label{tab:blink_type_recall}",
        "  \\begin{tabular}{lcc}",
        "    \\toprule",
        "    Condition & Normal recall & Long recall \\\\",
        "    \\midrule",
    ]
    label_width = max(len(c) for c in VISIBLE_CONDITIONS)
    for condition in VISIBLE_CONDITIONS:
        normal = float(by_condition_type[(condition, "Normal")]["recall"])
        long = float(by_condition_type[(condition, "Long")]["recall"])
        lines.append(
            f"    {condition:<{label_width}} & {_latex_recall(normal, best_normal)} & {_latex_recall(long, best_long)} \\\\"
        )
        if condition == "MNE-annot":
            lines.append("% DBO-related results are intentionally commented out because DBO is reserved for a future paper.")
            lines.append("%    DBO            & 0.0000 & 0.0000 \\\\")
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    TABLE_TEX.parent.mkdir(parents=True, exist_ok=True)
    TABLE_TEX.write_text("\n".join(lines), encoding="utf-8")


def _submit_tasks(tasks: list[dict], use_threads: bool, max_workers: int):
    if use_threads:
        executor = ThreadPoolExecutor(max_workers=max_workers)
    else:
        executor = ProcessPoolExecutor(max_workers=max_workers, initializer=_init_worker)
    future_map = {
        executor.submit(run_one_cell, task["pair"], task["condition"]): task
        for task in tasks
    }
    return executor, future_map


def run(args: argparse.Namespace) -> list[dict]:
    _init_worker()
    pairs = _select_pairs(discover_pairs(), args)
    conditions = args.conditions or VISIBLE_CONDITIONS
    bad_conditions = sorted(set(conditions) - set(VISIBLE_CONDITIONS))
    if bad_conditions:
        raise ValueError(f"Unsupported visible conditions: {bad_conditions}")

    tasks = []
    rows = []
    for pair in pairs:
        for condition in conditions:
            cache = _cache_path(pair["dataset"], pair["name"], condition)
            cached = None if args.no_cache else _load_cache(cache)
            if cached is not None:
                rows.append(cached)
            else:
                tasks.append({"pair": pair, "condition": condition, "cache": cache})

    total_tasks = len(rows) + len(tasks)
    max_workers = max(1, int(args.max_workers or DEFAULT_MAX_WORKERS))
    if args.smoke_session is not None or args.limit is not None:
        max_workers = min(max_workers, 1 if args.max_workers is None else max_workers)
    _write_progress(rows, total_tasks, max_workers)

    start_s = time.perf_counter()
    if tasks:
        mode = "ThreadPoolExecutor" if args.use_threads else "ProcessPoolExecutor"
        print(f"pending cells: {len(tasks)} with {mode} max_workers={max_workers}", flush=True)
        executor, future_map = _submit_tasks(tasks, args.use_threads, max_workers)
        with executor:
            for future in as_completed(future_map):
                task = future_map[future]
                pair = task["pair"]
                condition = task["condition"]
                try:
                    payload = future.result()
                    if not args.no_cache:
                        _save_cache(task["cache"], payload)
                    rows.append(payload)
                    print(
                        f"done {pair['dataset']} {pair['name']} {condition}: "
                        f"best={payload['best_channel']} tp={payload['tp']} fn={payload['fn']} "
                        f"recall={payload['recall']:.4f}",
                        flush=True,
                    )
                except Exception as exc:
                    print(f"ERROR {pair['dataset']} {pair['name']} {condition}: {exc}", flush=True)
                    raise
                print(_progress_line(len(rows), total_tasks, start_s), flush=True)
                _write_progress(
                    rows,
                    total_tasks,
                    max_workers,
                    {"dataset": pair["dataset"], "session": pair["name"], "condition": condition},
                )

    summary = aggregate(rows)
    for row in summary:
        if args.smoke_session is not None or args.limit is not None:
            if int(row["n_blinks"]):
                print(
                    f"{row['condition']} {row['blink_type']}: "
                    f"n={row['n_blinks']} tp={row['tp']} fn={row['fn']} recall={float(row['recall']):.4f}",
                    flush=True,
                )

    full_run = args.smoke_session is None and args.limit is None and set(conditions) == set(VISIBLE_CONDITIONS)
    if full_run:
        _write_csv(SUMMARY_CSV, summary)
        write_latex_table(summary)
        print(f"wrote {SUMMARY_CSV}", flush=True)
        print(f"wrote {TABLE_TEX}", flush=True)
    else:
        print("smoke/limited run: skipped final CSV/table rewrite", flush=True)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Event-level recall by GT blink duration for Raja + Cao2018.")
    parser.add_argument("--dataset", choices=["all", "raja", "cao2018"], default="all")
    parser.add_argument("--conditions", nargs="+", choices=VISIBLE_CONDITIONS, default=None)
    parser.add_argument("--smoke-session", type=int, default=None, help="Run one Raja session by 1-based index.")
    parser.add_argument("--limit", type=int, default=None, help="Limit selected sessions before condition expansion.")
    parser.add_argument("--use-threads", action="store_true", help="Use ThreadPoolExecutor instead of ProcessPoolExecutor.")
    parser.add_argument("--max-workers", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    return parser.parse_args()


def main() -> None:
    setup_tutorial_logging()
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
