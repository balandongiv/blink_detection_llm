# `experiment_script/` — what each script does

All scripts assume the conda env `double_threshold_algo` and resolve the repo root as
`Path(__file__).resolve().parents[1]`, so they work unchanged from `experiment_script/`.

## The naming rule

**A script is named for the artifact it produces.** Read the filename and you know which
table or figure in the manuscript it is responsible for:

```
tab<N>_<slug>.py          -> writing/e_result/tab_<slug>.tex
fig<N>_<slug>.py          -> writing/figures/fig_<slug>.{pdf,png}
tab<N>_fig<M>_<slug>.py   -> both (one analysis, two renderings)
exp<N>_a_<slug>.py        -> runs detection, emits the result CSVs (no manuscript artifact)
```

The numbers are the manuscript's figure/table numbers, defined in
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
| `publication_results/exp2_{cao,raja}` | 4 conditions, `all_channel` gate, `best_channel` recorded | 58 + 46 |
| `publication_results/exp3_{cao,raja}` | 7 epoch durations (10–120 s) × 4 selections × {median, mean} | 58 + 46 |

Experiments 4–8 (boundary tolerance, `n_min`, `std_threshold`, morphology, epoch health,
long-blink recall) were **not** carried into the final result set. Their scripts, setup
yamls and manuscript sections have been removed.

---

## Primary experiments — run detection, emit CSVs

| Script | Purpose |
|--------|---------|
| `exp1_a_channel_selection_{raja,cao2018}.py` | Channel-selection ablation. Runs the complete three-stage pipeline **per channel group** × {median, mean}; writes `exp1_channel_selection_{ds}_{results,summary}.csv` plus a butterfly HTML report. |
| `exp2_a_strategy_comparison_{raja,cao2018}.py` | Per-dataset sweep on the `all_channel` gate × the four conditions defined in `src/exp/exp2_strategy_conditions.py`. Resume-safe via `src/utils/session_sweep.py`. Writes `exp2_strategy_comparison_{ds}_results.csv`. |
| `exp3_a_epoch_duration_{raja,cao2018}.py` | Epoch-duration sweep: for every duration in `setup/exp3_epoch_duration.yaml`, re-runs the full pipeline on each channel group × {median, mean}. Writes `exp3_epoch_duration_{ds}_{results,summary}.csv`. |
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
| `tab1_egi_channel_map.py` | Table 1 — Raja EGI ↔ 10–20 mapping, from the `egi_pair` block of `brain_region_raja.yaml` |
| `tab2_exp1_channel_ablation.py` | Table 2 — per-channel precision/recall/F1, both corpora |
| `tab3_fig3_region_performance.py` | Table 3 + Figure 3 — region-level means and the whole-scalp electrode map |
| `fig1_exp1_region_boxplot.py` | Figure 1 — session-level F1 by channel-selection group |
| `fig2_exp1_single_channel_boxplot.py` | Figure 2 — session-level F1 for the single-channel groups |

### Experiment 2 — strategy comparison

| Script | Produces |
|--------|----------|
| `tab4_tab5_strategy_comparison_30s.py` | Tables 4 and 5 — headline four-condition comparison, and baseline inversions |
| `fig4_fig5_condition_prf.py` | Figures 4 and 5 — pooled precision/recall/F1, and F1 by dataset |
| `tab6_cross_dataset_gap.py` | Table 6 — Raja − Cao2018 generalisation gap |
| `fig6_exp2_pr_scatter.py` | Figure 6 — per-session PR scatter, corpora shown separately |
| `fig7_pr_operating_points.py` | Figure 7 — pooled operating points with iso-F1 contours |
| `tab7_fig8_count_agreement.py` | Table 7 + Figure 8 — predicted vs true blink count, Bland–Altman |
| `tab8_error_structure.py` | Table 8 — FP:FN decomposition per condition |
| `tab9_best_session.py` | Table 9 — best/worst/median session and subject |
| `tab10_failure_analysis.py` | Table 10 — the five lowest-F1 sessions per corpus |
| `tab11_fig9_channel_selection_frequency.py` | Table 11 + Figure 9 — how often each electrode wins |
| `tab12_channel_robustness.py` | Table 12 — agreement between conditions on the best channel |

### Experiment 3 and summary

| Script | Produces |
|--------|----------|
| `tab13_fig10_epoch_duration.py` | Table 13 + Figure 10 — macro-F1 across the seven epoch durations |
| `tab14_tab15_fig11_exp_summary.py` | Tables 14/15 + Figure 11 — cross-experiment summary, paired stats, box plot |
| `tab16_literature_comparison.py` | Table 16 — literature comparison (not experiment-backed) |

### Orchestration and checks

| Script | Purpose |
|--------|---------|
| `_run_all_experiments.py`, `run_exp123_orchestrator.py`, `run_exp123_full_pipeline_orchestrator.py` | Run exp1–exp3 end to end, with Telegram progress reporting. |
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
