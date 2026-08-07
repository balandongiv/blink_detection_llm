"""Runs the exp1/exp2/exp3 pipeline end to end, in sequence, with Telegram updates.

Order::

    exp1_a_channel_selection_cao2018.py
    exp1_a_channel_selection_raja.py
    exp1_b_plot_region_boxplot.py
    exp1_b_plot_single_channel.py
    -> analysis + both plots sent to Telegram

    exp2_a_strategy_comparison_cao2018.py
    exp2_a_strategy_comparison_raja.py
    exp2_b_plot_pr_scatter.py
    -> analysis + plot sent to Telegram

    exp3_a_epoch_duration_cao2018.py
    exp3_a_epoch_duration_raja.py
    exp3_b_plot_epoch_duration.py
    -> analysis + plot sent to Telegram

    sanity_check_all_channel_30s.py

A heartbeat is sent to Telegram every 10 minutes while a step is running (via
run_task's background thread), independent of the per-experiment analysis+plot
updates sent after exp1/exp2/exp3 complete for both datasets.

Run inside conda env double_threshold_algo:
    python experiment_script/run_exp123_full_pipeline_orchestrator.py
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from telegram_heartbeat import (  # noqa: E402
    send_key_update,
    send_telegram_photo,
    send_urgent_update,
    set_state,
)

PYTHON = sys.executable
HEARTBEAT_INTERVAL_S = 600  # 10 minutes
LOG_DIR = REPO_ROOT / "logs" / "exp123_full_pipeline_orchestrator"
LOG_DIR.mkdir(parents=True, exist_ok=True)
FIGDIR = REPO_ROOT / "writing" / "figures"

_PATH_CFG = yaml.safe_load((REPO_ROOT / "experiment_script" / "setup" / "exp_path.yaml").read_text())
OUT_DIRS = _PATH_CFG["out_dirs"]

EXP1_RAJA_OUT = REPO_ROOT / Path(OUT_DIRS["exp1"]["raja"])
EXP1_CAO_OUT = REPO_ROOT / Path(OUT_DIRS["exp1"]["cao2018"])
EXP2_RAJA_OUT = REPO_ROOT / Path(OUT_DIRS["exp2"]["raja"])
EXP2_CAO_OUT = REPO_ROOT / Path(OUT_DIRS["exp2"]["cao2018"])
EXP3_RAJA_OUT = REPO_ROOT / Path(OUT_DIRS["exp3"]["raja"])
EXP3_CAO_OUT = REPO_ROOT / Path(OUT_DIRS["exp3"]["cao2018"])


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _tail(path: Path, n: int = 8) -> str:
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
        return "\n".join(lines[-n:]) if lines else "(log empty)"
    except Exception:
        return "(no log yet)"


def run_task(label: str, cmd: list[str], out_dir: Path | None = None, total_n: int = 0) -> bool:
    log_path = LOG_DIR / f"{label.replace(' ', '_')}.log"
    print(f"\n[{_ts()}] START {label}\n         cmd: {' '.join(str(c) for c in cmd)}\n         log: {log_path}")
    send_key_update(f"START {label}\ncmd: {' '.join(str(c) for c in cmd)}")
    set_state(current_task=label, last_step="launching", next_step="running")

    stop_event = threading.Event()
    start_time = time.time()

    def _heartbeat_loop() -> None:
        while not stop_event.wait(HEARTBEAT_INTERVAL_S):
            elapsed = timedelta(seconds=int(time.time() - start_time))
            progress = ""
            if out_dir is not None:
                sess_dir = out_dir / "sessions"
                n_cached = len(list(sess_dir.glob("*.csv"))) if sess_dir.exists() else 0
                progress = f"{n_cached}/{total_n} sessions\n" if total_n else f"{n_cached} sessions\n"
            send_key_update(
                f"{label} still running\nelapsed: {elapsed}\n{progress}"
                f"last log lines:\n{_tail(log_path, 6)}"
            )

    hb_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    hb_thread.start()

    ok = False
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as lf:
            lf.write(f"# {' '.join(str(c) for c in cmd)}\n# started {_ts()}\n\n")
            proc = subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
            for line in proc.stdout:
                sys.stdout.write(line)
                lf.write(line)
            proc.wait()
        ok = proc.returncode == 0
    except Exception as exc:  # noqa: BLE001
        send_urgent_update(f"{label} crashed to launch: {exc}\n{traceback.format_exc()[-1200:]}")
        ok = False
    finally:
        stop_event.set()
        hb_thread.join(timeout=5)

    elapsed = timedelta(seconds=int(time.time() - start_time))
    status = "OK" if ok else "FAILED"
    print(f"[{_ts()}] {status} {label} (elapsed={elapsed})")
    if not ok:
        send_urgent_update(f"{label} FAILED after {elapsed}. Tail of log:\n{_tail(log_path, 15)}")
    else:
        send_key_update(f"DONE {label} (elapsed={elapsed})")
    return ok


# ---------------------------------------------------------------------------
# Per-experiment analysis (plain precision/recall/F1 only — no Stage A / internal
# column names in any Telegram-facing text)
# ---------------------------------------------------------------------------

def analyze_exp1(dataset_label: str, csv_path: Path) -> str:
    lines = [f"[exp1 {dataset_label}] channel selection — top channels by F1"]
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        return f"[exp1 {dataset_label}] ERROR reading {csv_path}: {exc}"
    for center in sorted(df["center_method"].dropna().unique()):
        sub = df[df["center_method"] == center].sort_values("f1_macro", ascending=False).head(3)
        lines.append(f"  center={center}:")
        for _, r in sub.iterrows():
            lines.append(
                f"    {r['selection']}/{r['channel']}: "
                f"precision={r['precision_macro']:.3f} recall={r['recall_macro']:.3f} F1={r['f1_macro']:.3f}"
            )
    return "\n".join(lines)


def analyze_exp2(dataset_label: str, csv_path: Path) -> str:
    lines = [f"[exp2 {dataset_label}] strategy comparison — mean precision/recall/F1 by condition"]
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        return f"[exp2 {dataset_label}] ERROR reading {csv_path}: {exc}"
    grp = df.groupby("condition")[["precision", "recall", "f1"]].mean().sort_values("f1", ascending=False)
    for cond, row in grp.iterrows():
        lines.append(f"  {cond}: precision={row['precision']:.3f} recall={row['recall']:.3f} F1={row['f1']:.3f}")
    return "\n".join(lines)


def analyze_exp3(dataset_label: str, csv_path: Path) -> str:
    lines = [f"[exp3 {dataset_label}] epoch-duration sweep — mean precision/recall/F1 by duration"]
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        return f"[exp3 {dataset_label}] ERROR reading {csv_path}: {exc}"
    grp = df.groupby("epoch_duration_s")[["precision", "recall", "f1"]].mean().sort_index()
    for dur, row in grp.iterrows():
        lines.append(f"  {dur:.0f}s: precision={row['precision']:.3f} recall={row['recall']:.3f} F1={row['f1']:.3f}")
    return "\n".join(lines)


def send_analysis_and_plots(text: str, plot_paths: list[Path]) -> None:
    send_key_update(text)
    for p in plot_paths:
        if p.exists():
            send_telegram_photo(p, caption=p.name)
        else:
            send_key_update(f"WARNING: expected plot not found: {p}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    send_key_update(
        "Full exp1/exp2/exp3 pipeline orchestrator starting.\n"
        "Order: exp1 (cao2018, raja, both plots) -> exp2 (cao2018, raja, plot) -> "
        "exp3 (cao2018, raja, plot) -> sanity check.\n"
        "Heartbeat every 10 min while a step runs; analysis + plot(s) sent to Telegram "
        "after each major experiment completes for both datasets."
    )

    # ---- exp1 ----
    # n_jobs=1: the default process-pool (n_jobs=10) has previously died silently a few
    # minutes in with no traceback on this machine (see run_exp123_orchestrator.py) —
    # single-process is slower but reliable, and --out-dir session caching means a
    # crash mid-run only costs the sessions not yet cached.
    if not run_task(
        "exp1 Cao2018",
        [PYTHON, "experiment_script/exp1_a_channel_selection_cao2018.py", "--n-jobs", "1"],
        EXP1_CAO_OUT,
    ):
        return
    if not run_task(
        "exp1 Raja",
        [PYTHON, "experiment_script/exp1_a_channel_selection_raja.py", "--n-jobs", "1"],
        EXP1_RAJA_OUT,
    ):
        return
    if not run_task("exp1 plot: region boxplot", [PYTHON, "experiment_script/exp1_b_plot_region_boxplot.py"]):
        return
    if not run_task("exp1 plot: single channel", [PYTHON, "experiment_script/exp1_b_plot_single_channel.py"]):
        return

    exp1_text = "\n\n".join([
        analyze_exp1("Cao2018", EXP1_CAO_OUT / "exp1_channel_selection_cao2018_summary.csv"),
        analyze_exp1("Raja", EXP1_RAJA_OUT / "exp1_channel_selection_raja_summary.csv"),
    ])
    send_analysis_and_plots(exp1_text, [
        FIGDIR / "fig_exp1_region_boxplot.png",
        FIGDIR / "fig_exp1_single_channel_boxplot.png",
    ])

    # ---- exp2 ----
    if not run_task(
        "exp2 Cao2018",
        [PYTHON, "experiment_script/exp2_a_strategy_comparison_cao2018.py", "--n-jobs", "1"],
        EXP2_CAO_OUT,
    ):
        return
    if not run_task(
        "exp2 Raja",
        [PYTHON, "experiment_script/exp2_a_strategy_comparison_raja.py", "--n-jobs", "1"],
        EXP2_RAJA_OUT,
    ):
        return
    if not run_task("exp2 plot: PR scatter", [PYTHON, "experiment_script/exp2_b_plot_pr_scatter.py"]):
        return

    exp2_text = "\n\n".join([
        analyze_exp2("Cao2018", EXP2_CAO_OUT / "exp2_strategy_comparison_cao2018_results.csv"),
        analyze_exp2("Raja", EXP2_RAJA_OUT / "exp2_strategy_comparison_raja_results.csv"),
    ])
    send_analysis_and_plots(exp2_text, [FIGDIR / "fig_exp2_pr_scatter.png"])

    # ---- exp3 ----
    if not run_task(
        "exp3 Cao2018",
        [PYTHON, "experiment_script/exp3_a_epoch_duration_cao2018.py", "--n-jobs", "1"],
        EXP3_CAO_OUT,
    ):
        return
    if not run_task(
        "exp3 Raja",
        [PYTHON, "experiment_script/exp3_a_epoch_duration_raja.py", "--n-jobs", "1"],
        EXP3_RAJA_OUT,
    ):
        return
    if not run_task("exp3 plot: epoch duration", [PYTHON, "experiment_script/exp3_b_plot_epoch_duration.py"]):
        return

    exp3_text = "\n\n".join([
        analyze_exp3("Cao2018", EXP3_CAO_OUT / "exp3_epoch_duration_cao2018_summary.csv"),
        analyze_exp3("Raja", EXP3_RAJA_OUT / "exp3_epoch_duration_raja_summary.csv"),
    ])
    send_analysis_and_plots(exp3_text, [FIGDIR / "fig_exp3_epoch_duration.png"])

    # ---- sanity check ----
    if not run_task("sanity check (all_channel/30s)", [PYTHON, "experiment_script/sanity_check_all_channel_30s.py"]):
        return

    send_key_update("Full exp1/exp2/exp3 pipeline orchestrator finished.")


if __name__ == "__main__":
    main()
