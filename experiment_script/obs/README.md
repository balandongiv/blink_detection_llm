# experiment_script/obs/

This folder holds material that is no longer part of the active experiment-script
workflow: three pre-existing stray files (documented below), four scripts moved in the
2026-09-14 pass with explicit user authorization, and 19 more moved in a second,
broader 2026-09-15 pass (see "Second pass" below) once the user re-authorized moving
every script behind a genuinely not-compiled manuscript artifact, not just the
provably-dead ones.

## Pre-existing stray files (not moved by this pass, documented for the first time in
the prior "Agent 4" pass)

- **`PROMPT_rerun_std_threshold_3.0.md`** -- an orchestrator prompt/runbook for an
  earlier task: re-running the exp1-exp8 suite at `std_threshold = 3.0` (the MAD
  multiplier `k` used by the double-thresholding detector) instead of the then-current
  `3.5`, one experiment at a time, gated on not regressing the `runs/` baseline. It
  references the PyBlinker package migration (`pyblinker.double_thresholding.
  blink_position_strategy_dbo`) and the `double_threshold_algo` conda env. Historical
  task instructions, superseded by the std=3.0 re-run it describes having already
  happened.

- **`extende_experiment.md`** -- design notes for an "extended experiment": a table of
  channel-selection conditions (single-channel, frontal/central/parietal/occipital
  left-right-bilateral groups, midline, all-channels) with their HydroCel/10-20 channel
  lists and purpose, plus (further down) notes on channel-combination rules. Reads as
  planning material for what became the channel-selection experiment scripts
  (`exp1_a_channel_selection_*.py`) and the channel-group config
  (`channel_group_config.py`).

- **`select_channels_post_exp1.py.bak_pre_replication`** -- a `.bak` snapshot of a
  "post-Exp1 channel selection" script, taken before a replication effort. Reads Exp1
  summary CSVs (Raja + Cao2018) and picks the top-4 individual channels and top-4
  regional groups by `det_f1` (median center, "any" rule), writing
  `runs/channel_selection/selected_channels.json` and a companion Markdown report. Kept
  as a `.bak` rather than the live version, presumably superseded by
  `channel_group_config.py` and/or the current `exp1_*` scripts.

## This pass (2026-09-14) -- 4 scripts moved, with explicit user authorization

A prior pass ("Agent 4") reviewed the 16 generator scripts behind the manuscript's 21
"on disk but not compiled" table/figure items (per `reports/result_inventory.md`) and
moved **0** of them: nearly every one sits behind an explicit "commented out on
purpose, do not delete, re-enable by uncommenting if needed again" note, i.e. a paused
content decision rather than confirmed-dead work. That reasoning was re-examined
independently in this pass (see `reports/obsolete_scripts.csv`) and, for those 16,
still holds -- no new evidence surfaced that changes any of those 16 verdicts, so all
16 remain `uncertain` and in place in `experiment_script/`, not here.

This pass additionally swept every *other* `.py` file in `experiment_script/` (~50+
scripts total) looking for genuinely abandoned tooling -- not manuscript content
paused behind a comment, but code that can no longer even run, or that produces
nothing reachable from `writing/` under any circumstance. Four were found and moved
here:

- **`tab1_egi_channel_map.py`** -- generates `tab:egi_map`, which is not merely
  commented out but **never referenced anywhere in `writing/` at all**, live or
  commented, not even by a commented-out `\input`. This is the example the user cited
  explicitly when authorizing this pass. `reproduce_manuscript.py`'s MANIFEST entry
  for `tab:egi_map` was updated to point at `obs/tab1_egi_channel_map.py` (its `script`
  field is resolved relative to `experiment_script/`, so `reproduce_manuscript.py
  check` still finds it); `SCRIPTS_OVERVIEW.md` updated to match.

- **`_run_all_experiments.py`** -- the std=3.0 re-run orchestrator for "Exp1-Exp8".
  Its exp4/exp5/exp7/exp8 phases call `exp4_a_boundary_tolerance_*.py`,
  `exp5_a_nmin_sensitivity_*.py`, `run_exp7_*.py` and `exp8_a_long_blink_analysis_*.py`
  -- none of which exist anywhere in the repo. `SCRIPTS_OVERVIEW.md` itself documents
  that "Experiments 4-8 ... were not carried into the final result set. Their scripts,
  setup yamls and manuscript sections have been removed." -- this was the leftover
  orchestrator for that already-removed feature, and its exp1-3 phases also target the
  deprecated `runs_second_iteration/` tree rather than the current `publication_results/`
  source of truth. A docstring-only mention in `src/project_paths.py` (not a functional
  import) was updated to point at the new path rather than left dangling.

- **`run_exp123_full_pipeline_orchestrator.py`** -- its `subprocess.run()` calls name
  `exp1_b_plot_region_boxplot.py`, `exp1_b_plot_single_channel.py`,
  `exp2_b_plot_pr_scatter.py` and `exp3_b_plot_epoch_duration.py`, none of which exist
  under any name in the current `experiment_script/` folder (the equivalent
  functionality now lives in the renamed `fig1_exp1_region_boxplot.py` /
  `res_exp1_fig_single_channel_boxplot_by_region.py` /
  `res_exp3_fig_strategy_precision_recall_scatter.py` /
  `res_exp2_fig_f1_by_epoch_duration_fp1_fp2.py`, but this orchestrator's call sites
  were never updated). It would crash the first time it reached the plotting step.

- **`_tmp_epoch_dump.py`** -- a one-off, ad-hoc debug script (the name says it plainly):
  imports the active epoch-duration generator purely to print per-duration F1/p-value
  numbers to stdout for manual inspection. No file output, no manuscript artifact,
  nothing else imports it.

Each of these four was verified two ways before moving: (a) a repo-wide grep for the
script's own filename, to confirm no active/live file still calls or imports it
(comment-only or documentation-only mentions were updated in place rather than treated
as blockers), and (b) for `tab1_egi_channel_map.py`, a grep of `writing/` confirming
zero reachability, live or commented. Full per-script evidence citations are in
`reports/obsolete_scripts.csv`. `reproduce_manuscript.py check` was re-run after all
four moves and prints "All artifacts accounted for."

## Everything else reviewed this pass, not moved

The remaining ~46 scripts in `experiment_script/` were also freshly reviewed this
pass (not just the original 16), split into:

- **14 active pipeline / manuscript-generator scripts** (the 6 primary `exp1_a_*` /
  `exp2_a_*` / `exp3_a_*` detectors, `exp1_step_b_get_best_region_channel.py`, and the
  7 `res_exp*.py` generators behind the manuscript's 1 compiled table and 8 compiled
  figures) plus **7 shared-library modules** (`paper_data.py`, `channel_group_config.py`,
  `butterfly_report.py`, `paper_style.py`, `runs_dir.py`, `exp1_subset_data.py` --
  newly confirmed this pass to be a load-bearing dependency of 4 of the 7 active
  figure generators -- and `reproduce_manuscript.py` itself). These are all
  `confidence=n/a` in the CSV: active, keep, do not touch.
- **A further ~11 tooling/QC/prose-drafting scripts** (`manuscript_qc.py`,
  `exp1_check_prose.py`, `exp1_draft_prose.py`, `exp1_prose_packets.py`,
  `exp3_prose_packets.py`, `exp3_redraft_prose.py`, `init_replication.py`,
  `sanity_check_all_channel_30s.py`, `sanity_check_exp1_2_3_s01_051017m.py`,
  `smoke_test_exp_path.py`, `__init__.py`) verified this pass to be current, working,
  and consistent with the `publication_results/`-only convention. Also `confidence=n/a`.
- **16 manuscript-generator scripts behind commented-out sections** -- the original 16
  from the Agent-4 pass, all re-affirmed `uncertain` this pass with no new evidence
  found (see `reports/obsolete_scripts.csv` for the full re-verification of each).
- **3 newly-flagged `uncertain` scripts**: `compute_paper_numbers.py` (superseded by
  the `publication_results/`-only pipeline in spirit, but still named explicitly in
  `writing/VALUE_AUDIT.md` as the regeneration command for a historical numbers
  snapshot), `exp_tg_report.py` (no current importer, but still documented as current
  tooling in `SCRIPTS_OVERVIEW.md`), and `run_exp123_orchestrator.py` (a one-off
  historical incident-recovery script targeting the deprecated `runs/` tree, but not
  provably broken the way the two moved orchestrators are, since its one subprocess
  call still resolves to a script that exists).

See `reports/obsolete_scripts.csv` for the full row-by-row breakdown (columns:
`old_path,new_path,reason,evidence,confidence,notes`) covering all 54 scripts
reviewed (50 currently in `experiment_script/` plus these 4 in `obs/`).

## Second pass (2026-09-15) — 19 more scripts moved, broader authorization

The user re-authorized this cleanup with a wider scope than the first pass: rather than
requiring proof a script is unreachable under any circumstance, "paused behind a comment,
re-enable if needed" was now also sufficient grounds to move a script here, since these
tables/figures are confirmed not compiled in
`writing/ACCESS_latex_template_20260513/0_original_access.pdf` per
`reports/result_inventory.md`, and moving (not deleting) keeps them fully restorable.

**15 manuscript-generator scripts moved** — the same 15 that the first pass had marked
`uncertain` (their content decision was never in doubt; only whether to physically move
them was), each behind an explicit "commented out on purpose, re-enable by uncommenting"
note in `e_result/exp1/sec.tex`, `e_result/exp3/sec.tex` (whole file, since
`e_result/exp3/sec` itself is never `\input` from `result.tex`), `e_result/exp4/sec.tex`
(five tables present on disk but never `\input` there at all, not even commented), or
`e_result/exp_summary/`/`c_literature_review/` (never wired in at all):

`tab3_fig3_region_performance.py`, `fig1_exp1_region_boxplot.py`,
`tab17_exp1_subset_summary.py`, `tab21_exp1_single_channel_region.py`,
`fig14_exp1_single_channel_delta.py`, `fig12_exp1_coverage_curve.py`,
`tab11_fig9_channel_selection_frequency.py`, `tab9_best_session.py`,
`tab7_fig8_count_agreement.py`, `tab6_cross_dataset_gap.py`, `tab8_error_structure.py`,
`tab10_failure_analysis.py`, `tab14_tab15_fig11_exp_summary.py`,
`tab16_literature_comparison.py`, `tab19_exp3_threshold_estimator.py`.

Two of these (`tab3_fig3_region_performance.py`, `tab17_exp1_subset_summary.py`) were
flagged by the first pass as having a "live functional import" from
`exp1_prose_packets.py` — re-checked this pass: the only real `import` is
`import tab3_fig3_region_performance as R` inside `exp1_prose_packets.py`, which moved to
`obs/` in the same pass (see below), so both files are still in the same directory as
each other post-move and the import still resolves. No live (non-`obs/`) script imports
either module by name (only docstring/comment mentions of the kind `"""Companion to
Table 17 (tab17_exp1_subset_summary.py): ..."""`, which are not functional dependencies).

**4 one-off ChatGPT-UI prose-drafting/redrafting scripts moved** — their job (producing
the now-finalized prose already baked into the live `.tex` paragraph files) is done, and
they have no ongoing reusable purpose (unlike `exp1_check_prose.py`/`manuscript_qc.py`,
which are general reusable QC gates kept active): `exp1_draft_prose.py` (the user's own
example of a script to delete this round — moved rather than deleted per the user's
"move to obs/" policy choice), `exp1_prose_packets.py`, `exp3_prose_packets.py`,
`exp3_redraft_prose.py`.

**Path-resolution fix applied to all 21 obs/ scripts that need it** (the 19 above plus
the two from the first pass, `tab1_egi_channel_map.py` and `_tmp_epoch_dump.py`, which
had the same latent bug, unfixed until now): every script here originally computed
`experiment_script/`'s own path as `Path(__file__).resolve().parent` (correct only when
the file lives directly in `experiment_script/`) or the repo root as
`Path(__file__).resolve().parents[1]`. Moving one directory deeper into `obs/` shifts
both by one level; fixed to `.parent.parent` and `.parents[2]` respectively so these
scripts remain technically runnable (not just historically readable) if ever restored or
run in place for reference. Verified with `python -m py_compile` on every file in this
folder (23/23 pass) after the fix.

Companion LaTeX files moved to `writing/e_result/obs/` in the same pass — see that
folder's own `README.md` for the file-by-file `\input` audit. `SCRIPTS_OVERVIEW.md` and
`reproduce_manuscript.py`'s MANIFEST were updated to point at the new `obs/` paths for
both scripts and outputs; `reproduce_manuscript.py check` passes
("All artifacts accounted for.").
