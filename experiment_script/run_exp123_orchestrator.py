"""Supplement to the already-running exp1/exp2/exp3 pipeline (launched from an earlier
session; writes to runs/exp1_channel_*, runs/exp2_*, runs/exp3_*).

That run already covers exp1 Raja+Cao2018, exp2 Raja+Cao2018, exp3 Raja+Cao2018 (now
including the all_channel group — see experiment_script/setup/exp3_epoch_duration.yaml)
with a Telegram heartbeat every 10 min and a plot + analysis after each experiment. This
script does NOT duplicate that work. It only:

  1. Waits for exp1 Cao2018 (already ~done) to finish, then re-runs exp1 Raja — its
     output directory (runs/exp1_channel_raja) was found missing on disk even though the
     earlier run's log showed it completing; something deleted it after the fact. Waiting
     for Cao2018 first avoids the resource contention that made an earlier concurrent
     attempt at this rerun crash (10+10 worker processes on one machine).
  2. Waits for the other process to produce exp2 (Raja, Cao2018) and exp3 (Raja, Cao2018)
     results, then runs the sanity check: reads the ACTUAL exp1/exp2/exp3 result CSVs
     produced by the real pipeline runs, filters each to epoch_duration_s=30 / all 32
     channels (selection == "all_channel"), and compares the Proposed result across all
     three experiments for both datasets, to catch any pipeline drift between the three
     independently invoked scripts. Flags ANY difference beyond tolerance, including the
     expected exp1-vs-exp2 engine-difference gap (per user's explicit choice).

No separate "sanity-only" runs are launched — exp3's all_channel group is now a standing
part of experiment_script/setup/exp3_epoch_duration.yaml, so the real exp3 run already
produces the data point this check needs.

Run inside conda env double_threshold_algo:
    python experiment_script/run_exp123_orchestrator.py
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
    send_urgent_update,
    set_state,
)

PYTHON = sys.executable
HEARTBEAT_INTERVAL_S = 600  # 10 minutes
POLL_INTERVAL_S = 120
LOG_DIR = REPO_ROOT / "logs" / "exp123_orchestrator"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_PATH_CFG = yaml.safe_load((REPO_ROOT / "experiment_script" / "setup" / "exp_path.yaml").read_text())
OUT_DIRS = _PATH_CFG["out_dirs"]

EXP1_RAJA_OUT = REPO_ROOT / Path(OUT_DIRS["exp1"]["raja"])
EXP1_CAO_OUT = REPO_ROOT / Path(OUT_DIRS["exp1"]["cao2018"])
EXP2_RAJA_OUT = REPO_ROOT / Path(OUT_DIRS["exp2"]["raja"])
EXP2_CAO_OUT = REPO_ROOT / Path(OUT_DIRS["exp2"]["cao2018"])
EXP3_RAJA_OUT = REPO_ROOT / Path(OUT_DIRS["exp3"]["raja"])
EXP3_CAO_OUT = REPO_ROOT / Path(OUT_DIRS["exp3"]["cao2018"])

TOLERANCE = 1e-3  # sanity-check flag threshold


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _tail(path: Path, n: int = 8) -> str:
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
        return "\n".join(lines[-n:]) if lines else "(log empty)"
    except Exception:
        return "(no log yet)"


def wait_for_files(label: str, paths: list[Path], max_wait_s: int = 24 * 3600) -> bool:
    print(f"[{_ts()}] WAIT {label}: polling for {[str(p) for p in paths]}")
    waited = 0
    last_notify = 0
    while waited < max_wait_s:
        if all(p.exists() for p in paths):
            print(f"[{_ts()}] WAIT {label}: all files present")
            return True
        time.sleep(POLL_INTERVAL_S)
        waited += POLL_INTERVAL_S
        if waited - last_notify >= HEARTBEAT_INTERVAL_S:
            last_notify = waited
            missing = [p.name for p in paths if not p.exists()]
            send_key_update(f"Waiting on {label} (other process) — still missing: {missing}")
    send_urgent_update(f"Timed out waiting for {label}: {[str(p) for p in paths if not p.exists()]}")
    return False


def run_task(label: str, cmd: list[str], out_dir: Path, total_n: int) -> bool:
    log_path = LOG_DIR / f"{label.replace(' ', '_')}.log"
    print(f"\n[{_ts()}] START {label}\n         cmd: {' '.join(str(c) for c in cmd)}\n         log: {log_path}")
    send_key_update(f"START {label}\ncmd: {' '.join(str(c) for c in cmd)}")
    set_state(current_task=label, last_step="launching", next_step="running")

    stop_event = threading.Event()
    start_time = time.time()

    def _heartbeat_loop() -> None:
        while not stop_event.wait(HEARTBEAT_INTERVAL_S):
            elapsed = timedelta(seconds=int(time.time() - start_time))
            sess_dir = out_dir / "sessions"
            n_cached = len(list(sess_dir.glob("*.csv"))) if sess_dir.exists() else 0
            progress = f"{n_cached}/{total_n} sessions" if total_n else f"{n_cached} sessions"
            send_key_update(
                f"{label} still running\nelapsed: {elapsed}\nprogress: {progress}\n"
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
# Sanity check: all_channel / 30s / median Proposed result across exp1/2/3
# ---------------------------------------------------------------------------

def sanity_check() -> None:
    lines = [
        "SANITY CHECK — all_channel (32 ch), 30s epoch, median centre, Proposed",
        "Source: the actual result CSVs written by exp1/exp2/exp3's real runs (no separate",
        "sanity-only run). exp1 & exp3 share the same per-channel engine and should match",
        "near-exactly; exp2 uses a different session-adaptive best-channel engine, so a",
        "small gap there is structurally expected per HANDOFF.md 2026-07-15 — still",
        "reported below rather than suppressed.",
        "",
    ]
    any_flag = False

    datasets = [
        (
            "Raja",
            EXP1_RAJA_OUT, "exp1_channel_selection_raja_summary.csv",
            EXP3_RAJA_OUT, "exp3_epoch_duration_raja_summary.csv",
            EXP2_RAJA_OUT, "exp2_strategy_comparison_raja_results.csv",
        ),
        (
            "Cao2018",
            EXP1_CAO_OUT, "exp1_channel_selection_cao2018_summary.csv",
            EXP3_CAO_OUT, "exp3_epoch_duration_cao2018_summary.csv",
            EXP2_CAO_OUT, "exp2_strategy_comparison_cao2018_results.csv",
        ),
    ]

    for name, exp1_dir, exp1_file, exp3_dir, exp3_file, exp2_dir, exp2_file in datasets:
        lines.append(f"[{name}]")
        try:
            e1 = pd.read_csv(exp1_dir / exp1_file)
            e1 = e1[(e1.selection == "all_channel") & (e1.center_method == "median")]
            e1 = e1.set_index("channel")["f1_macro"].sort_index()
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  ERROR reading exp1 summary: {exc}")
            e1 = None

        try:
            e3 = pd.read_csv(exp3_dir / exp3_file)
            e3 = e3[
                (e3.selection == "all_channel")
                & (e3.center_method == "median")
                & (e3.epoch_duration_s == 30.0)
            ]
            e3 = e3.set_index("channel")["f1"].sort_index()
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  ERROR reading exp3 summary: {exc}")
            e3 = None

        try:
            e2 = pd.read_csv(exp2_dir / exp2_file)
            e2_sub = e2[(e2.selection == "all_channel") & (e2.condition == "Proposed-Med")]
            e2_f1 = float(e2_sub.f1.mean()) if not e2_sub.empty else float("nan")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  ERROR reading exp2 results: {exc}")
            e2_f1 = float("nan")

        if e1 is not None and e3 is not None:
            common = sorted(set(e1.index) & set(e3.index))
            if not common:
                lines.append("  no common channels between exp1 and exp3 all_channel/median rows")
            else:
                max_diff = max(abs(e1[ch] - e3[ch]) for ch in common)
                mismatches = [ch for ch in common if abs(e1[ch] - e3[ch]) > TOLERANCE]
                lines.append(f"  exp1 vs exp3 (per-channel, {len(common)} channels): max|diff|={max_diff:.5f}")
                if mismatches:
                    any_flag = True
                    lines.append(f"  FLAG: {len(mismatches)} channel(s) exceed tolerance {TOLERANCE}:")
                    for ch in mismatches:
                        lines.append(f"    {ch}: exp1={e1[ch]:.5f}  exp3={e3[ch]:.5f}  diff={e1[ch]-e3[ch]:+.5f}")
                else:
                    lines.append(f"  OK: all channels within tolerance {TOLERANCE}")

                best_ch = max(common, key=lambda c: e1[c])
                lines.append(f"  best common channel: {best_ch}  exp1={e1[best_ch]:.4f}  exp3={e3[best_ch]:.4f}")
                gap = abs(e1[best_ch] - e2_f1)
                flag_note = " FLAG (exceeds tolerance)" if gap > TOLERANCE else ""
                lines.append(
                    f"  exp1 best-channel F1={e1[best_ch]:.4f}  vs  exp2 Proposed-Med (all_channel) "
                    f"macro F1={e2_f1:.4f}  |diff|={gap:.4f}{flag_note}"
                )
                if gap > TOLERANCE:
                    any_flag = True
        lines.append("")

    lines.append("FLAGGED: yes — review above" if any_flag else "FLAGGED: no drift detected beyond tolerance")
    send_key_update("\n".join(lines))
    if any_flag:
        send_urgent_update(
            f"Sanity check found at least one difference beyond tolerance ({TOLERANCE}) — "
            "see the detailed message above for the exp1/exp2/exp3 all_channel/30s/median comparison."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    send_key_update(
        "Sanity-check supplement (v2) starting.\n"
        "Root-cause path fix applied: exp1/2/3 primaries + their _b plot scripts now all "
        "read out-dirs from experiment_script/setup/exp_path.yaml (no more hardcoded "
        "runs0/ vs runs/ mismatch). exp3_epoch_duration.yaml now includes all_channel as "
        "a standing group for both datasets, so the sanity check reads straight from the "
        "real exp1/exp2/exp3 output — no separate sanity-only run.\n"
        "Waiting for exp1 Cao2018 (other process, nearly done) before re-running exp1 "
        "Raja, to avoid the resource contention that crashed the previous concurrent "
        "attempt."
    )

    if not wait_for_files(
        "exp1 Cao2018 (other process)",
        [EXP1_CAO_OUT / "exp1_channel_selection_cao2018_summary.csv"],
        max_wait_s=3 * 3600,
    ):
        return

    # Two prior attempts (n_jobs=10, then n_jobs=4) both died silently ~2-3 min in with no
    # traceback, while the system had ample free RAM (35GB/64GB) — not simple resource
    # exhaustion. Use n_jobs=1 (single process, no ProcessPoolExecutor) to rule out
    # multiprocessing entirely; slower (~1-2h for 46 sessions) but should be reliable.
    if not run_task(
        "exp1 Raja (rerun n_jobs=1)",
        [PYTHON, "experiment_script/exp1_a_channel_selection_raja.py",
         "--out-dir", str(EXP1_RAJA_OUT), "--n-jobs", "1"],
        EXP1_RAJA_OUT, 46,
    ):
        send_urgent_update("exp1 Raja rerun failed a 3rd time (now at n_jobs=1) — needs manual investigation.")
        return

    send_key_update(
        "exp1 Raja rerun done. Now waiting on the other process for exp2 (Raja, Cao2018) "
        "and exp3 (Raja, Cao2018, now including all_channel) — this can take several hours."
    )

    ok = wait_for_files(
        "exp2 + exp3 (other process)",
        [
            EXP2_RAJA_OUT / "exp2_strategy_comparison_raja_results.csv",
            EXP2_CAO_OUT / "exp2_strategy_comparison_cao2018_results.csv",
            EXP3_RAJA_OUT / "exp3_epoch_duration_raja_summary.csv",
            EXP3_CAO_OUT / "exp3_epoch_duration_cao2018_summary.csv",
        ],
    )
    if not ok:
        return

    sanity_check()
    send_key_update("Sanity-check supplement finished.")


if __name__ == "__main__":
    main()
