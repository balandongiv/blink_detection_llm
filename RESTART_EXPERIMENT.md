# Restarting the Experiment Pipeline from Scratch

## Single file to refer to

```
scripts/run_orchestration.py
```

This is the master pipeline runner. It orchestrates all four experiments in sequence,
determines the best epoch duration, and then calls `scripts/analyze_and_update.py` to
regenerate all LaTeX tables and update the manuscript. Everything flows from one command.

---

## Prerequisites

| Item | Value |
|---|---|
| Conda environment | `pyblinker_worktree_epoch_blink` |
| Working directory | repo root (`blink_detection_llm/`) |
| `logs/` folder | must be empty (or non-existent) |

---

## Pipeline stages (what the script runs)

| Step | Script | Output |
|---|---|---|
| 1 | `tutorial/40_exp1_epoch_duration.py` | `logs/.../exp40/summary.json` — picks best epoch |
| 2 | `tutorial/41_exp1_exp2_strategy_comparison.py` | `logs/.../exp41/exp41_strategy_comparison_results.csv` |
| 3 | `tutorial/42_exp4_boundary_tolerance.py` | `logs/.../exp42/exp42_boundary_tolerance_results.csv` |
| 4 | `tutorial/45_exp6_morphological_detailed.py` | `logs/.../exp45/exp45_morphological_event_counts.csv` |
| 5 | `scripts/analyze_and_update.py` | LaTeX tables + updated `writing/*.tex` |

Steps 2–4 all use the best epoch duration found in Step 1.

---

## How to run manually (no agent)

```powershell
conda run -n pyblinker_worktree_epoch_blink python scripts/run_orchestration.py
```

Or via the PowerShell launcher (opens a visible terminal window):

```powershell
.\scripts\launch_orchestration.ps1
```

Check completion by reading:

```
logs/experiment_orchestration_<timestamp>/summary.json
```

All five keys in `experiment_status` must be `"OK"`.

---

## Agent prompt

Use the following prompt when starting a fresh Claude Code agent session
(e.g. via `/agents` → New agent, or `claude` CLI in the repo root).
Paste it verbatim — it is self-contained.

---

```
You are running a blink-detection research pipeline in the repo at the current
working directory. The logs/ folder is empty and we want a clean, full re-run.

**Single reference file:** scripts/run_orchestration.py
Read it first to understand the pipeline before doing anything else.

**Your task — execute these steps in order:**

1. Run the master orchestration script with the correct conda environment:

       conda run -n pyblinker_worktree_epoch_blink \
           python scripts/run_orchestration.py

   Stream / show the output. Do NOT split this into individual experiment runs —
   run_orchestration.py handles sequencing internally.

2. After the script finishes, read:
       logs/experiment_orchestration_<timestamp>/summary.json
   (use the most recently created subfolder under logs/).

3. Verify that every key in `experiment_status` is "OK".
   If any key is "FAILED", read the corresponding run log
   (e.g. logs/.../exp40/exp40_run.log) and report the error.

4. Report a concise summary:
   - timestamp of the run
   - best_epoch_duration_s
   - macro_f1 for the best epoch (from exp1_best_row)
   - status of each experiment step

Do not modify any source files. Do not re-run individual experiments separately.
If the orchestration script exits with a non-zero code, report the last 40 lines
of the relevant .log file and stop.
```

---

## Checking for a partial run (power outage / interruption)

If `logs/` is **not** empty, check before re-running:

```powershell
# List existing orchestration runs newest-first
Get-ChildItem logs -Directory | Sort-Object LastWriteTime -Descending

# Check the summary of the most recent run
Get-Content logs\experiment_orchestration_<timestamp>\summary.json
```

If all five `experiment_status` values are `"OK"`, the run already completed —
**no re-run is needed**. Only delete `logs/` and restart if the run is confirmed
incomplete or corrupted.
