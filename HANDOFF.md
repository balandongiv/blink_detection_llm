# HANDOFF — Exp 1 channel-selection full sweep (Raja)

**Goal:** run the complete channel-selection ablation across **all** Raja sessions via
`experiment_script/run_exp1_raja.py`, using most of the CPU, then report the summary.
Everything is wired, parallelized, and validated; this is just the long compute run.

---

## 1. Run it (one command)

```
& "C:\Users\balan\anaconda3\envs\double_threshold_algo\python.exe" experiment_script/run_exp1_raja.py
```

- **Use the `double_threshold_algo` env** (full path above). This is the canonical env
  that reproduces the paper. Do NOT use `pyblinker_worktree_epoch_blink`.
- No argparse — it is the IntelliJ "green play button" script; all settings are
  top-of-file variables.
- Long run (see §4). Prefer background + check back rather than blocking.

## 2. Verify these settings BEFORE running (top of `run_exp1_raja.py`)

| Variable | Required for full sweep | Notes |
|----------|-------------------------|-------|
| `GROUPS_TO_RUN` | **`None`** (all channel groups) | Currently `{"frontal_left","frontal_right","frontal"}` from a quick check. **Must set to `None`** for the complete ablation, else only 3 groups run. |
| `MAX_SESSIONS` | **`None`** (all 46 sessions) | Already `None`. A number = smoke-test limit. |
| `N_JOBS` | **`None`** (uses most cores) | Already `None` → `cpu_count - 1` workers (this machine: **24 cpus → 23 workers**). Set an int to cap it. |
| `OVERWRITE` | **`False`** (keep it) | Power-outage / interruption resume. Sessions with a complete per-session CSV are skipped; finished work is never overwritten. |

### Resume after a power outage (the intended recovery path)

Just **re-run the exact same command** with `OVERWRITE = False` (the default). It will:
- skip every session that already has a complete CSV in `runs/exp1_channel_raja/sessions/`,
- recompute only the sessions that had not finished,
- never overwrite or recompute completed sessions.

Per-session CSVs are written **atomically** (temp file → `fsync` → `os.replace`), so a crash
*during* a write cannot leave a half-written file that resume would mistake for "done". A
leftover `*.tmp` from a hard crash is harmless — it is ignored on resume and overwritten on
the next attempt. (Validated: run 2 sessions, re-run → both `SKIP (cached)`, no recompute.)

> **RESUME HAZARD — only when you change the experiment:** the per-session cache holds
> whatever groups were run when it was written. If you change `GROUPS_TO_RUN`
> (e.g. frontal-only → `None`), old cached sessions would be skipped and end up **missing the
> new groups**. The cache is currently empty (`runs/exp1_channel_raja/` cleared), so starting
> with `GROUPS_TO_RUN = None` is clean. If you ever change `GROUPS_TO_RUN` after a run, delete
> `runs/exp1_channel_raja/sessions/` or set `OVERWRITE = True` for one full recompute — this is
> the *only* time `OVERWRITE = True` is appropriate.

## 3. CPU parallelism (already built in)

- The sweep parallelizes **across sessions** with a `ProcessPoolExecutor` (one session per
  worker; each worker loops that session's channel groups).
- `N_JOBS = None` → `os.cpu_count() - 1` workers = majority of CPU.
- The script sets `OMP/MKL/OPENBLAS/NUMEXPR/VECLIB _NUM_THREADS = 1` at import time so the
  process pool scales cleanly without thread oversubscription. Leave that as-is.
- Verified working on Windows under `double_threshold_algo`: a 2-session / `N_JOBS=2` test
  completed correctly (`Running 2 session(s) with n_jobs=2 (of 24 cpus)`).

## 4. Config & scale (already set, do NOT change)

From `experiment_script/setup/exp1_channel_selection_raja.yaml`:
- `std_threshold: 3.5`  ← **validated best value** (precision ~0.90; old `1.5` gave ~0.40). Do not revert.
- `epoch_duration_s: 30.0`, filter `1–20 Hz`, `resample_rate: 100`.

Scale:
- **46 Raja sessions.**
- With `GROUPS_TO_RUN = None`: ~21 groups/session (`all`, frontal/central/parietal/occipital
  + L/R splits, `posterior`, `single:<ch>` per frontal electrode) × {median, mean} ≈ ~42
  rows/session. Each (session, group) re-reads the `.fif` + re-runs autoreject, so it is
  CPU-bound — hence the process pool. Resume makes interruptions safe.

Architecture note: the pipeline runs **one channel group per `run_one_session` call**; the
runner/worker loops over groups. `run_one_session` deliberately **raises** if handed >1 group.
Do not reintroduce a multi-group loop inside `channel_ablation_utils.run_one_session`.

## 5. Outputs (under `runs/exp1_channel_raja/`)

- `sessions/<session>.csv` — per-session rows (resume unit).
- `exp1_channel_selection_raja_results.csv` — all rows pooled.
- `exp1_channel_selection_raja_summary.csv` — macro-averaged per (selection, rule, centre).
- `summary.json` — run metadata.
- A `CHANNEL ABLATION SUMMARY — RAJA` table is also printed at the end.

## 6. Correctness already verified (no need to re-check)

Under `double_threshold_algo`, session `S01_20170519_043933`, `std=3.5`, median:
`frontal_left` → **det P=0.8993 / R=0.9710 / F1=0.9338, best_ch=E22**, which **exactly matches**
`experiment_script/check_exp1_vs_10d.py` (its `all` group = the same 4 frontal-left electrodes
from `brain_region.yaml`), and that script reports `PASS — identical` to tutorial/10d.

Re-confirm the engine anytime:
```
& "C:\Users\balan\anaconda3\envs\double_threshold_algo\python.exe" experiment_script/check_exp1_vs_10d.py
```
Expect `PASS — outputs are identical.`

## 7. After the sweep

- Report the printed summary table (sort by `det_f1` to see the best channel group).
- The winning Stage-A group later feeds the downstream gate
  (`channel_group_selection.yaml`) for exp2–exp8 — **do not** edit that gate as part of this
  task; just surface which group wins.

## 8. Cao2018 (optional, same pattern)

`experiment_script/run_exp1_cao2018.py` is the Cao2018 twin (`discover_cao_pairs`,
`use_epoch_health=False`). It does **not** yet have the `MAX_SESSIONS` / `N_JOBS` parallel
knobs — only run it if explicitly asked, and expect it to be serial.
