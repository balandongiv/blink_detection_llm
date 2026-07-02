# Experiment Manager Task — Re-run Exp1–Exp8 at `std_threshold = 3.0`

## Role
You are the **experiment manager**. Execute the full blink-detection experiment suite
(`exp1`…`exp8`, both datasets) at `std_threshold = 3.0`, **one experiment at a time, in
series**, and gate each step on not regressing against the existing baseline in `runs/`.
You make the change, run it, compare, and either continue or **stop and ask the user**.

## Background — why we are doing this
- **Exp6** is the `std_threshold` ablation (the MAD multiplier *k* in
  `threshold = center + k · scaling_factor · MAD`). Its outputs live in
  `runs/exp6_raja/` and `runs/exp6_cao/` (`exp6_std_threshold_*_summary.csv`,
  `summary.json`; sweep = `{2.5, 3.0, 3.5, 4.0}`, `center_method = median`).
- Reading those results we concluded: **performance declines at `3.5`**, and
  **`3.0` gives the best cross-dataset (Raja + Cao2018) precision/recall balance.**
- **Every other experiment currently runs at `std_threshold = 3.5`** (see the setup
  YAMLs below). The goal is to adopt `3.0` across the suite **only if it does not make
  any experiment worse**.
- **Repository note:** the detector was migrated into the standalone PyBlinker package —
  it is now `pyblinker.double_thresholding.blink_position_strategy_dbo`
  (was `src/strategy_dbo_drop`). All `experiment_script/` scripts have already been
  repointed to the new import. Do a quick smoke check before the long runs.
- **PyBlinker install:** `pyblinker` is installed into the `double_threshold_algo` env
  **from GitHub (non-editable), pinned to version `0.5.0`**:
  `pip install "pyblinker[double-thresholding] @ git+https://github.com/balandongiv/pyblinker.git"`.
  It resolves to `site-packages`, **not** the local `pyblinker/` working tree, so editing
  the local source no longer affects runs — to apply a source change you must reinstall
  (re-run the git install, or `pip install -e pyblinker`).

## Objective (definition of done)
For each experiment `exp1 → exp8`, on **both datasets (`raja` and `cao2018`)**:
1. Run it at `std_threshold = 3.0`.
2. Compare the new result against the stored `std = 3.5` baseline in `runs/`.
3. If the new result is **not worse**, continue to the next experiment.
4. If the new result **is worse**, **STOP immediately, do not start the next
   experiment, report the numbers, and ask the user how to proceed.**

## Environment & preconditions
- **Conda env:** `double_threshold_algo` (has `pyblinker==0.5.0` from GitHub,
  `blink_evaluation`, and `autoreject` installed).
  - ⚠️ `experiment_script/SCRIPTS_OVERVIEW.md` mentions an older env name
    (`pyblinker_worktree_epoch_blink`) — that is **stale**; use `double_threshold_algo`.
- **Datasets** must be present on disk (Raja + Cao2018 paths come from `paths.yaml` /
  `src.project_paths`). The experiments will report "No sessions found" if a path is wrong.
- **Run from the repo root**, never from inside the `pyblinker/` source directory. PyBlinker
  is installed in `site-packages`; if the current working directory is the local
  `pyblinker/` source tree it will shadow the install (and its stale `pyblinker.egg-info`
  reports the old `0.4.5`). The `run_exp*` scripts already put the repo root on `sys.path`,
  so just launch them from the repo root.
- **Smoke test first** (cheap; catches import/migration/version drift before a multi-hour
  run). Run it from the repo root:
  ```
  conda run -n double_threshold_algo python -c "import importlib.metadata as m; v=m.version('pyblinker'); assert v=='0.5.0', f'expected pyblinker 0.5.0, got {v}'; import blink_evaluation, autoreject; from pyblinker.double_thresholding import blink_position_strategy_dbo; print('ok', v)"
  ```
  Optionally run one experiment with a small `MAX_SESSIONS` cap to confirm it writes a CSV.

## How `std_threshold` is configured (what to edit)
`std_threshold` is read from per-experiment YAML configs in `experiment_script/setup/`.
Change `std_threshold: 3.5` → `std_threshold: 3.0` in these files:

| Setup YAML | Drives |
|---|---|
| `setup/exp1_channel_selection_raja.yaml`    | exp1 (Raja) |
| `setup/exp1_channel_selection_cao2018.yaml` | exp1 (Cao2018) |
| `setup/exp2_strategy_comparison.yaml`       | **exp2, and also exp7 & exp8** (they reuse exp2's condition runners) |
| `setup/exp3_epoch_duration.yaml`            | exp3 |
| `setup/exp4_boundary_tolerance.yaml`        | exp4 |
| `setup/exp5_nmin_sensitivity.yaml`          | exp5 |
| `setup/exp6_morphological.yaml`             | exp6 default (but exp6 **sweeps** `std_threshold`; see note below) |

- `exp7` and `exp8` have **no** `std_threshold` key of their own — they inherit it from
  `setup/exp2_strategy_comparison.yaml`. Editing exp2's YAML is sufficient for all three.
- **Exp6 is the ablation itself.** Its sweep list (`STD_THRESHOLDS = [2.5, 3.0, 3.5, 4.0]`)
  is hard-coded in `run_exp6_{raja,cao2018}.py`, and `3.0` is already one of its rows.
  Do **not** collapse exp6 to a single threshold; either (a) treat exp6 as the *source of
  the 3.0 decision* (no re-run needed) or (b) re-run the sweep unchanged. Confirm with the
  user only if ambiguous — by default, **skip re-running exp6** and reuse its existing 3.0 row.

## ⚠️ Critical: preserve the baseline and avoid stale cache
Each `run_expN_{raja,cao2018}.py` writes to `runs/expN_{raja,cao}/` and caches **per-session
CSVs** under `sessions/`, with `OVERWRITE = False` by default. This has two consequences you
**must** handle:
1. **Stale cache:** running again with `OVERWRITE = False` into the *same* directory will
   just re-load the cached `std = 3.5` rows and **not** recompute at `3.0`.
2. **Baseline loss:** running with `OVERWRITE = True` into the same directory will *destroy*
   the `3.5` baseline you need for the comparison.

**Required approach:** write the new `3.0` results to a **separate output directory** so the
`3.5` baseline stays intact for comparison. For each run script, set its `OUT_DIR` to a new
folder, e.g. `runs/exp2_raja_std30/` (and likewise per experiment/dataset). Keep
`OVERWRITE = False` so the new dir still benefits from resume-on-crash. Do **not** modify or
delete anything under the original `runs/expN_*` baseline folders.

## Run order (strictly in series)
Run both datasets for an experiment, validate, then move on. Suggested order:
`exp1 → exp2 → exp3 → exp4 → exp5 → (exp6: skip/reuse) → exp7 → exp8`.

Entry points (no argparse — they are "press-Play" scripts; run with the conda env):
```
conda run -n double_threshold_algo python experiment_script/run_exp1_raja.py
conda run -n double_threshold_algo python experiment_script/run_exp1_cao2018.py
conda run -n double_threshold_algo python experiment_script/run_exp2_raja.py
conda run -n double_threshold_algo python experiment_script/run_exp2_cao2018.py
...  # through exp8
```
These are long-running and CPU-heavy (process pools, autoreject). Run them in the background
and wait for completion before comparing.

## New analysis — micro-F1 and macro-F1 (compute both, every experiment)
The existing `*_summary.csv` files report **macro** metrics only (a simple mean of
per-session F1). For this re-run you must additionally compute and report **micro-F1**, and
make the macro vs micro distinction explicit. Both are computed for the **`Proposed-Med`**
condition, **per dataset**, on the headline `selection` / `channel_in_group` rows, for both
the new (`3.0`) run and the `3.5` baseline.

- **Macro-F1** = mean of the per-session `det_f1` values (equal weight per session).
  This is what `*_summary.csv` already holds; or recompute as `mean(det_f1)` over the
  per-session rows in `*_results.csv`.
- **Micro-F1** = pool the per-session counts first, then compute once from the totals
  (weights by event count, so blink-rich sessions count more):
  ```
  TP = Σ det_tp,  FP = Σ det_fp,  FN = Σ det_fn      # summed over sessions
  micro_precision = TP / (TP + FP)
  micro_recall    = TP / (TP + FN)
  micro_f1        = 2·micro_precision·micro_recall / (micro_precision + micro_recall)
  ```
  The `det_tp`, `det_fp`, `det_fn` columns are present per session in every
  `*_results.csv`, so no re-detection is needed — derive micro-F1 directly from them.
- Report macro and micro **side by side**; large gaps between them indicate session-size
  imbalance (a few high-blink sessions dominating), which is itself a useful finding.

## Acceptance gate — what "better / not worse" means
- **Headline condition:** `Proposed-Med` (median + MAD, the primary detector). The other
  conditions (`BLINKER-concat`, `MNE-annot`, `Proposed-Mean`) are baselines and are not the
  decision metric.
- **Metrics:** **both macro-F1 and micro-F1** for `Proposed-Med`, new (`3.0`) vs the `3.5`
  baseline, compared on the **same** `selection` / `channel_in_group` rows (e.g. the best
  channel group). Also record `det_precision` / `det_recall` (macro **and** micro) for context.
- **Per dataset:** evaluate Raja and Cao2018 separately, and keep the **cross-dataset
  balance** in mind (the whole motivation for `3.0`).
- **Pass (continue):** for `Proposed-Med`, **both** macro-F1 and micro-F1 at `3.0` are
  **≥** the `3.5` baseline (allow a tiny tolerance, e.g. ≥ baseline − 0.001) on the headline
  rows for **both** datasets. A precision↓/recall↑ shift is expected going `3.5 → 3.0`;
  judge on F1.
- **Ambiguous (stop + ask):** if macro and micro **disagree** (one improves, the other
  regresses), do not decide unilaterally — stop, show both numbers, and ask the user.
- **Fail (stop + ask):** either macro-F1 or micro-F1 regresses below the baseline on either
  dataset's headline rows. Stop, report, escalate.

## Reporting (after each experiment)
- Produce a short comparison table for `Proposed-Med`, new (`3.0`) vs baseline (`3.5`), per
  dataset and per headline selection, with **both** averaging schemes — for example:

  | dataset | selection | scheme | precision | recall | F1 (3.0) | F1 (3.5) | Δ F1 |
  |---|---|---|---|---|---|---|---|
  | raja | frontal_left/E22 | macro | … | … | … | … | … |
  | raja | frontal_left/E22 | micro | … | … | … | … | … |
  | cao2018 | … | macro | … | … | … | … | … |
  | cao2018 | … | micro | … | … | … | … | … |

- Always show macro and micro on adjacent rows so the gap is visible at a glance.
- **Use only `det_precision`, `det_recall`, `det_f1` (macro & micro forms).** Do **not**
  report or mention Stage A, `stageA_*`, `pct_flagged`, or any epoch-level/screening metrics.
- State clearly: **PASS → continuing to expN+1**, **AMBIGUOUS (macro/micro disagree) →
  stopped, awaiting user**, or **FAIL → stopped, awaiting user**.

## Guardrails (do not deviate)
- One experiment at a time, in series. Never start `expN+1` before `expN` has completed
  **and** passed the gate.
- Never overwrite or delete the existing `runs/expN_*` (`std = 3.5`) baselines.
- On any runtime error, non-zero exit, "No sessions found", or regression → **stop and ask
  the user**; do not silently retry destructive actions or change unrelated settings.
- Do not change any parameter other than `std_threshold` (and the `OUT_DIR` redirection
  required to protect the baseline).
