# Final Cleanup Summary — Manuscript Result Pipeline Audit

Date: 2026-09-14
Scope: `writing/ACCESS_latex_template_20260513/access.tex` (the compiled IEEE Access manuscript), `experiment_script/`, `publication_results/`, per the brief in `tem.md`.

## 1. Active result figures and tables found

**1 table, 8 figures** currently compiled into the manuscript PDF (`writing/ACCESS_latex_template_20260513/access.pdf`, 13 pages):

| # | Item | Manuscript experiment |
|---|---|---|
| Fig. 1 | `fig:pipeline_flow` (method diagram, no data) | n/a |
| Fig. 2 | `fig:eeg_map` (montage diagram, no data) | n/a |
| Fig. 3 | `fig:exp1_subset_per_electrode` | Experiment 1 |
| Fig. 4 | `fig:exp1_subset_per_electrode_stats` | Experiment 1 |
| Fig. 5 | `fig:exp1_single_channel` | Experiment 1 |
| Fig. 6 | `fig:exp1_single_channel_stats` | Experiment 1 |
| Fig. 7 | `fig:f1_by_epoch` | Experiment 2 |
| Table 1 | `tab:f1_significance` | Experiment 3 |
| Fig. 8 | `fig:exp2_pr_scatter` | Experiment 3 |

This is far smaller than the ~17-artifact manuscript described in the pre-existing `experiment_script/SCRIPTS_OVERVIEW.md` and `reproduce_manuscript.py` MANIFEST, both confirmed **stale** — they describe an earlier version of the manuscript before its 3 most recent commits ("clean up" / "baseline" / "clean up") trimmed it down. Agent 2 corrected the stale figure/table numbers it found in those docs; the underlying manuscript-restructuring decision itself was left alone, as instructed.

Full detail: `reports/result_inventory.csv`, `reports/result_inventory.md`.

## 2. Scripts renamed

**7** generator scripts renamed via `git mv` to `res_exp<manuscript-experiment-number>_{table,fig}_<caption-slug>.py`, using the manuscript's own Experiment 1/2/3 numbering (which does **not** match the on-disk `e_result/exp1`–`exp4` folder numbers — see `reports/result_inventory.md` for the mismatch, e.g. the manuscript's Experiment 3 lives entirely under disk folder `exp4/`).

All references updated: `experiment_script/SCRIPTS_OVERVIEW.md`, `reproduce_manuscript.py`'s MANIFEST (including 4 stale figure/table numbers corrected), 3 real Python import dependencies, 2 prose-reference files, and one generated `.tex` provenance comment. Verified post-rename: `reproduce_manuscript.py check` → "All artifacts accounted for."

Full mapping, including the 43 scripts examined and deliberately left un-renamed (shared modules, raw-data orchestrators, and generators for not-yet-compiled content): `reports/script_rename_map.csv`.

## 3. Obsolete scripts moved

**0 moved.** Agent 4 reviewed all 16 distinct generator scripts behind the manuscript's 21 not-currently-compiled tables/figures and found none met a "clear, specific evidence of permanent abandonment" bar — most sit behind explicit `%`-commented `\input`/`\subsection` blocks with inline authorial notes like *"disabled per instruction... re-enable by uncommenting if needed again"*, consistent with the manuscript being mid-restructuring rather than these sections being permanently dead. One script (`tab3_fig3_region_performance.py`) is additionally still live-imported by `exp1_prose_packets.py`, which alone would rule out moving it.

**All 16 marked `uncertain`**, per the task brief's own instruction to prefer "uncertain" over guessing. `experiment_script/obs/` was left with only its 3 pre-existing stray files (now documented in a new `experiment_script/obs/README.md`, which previously didn't exist); nothing new was added to it.

Full breakdown with per-script evidence: `reports/obsolete_scripts.csv`.

## 4-7. Independent validation

**129 values checked** against `publication_results/` CSVs, recomputed from scratch (no reuse of existing generator code), across Table 1 and Figures 3–8:

| Match status | Count |
|---|---|
| MATCH | 127 |
| ROUNDING_DIFFERENCE | 0 |
| MISMATCH | 2 |
| UNCLEAR_SOURCE | 0 |
| NOT_REPRODUCIBLE_FROM_AVAILABLE_CSV | 0 |

Both MISMATCHes are the **same qualitative prose claim**, checked once per dataset (`writing/e_result/exp4/par5.tex`): it states the proposed method is "separated from both baselines in the same direction," but the recomputed numbers show BLINKER-concat has *higher recall* than the proposed method on both Internal (95.18% vs 90.14%) and Cao2018 (97.15% vs 89.09%) — a prose overstatement, not a computational error. No printed numeric value in the manuscript is wrong.

The independent re-check also **confirmed a previously-known fix is correctly applied**: an earlier version of the epoch-duration figure (Fig. 7) computed its best-channel-per-session oracle across all 4 channel-selection gates instead of restricting to `all_channel`, inflating F1 by up to 1.25pp and flipping one duration's significance. The currently active generator (`res_exp2_fig_f1_by_epoch_duration_fp1_fp2.py`, renamed from `tab13_fig10_epoch_duration.py`) was independently verified to already restrict to `all_channel` correctly.

Full detail: `validation/validate_exp{1,2,3}_results.py`, `reports/result_validation_table.csv`, `reports/result_validation_report.md`.

## 8. Manuscript values needing human/author decision

See `reports/human_review_checklist.md` — currently just the one par5.tex prose item above. No numeric/statistical value in the compiled manuscript was found to be wrong.

## 9. Scripts/figures that could not be confidently mapped

- The 16 "uncertain" scripts from Agent 4 (item 3 above) — a content decision on whether to re-enable their manuscript sections, not a mapping failure.
- Two image assets (`figures/fig_exp_boxplot.{pdf,png}`, `figures/fig_count_agreement.{pdf,png}`) exist on disk with **no surviving `.tex` wrapper anywhere** in `writing/` — they have no caption/label and are not reachable from the manuscript at all. `VALUE_AUDIT.md` confirms their wrappers were previously deleted. These are the closest things to genuinely orphaned assets found in this audit; still left in place (not deleted) per the "never delete" constraint, flagged here for a human decision on whether to delete them or restore their wrappers.
- `writing/FIGURE_TABLE_MAP.md`, referenced by `reproduce_manuscript.py` as "the authority," does not exist on disk. Not recreated in this pass (out of scope — recreating it is a documentation task, not a validation/cleanup one), but flagged for the author.

## 10. Commands used to reproduce these checks

```
# Manuscript recompile
cd writing/ACCESS_latex_template_20260513 && latexmk -pdf -interaction=nonstopmode access.tex

# Reproducibility / provenance check
conda run -n double_threshold_algo python experiment_script/reproduce_manuscript.py check

# Independent validation
conda run -n double_threshold_algo python validation/validate_exp1_results.py
conda run -n double_threshold_algo python validation/validate_exp2_results.py
conda run -n double_threshold_algo python validation/validate_exp3_results.py

# Test suite
conda run -n double_threshold_algo python -m pytest tests/ -q
```

## Reproducibility / test status

- **Manuscript recompile:** succeeds, 13 pages (same page count as `0_original_access.pdf` pre-cleanup). Only cosmetic underfull/overfull-hbox warnings from bibliography name hyphenation — no errors.
- **`reproduce_manuscript.py check`:** "All artifacts accounted for" (re-verified after Agent 4's pass, post-rename).
- **Test suite:** `1 failed, 38 passed, 8 errors` — all pre-existing and unrelated to this cleanup:
  - 8 errors: `tests/test_kleifges_masterlist_regression.py` (40s/60s classes) fail on `FileNotFoundError` for `tests/blink_events_masterlist_kleifges_{40s,60s}.csv`, which have **zero git history** — they were never committed/generated, unrelated to any file this session touched.
  - 1 failure: `tests/exp1/test_exp1_all_median_raja_lane_summary.py` fails on an exp1 pipeline data-filtering assertion ("'all' group not found"); last touched by unrelated refactor commits (`a2148fb`, `b16e22d`, `73db2b7`) well before this session.
  - No test failure traces to a renamed file, an updated reference, or any file moved/edited by Agents 2-4.

## Files changed this session (per final `git status`)

```
 M experiment_script/SCRIPTS_OVERVIEW.md
 M experiment_script/_tmp_epoch_dump.py
 M experiment_script/exp3_prose_packets.py
 M experiment_script/exp3_redraft_prose.py
 M experiment_script/fig14_exp1_single_channel_delta.py
 M experiment_script/reproduce_manuscript.py
 M experiment_script/tab21_exp1_single_channel_region.py
 M writing/e_result/exp4/tab_f1_significance.tex
RM experiment_script/fig13_exp1_subset_per_electrode.py -> experiment_script/res_exp1_fig_regional_subset_per_electrode_f1.py
RM experiment_script/fig15_exp1_subset_per_electrode_stats.py -> experiment_script/res_exp1_fig_regional_subset_vs_montage_significance.py
RM experiment_script/fig2_exp1_single_channel_boxplot.py -> experiment_script/res_exp1_fig_single_channel_boxplot_by_region.py
RM experiment_script/fig16_exp1_single_channel_stats.py -> experiment_script/res_exp1_fig_single_channel_vs_montage_significance.py
RM experiment_script/tab13_fig10_epoch_duration.py -> experiment_script/res_exp2_fig_f1_by_epoch_duration_fp1_fp2.py
R  experiment_script/fig6_exp2_pr_scatter.py -> experiment_script/res_exp3_fig_strategy_precision_recall_scatter.py
RM experiment_script/tab4_f1_significance.py -> experiment_script/res_exp3_table_strategy_f1_significance.py
?? experiment_script/obs/README.md
?? reports/                       (result_inventory.{csv,md}, script_rename_map.csv, obsolete_scripts.csv,
                                    result_validation_table.csv, result_validation_report.md, watchdog_log.md,
                                    final_cleanup_summary.md, human_review_checklist.md)
?? validation/                    (validate_exp1_results.py, validate_exp2_results.py, validate_exp3_results.py,
                                    _exp{1,2,3}_validation_rows.json — intermediate working files from Agent 3)
```

(`tem.md`, `checklist.md`, `agent-skillbook/` predate this session's cleanup work and are untouched by it.)

No file was deleted. No CSV data or manuscript scientific interpretation was changed — only filenames, stale documentation labels, and one generated `.tex` provenance comment were corrected.

## Follow-up round (2026-09-14, later same day) — user-requested extensions

The user asked for three more things after reviewing the above. Status:

### 1. `publication_results/` folder naming vs. manuscript numbering — RESOLVED

Confirmed misaligned (`publication_results/exp2_*` held strategy-comparison data = manuscript
Experiment 3; `exp3_*` held epoch-duration data = manuscript Experiment 2 — backwards).
Presented the user a scope choice (safe/top-level-only vs. full internal-consistency
refactor into core `src/exp/` pipeline modules); user chose the safe scope.

Done: physically swapped the two `publication_results/exp{2,3}_{cao,raja}` folders (`git mv`
through a temp name); renamed the 4 primary generator scripts (`exp2_a_strategy_comparison_*.py`
→ `exp3_a_strategy_comparison_*.py`, `exp3_a_epoch_duration_*.py` → `exp2_a_epoch_duration_*.py`);
updated `experiment_script/setup/exp_path.yaml` (the single source of truth) so every existing
`paper_data.py` consumer kept working with zero code changes; fixed the 2 validation scripts'
hardcoded paths, `reproduce_manuscript.py`'s MANIFEST source-path template, and `SCRIPTS_OVERVIEW.md`.
Deliberately deferred: `paper_data.py`'s internal `exp2`/`exp3` key semantics, `load_exp2_best()`,
and the `src/exp/` core condition/sweep modules — a documented, user-approved scope boundary.
Re-verified: both validation scripts reproduce identical numbers to before the swap (41/41 and
16/18 MATCH); `reproduce_manuscript.py check` passes; manuscript recompile shows "nothing to do"
(no `.tex` file touched). Full detail: `reports/result_inventory.md`'s 2026-09-14 addendum.

### 2. Broader obsolete-script sweep, with explicit authorization to actually move things — DONE

The user explicitly authorized moving genuinely-unused scripts this time (citing
`tab1_egi_channel_map.py` as an example). A follow-up pass reviewed all 54 scripts in
`experiment_script/` (the original 16 "not compiled" candidates plus every other script) and
moved **4**, each independently re-verified by the watchdog:

| Moved | Evidence |
|---|---|
| `tab1_egi_channel_map.py` | Generates `tab:egi_map`, never `\input`/`\ref`'d anywhere in `writing/`, live or commented — the user's own example. |
| `_run_all_experiments.py` | Calls `exp4_a_boundary_tolerance_*.py`, `exp5_a_nmin_sensitivity_*.py`, `run_exp7_*.py`, `exp8_a_long_blink_analysis_*.py` — confirmed none of these files exist; `SCRIPTS_OVERVIEW.md` documents Experiments 4-8 as removed. |
| `run_exp123_full_pipeline_orchestrator.py` | `subprocess.run()` calls name `exp1_b_plot_region_boxplot.py`, `exp1_b_plot_single_channel.py`, `exp2_b_plot_pr_scatter.py`, `exp3_b_plot_epoch_duration.py` — confirmed none exist; would crash immediately if run. (A separate, similarly-named `run_exp123_orchestrator.py` — without "_full_pipeline" — was kept, marked uncertain rather than provably broken.) |
| `_tmp_epoch_dump.py` | One-off ad-hoc debug script, no output, no importer. |

All 4 moved via `git mv` (confirmed proper rename detection, not delete+add). The one live
reference to each was fixed: `reproduce_manuscript.py`'s MANIFEST `script` field for `tab:egi_map`
now points to `obs/tab1_egi_channel_map.py`, and `src/project_paths.py`'s docstring mention of
`_run_all_experiments.py` now names its `obs/` path. `SCRIPTS_OVERVIEW.md` updated accordingly.
Re-verified: `reproduce_manuscript.py check` still passes after the moves.

**18 scripts remain marked `uncertain`** (the original 16, re-confirmed independently with no new
evidence changing any of them, plus 2 newly flagged: `compute_paper_numbers.py`, still named in
`writing/VALUE_AUDIT.md` despite being superseded by the `publication_results/`-only convention;
and `exp_tg_report.py`, no current importer but still documented as current tooling) — all still
sit behind a restorable comment or an undocumented-but-not-disproven status, so were left in place
per the same conservative standard as the first pass. **32 scripts kept** as actively used (14
pipeline/generator scripts, 6 shared-library modules, plus `exp1_subset_data.py` newly confirmed
as a load-bearing dependency, and ~11 verified-current tooling/QC scripts).

Full breakdown: `reports/obsolete_scripts.csv` (54 rows). `experiment_script/obs/README.md` updated.

### 3. Root-level log and handoff-doc cleanup — RESOLVED

Moved (not deleted) into new `archive/` folder: 7 run/daemon `.log` files (`archive/logs/`) and
10 historical planning/handoff `.md` documents dated 2026-05-25 through 2026-07-22, all predating
the manuscript's later restructuring and none linked from `README.md` (`archive/handoff_docs/`).
3 scripts citing these docs in comments (`compute_paper_numbers.py`, `init_replication.py`,
`run_exp123_orchestrator.py`) had their citations updated to the new path; none read these docs
at runtime, so nothing was at risk of breaking. See `archive/README.md`.

## Nothing in this run has been committed to git.

All changes above are currently unstaged/untracked working-tree changes, exactly as the constraints required ("do not silently overwrite," "preserve reproducibility," git-aware operations). Review `reports/human_review_checklist.md` and the two mismatch/orphan items above, then decide what to commit.
