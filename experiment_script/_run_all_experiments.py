"""Orchestrator: re-run Exp1-Exp8 at std_threshold=3.0 and gate on Proposed-Med F1.

Run from REPO ROOT:
    conda run -n double_threshold_algo python experiment_script/_run_all_experiments.py

What it does
------------
1. Smoke-tests the pyblinker install.
2. For each experiment (exp1→exp5, skip exp6, exp7→exp8):
   a. Runs each dataset script with ``--out-dir runs_second_iteration/<exp>_<dataset>``
      and ``BLINK_YAML_VARIANT=std30`` set in its environment — every script's
      ``load_exp_config()`` call (src/project_paths.py) then transparently loads
      the sibling ``<yaml-stem>_std30.yaml`` instead of the baseline yaml, so no
      script source is patched (original baseline in runs/ untouched).
   b. Reads the new *_results.csv and baseline *_results.csv.
   c. Computes macro-F1 and micro-F1 for Proposed-Med rows on both datasets.
   d. Calls codex CLI (--dangerously-bypass-approvals-and-sandbox) for algorithm-performance insight.
   e. Sends the comparison table + AI insight to Telegram.
   f. Gates on pass/fail: stops immediately if either F1 regresses.
3. Sends a final summary if all experiments pass.

Gate rules
----------
- PASS:    both macro-F1 and micro-F1 for Proposed-Med >= baseline − 0.001 on BOTH datasets.
- AMBIGUOUS: macro vs micro disagree → stop + ask user.
- FAIL:    either metric regresses on either dataset → stop + ask user.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import textwrap
import threading
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from telegram_heartbeat import send_telegram_chunked, send_telegram_message, send_urgent_update, set_state

GATE_TOL = 0.001  # allow up to 0.1pp regression before declaring FAIL

# ---------------------------------------------------------------------------
# Experiment catalogue
#
# Every "script" here takes ``--out-dir`` as a real CLI flag (see
# experiment_script/exp*_a_*.py), and reads its yaml via
# src.project_paths.load_exp_config(), which honours the BLINK_YAML_VARIANT
# env var — so the std30 re-run below passes both directly, no script-source
# patching required.
# ---------------------------------------------------------------------------

EXPERIMENTS = [
    {
        "exp_name": "exp1",
        "description": "Channel selection ablation",
        "runs": [
            {
                "dataset": "raja",
                "script": "experiment_script/exp1_a_channel_selection_raja.py",
                "orig_out": "runs/exp1_channel_raja",
                "std30_out": "runs_second_iteration/exp1_channel_raja",
                "results_csv": "exp1_channel_selection_raja_results.csv",
            },
            {
                "dataset": "cao2018",
                "script": "experiment_script/exp1_a_channel_selection_cao2018.py",
                "orig_out": "runs/exp1_channel_cao",
                "std30_out": "runs_second_iteration/exp1_channel_cao",
                "results_csv": "exp1_channel_selection_cao2018_results.csv",
            },
        ],
        "proposed_med_filter": "center_method_median",
    },
    {
        "exp_name": "exp2",
        "description": "Strategy comparison (BLINKER / MNE / Proposed-Med)",
        "runs": [
            {
                "dataset": "raja",
                "script": "experiment_script/exp2_a_strategy_comparison_raja.py",
                "orig_out": "runs/exp2_raja",
                "std30_out": "runs_second_iteration/exp2_raja",
                "results_csv": "exp2_strategy_comparison_raja_results.csv",
            },
            {
                "dataset": "cao2018",
                "script": "experiment_script/exp2_a_strategy_comparison_cao2018.py",
                "orig_out": "runs/exp2_cao",
                "std30_out": "runs_second_iteration/exp2_cao",
                "results_csv": "exp2_strategy_comparison_cao2018_results.csv",
            },
        ],
        "proposed_med_filter": "condition_Proposed-Med",
    },
    {
        "exp_name": "exp3",
        "description": "Epoch-duration sensitivity",
        "runs": [
            {
                "dataset": "raja",
                "script": "experiment_script/exp3_a_epoch_duration_raja.py",
                "orig_out": "runs/exp3_raja",
                "std30_out": "runs_second_iteration/exp3_raja",
                "results_csv": "exp3_epoch_duration_raja_results.csv",
            },
            {
                "dataset": "cao2018",
                "script": "experiment_script/exp3_a_epoch_duration_cao2018.py",
                "orig_out": "runs/exp3_cao",
                "std30_out": "runs_second_iteration/exp3_cao",
                "results_csv": "exp3_epoch_duration_cao2018_results.csv",
            },
        ],
        "proposed_med_filter": "center_method_median",
    },
    {
        "exp_name": "exp4",
        "description": "Boundary-tolerance sweep",
        "runs": [
            {
                "dataset": "raja",
                "script": "experiment_script/exp4_a_boundary_tolerance_raja.py",
                "orig_out": "runs/exp4_raja",
                "std30_out": "runs_second_iteration/exp4_raja",
                "results_csv": "exp4_boundary_tolerance_raja_results.csv",
            },
            {
                "dataset": "cao2018",
                "script": "experiment_script/exp4_a_boundary_tolerance_cao2018.py",
                "orig_out": "runs/exp4_cao",
                "std30_out": "runs_second_iteration/exp4_cao",
                "results_csv": "exp4_boundary_tolerance_cao2018_results.csv",
            },
        ],
        "proposed_med_filter": "center_method_median",
    },
    {
        "exp_name": "exp5",
        "description": "Min-flagged-epochs sensitivity",
        "runs": [
            {
                "dataset": "raja",
                "script": "experiment_script/exp5_a_nmin_sensitivity_raja.py",
                "orig_out": "runs/exp5_raja",
                "std30_out": "runs_second_iteration/exp5_raja",
                "results_csv": "exp5_nmin_sensitivity_raja_results.csv",
            },
            {
                "dataset": "cao2018",
                "script": "experiment_script/exp5_a_nmin_sensitivity_cao2018.py",
                "orig_out": "runs/exp5_cao",
                "std30_out": "runs_second_iteration/exp5_cao",
                "results_csv": "exp5_nmin_sensitivity_cao2018_results.csv",
            },
        ],
        "proposed_med_filter": "center_method_median",
    },
    # exp6 (experiment_script/exp6_a_std_threshold_{raja,cao2018}.py) is the
    # ablation that generated the std=3.0 decision — skip re-run.
    {
        "exp_name": "exp7",
        "description": "Epoch-health filter effect",
        "runs": [
            {
                "dataset": "raja",
                "script": "experiment_script/run_exp7_raja.py",
                "orig_out": "runs/exp7_raja",
                "std30_out": "runs_second_iteration/exp7_raja",
                "results_csv": "exp7_epoch_health_raja_results.csv",
            },
            {
                "dataset": "cao2018",
                "script": "experiment_script/run_exp7_cao2018.py",
                "orig_out": "runs/exp7_cao",
                "std30_out": "runs_second_iteration/exp7_cao",
                "results_csv": "exp7_epoch_health_cao2018_results.csv",
            },
        ],
        "proposed_med_filter": "center_method_median",
    },
    {
        "exp_name": "exp8",
        "description": "Long-blink analysis",
        "runs": [
            {
                "dataset": "raja",
                "script": "experiment_script/exp8_a_long_blink_analysis_raja.py",
                "orig_out": "runs/exp8_raja",
                "std30_out": "runs_second_iteration/exp8_raja",
                "results_csv": "exp8_long_blink_raja_results.csv",
            },
            {
                "dataset": "cao2018",
                "script": "experiment_script/exp8_a_long_blink_analysis_cao2018.py",
                "orig_out": "runs/exp8_cao",
                "std30_out": "runs_second_iteration/exp8_cao",
                "results_csv": "exp8_long_blink_cao2018_results.csv",
            },
        ],
        "proposed_med_filter": "blink_category_all",
    },
]

# exp7's run_exp7_*.py scripts were not migrated to the exp<N>_a_*.py / --out-dir
# convention in this pass (out of scope) — they still take a hardcoded OUT_DIR
# module constant and don't honour BLINK_YAML_VARIANT, so their entry above will
# run against the baseline yaml/out-dir regardless of --out-dir/env being passed.
_UNMIGRATED_SCRIPTS = {"experiment_script/run_exp7_raja.py", "experiment_script/run_exp7_cao2018.py"}

# ---------------------------------------------------------------------------
# Output folder: honour BLINK_RUNS_DIR for a fresh "from factory" run so the
# canonical runs_second_iteration/ is never clobbered.
# ---------------------------------------------------------------------------
_RUNS_NAME = os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
if _RUNS_NAME != "runs_second_iteration":
    print("=" * 72)
    print(f"WARNING: BLINK_RUNS_DIR set -> writing std=3.0 results into '{_RUNS_NAME}/'")
    print(f"  (the canonical 'runs_second_iteration/' is left untouched; the regression")
    print(f"   gate still reads the read-only 'runs/' baseline).")
    print("=" * 72)
    for _exp_cfg in EXPERIMENTS:
        for _rc in _exp_cfg["runs"]:
            _rc["std30_out"] = _rc["std30_out"].replace("runs_second_iteration", _RUNS_NAME, 1)


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------

def _patch_out_dir(src_path: Path, orig_out: str, std30_out: str) -> Path:
    """Unmigrated scripts only: text-patch the hardcoded ``OUT_DIR = Path(...)``
    literal in a temp copy; caller must delete it. The yaml swap does NOT need
    patching — src.project_paths.load_exp_config() already honours
    BLINK_YAML_VARIANT centrally, so every script (migrated or not) picks up
    the std30 yaml automatically as long as the env var is set.
    """
    text = src_path.read_text(encoding="utf-8")
    text = text.replace(f'OUT_DIR = Path("{orig_out}")', f'OUT_DIR = Path("{std30_out}")')
    tmp_path = src_path.parent / f"_std30_tmp_{src_path.name}"
    tmp_path.write_text(text, encoding="utf-8")
    return tmp_path


def _run_script(run_cfg: dict, out_dir: Path, *, migrated: bool) -> int:
    """Run the script named in *run_cfg* against *out_dir*, return exit code.

    Migrated scripts (the exp<N>_a_*.py family) accept --out-dir as a real CLI
    flag. Unmigrated scripts (see _UNMIGRATED_SCRIPTS) hardcode an
    ``OUT_DIR = Path(...)`` module constant instead, so a temp copy with that
    one line text-patched is run in their place. Both get
    BLINK_YAML_VARIANT=std30 in their environment — src.project_paths.
    load_exp_config() honours it for every script, migrated or not.
    """
    src_path = REPO_ROOT / run_cfg["script"]
    env = {**os.environ, "BLINK_YAML_VARIANT": "std30"}
    tmp_path: Path | None = None
    try:
        if migrated:
            cmd = [sys.executable, str(src_path), "--out-dir", str(out_dir)]
        else:
            tmp_path = _patch_out_dir(src_path, run_cfg["orig_out"], run_cfg["std30_out"])
            cmd = [sys.executable, str(tmp_path)]
        print(f"\n[orchestrator] Running: {' '.join(cmd)}  (BLINK_YAML_VARIANT=std30)")
        result = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env)
        return result.returncode
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    # Coerce numeric columns — every migrated exp<N>_a_*.py writes plain
    # (unprefixed) precision/recall/f1/tp/fp/fn columns, not det_*.
    numeric = {"tp", "fp", "fn", "precision", "recall", "f1"}
    coerced = []
    for r in rows:
        row = dict(r)
        for k in numeric:
            if k in row and isinstance(row[k], str):
                try:
                    row[k] = float(row[k])
                except ValueError:
                    pass
        coerced.append(row)
    return coerced


def _filter_rows(rows: list[dict], filter_spec: str) -> list[dict]:
    """filter_spec = 'col_val' where col and val are split on the FIRST underscore pair."""
    # Spec format: "center_method_median", "condition_Proposed-Med", "blink_category_all"
    # Split: first part before last '_' that matches a column
    if filter_spec.startswith("center_method_"):
        val = filter_spec[len("center_method_"):]
        return [r for r in rows if str(r.get("center_method", "")).strip() == val]
    elif filter_spec.startswith("condition_"):
        val = filter_spec[len("condition_"):]
        return [r for r in rows if str(r.get("condition", "")).strip() == val]
    elif filter_spec.startswith("blink_category_"):
        val = filter_spec[len("blink_category_"):]
        return [r for r in rows if str(r.get("blink_category", "")).strip() == val]
    return rows


def _compute_metrics(rows: list[dict]) -> dict | None:
    def _f(r, k):
        v = r.get(k, None)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    f1_vals = [v for r in rows for v in [_f(r, "f1")] if v is not None]
    p_vals  = [v for r in rows for v in [_f(r, "precision")] if v is not None]
    rc_vals = [v for r in rows for v in [_f(r, "recall")] if v is not None]

    if not f1_vals:
        return None

    macro_f1   = sum(f1_vals) / len(f1_vals)
    macro_prec = sum(p_vals) / len(p_vals) if p_vals else float("nan")
    macro_rec  = sum(rc_vals) / len(rc_vals) if rc_vals else float("nan")

    tp = sum(_f(r, "tp") or 0.0 for r in rows)
    fp = sum(_f(r, "fp") or 0.0 for r in rows)
    fn = sum(_f(r, "fn") or 0.0 for r in rows)
    micro_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    micro_rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    denom = micro_prec + micro_rec
    micro_f1 = 2 * micro_prec * micro_rec / denom if denom > 0 else 0.0

    return {
        "macro_f1":   macro_f1,
        "macro_prec": macro_prec,
        "macro_rec":  macro_rec,
        "micro_f1":   micro_f1,
        "micro_prec": micro_prec,
        "micro_rec":  micro_rec,
        "n_rows":     len(rows),
    }


def _gate_status(new: dict | None, base: dict | None) -> tuple[str, str]:
    """Return (status, explanation). status = PASS | FAIL | AMBIGUOUS | NO_BASELINE."""
    if new is None:
        return "FAIL", "No rows matched the Proposed-Med filter in new results."
    if base is None:
        return "NO_BASELINE", "No baseline results found — reporting new results only."

    macro_ok = new["macro_f1"] >= base["macro_f1"] - GATE_TOL
    micro_ok = new["micro_f1"] >= base["micro_f1"] - GATE_TOL

    if macro_ok and micro_ok:
        return "PASS", (
            f"macro-F1: {new['macro_f1']:.4f} vs {base['macro_f1']:.4f} "
            f"(Δ{new['macro_f1'] - base['macro_f1']:+.4f}) | "
            f"micro-F1: {new['micro_f1']:.4f} vs {base['micro_f1']:.4f} "
            f"(Δ{new['micro_f1'] - base['micro_f1']:+.4f})"
        )
    elif macro_ok != micro_ok:
        return "AMBIGUOUS", (
            f"macro-F1: {new['macro_f1']:.4f} vs {base['macro_f1']:.4f} "
            f"({'ok' if macro_ok else 'REGRESSED'}) | "
            f"micro-F1: {new['micro_f1']:.4f} vs {base['micro_f1']:.4f} "
            f"({'ok' if micro_ok else 'REGRESSED'})"
        )
    else:
        return "FAIL", (
            f"macro-F1: {new['macro_f1']:.4f} vs {base['macro_f1']:.4f} "
            f"(Δ{new['macro_f1'] - base['macro_f1']:+.4f}) | "
            f"micro-F1: {new['micro_f1']:.4f} vs {base['micro_f1']:.4f} "
            f"(Δ{new['micro_f1'] - base['micro_f1']:+.4f})"
        )


# ---------------------------------------------------------------------------
# 5-minute Telegram heartbeat (tqdm-style progress while scripts run)
# ---------------------------------------------------------------------------

class _HeartbeatThread:
    """Fires a Telegram progress update every `interval` seconds.

    While a dataset script is running, reports how many session CSVs have
    been written vs expected.  When the script finishes the caller calls
    mark_completed() and the next tick is suppressed (the full report covers it).
    """

    INTERVAL = 300  # 5 minutes

    def __init__(self) -> None:
        self._stop_evt   = threading.Event()
        self._lock       = threading.Lock()
        self._exp_name   = None
        self._dataset    = None
        self._out_dir: Path | None  = None
        self._expected   = 0
        self._completed  = False
        self._phase_start: float | None = None
        self._thread     = threading.Thread(target=self._run, daemon=True, name="hb-thread")

    # ---- public API ---------------------------------------------------------

    def start(self) -> None:
        self._thread.start()

    def set_phase(self, exp_name: str, dataset: str, out_dir: Path, expected: int) -> None:
        with self._lock:
            self._exp_name    = exp_name
            self._dataset     = dataset
            self._out_dir     = out_dir
            self._expected    = expected
            self._completed   = False
            self._phase_start = time.time()

    def mark_completed(self) -> None:
        with self._lock:
            self._completed = True

    def stop(self) -> None:
        self._stop_evt.set()

    # ---- internal -----------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_evt.wait(self.INTERVAL):
            with self._lock:
                if self._completed or self._out_dir is None:
                    continue
                exp_name    = self._exp_name
                dataset     = self._dataset
                out_dir     = self._out_dir
                expected    = self._expected
                phase_start = self._phase_start

            sessions_dir = out_dir / "sessions"
            done = len(list(sessions_dir.glob("*.csv"))) if sessions_dir.exists() else 0
            pct  = (done / expected * 100) if expected else 0

            # tqdm-style bar (20 chars wide)
            filled  = int(pct / 5)
            bar     = "█" * filled + "░" * (20 - filled)

            elapsed_min = (time.time() - phase_start) / 60 if phase_start else 0
            if done > 0 and expected > 0:
                eta_min = elapsed_min / done * (expected - done)
                eta_str = f"ETA ~{eta_min:.0f} min"
            else:
                eta_str = "ETA unknown"

            msg = (
                f"[Heartbeat] {exp_name} | {dataset}\n"
                f"Sessions: {done}/{expected} ({pct:.0f}%)\n"
                f"[{bar}]\n"
                f"Elapsed: {elapsed_min:.1f} min | {eta_str}"
            )
            try:
                send_telegram_message(msg)
            except Exception:
                pass  # never let a failed Telegram call kill the heartbeat


# ---------------------------------------------------------------------------
# Claude "codex xhigh" analysis
# ---------------------------------------------------------------------------

def _codex_analysis(exp_name: str, description: str, comparison_text: str) -> str:
    """Run codex CLI for deep algorithm-performance insight."""
    prompt = textwrap.dedent(f"""
        You are an EEG blink-detection algorithm expert reviewing a parameter-sensitivity experiment.

        Experiment: {exp_name} — {description}
        Change being tested: std_threshold 3.5 → 3.0 (MAD multiplier k in the double-threshold pipeline).
        Primary detector: Proposed-Med (median centre + MAD scaling, blink_position_strategy_dbo).

        Experiment results and gate status (both Raja and Cao2018 datasets):
        {comparison_text}

        Please give a concise Telegram-friendly analysis (300 words max, plain text, no markdown):
        1. What the metric changes tell us about the precision/recall trade-off at k=3.0.
        2. Whether the cross-dataset pattern (Raja vs Cao2018) is consistent or diverges.
        3. Algorithmic interpretation: why a lower k changes blink detection behaviour.
        4. Whether you recommend proceeding or pausing, and the key risk to watch in the next experiment.
    """).strip()

    try:
        result = subprocess.run(
            ["codex", "--dangerously-bypass-approvals-and-sandbox", prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            return f"[codex] CLI error (rc={result.returncode}): {result.stderr[:300]}"
        return result.stdout.strip() or "[codex] no output returned"
    except FileNotFoundError:
        return "[codex] CLI not found — ensure codex is on PATH"
    except subprocess.TimeoutExpired:
        return "[codex] CLI timed out after 300s"
    except Exception as exc:
        return f"[codex] failed: {exc}"


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def _smoke_test() -> bool:
    cmd = [
        sys.executable, "-c",
        (
            "import importlib.metadata as m; v=m.version('pyblinker'); "
            "assert v=='0.5.0', f'expected pyblinker 0.5.0, got {v}'; "
            "import blink_evaluation, autoreject; "
            "from pyblinker.double_thresholding import blink_position_strategy_dbo; "
            "print('smoke ok', v)"
        ),
    ]
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        print("SMOKE TEST FAILED:\n", result.stdout, result.stderr)
        return False
    print("Smoke test:", result.stdout.strip())
    return True


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main() -> None:
    ts_start = time.time()
    print(f"[orchestrator] Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    heartbeat = _HeartbeatThread()
    heartbeat.start()

    # Smoke test
    send_telegram_message(
        f"[Orchestrator] Starting std_threshold=3.0 re-run suite\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Experiments: exp1→exp5, exp7, exp8 (exp6 skipped — ablation source)\n"
        f"Running smoke test..."
    )
    set_state(current_task="std30 orchestrator", last_step="startup", next_step="smoke test")

    if not _smoke_test():
        send_urgent_update("SMOKE TEST FAILED — check pyblinker install. Orchestrator aborted.")
        sys.exit(1)

    send_telegram_message("Smoke test OK (pyblinker 0.5.0). Starting exp1...")
    set_state(last_step="smoke test OK", next_step="exp1 raja")

    # -----------------------------------------------------------------------
    # Main experiment loop
    # -----------------------------------------------------------------------
    for exp_cfg in EXPERIMENTS:
        exp_name   = exp_cfg["exp_name"]
        exp_desc   = exp_cfg["description"]
        runs       = exp_cfg["runs"]
        filter_spec = exp_cfg["proposed_med_filter"]

        # Resume: skip if all results CSVs already exist
        all_done = all(
            (REPO_ROOT / rc["std30_out"] / rc["results_csv"]).exists()
            for rc in runs
        )
        if all_done:
            print(f"[orchestrator] {exp_name.upper()} — results already exist, skipping.")
            send_telegram_message(f"[{exp_name}] Skipped — results already written.")
            continue

        print(f"\n{'='*70}")
        print(f"[orchestrator] {exp_name.upper()} — {exp_desc}")
        print(f"{'='*70}")
        set_state(
            current_task=f"std30 {exp_name}",
            last_step=f"starting {exp_name}",
            next_step=f"run {exp_name} raja",
        )
        send_telegram_message(f"[{exp_name}] Starting: {exp_desc}")

        dataset_results: dict[str, dict] = {}  # dataset → {new, base, status, explanation}

        # Run each dataset sequentially
        for run_cfg in runs:
            dataset  = run_cfg["dataset"]
            migrated = run_cfg["script"] not in _UNMIGRATED_SCRIPTS
            out_dir  = REPO_ROOT / run_cfg["std30_out"]

            set_state(last_step=f"{exp_name} {dataset} starting", next_step=f"run {exp_name} {dataset}")

            # Count expected sessions from the baseline dir
            baseline_sessions = REPO_ROOT / run_cfg["orig_out"] / "sessions"
            expected_sessions = (
                len(list(baseline_sessions.glob("*.csv")))
                if baseline_sessions.exists() else 0
            )
            heartbeat.set_phase(exp_name, dataset, out_dir, expected_sessions)

            rc = _run_script(run_cfg, out_dir, migrated=migrated)
            heartbeat.mark_completed()

            if rc != 0:
                msg = (
                    f"[{exp_name} {dataset}] Script exited with code {rc}. "
                    "Stopping — please investigate."
                )
                send_urgent_update(msg)
                print(msg)
                sys.exit(1)

            set_state(last_step=f"{exp_name} {dataset} complete", next_step="compare metrics")

            # Load results
            new_csv  = REPO_ROOT / run_cfg["std30_out"] / run_cfg["results_csv"]
            base_csv = REPO_ROOT / run_cfg["orig_out"]  / run_cfg["results_csv"]

            new_rows  = _filter_rows(_load_csv(new_csv),  filter_spec)
            base_rows = _filter_rows(_load_csv(base_csv), filter_spec)

            new_m  = _compute_metrics(new_rows)
            base_m = _compute_metrics(base_rows)

            status, explanation = _gate_status(new_m, base_m)
            dataset_results[dataset] = {
                "new":         new_m,
                "base":        base_m,
                "status":      status,
                "explanation": explanation,
            }

        # -----------------------------------------------------------------------
        # Build comparison text for Telegram + Claude
        # -----------------------------------------------------------------------
        lines = [f"[{exp_name}] {exp_desc} — std_threshold 3.5→3.0"]
        lines.append(f"{'─'*55}")

        for run_cfg in runs:
            dataset = run_cfg["dataset"]
            dr      = dataset_results[dataset]
            nm      = dr["new"]
            bm      = dr["base"]

            lines.append(f"\nDataset: {dataset.upper()}")
            lines.append(
                f"{'scheme':<8} {'prec':>7} {'recall':>7} {'F1(3.0)':>8} "
                f"{'F1(3.5)':>8} {'ΔF1':>7}"
            )
            if nm and bm:
                for scheme, (np_, nr, nf), (bp, br, bf) in [
                    ("macro", (nm["macro_prec"], nm["macro_rec"], nm["macro_f1"]),
                              (bm["macro_prec"], bm["macro_rec"], bm["macro_f1"])),
                    ("micro", (nm["micro_prec"], nm["micro_rec"], nm["micro_f1"]),
                              (bm["micro_prec"], bm["micro_rec"], bm["micro_f1"])),
                ]:
                    lines.append(
                        f"{scheme:<8} {np_:>7.4f} {nr:>7.4f} {nf:>8.4f} "
                        f"{bf:>8.4f} {nf - bf:>+7.4f}"
                    )
            elif nm:
                lines.append(
                    f"macro    {nm['macro_prec']:>7.4f} {nm['macro_rec']:>7.4f} {nm['macro_f1']:>8.4f}  (no baseline)")
                lines.append(
                    f"micro    {nm['micro_prec']:>7.4f} {nm['micro_rec']:>7.4f} {nm['micro_f1']:>8.4f}")
            else:
                lines.append("  No results loaded.")

            lines.append(f"Status: {dr['status']} — {dr['explanation']}")

        comparison_text = "\n".join(lines)
        print(comparison_text)

        # -----------------------------------------------------------------------
        # Claude codex xhigh analysis
        # -----------------------------------------------------------------------
        print("\n[orchestrator] Requesting codex xhigh analysis...")
        ai_insight = _codex_analysis(exp_name, exp_desc, comparison_text)

        # -----------------------------------------------------------------------
        # Send full Telegram report
        # -----------------------------------------------------------------------
        full_msg = (
            comparison_text
            + "\n\n--- AI Insight (codex xhigh) ---\n"
            + ai_insight
        )
        send_telegram_chunked(full_msg)

        # -----------------------------------------------------------------------
        # Gate
        # -----------------------------------------------------------------------
        all_statuses = [dr["status"] for dr in dataset_results.values()]

        if any(s == "FAIL" for s in all_statuses):
            msg = (
                f"[{exp_name}] GATE FAIL — F1 regressed. "
                "Stopping suite. Awaiting user decision."
            )
            send_urgent_update(msg)
            print(f"\n{msg}")
            sys.exit(1)

        if any(s == "AMBIGUOUS" for s in all_statuses):
            msg = (
                f"[{exp_name}] GATE AMBIGUOUS — macro/micro disagree. "
                "Stopping suite. Awaiting user decision."
            )
            send_urgent_update(msg)
            print(f"\n{msg}")
            sys.exit(1)

        # NO_BASELINE is treated as pass (continue with a note)
        set_state(
            last_step=f"{exp_name} gate {'PASS' if 'PASS' in all_statuses else 'NO_BASELINE'}",
            next_step=f"next experiment after {exp_name}",
        )
        print(f"[orchestrator] {exp_name} → PASS — continuing.")

    # -----------------------------------------------------------------------
    # All experiments complete
    # -----------------------------------------------------------------------
    elapsed = (time.time() - ts_start) / 60
    final_msg = (
        f"[Orchestrator] ALL EXPERIMENTS PASS at std_threshold=3.0\n"
        f"Experiments: exp1→exp5, exp7, exp8\n"
        f"Total elapsed: {elapsed:.1f} min\n"
        f"Baseline (3.5) untouched. Recommend updating default std_threshold to 3.0."
    )
    heartbeat.stop()
    send_telegram_message(final_msg)
    set_state(last_step="all experiments complete", next_step="update default std_threshold")
    print(f"\n{final_msg}")


if __name__ == "__main__":
    main()
