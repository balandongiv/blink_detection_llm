# Figure / Table → generator script map

**Single source of truth for every artifact in the manuscript.**

Data source of truth: `publication_results/` only. Nothing in this manuscript may be
generated from `runs/`, `runs0/`, or `runs_second_iteration/`.

| Directory | Contents | Sessions |
|---|---|---|
| `publication_results/exp1_channel_{cao,raja}` | 18–20 channel groups × {median, mean} × 32 channels | 58 + 46 |
| `publication_results/exp2_{cao,raja}` | 4 conditions × sessions, `all_channel` gate, `best_channel` recorded | 58 + 46 |
| `publication_results/exp3_{cao,raja}` | 7 epoch durations (10/20/30/40/50/60/120 s) × 4 selections × {median, mean} | 58 + 46 |

Only **three** experiments are backed by data. Everything else has been removed from
both `experiment_script/` and `writing/e_result/`.

**Channel labelling.** Electrodes are reported by 10--20 scalp location on both corpora.
Raja's native EGI HydroCel indices are mapped through the `egi_pair` block of
`brain_region_raja.yaml`, which covers all 32 recorded electrodes; `32_ch.csv` is *not*
used, because it leaves E3 and E23 unmapped when they are in fact AF4 and AF3.

---

## Naming convention

Every script that emits a manuscript artifact is named for the artifact it produces:

```
tab<N>_<slug>.py      -> writes writing/e_result/tab_<slug>.tex
fig<N>_<slug>.py      -> writes writing/figures/fig_<slug>.{pdf,png}
tab<N>_fig<M>_<slug>.py -> writes both (one analysis, two renderings)
```

The `exp<N>_a_*.py` **primaries** keep their names: they run detection and emit result
CSVs, not manuscript artifacts.

---

## Experiment 1 — EEG channel-subset analysis (`publication_results/exp1_channel_*`)

| # | Artifact | LaTeX file | Generator script |
|---|---|---|---|
| Table 1 | EGI-128 → 10–20 channel map | `e_result/exp1/tab_egi_channel_map.tex` | `tab1_egi_channel_map.py` |
| Table 3 + Figure 3 | Region-level performance | `e_result/exp1/tab_region_performance.tex`, `figures/fig_region_performance.*` | `tab3_fig3_region_performance.py` |
| Table 17 | Channel subsets vs the full montage, with Wilcoxon/Bonferroni/rank-biserial | `e_result/exp1/tab_exp1_subset_summary.tex` | `tab17_exp1_subset_summary.py` |
| Table 18 | Single electrode vs the same electrode inside the full montage | `e_result/exp1/tab_exp1_solo_vs_montage.tex` | `tab18_exp1_solo_vs_montage.py` |
| Figure 1 | Region / hemisphere box plot | `figures/fig_exp1_region_boxplot.*` | `fig1_exp1_region_boxplot.py` |
| Figure 2 | Single-channel box plot | `figures/fig_exp1_single_channel_boxplot.*` | `fig2_exp1_single_channel_boxplot.py` |
| Figure 12 | $F_1$ against number of electrodes given to the pipeline | `figures/fig_exp1_coverage_curve.*` | `fig12_exp1_coverage_curve.py` |

Shared analysis layer for the three subset artifacts: `exp1_subset_data.py` (subset vs
reference stats, solo-vs-montage contrast, oracle cost, Stage-B thresholds).

**Terminology.** Experiment 1 restricts the channel set and re-runs the complete
Stage A→B→C pipeline on each subset, so it measures whether a subset is *sufficient*.
It is **not** a leave-one-region-out ablation and does not establish that any region is
*necessary* to the full system. The one exception is Table 18, which removes the other
31 electrodes from detection on a named electrode.

**Per-electrode vs single-electrode.** Table 2, Table 3 and Figure 3 report electrodes
scored *inside* the 32-channel run, where Stage A screens epochs using every electrode.
The genuine single-electrode condition is the `*_only` selection groups, reported in
Table 18 and Figure 2. Do not describe the former as "single-channel" results.

### Prose pipeline

| Artifact | Path | Generator |
|---|---|---|
| Evidence packets (one per paragraph) | `e_result/exp1/_packets/*.txt` | `exp1_prose_packets.py` |
| Paragraph drafts + transcripts | `e_result/exp1/p*/paragraph.tex`, `e_result/exp1/_transcripts/` | `exp1_draft_prose.py` |

## Experiment 2 — Strategy comparison (`publication_results/exp2_*`)

| # | Artifact | LaTeX file | Generator script |
|---|---|---|---|
| Table 4 + Table 5 | 4-condition comparison at 30 s; baseline inversions | `e_result/exp4/tab_strategycomparison_30s_epoch.tex`, `e_result/exp4/tab_exp2_inversions.tex` | `tab4_tab5_strategy_comparison_30s.py` |
| Table 19 | Stage-B threshold estimator comparison (Proposed-Med vs Proposed-Mean only), manuscript Experiment 3 | `e_result/exp3/tab_threshold_estimator_stageb.tex` | `tab19_exp3_threshold_estimator.py` |
| Figure 4 + Figure 5 | Condition P/R/F1; F1 by dataset | `figures/fig_condition_prf.pdf`, `figures/fig_f1_by_dataset.pdf` | `fig4_fig5_condition_prf.py` |
| Table 6 | Cross-dataset generalisation gap | `e_result/exp4/tab_cross_dataset_gap.tex` | `tab6_cross_dataset_gap.py` |
| Figure 6 | Per-session precision–recall scatter | `figures/fig_exp2_pr_scatter.*` | `fig6_exp2_pr_scatter.py` |
| Figure 7 | Macro operating points in PR space | `figures/fig_pr_scatter.*` | `fig7_pr_operating_points.py` |
| Table 7 + Figure 8 | Blink-count agreement | `e_result/exp4/tab_count_agreement.tex`, `figures/fig_count_agreement.*` | `tab7_fig8_count_agreement.py` |
| Table 8 | Error-structure decomposition (FP- vs FN-dominant) | `e_result/exp4/tab_error_structure.tex` | `tab8_error_structure.py` |
| Table 9 | Per-session / per-subject ranking | `e_result/exp4/tab_best_session.tex` | `tab9_best_session.py` |
| Table 10 | Per-session failure analysis | `e_result/exp4/tab_failure_analysis.tex` | `tab10_failure_analysis.py` |
| Table 11 + Figure 9 | Best-channel selection frequency | `e_result/exp1/tab_channel_selection.tex`, `figures/fig_channel_selection.pdf` | `tab11_fig9_channel_selection_frequency.py` |
| Table 12 | Best-channel stability across methods | `e_result/exp1/tab_channel_robustness.tex` | `tab12_channel_robustness.py` |

## Experiment 3 — Epoch-duration stability (`publication_results/exp3_*`)

| # | Artifact | LaTeX file | Generator script |
|---|---|---|---|
| Table 13 + Figure 10 | Macro-F1 across 7 epoch durations | `e_result/exp2/tab_effect_different_epoch_size.tex`, `figures/fig_exp3_epoch_duration.*` | `tab13_fig10_epoch_duration.py` |

## Cross-experiment summary

| # | Artifact | LaTeX file | Generator script |
|---|---|---|---|
| Table 14 + Table 15 + Figure 11 | Proposed-Med summary, paired stats, session-level box plot | `e_result/exp_summary/tab_exp_summary.tex`, `e_result/exp_summary/tab_exp_stats.tex`, `figures/fig_exp_boxplot.*` | `tab14_tab15_fig11_exp_summary.py` |

## Literature review (not experiment-backed)

| # | Artifact | LaTeX file | Generator script |
|---|---|---|---|
| Table 16 | Literature comparison | `c_literature_review/tab_literature_comparison.tex` | `tab16_literature_comparison.py` |

---

## Removed — no `publication_results/` backing

These sub-experiments were never included in the final result set. Scripts deleted,
LaTeX sections and table files removed, `\input` lines dropped from `e_result/result.tex`.

| Removed analysis | Scripts deleted | LaTeX removed |
|---|---|---|
| Exp 4 — boundary / IoU tolerance | `exp4_a_boundary_tolerance_{cao2018,raja}.py`, `setup/exp4_boundary_tolerance.yaml` | `\subsection{...Boundary Tolerance}`, `tab_boundary_tolerance.tex` |
| Exp 5 — `n_min` sensitivity | `exp5_a_nmin_sensitivity_{cao2018,raja}.py`, `setup/exp5_nmin_sensitivity.yaml` | — (never written up) |
| Exp 6 — `std_threshold` ablation | `exp6_a_std_threshold_{cao2018,raja}.py`, `setup/exp6_std_threshold.yaml` | — (method-section constant only) |
| Exp 6 — blink morphology | `exp6_morphological.py`, `setup/exp6_morphological.yaml` | — |
| Exp 7 — epoch-health exclusion | `exp7_epoch_health_effect.py`, `run_exp7_{cao2018,raja}.py`, `setup/exp7_epoch_health_effect.yaml` | — |
| Exp 8 — long-blink recall | `exp8_a_long_blink_analysis_{cao2018,raja}.py`, `paper_blink_type_recall.py`, `setup/exp8_long_blink_analysis.yaml` | `\subsection{Recall by Blink Duration}`, `tab_blink_type_recall.tex` |
| Strategy C — DBO | (already removed) | commented-out `\iffalse` block in `result.tex` |
| Experiment code summary | — | `tab_experiment_code_summary.tex` (indexed exp4–exp8) |

Superseded generators also deleted, their artifacts now produced by the named scripts above:
`regen_paper_tables.py` (a 12-table monolith), `update_exp2_latex.py`,
`paper_error_structure_session.py`, `paper_channel_selection_frequency.py`,
`paper_result_figures.py`, `regen_simple_figs.py`, `plot_region_performance.py`,
`exp3_b_plot_epoch_duration.py`.

---

## Verification

`python experiment_script/reproduce_manuscript.py check` walks the same mapping as a
machine-checkable manifest and fails if any generator, source CSV, or generated output is
missing. Run it before every submission build.
