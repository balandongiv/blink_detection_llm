# `experiment_script/` — what each script does

Two kinds of files live here:

* **Primary experiments** `exp1_…` – `exp8_…` — run detection and produce the raw result
  CSVs. Numbered to follow the reordered result-section outline
  (see `tutorial/channel_region_refactor_plan.md` §5). **exp1 = channel selection**,
  **exp2 = strategy comparison**, then exp3–exp8.
* **Supporting / post-processing** `paper_…` — *consume* an experiment's CSV output and
  emit the paper's tables and figures (they do not run detection themselves, except
  `paper_blink_type_recall.py`). The `paper_` prefix keeps them visually distinct from the
  `exp*` primaries.

All scripts assume the conda env `pyblinker_worktree_epoch_blink` and resolve the repo root as
`Path(__file__).resolve().parents[1]`, so they work unchanged from `experiment_script/`.

> **Sampling rate:** the pipeline now downsamples to **100 Hz** (`RESAMPLE_RATE = 100`
> in each `exp*` primary; `resample_rate=100` in `condition_runner_utils.py` and
> `channel_ablation_utils.py`), matching the documented methodology. This is
> **results-affecting** — any cached results predating this change must be re-run.

---

## Primary experiments

| Script | Purpose | Paper section(s) |
|--------|---------|------------------|
| `exp1_channel_selection_raja.py` | Channel-selection ablation (Raja). Runs the **complete 3-stage pipeline per channel group** (`all/frontal/central/parietal/occipital/posterior/…`) × {median, mean}; reports Stage-A epoch metrics + downstream event F1; writes a **butterfly HTML report** (per-subject + all-subject TP/FN/FP). Writes `exp1_channel_selection_raja_{results,summary}.csv` + butterfly HTML. | **II. Mechanism** — *Channel-selection & aggregation* |
| `exp1_channel_selection_cao2018.py` | Same ablation for Cao2018 (10-20 montage; `epoch_health` filtering). Writes `exp1_channel_selection_cao2018_{results,summary}.csv`. | **II. Mechanism** |
| `exp2_strategy_comparison.py` | Main comparison of BLINKER-concat, MNE-annot, **Proposed-Mean**, **Proposed-Med** (+ DBO, hidden) on Raja+Cao2018, 30 s. Also the median-vs-mean estimator contrast and the cross-dataset gap. Writes `runs/exp2_strategy_30s/exp41_strategy_comparison_{results,summary}.csv` (output basename kept as legacy `exp41_*`). | **I. Contribution** — *Strategy comparison*, *Estimator (median vs mean)*, *Cross-dataset generalisation* |
| `exp3_epoch_duration.py` | Proposed-Med across epoch durations (e.g. 20/30/40/60/120 s) on Raja+Cao2018; Wilcoxon vs reference. Writes `runs/exp3_epoch/exp1_epoch_duration_{results,summary}.csv` + `summary.json` (`best_epoch_duration_s`). | **III. Robustness** — *Stability across epoch durations* |
| `exp4_boundary_tolerance.py` | Proposed-Med across IoU matching thresholds {0,0.1,0.2,0.3,0.5}; F1 range = sensitivity. Writes `runs/exp4_tolerance/exp42_boundary_tolerance_{results,summary}.csv`. | **III. Robustness** — *Boundary-tolerance stability* |
| `exp5_nmin_sensitivity.py` | Sensitivity to the Stage-B fallback count `n_min`: threshold-variance vs sub-sample size, and fallback frequency vs epoch duration. Console tables (no paper table yet). | **III. Robustness** — *Stage-B fallback / `n_min`* |
| `exp6_morphological.py` | Detailed blink-region morphology: TP/FN/FP butterfly plots stratified by duration and amplitude, per-subject + all-subject, into one MNE HTML report. Writes `runs/exp6_morphology/`. | **IV. Characterization** — *Blink-region morphology* |
| `exp7_epoch_health_effect.py` | Effect of **excluding low-health epochs** (`health_on` vs `health_off`) for **all five** conditions on Raja+Cao2018; reports per-condition ΔF1. Quantifies how much a preprocessing choice (not the detector) inflates/deflates the numbers, and whether it helps the proposed method more than the baselines. **Reuses exp2** (strategy comparison) for the `health_on` side via `--reuse-exp1-csv`. | **III. Robustness** — *Epoch-health exclusion sensitivity* |
| `exp8_long_blink_analysis.py` | Recall for **normal (<0.5 s) vs long (≥0.5 s)** blinks, all five conditions on Raja+Cao2018; reports the per-detector recall gap. Long closures (microsleep/drowsiness) are the safety-critical events that shape-based detectors tend to miss. Extends the single-pipeline `tutorial/14` and the duration table in `paper_blink_type_recall.py` to all five conditions + per-session detail. | **IV. Characterization** — *Long-blink (drowsiness) recall* |

### Shared engine / figure utilities (used by `exp1_channel_selection_*`)

| File | Purpose | Related experiment |
|------|---------|--------------------|
| `channel_ablation_utils.py` | The ablation engine: builds channel-selection groups from a region YAML and, **for each group, recomputes Stage A (autoreject) on that group's own channels** before Stage B/C — the straightforward `tutorial/10d` approach (no learn-once-then-reuse across groups). Computes Stage-A + downstream metrics and extracts TP/FN/FP windows. Resamples to 100 Hz. | **exp1** |
| `butterfly_report.py` | Builds the MNE HTML butterfly report (per-group, per-subject + all-subject TP/FN/FP overlays). | **exp1** |
| `condition_runner_utils.py` | Imports the five `exp2_strategy_comparison` condition runners + session-prep / GT helpers, so the analyses reuse the *exact* exp2 detector configuration instead of re-declaring it. Resamples to 100 Hz; applies the channel-group gate. | **exp7, exp8** |
| `channel_group_config.py` | Reads the channel-group gate (`channel_group_selection.yaml`) and subsets a prepared session to the approved Stage-A group. No-op when the group is `all`. | **exp2–exp8** |
| `__init__.py` | Marks `experiment_script` as a package so the `exp*` scripts can import the utils above. | — |

> `tutorial/tutorial_utils.py` is **not** here on purpose — it is shared by ~20 non-experiment
> tutorials. The experiments import it as `tutorial.tutorial_utils`.

---

## Channel-group selection gate (`exp1` → `exp2`..`exp8`)

Experiment 1 (channel selection) decides which Stage-A channel group works best; that decision is
carried into the downstream experiments through a **hard-approval gate** so the chosen montage is
applied deliberately, never by accident:

* **`channel_group_selection.yaml`** (repo root) — records the chosen Stage-A group per dataset
  (`raja`, `cao2018`). Default is `all` (the full per-dataset region montage), so `exp2`..`exp8`
  behave exactly as before. Selecting any non-`all` group **requires `approved_by` (and
  `approved_date`) to be filled**, otherwise the experiments raise at runtime — forcing an
  explicit, reviewable human/agent sign-off.
* **`channel_group_config.py`** — `apply_stage_a_channel_group(prepared, dataset)` is called right
  after a session is prepared in `exp2`–`exp6` and inside `condition_runner_utils.prepare_session`
  (covering `exp7`/`exp8`); it subsets the montage to the approved group (no-op when `all`).
  `exp1_channel_selection_*` deliberately does **not** call it — exp1 must see the full montage to
  compare every group. The `paper_*` post-processors do not consume the gate yet.
* **All-channels warning:** because `exp2`–`exp8` go through `apply_stage_a_channel_group`, they emit
  a `logging.WARNING` (once per dataset) whenever the effective group is `all` — i.e. you are running
  Stage A on every channel because no winner has been recorded yet. exp1 does not warn (it is the
  experiment that *chooses* the group).

**Design doc — `experiment_script/extende_experiment.md`** (moved here from `tutorial/`) is the
original specification for the *"Compare channel-selection strategies"* ablation: spatial channel
groups × aggregation rules, Stage-A epoch-level ground truth, and downstream effects. A future
human/agent choosing the winning group should read it together with the `exp1_channel_selection_*`
outputs (weighing det-F1, Stage-A epoch F1, #channels, FP-epoch rate, recall, cross-dataset
consistency, best-channel stability, median-vs-mean), then record the choice **and its rationale**
in `channel_group_selection.yaml`.

---

## Supporting / post-processing scripts

These read an experiment's result CSV and write the paper artifacts. "Depends on" = which
experiment must run first.

| Script | Purpose | Depends on | Paper section / artifact |
|--------|---------|-----------|--------------------------|
| `paper_channel_selection_frequency.py` | Frequency of best-channel selection by dataset/method/subject + method overlap. Writes `tab_channel_selection.tex`, `fig_channel_selection.pdf`. | **exp2** (reads `exp41_strategy_comparison_results.csv`) | *EEG Channel Selection* (Part IV) — complements exp1 |
| `paper_error_structure_session.py` | Decomposes errors into FP/FN regimes and ranks best/worst sessions & subjects. Writes `tab_error_structure.tex`, `tab_best_session.tex`. | **exp2** | *Error-Structure Decomposition* + *Per-Session/Subject Variability* (Part IV) |
| `paper_epoch_duration_figure.py` | Regenerates the epoch-duration F1 bar figure. Writes `fig_f1_by_epoch.pdf`. | **exp3** (reads its summary CSV) | *Stability across epoch durations* figure (Part III) |
| `paper_blink_type_recall.py` | Event-level recall for Normal (<0.5 s) vs Long (≥0.5 s) blinks; **runs detection** by importing the four strategy runners from `exp2_strategy_comparison.py`. Writes `tab_blink_type_recall.tex`. | **exp2** (imports its runners) | *Recall by Blink Duration* (Part IV) |
| `paper_result_figures.py` | Regenerates the main result figures. Writes `fig_condition_prf.pdf`, `fig_f1_by_dataset.pdf`. | **exp2** (reads its summary CSV) | *Strategy comparison* + *Cross-dataset* figures (Part I/IV) |

---

## Reuse of prior results (don't recompute from scratch)

The suite is layered so that later analyses **consume earlier outputs** instead of re-running
detection:

* `paper_channel_selection_frequency`, `paper_error_structure_session`,
  `paper_blink_type_recall`(partial), `paper_result_figures` read **exp2**'s results CSV.
* `paper_epoch_duration_figure` reads **exp3**'s summary CSV.
* **exp7**'s `health_on` side *is* exp2 by construction → pass `--reuse-exp1-csv …` and only the
  `health_off` side is computed (≈ half the work; the slow DBO/Proposed runs on kept epochs are
  not repeated).
* **exp8**'s detection on the standard valid-epoch set is the same pipeline exp2/`paper_blink_type_recall` run;
  it adds the normal/long split and DBO. (Detections aren't persisted by exp2, so exp8 still runs detection
  once per session×condition; if this becomes a bottleneck, add a detection cache to exp2.)

Rule of thumb: if a number already exists in an upstream CSV under identical settings, read it —
don't recompute it.

## ⚠️ Wiring notes (input paths to reconcile before re-running)

The supporting scripts still point at the **previous** run-directory names. After the rename, the
primary experiments write to new `--out-dir`s (see plan §7). Either keep the old run-dir names when
running the primaries, or update these input paths:

| Script | Reads (current) | New primary output |
|--------|-----------------|--------------------|
| `paper_channel_selection_frequency`, `paper_error_structure_session`, `paper_result_figures` | `runs/exp41_cao_30s/exp41_strategy_comparison_*.csv` | `runs/exp2_strategy_30s/…` (basename stays `exp41_*`) |
| `paper_epoch_duration_figure` | `runs/exp40_cao/exp1_epoch_duration_summary.csv` | `runs/exp3_epoch/…` |

Also: `paper_channel_selection_frequency` reads the legacy `brain_region.yaml` (now bare HydroCel ints). To stay consistent with
the per-dataset refactor it should be switched to `brain_region_raja.yaml` / `brain_region_cao2018.yaml`.
These are **flagged, not changed** (this turn only moved + documented the files).

Stale `% Source: … tutorial/4x_… / tutorial/5x_…` provenance comments in `writing/e_result/*.tex`
likewise need updating to `experiment_script/paper_…` — left for the paper-edit step.
