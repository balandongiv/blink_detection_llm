# `experiment_script/` — what each script does

All scripts assume the conda env `double_threshold_algo` and resolve the repo root as
`Path(__file__).resolve().parents[1]`, so they work unchanged from `experiment_script/`.

## The naming rule

**A script is named for the artifact it produces.** Read the filename and you know which
table or figure in the manuscript it is responsible for:

```
tab<N>_<slug>.py          -> writing/e_result/exp<M>/tab_<slug>.tex
fig<N>_<slug>.py          -> writing/figures/fig_<slug>.{pdf,png}
tab<N>_fig<M>_<slug>.py   -> both (one analysis, two renderings)
exp<N>_a_<slug>.py        -> runs detection, emits the result CSVs (no manuscript artifact)
```

Tables live under the `e_result/exp<M>/` folder for the manuscript experiment section
that `\input`s them (`exp1`–`exp4`), or `e_result/exp_summary/` for tables that span more
than one experiment. The numbers are the manuscript's figure/table numbers, defined in
**`writing/FIGURE_TABLE_MAP.md`** — that file is the authority. If the manuscript is
renumbered, rename the scripts to match.

## Source of truth

Every manuscript artifact is generated from **`publication_results/`** and nothing else.
`runs/`, `runs0/` and `runs_second_iteration/` are working directories whose contents do
**not** match the published manuscript; no generator may read them. Paths come from
`experiment_script/setup/exp_path.yaml` (`out_dir: publication_results`) via
`experiment_script/paper_data.py`.

Only **three** experiments have published results:

| Directory | Contents | Sessions |
|---|---|---|
| `publication_results/exp1_channel_{cao,raja}` | 18–20 channel groups × {median, mean} × 32 channels | 58 + 46 |
| `publication_results/exp2_{cao,raja}` | 7 epoch durations (10–120 s) × 4 selections × {median, mean} (manuscript "Experiment 2") | 58 + 46 |
| `publication_results/exp3_{cao,raja}` | 4 conditions, `all_channel` gate, `best_channel` recorded (manuscript "Experiment 3") | 58 + 46 |

**Note (2026-09-14):** these two folders were renamed from their original `exp2`=strategy/`exp3`=epoch-duration
disk-numbering to match the manuscript's own Experiment 2 (epoch duration) / Experiment 3 (strategy comparison)
numbering. `experiment_script/paper_data.py`'s internal `exp2`/`exp3` keys, `load_exp2_best()`, and the CSV
filenames inside each folder still use the historical numbering — this was a deliberate scope decision (see
`experiment_script/setup/exp_path.yaml`'s note and `reports/result_inventory.md`'s addendum).

Experiments 4–8 (boundary tolerance, `n_min`, `std_threshold`, morphology, epoch health,
long-blink recall) were **not** carried into the final result set. Their scripts, setup
yamls and manuscript sections have been removed.

---

## Primary experiments — run detection, emit CSVs

| Script | Purpose |
|--------|---------|
| `exp1_a_channel_selection_{raja,cao2018}.py` | Channel-selection ablation. Runs the complete three-stage pipeline **per channel group** × {median, mean}; writes `exp1_channel_selection_{ds}_{results,summary}.csv` plus a butterfly HTML report. |
| `exp3_a_strategy_comparison_{raja,cao2018}.py` (formerly `exp2_a_strategy_comparison_*`) | Per-dataset sweep on the `all_channel` gate × the four conditions defined in `src/exp/exp2_strategy_conditions.py`. Resume-safe via `src/utils/session_sweep.py`. Writes `exp2_strategy_comparison_{ds}_results.csv` into `publication_results/exp3_{ds}/` — renamed 2026-09-14 so the on-disk folder matches the manuscript's own "Experiment 3: Strategy Comparison" numbering; the internal `src/exp/exp2_*` module name and CSV filename prefix are historical and were deliberately left as-is (see `experiment_script/setup/exp_path.yaml`'s note). |
| `exp2_a_epoch_duration_{raja,cao2018}.py` (formerly `exp3_a_epoch_duration_*`) | Epoch-duration sweep: for every duration in `setup/exp3_epoch_duration.yaml`, re-runs the full pipeline on each channel group × {median, mean}. Writes `exp3_epoch_duration_{ds}_{results,summary}.csv` into `publication_results/exp2_{ds}/` — renamed 2026-09-14 to match the manuscript's "Experiment 2: Epoch Duration" numbering; same historical-internals note as above applies. |
| `exp1_step_b_get_best_region_channel.py` | Reads exp1 summaries and reports the winning channel group, for recording in `channel_group_selection.yaml`. |

## Shared data layer

| File | Purpose |
|------|---------|
| `paper_data.py` | **Every generator imports this.** Resolves `publication_results/` paths, loads the result CSVs, applies best-channel-per-session aggregation, maps channels to regions and 10–20 scalp locations, runs the paired Wilcoxon tests, and writes `.tex`/figure files with a provenance comment. Put shared logic here, not in a generator. |
| `channel_ablation_utils.py` (in `src/utils/`) | The ablation engine used by `exp1`/`exp3`: builds channel groups from a region YAML and recomputes Stage A on each group's own channels before Stage B/C. |
| `condition_runner_utils.py` (in `src/utils/`) | Imports the condition runners from `src/exp/exp2_strategy_conditions.py` so analyses reuse the exact exp2 detector configuration. |
| `channel_group_config.py` | Reads the channel-group approval gate (`channel_group_selection.yaml`) and subsets a prepared session to the approved group. |
| `butterfly_report.py` | Builds the MNE HTML butterfly report (per-group, per-subject TP/FN/FP overlays). |

## Artifact generators

Run after the primaries. Each reads `publication_results/` and writes the manuscript files.

### Experiment 1 — channel selection

| Script | Produces |
|--------|----------|
| `res_exp1_fig_single_channel_boxplot_by_region.py` (formerly `fig2_exp1_single_channel_boxplot.py`) | Figure 5 (compiled) — session-level F1 for the single-channel groups |
| `res_exp1_fig_regional_subset_per_electrode_f1.py` (formerly `fig13_exp1_subset_per_electrode.py`) | Figure 3 (compiled) — per-electrode F1 within each region's own channel-subset rerun |
| `res_exp1_fig_regional_subset_vs_montage_significance.py` (formerly `fig15_exp1_subset_per_electrode_stats.py`) | Figure 4 (compiled) — per-electrode subset-vs-montage significance |
| `res_exp1_fig_single_channel_vs_montage_significance.py` (formerly `fig16_exp1_single_channel_stats.py`) | Figure 6 (compiled) — per-electrode single-channel-vs-montage significance |

Moved to `obs/` (2026-09-15) — every one of these sits behind a `%\input`/comment in
`e_result/exp1/sec.tex`, or (for `tab1_egi_channel_map.py`) is never referenced at all. See
`writing/e_result/obs/README.md` and `reports/result_inventory.md` for the compiled-vs-not
audit that justified each move:

| Script | Would have produced |
|--------|----------|
| `obs/tab1_egi_channel_map.py` | `tab:egi_map` — never `\input`/`\ref`'d anywhere in `writing/`, live or commented; Raja EGI ↔ 10–20 mapping |
| `obs/tab3_fig3_region_performance.py` | `tab:region_performance` + `fig:region_performance` — region-level means and the whole-scalp electrode map |
| `obs/fig1_exp1_region_boxplot.py` | `fig:exp1_region_boxplot` — session-level F1 by channel-selection group |
| `obs/tab17_exp1_subset_summary.py` | `tab:exp1_subset_summary` — channel-subset vs. full-montage performance |
| `obs/tab21_exp1_single_channel_region.py` | `tab:exp1_single_channel_region` — single-electrode results aggregated to region |
| `obs/fig12_exp1_coverage_curve.py` | `fig:exp1_coverage_curve` — F1 vs. electrode count |
| `obs/fig14_exp1_single_channel_delta.py` | `fig:exp1_single_channel_delta` — single-channel minus full-montage F1 |
| `obs/tab11_fig9_channel_selection_frequency.py` | `tab:channel_selection` + `fig:channel_selection` — best-channel selection frequency |

### Experiment 2 — strategy comparison

| Script | Produces |
|--------|----------|
| `res_exp3_table_strategy_f1_significance.py` (formerly `tab4_f1_significance.py`) | Table 1 (compiled, manuscript Experiment 3: Strategy Comparison) — Proposed-approach F1 per dataset with significance vs. the best baseline |
| `res_exp3_fig_strategy_precision_recall_scatter.py` (formerly `fig6_exp2_pr_scatter.py`) | Figure 8 (compiled, manuscript Experiment 3: Strategy Comparison) — per-session PR scatter, corpora shown separately |

`tab4_tab5_strategy_comparison_30s.py`, `fig4_fig5_condition_prf.py`, `fig7_pr_operating_points.py`
and `tab12_channel_robustness.py` were already deleted in an earlier pass (the headline numbers
consolidated into `tab:f1_significance` above; see the removal notes in
`experiment_script/reproduce_manuscript.py`'s MANIFEST comments) — not merely moved, actually
gone from disk, so they are not listed here or in `obs/`.

Moved to `obs/` (2026-09-15) — none of these tables is `\input` anywhere in
`e_result/exp4/sec.tex`, live or commented:

| Script | Would have produced |
|--------|----------|
| `obs/tab6_cross_dataset_gap.py` | `tab:cross_dataset_gap` — Raja − Cao2018 generalisation gap |
| `obs/tab7_fig8_count_agreement.py` | `tab:count_agreement` — predicted vs true blink count, Bland–Altman |
| `obs/tab8_error_structure.py` | `tab:error-structure` — FP:FN decomposition per condition |
| `obs/tab9_best_session.py` | `tab:best-session` — best/worst/median session and subject |
| `obs/tab10_failure_analysis.py` | `tab:failure_analysis` — the five lowest-F1 sessions per corpus |
| `obs/tab11_fig9_channel_selection_frequency.py` | `tab:channel_selection` + `fig:channel_selection` — how often each electrode wins |

### Experiment 3 and summary

| Script | Produces |
|--------|----------|
| `res_exp2_fig_f1_by_epoch_duration_fp1_fp2.py` (formerly `tab13_fig10_epoch_duration.py`) | Figure 7 (compiled, no table, manuscript Experiment 2: Stability Across Epoch Durations) — macro-F1 across the seven epoch durations, Fp1/Fp2 reported separately |

Moved to `obs/` (2026-09-15) — neither `e_result/exp_summary/` nor `e_result/exp3/` (the
Stage-B median-vs-mean estimator ablation) nor `c_literature_review/tab_literature_comparison.tex`
is `\input` from `result.tex`/`access.tex` at all, live or commented:

| Script | Would have produced |
|--------|----------|
| `obs/tab14_tab15_fig11_exp_summary.py` | `tab:exp_summary` + `tab:exp_stats` + `fig:exp_boxplot` — cross-experiment summary, paired stats, box plot |
| `obs/tab16_literature_comparison.py` | `tab:literature_comparison` — literature comparison (not experiment-backed) |
| `obs/tab19_exp3_threshold_estimator.py` | `tab:exp3_estimator` — Proposed-Med vs Proposed-Mean threshold-estimator comparison |

### Orchestration and checks

| Script | Purpose |
|--------|---------|
| `run_exp123_orchestrator.py` | Run exp1–exp3 end to end, with Telegram progress reporting. |
| `obs/_run_all_experiments.py`, `obs/run_exp123_full_pipeline_orchestrator.py` | Moved to `obs/` (2026-09-14) — both call `experiment_script/exp4_a_*`/`exp5_a_*`/`run_exp7_*`/`exp8_a_*`/`exp1_b_plot_*`/`exp2_b_plot_*`/`exp3_b_plot_*` scripts that no longer exist (Experiments 4-8 were removed per the note below, and the plotting scripts were later folded into the renamed `res_exp*.py`/`fig*.py`/`tab*.py` generators); would fail immediately if run. |
| `compute_paper_numbers.py` | Recomputes the headline numbers for auditing prose against the CSVs. |
| `sanity_check_all_channel_30s.py`, `sanity_check_exp1_2_3_s01_051017m.py`, `smoke_test_exp_path.py` | Fast checks that the wiring and a known session still reproduce. |
| `reproduce_manuscript.py` | Walks the artifact registry and verifies every manuscript file has a live generator. |
| `init_replication.py`, `runs_dir.py` | Replication scaffolding (`BLINK_RUNS_DIR`) for re-running the pipeline into a fresh directory. |
| `exp_tg_report.py` | Telegram reporting helper. |

---

## Aggregation convention

Every four-condition comparison uses **best-channel-per-session**: for each session take the
row with the highest event-level F1, then average across sessions. The same rule is applied
to all four conditions, so no condition gets a selection advantage the others do not.
See `writing/VALUE_AUDIT.md`.

## Channel-group approval gate

`channel_group_selection.yaml` (repo root) records the chosen Stage-A group per dataset.
Selecting any non-`all` group **requires `approved_by` and `approved_date`**, otherwise the
experiments raise at runtime. `exp1` deliberately does not consult the gate — it is the
experiment that chooses the group. `exp2`/`exp3` emit a warning when the effective group is
still `all`.
