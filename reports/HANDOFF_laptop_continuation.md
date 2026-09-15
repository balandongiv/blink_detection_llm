# Handoff: continuing on another machine

Continuing the manuscript result-pipeline audit on branch `cleanup/manuscript-result-audit`
(pushed from another machine, not yet merged to `main`). Read `reports/final_cleanup_summary.md`
and `experiment_script/obs/README.md` / `writing/e_result/obs/README.md` first for full context
on what's already done. Three things are explicitly left open:

## 1. `reports/obsolete_scripts.csv` is stale — fix this first, it's quick

Of the 18 rows still marked `confidence=uncertain`, 15 were actually moved to
`experiment_script/obs/` in the round-2 pass (the CSV rows were never updated to match):
`tab3_fig3_region_performance.py`, `tab17_exp1_subset_summary.py`, `fig1_exp1_region_boxplot.py`,
`tab21_exp1_single_channel_region.py`, `fig14_exp1_single_channel_delta.py`,
`fig12_exp1_coverage_curve.py`, `tab11_fig9_channel_selection_frequency.py`,
`tab9_best_session.py`, `tab7_fig8_count_agreement.py`, `tab6_cross_dataset_gap.py`,
`tab8_error_structure.py`, `tab10_failure_analysis.py`, `tab14_tab15_fig11_exp_summary.py`,
`tab16_literature_comparison.py`, `tab19_exp3_threshold_estimator.py`. Update their `new_path`
and `confidence` columns (-> `moved`) to match reality. The 4 prose-tooling rows
(`exp1_draft_prose.py`, `exp1_prose_packets.py`, `exp3_prose_packets.py`,
`exp3_redraft_prose.py`, currently listed `confidence=n/a, active`) also moved and need the
same update.

Only 3 rows are genuinely still untouched and uncertain: `compute_paper_numbers.py`,
`exp_tg_report.py`, `run_exp123_orchestrator.py`. These need an actual human/content decision,
not more evidence-gathering — the evidence in the CSV for each was already re-verified twice
(rounds 1 and 2) with no new signal either time.

## 2. Wilcoxon/Bonferroni refactor (an open question, not a decided plan)

The same paired-Wilcoxon-plus-Bonferroni-correction logic is independently reimplemented in 4
live, currently-compiled generator scripts, instead of calling one shared helper:
- `experiment_script/res_exp1_fig_regional_subset_vs_montage_significance.py`
- `experiment_script/res_exp1_fig_single_channel_vs_montage_significance.py`
- `experiment_script/res_exp2_fig_f1_by_epoch_duration_fp1_fp2.py`
- `experiment_script/res_exp3_table_strategy_f1_significance.py`
(`experiment_script/compute_paper_numbers.py` has a fifth copy, but it's a QC/audit tool, not a
manuscript generator.)

`experiment_script/paper_data.py` is already the shared layer everything else imports (CSV
loading, region colours, best-channel-per-session aggregation) — this would extend it with one
more shared function. The catch: each of the 4 call sites has a *different* Bonferroni family
size (2 baselines x 2 datasets; 24 or 18 electrodes per dataset; 6 durations; etc.), so the
helper needs a `family_size`/`alpha` parameter, not a hardcoded one. Given the hard constraint
that `writing/ACCESS_latex_template_20260513/0_original_access.pdf` must not change: if you do
this, regenerate all 4 outputs afterward (`reproduce_manuscript.py build --only <script>` or run
each directly) and diff every changed `.tex`/figure against the currently-committed version,
plus a full `latexmk -pdf` recompile, before trusting it produced identical numbers.

## 3. Your planned value re-confirmation

Nothing else needs to happen for this from my side. One pointer:
`reports/result_validation_table.csv` and `validation/validate_exp{1,2,3}_results.py` are the
independent (non-generator-code) recomputation from round 1, already cross-checked once against
the manuscript's published numbers. If you re-derive anything, that's the existing baseline to
diff against rather than starting from zero.
