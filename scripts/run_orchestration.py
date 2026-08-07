"""Master orchestration for blink detection experiments.

Usage:
    conda run -n pyblinker_worktree_epoch_blink python scripts/run_orchestration.py
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Experiment scripts moved to experiment_script/ and renamed to the result-section
# academic outline (exp1..exp6); see tutorial/channel_region_refactor_plan.md.
SCRIPT_40 = REPO_ROOT / "experiment_script" / "exp3_epoch_duration.py"
SCRIPT_41 = REPO_ROOT / "experiment_script" / "exp2_a_strategy_comparison.py"
SCRIPT_42 = REPO_ROOT / "experiment_script" / "exp4_boundary_tolerance.py"
SCRIPT_45 = REPO_ROOT / "experiment_script" / "exp6_morphological.py"
ANALYZE_SCRIPT = REPO_ROOT / "scripts" / "analyze_and_update.py"
LOG_BASE = REPO_ROOT / "logs"

AGENT_NAME = "orchestration-runner"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _banner(msg: str) -> None:
    width = max(len(msg) + 6, 72)
    bar = "=" * width
    print(f"\n{bar}\n  {msg}\n{bar}")
    sys.stdout.flush()


def _run(label: str, cmd: list[str], log_path: Path) -> tuple[bool, str]:
    """Run subprocess, stream output to console + log file.  Return (ok, full_output)."""
    start = time.time()
    print(f"\n[{_ts()}] [RUNNING] {label}")
    print(f"         cmd : {' '.join(str(x) for x in cmd)}")
    print(f"         log : {log_path}")
    sys.stdout.flush()

    log_path.parent.mkdir(parents=True, exist_ok=True)
    captured: list[str] = []

    with log_path.open("w", encoding="utf-8", errors="replace") as lf:
        lf.write(f"# Command: {' '.join(str(x) for x in cmd)}\n")
        lf.write(f"# Started: {datetime.now().isoformat()}\n\n")
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lf.write(line)
            captured.append(line)
        proc.wait()

    elapsed = time.time() - start
    success = proc.returncode == 0
    tag = "DONE" if success else "FAILED"
    print(f"[{_ts()}] [{tag}] {label}  (exit={proc.returncode}, elapsed={elapsed:.1f}s)")
    sys.stdout.flush()
    return success, "".join(captured)


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if src.exists():
        dst.write_bytes(src.read_bytes())
        return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = LOG_BASE / f"experiment_orchestration_{ts}"
    log_dir.mkdir(parents=True, exist_ok=True)

    _banner(f"[START] Experiment orchestration  {ts}")
    print(f"[{_ts()}] [INFO] Project root    : {REPO_ROOT}")
    print(f"[{_ts()}] [INFO] Log directory   : {log_dir}")
    print(f"[{_ts()}] [INFO] Python           : {sys.executable}")
    sys.stdout.flush()

    exp_status: dict[str, str] = {}

    # -----------------------------------------------------------------------
    # Step 1: Experiment 40 — epoch duration sweep
    # -----------------------------------------------------------------------
    _banner("[START] Experiment 1: epoch duration sweep (Exp 40)")
    print(f"[{_ts()}] [INFO] Agent: epoch-sweep-runner")
    print(f"[{_ts()}] [INFO] Epoch durations: 20, 30, 40, 60, 120 s")
    print(f"[{_ts()}] [INFO] Primary metric: macro_F1 (dataset=all)")
    sys.stdout.flush()

    exp40_dir = log_dir / "exp40"
    exp40_dir.mkdir(parents=True, exist_ok=True)

    ok40, _ = _run(
        "Exp40 — epoch duration sweep",
        [
            sys.executable, str(SCRIPT_40),
            "--epoch-durations-s", "20,30,40,60,120",
            "--out-dir", str(exp40_dir),
            "--quiet",
        ],
        exp40_dir / "exp40_run.log",
    )

    if not ok40:
        print(f"[{_ts()}] [FATAL] Experiment 40 failed. Aborting pipeline.")
        sys.exit(1)

    exp_status["exp40"] = "OK"

    # Parse best epoch from summary.json
    summary40_path = exp40_dir / "summary.json"
    if not summary40_path.exists():
        print(f"[{_ts()}] [FATAL] {summary40_path} not found after exp40.")
        sys.exit(1)

    summary40 = json.loads(summary40_path.read_text(encoding="utf-8"))
    best_epoch_s: float = float(summary40["best_epoch_duration_s"])
    metric_primary: str = summary40.get("metric_primary", "macro_f1 (dataset=all)")
    best_row: dict = summary40.get("best_row", {})

    print(f"\n[{_ts()}] [BEST EPOCH] Proposed-Med performs best at {best_epoch_s:.0f} seconds")
    print(f"[{_ts()}] [METRIC    ] {metric_primary}")
    if best_row:
        print(
            f"[{_ts()}] [BEST ROW  ] macro_F1={best_row.get('macro_f1', 'N/A'):.4f}  "
            f"macro_P={best_row.get('macro_precision', 'N/A'):.4f}  "
            f"macro_R={best_row.get('macro_recall', 'N/A'):.4f}  "
            f"n_sessions={best_row.get('n_sessions', 'N/A')}"
        )
    sys.stdout.flush()

    # Print epoch duration summary table
    summary_csv_path = exp40_dir / "exp1_epoch_duration_summary.csv"
    if summary_csv_path.exists():
        with summary_csv_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        all_rows = sorted(
            [r for r in rows if r.get("dataset") == "all"],
            key=lambda r: float(r.get("epoch_duration_s", 0))
        )
        if all_rows:
            print(f"\n  Epoch sweep summary (dataset=all):")
            print(f"  {'dur_s':>6}  {'macro_F1':>9}  {'macro_P':>9}  {'macro_R':>9}  {'n_sessions':>10}")
            print(f"  {'-' * 52}")
            for r in all_rows:
                marker = " <-- BEST" if float(r.get("epoch_duration_s", 0)) == best_epoch_s else ""
                print(
                    f"  {float(r['epoch_duration_s']):>6.0f}  "
                    f"{float(r['macro_f1']):>9.4f}  "
                    f"{float(r['macro_precision']):>9.4f}  "
                    f"{float(r['macro_recall']):>9.4f}  "
                    f"{int(float(r.get('n_sessions', 0))):>10}{marker}"
                )
        print()
    sys.stdout.flush()

    # -----------------------------------------------------------------------
    # Steps 2–4: Downstream experiments with best epoch
    # -----------------------------------------------------------------------
    downstream = [
        (
            "exp41",
            SCRIPT_41,
            "strategy-comparison-runner",
            "Strategy comparison (5 conditions)",
        ),
        (
            "exp42",
            SCRIPT_42,
            "boundary-tolerance-runner",
            "Boundary tolerance / IoU sweep",
        ),
        (
            "exp45",
            SCRIPT_45,
            "morphology-experiment-runner",
            "Morphological detailed analysis",
        ),
    ]

    exp_dirs: dict[str, Path] = {}

    for exp_id, script, agent, description in downstream:
        _banner(f"[START] {description} ({exp_id})")
        print(f"[{_ts()}] [INFO] Agent          : {agent}")
        print(f"[{_ts()}] [INFO] Epoch duration : {best_epoch_s:.0f} s")
        sys.stdout.flush()

        exp_dir = log_dir / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        exp_dirs[exp_id] = exp_dir

        ok, _ = _run(
            f"{exp_id} — {description}",
            [
                sys.executable, str(script),
                "--epoch-duration-s", str(best_epoch_s),
                "--out-dir", str(exp_dir),
                "--quiet",
            ],
            exp_dir / f"{exp_id}_run.log",
        )
        exp_status[exp_id] = "OK" if ok else "FAILED"
        if not ok:
            print(f"[{_ts()}] [WARN] {exp_id} failed; downstream analysis may be incomplete.")
        sys.stdout.flush()

    # -----------------------------------------------------------------------
    # Step 5: Collect top-level artifacts
    # -----------------------------------------------------------------------
    _banner("[START] Collecting top-level artifacts")

    artifact_map = [
        ("exp1_epoch_duration_results.csv",    exp40_dir / "exp1_epoch_duration_results.csv"),
        ("exp1_epoch_duration_results.json",   exp40_dir / "summary.json"),
        ("strategy_comparison_results.csv",    exp_dirs.get("exp41", log_dir) / "exp2_strategy_comparison_results.csv"),
        ("boundary_tolerance_results.csv",     exp_dirs.get("exp42", log_dir) / "exp42_boundary_tolerance_results.csv"),
        ("morphological_detailed_results.csv", exp_dirs.get("exp45", log_dir) / "exp45_morphological_event_counts.csv"),
    ]

    for dest_name, src_path in artifact_map:
        dest = log_dir / dest_name
        if _copy_if_exists(src_path, dest):
            print(f"[{_ts()}] [COPY] {dest_name}")
        else:
            print(f"[{_ts()}] [WARN] Missing: {src_path.name}")
    sys.stdout.flush()

    # -----------------------------------------------------------------------
    # Step 6: Analysis + LaTeX update
    # -----------------------------------------------------------------------
    _banner("[START] Analysis, failure analysis, and LaTeX update")
    print(f"[{_ts()}] [INFO] Agent: manuscript-analysis-planner / latex-results-writer")
    sys.stdout.flush()

    if ANALYZE_SCRIPT.exists():
        ok_a, _ = _run(
            "analyze_and_update.py",
            [
                sys.executable, str(ANALYZE_SCRIPT),
                "--log-dir", str(log_dir),
                "--best-epoch-s", str(best_epoch_s),
            ],
            log_dir / "analyze_and_update.log",
        )
        exp_status["analyze_and_update"] = "OK" if ok_a else "FAILED"
    else:
        print(f"[{_ts()}] [WARN] {ANALYZE_SCRIPT} not found; skipping analysis step.")
        exp_status["analyze_and_update"] = "SKIP"
    sys.stdout.flush()

    # -----------------------------------------------------------------------
    # Step 7: Generate top-level summary.json and summary.csv
    # -----------------------------------------------------------------------
    _banner("[START] Writing top-level summary artifacts")

    exp1_duration_rows: list[dict] = []
    if summary_csv_path.exists():
        with summary_csv_path.open(encoding="utf-8") as f:
            exp1_duration_rows = list(csv.DictReader(f))

    top_summary = {
        "timestamp": ts,
        "log_dir": str(log_dir),
        "best_epoch_duration_s": best_epoch_s,
        "metric_primary": metric_primary,
        "experiment_status": exp_status,
        "exp1_best_row": best_row,
        "exp1_duration_summary": exp1_duration_rows,
    }
    (log_dir / "summary.json").write_text(
        json.dumps(top_summary, indent=2, default=str), encoding="utf-8"
    )

    summary_csv_rows = [{"key": "best_epoch_s", "value": str(best_epoch_s)},
                        {"key": "metric", "value": metric_primary}]
    for exp_id, status in exp_status.items():
        summary_csv_rows.append({"key": exp_id, "value": status})

    with (log_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["key", "value"])
        w.writeheader()
        w.writerows(summary_csv_rows)

    print(f"[{_ts()}] [DONE] summary.json written to {log_dir / 'summary.json'}")
    print(f"[{_ts()}] [DONE] summary.csv written to  {log_dir / 'summary.csv'}")
    sys.stdout.flush()

    # -----------------------------------------------------------------------
    # Final summary table
    # -----------------------------------------------------------------------
    _banner("FINAL SUMMARY")
    print(f"  Log directory  : {log_dir}")
    print(f"  Best epoch     : {best_epoch_s:.0f} s")
    print(f"  Metric         : {metric_primary}")
    if best_row:
        print(f"  Best macro-F1  : {best_row.get('macro_f1', 'N/A'):.4f}")
    print()
    print(f"  {'Experiment':<28}  Status")
    print(f"  {'-' * 38}")
    for exp_id, status in exp_status.items():
        print(f"  {exp_id:<28}  {status}")
    print()

    n_failed = sum(1 for s in exp_status.values() if s == "FAILED")
    if n_failed == 0:
        print("[DONE] All experiments completed successfully.")
    else:
        print(f"[WARN] {n_failed} step(s) FAILED. Review logs in {log_dir}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
