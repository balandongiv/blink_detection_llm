# Manuscript Result Inventory

Source of truth: `writing/ACCESS_latex_template_20260513/access.tex`, walked through its live (non-commented) `\input` chain, cross-checked page-by-page against the compiled `writing/ACCESS_latex_template_20260513/0_original_access.pdf` (13 pages, generated 2026-09-14, MiKTeX pdfTeX). `writing/FIGURE_TABLE_MAP.md` does **not exist on disk** -- confirmed missing; this inventory was built by independently reading the LaTeX sources and the PDF, not from that (absent) file.

`experiment_script/reproduce_manuscript.py`'s internal `MANIFEST` and `experiment_script/SCRIPTS_OVERVIEW.md` were read afterward purely as a cross-check. Both are substantially **stale**: they describe an earlier, larger version of the manuscript (roughly 17 data-driven artifacts, numbered Figure 1-11 / Table 1-16 across an 'Experiment 1/2/3/4' scheme that matches the *disk folder names* `exp1`-`exp4`, not the current manuscript). The manuscript that actually compiles today has only 1 table and 8 figures, numbered Table 1 and Figures 1-8, organised into three sections literally titled 'Experiment 1' (channel selection), 'Experiment 2' (epoch duration) and 'Experiment 3' (strategy comparison) -- a *different* numbering from the disk folders. See the per-row notes below for specific mismatches; the single most important one for later renaming work is:

> **Disk folder != manuscript experiment number.** `e_result/exp1/` = manuscript Experiment 1 (channel selection, matches). `e_result/exp2/` = manuscript Experiment 2 (epoch duration) prose, but that experiment's one live figure is an asset literally named `fig_exp3_epoch_duration.pdf` and is spliced into `e_result/exp1/sec.tex`. `e_result/exp3/` on disk is a wholly different, **not-compiled** experiment (the Stage-B median-vs-mean threshold-estimator ablation). `e_result/exp4/` = manuscript Experiment 3 (strategy comparison).
>
> **This note describes the LaTeX `e_result/exp1`-`exp4` folders only** (still mismatched, left as-is — a much larger change than the one below).

## ADDENDUM (2026-09-14) — publication_results/ and primary-script renaming resolved

A separate, narrower mismatch — the `publication_results/exp2_*` / `exp3_*` **data** folders and the
`experiment_script/exp2_a_strategy_comparison_*.py` / `exp3_a_epoch_duration_*.py` **primary generator
scripts** — has been resolved:

- `publication_results/exp2_{cao,raja}` now holds the epoch-duration data (manuscript Experiment 2);
  `publication_results/exp3_{cao,raja}` now holds the strategy-comparison data (manuscript Experiment 3).
  Physically swapped via `git mv` through a temp name; re-validated with `validation/validate_exp2_results.py`
  and `validate_exp3_results.py` afterward — identical numeric results to before the swap (41/41 and 16/18
  MATCH respectively), confirming no data was altered, only relocated.
- `experiment_script/exp2_a_strategy_comparison_{cao2018,raja}.py` → `exp3_a_strategy_comparison_{cao2018,raja}.py`,
  and `experiment_script/exp3_a_epoch_duration_{cao2018,raja}.py` → `exp2_a_epoch_duration_{cao2018,raja}.py`
  (pure `git mv`, plus fixing each script's own self-referencing docstring example).
- `experiment_script/setup/exp_path.yaml` (the pipeline's single source of truth for output paths) was
  updated so its `out_dirs.exp2`/`out_dirs.exp3` values point at the newly-renamed folders — this is what let
  every existing `paper_data.py` consumer (`load("exp2"/"exp3", ds)`, `load_exp2_best()`, and the `res_exp*.py`
  scripts) keep working with **zero code changes**, since those call sites' `"exp2"`/`"exp3"` argument is an
  internal key, not a folder name.
- `experiment_script/reproduce_manuscript.py`'s MANIFEST source-path template and `experiment_script/SCRIPTS_OVERVIEW.md`
  were updated to match; `reproduce_manuscript.py check` passes; the manuscript recompiles unchanged (no `.tex`
  file was touched).

**Deliberately deferred (scope decision, not an oversight):** `paper_data.py`'s internal `_FILES`/`_SUMMARY`
dict keys, the `load_exp2_best()` function name, its 8 callers, and the `src/exp/exp2_strategy_conditions.py` /
`src/exp/exp3_epoch_duration_sweep.py` core pipeline modules all still use "exp2" to mean strategy comparison
and "exp3" to mean epoch duration internally — the opposite of the now-renamed folders/scripts. This was a
deliberate choice (offered to and confirmed by the user) to avoid a much larger, higher-risk refactor of the
core detection-pipeline condition/sweep logic for a purely cosmetic internal-consistency gain. The CSV
filenames inside the renamed folders (`exp2_strategy_comparison_*.csv` now lives inside `exp3_*/`;
`exp3_epoch_duration_*.csv` now lives inside `exp2_*/`) are the one remaining human-visible trace of this —
documented in `experiment_script/setup/exp_path.yaml`'s inline note and in both `validation/validate_exp2_results.py`
and `validate_exp3_results.py`'s docstrings.

## Summary counts

| Experiment | Active tables | Active figures |
|---|---|---|
| Experiment 1 | 0 | 4 |
| Experiment 2 | 0 | 1 |
| Experiment 3 | 1 | 1 |
| n/a | 0 | 2 |
| **Total** | **1** | **8** |

On-disk-but-not-compiled items: **21** (14 tables, 7 figures, of which 2 figures -- fig:exp_boxplot and fig:count_agreement -- are orphaned image files with no surviving `.tex` wrapper at all, so they carry no label/caption).

## Active items (compiled into the current PDF)

### Experiment 1

### Figure 3 -- `fig:exp1_subset_per_electrode`

- **Caption:** Per-electrode detection F1 within each region's own channel-subset rerun, coloured by scalp region. Each bar is one electrode scored inside that region's own self-contained subset run.
- **Short slug:** `regional_subset_per_electrode_f1`
- **LaTeX source:** `e_result/exp1/p05_regional/paragraph_per_electrode.tex (image: figures/fig_exp1_subset_per_electrode.pdf)`
- **Output file:** `figures/fig_exp1_subset_per_electrode.{pdf,png}`
- **Result section:** Experiment 1: EEG Channel-Subset Analysis > Regional Channel Subsets > Per-Electrode Detection
- **Notes:** Manifest (reproduce_manuscript.py) has no entry for this label at all -- it is a real compiled figure (PDF page 7) that the manifest does not track.

### Figure 4 -- `fig:exp1_subset_per_electrode_stats`

- **Caption:** Per-electrode comparison of Proposed-approach F1 when each electrode was evaluated inside its own self-contained anatomical subset rerun (narrow, opaque bar) against the same electrode evaluated inside the full-montage run (wide, translucent bar), for (A) Internal and (B) Cao2018. Bars show session-mean F1; electrodes are grouped by the anatomical subset in Figure 3 and ordered by descending subset F1 within each region. Comparisons are paired by session using two-tailed Wilcoxon signed-rank tests, with p Bonferroni-corrected separately within each dataset over every electrode tested there. An asterisk above an electrode marks adjusted p<0.05; electrodes without an asterisk did not reach this threshold. Exact adjusted p-values are not printed on the bars and are instead reported in the text for electrodes discussed individually.
- **Short slug:** `regional_subset_vs_montage_significance`
- **LaTeX source:** `e_result/exp1/p05_regional/paragraph_electrode_level_stats.tex (image: figures/fig_exp1_subset_per_electrode_stats.pdf)`
- **Output file:** `figures/fig_exp1_subset_per_electrode_stats.{pdf,png}`
- **Result section:** Experiment 1: EEG Channel-Subset Analysis > Regional Channel Subsets > Electrode-Level Significance Testing
- **Notes:** Not present in reproduce_manuscript.py MANIFEST.

### Figure 5 -- `fig:exp1_single_channel`

- **Caption:** Detection F1 of every electrode in the four curated anatomical regions operating as its own self-contained detector, in which the complete Stage A--Stage C pipeline was rerun on that one electrode alone, coloured by scalp region.
- **Short slug:** `single_channel_boxplot_by_region`
- **LaTeX source:** `e_result/exp1/sec.tex (image: figures/fig_exp1_single_channel_boxplot.pdf)`
- **Output file:** `figures/fig_exp1_single_channel_boxplot.{pdf,png}`
- **Result section:** Experiment 1: EEG Channel-Subset Analysis > Single-Channel Operation
- **Notes:** MANIFEST entry fig:exp1_single_channel exists and script/output path agree (fig2_exp1_single_channel_boxplot.py) EXCEPT the manifest's one-line description calls it 'Single-electrode detection F1 for every full-montage electrode' and SCRIPTS_OVERVIEW.md labels this script's output as 'Figure 2' -- both stale; it is Figure 5 in the current compiled PDF.

### Figure 6 -- `fig:exp1_single_channel_stats`

- **Caption:** Per-electrode comparison of Proposed-approach F1 when each electrode in the four curated anatomical regions operated as a complete self-contained detector (narrow, opaque bar) against the same electrode scored inside the full 32-channel montage (wide, translucent bar), for (A) Internal and (B) Cao2018. Comparisons are paired by session using two-tailed Wilcoxon signed-rank tests, with p Bonferroni-corrected separately within each dataset. An asterisk above an electrode marks adjusted p<0.05, electrodes without an asterisk did not reach this threshold.
- **Short slug:** `single_channel_vs_montage_significance`
- **LaTeX source:** `e_result/exp1/sec.tex (image: figures/fig_exp1_single_channel_stats.pdf)`
- **Output file:** `figures/fig_exp1_single_channel_stats.{pdf,png}`
- **Result section:** Experiment 1: EEG Channel-Subset Analysis > Single-Channel Operation > Electrode-Level Significance Testing
- **Notes:** Placed in a \begin{figure*} side-by-side pair together with Figure 7 (fig:f1_by_epoch), physically inside e_result/exp1/sec.tex even though Figure 7's content belongs to Experiment 2. Not present in reproduce_manuscript.py MANIFEST.

### Experiment 2

### Figure 7 -- `fig:f1_by_epoch`

- **Caption:** Macro-averaged F1 of Proposed-approach across epoch durations, on the full 32-channel montage, for Fp1 and Fp2 (Experiment 1's two consistently best-performing electrodes) reported separately: Internal (top row) and Cao2018 (bottom row). Durations of 10, 20, 30 (reference), 40, 50, 60 and 120 seconds were tested, and an asterisk marks the durations that differ significantly from the 30 s reference after Bonferroni correction.
- **Short slug:** `f1_by_epoch_duration_fp1_fp2`
- **LaTeX source:** `e_result/exp1/sec.tex (image: figures/fig_exp3_epoch_duration.pdf); prose in e_result/exp2/par2.tex`
- **Output file:** `figures/fig_exp3_epoch_duration.{pdf,png}`
- **Result section:** Experiment 2: Stability Across Epoch Durations
- **Notes:** IMPORTANT anomaly: this figure's caption/label is defined physically inside e_result/exp1/sec.tex (bundled into the same figure* block as Figure 6, per an explicit 'NOTE (moved on purpose...)' comment left in e_result/exp2/sec.tex), and its image filename says 'exp3' (fig_exp3_epoch_duration) even though the CONTENT and the manuscript's live prose (e_result/exp2/par2.tex, par3.tex) are Experiment 2 (epoch duration). This is the clearest instance of the disk-folder-number vs. manuscript-experiment-number mismatch: on disk, folder 'exp3' = epoch duration, but the compiled manuscript's 'Experiment 3' is Strategy Comparison (disk folder 'exp4'), and the compiled manuscript's 'Experiment 2' (epoch duration) instead pulls from disk folder 'exp2' for prose and disk folder 'exp3' for the figure asset name only. Agent 2 should treat 'exp3' in filenames/scripts as meaning epoch-duration content, not the manuscript's numbered Experiment 3. Not present in reproduce_manuscript.py MANIFEST (which instead lists a non-existent tab:epoch_duration -> e_result/exp2/tab_effect_different_epoch_size.tex, confirmed missing from disk).

### Experiment 3

### Table 1 -- `tab:f1_significance`

- **Caption:** Macro-F1 (%) for Proposed-approach and both baselines on Internal and Cao2018. An asterisk marks a baseline as significantly different from Proposed-approach (two-sided Wilcoxon signed-rank test on session-level F1, p<0.05, Bonferroni-corrected across the four tests shown).
- **Short slug:** `strategy_f1_significance`
- **LaTeX source:** `e_result/exp4/tab_f1_significance.tex`
- **Output file:** `e_result/exp4/tab_f1_significance.tex (LaTeX table, script comment: experiment_script/tab4_f1_significance.py)`
- **Result section:** Experiment 3: Strategy Comparison
- **Notes:** Lives on disk under the exp4/ folder even though it is the manuscript's 'Experiment 3'. Matches reproduce_manuscript.py MANIFEST entry tab:f1_significance (script tab4_f1_significance.py) exactly.

### Figure 8 -- `fig:exp2_pr_scatter`

- **Caption:** Per-session precision-recall operating points for Internal and Cao2018, shown separately. Each small point is one session's precision-recall pair for one condition. Marker shape encodes the condition (BLINKER, MNE, Proposed-approach) and marker color encodes the dataset. The large navy-outlined marker for each condition marks its mean over sessions within that dataset. Both axes run from 0 to 100 percent.
- **Short slug:** `strategy_precision_recall_scatter`
- **LaTeX source:** `e_result/exp4/sec.tex (image: figures/fig_exp2_pr_scatter.pdf)`
- **Output file:** `figures/fig_exp2_pr_scatter.{pdf,png}`
- **Result section:** Experiment 3: Strategy Comparison
- **Notes:** Filename says 'exp2' (fig_exp2_pr_scatter) but is used in the manuscript's Experiment 3 (Strategy Comparison) section, and lives physically in the exp4/ disk folder's sec.tex. Matches reproduce_manuscript.py MANIFEST entry fig:exp2_pr_scatter (script fig6_exp2_pr_scatter.py) by label, but SCRIPTS_OVERVIEW.md calls this 'Figure 6' -- stale, it is Figure 8 in the current compiled PDF.

### n/a

### Figure 1 -- `fig:pipeline_flow`

- **Caption:** Overview of the proposed epoch-aware double-thresholding pipeline for EEG blink-region detection. Continuous multichannel EEG signals are downsampled to 100 Hz, band-pass filtered from 1 to 20 Hz, and divided into non-overlapping 30-s epochs. Stage A applies multichannel peak-to-peak screening and a union rule to select candidate epochs, represented by E2, E5, and E7 in this example. Stage B pools the samples from the selected epochs to estimate a robust sample-level threshold independently for each channel. Stage C applies the resulting channel-specific thresholds to all valid epochs and reports each detected blink region by its epoch identifier, channel, onset time, and duration. Pale yellow denotes Stage A candidate epochs, red denotes detected blink regions, and the dashed green lines represent the channel-specific thresholds.
- **Short slug:** `pipeline_overview_flowchart`
- **LaTeX source:** `d_method/flowchart_pipeline_proposed.tex (image: images/flowchart.png)`
- **Output file:** `images/flowchart.png (PNG, referenced via graphicspath ../images/)`
- **Result section:** Method and Materials > Processing Pipeline Overview
- **Notes:** Hand-drawn/diagram figure, not data-driven (matches reproduce_manuscript.py LEGACY entry 'fig:pipeline', though that entry mis-describes it as 'tikz in d_method/' and uses a different logical id -- the real label is fig:pipeline_flow and the asset is a PNG, not inline TikZ). No table/figure counter conflicts.

### Figure 2 -- `fig:eeg_map`

- **Caption:** Scalp locations of the 32 electrodes used in this study, divided into eight anatomical regions (frontal left/right, central left/right, parietal left/right, and occipital left/right, abbreviated FL, FR, CL, CR, PL, PR, OL, and OR). Blue circles mark electrodes present in both the Internal and Cao2018 montages, yellow circles mark electrodes present only in the Internal montage, and red circles mark electrodes present only in the Cao2018 montage.
- **Short slug:** `electrode_montage_map`
- **LaTeX source:** `d_method/material/dataset.tex (image: images/eeg_map.png)`
- **Output file:** `images/eeg_map.png (PNG, referenced via graphicspath ../images/)`
- **Result section:** Method and Materials > Experimental Setup > Datasets
- **Notes:** Not present anywhere in the reproduce_manuscript.py MANIFEST or LEGACY list (a genuine gap in that manifest, since this figure IS compiled).

## On disk but not compiled

Reachable on disk (readable `.tex` files with real content, or in two cases orphaned image assets) but NOT part of the live `\input` chain from `access.tex` -- sitting behind a commented-out `\input`, a commented-out `\paragraph`/`\subsection`, an entire commented-out section, or (for `tab:egi_map` and the two orphaned figures) never referenced at all.

### Experiment 1

### Table n/a (not compiled) -- `tab:egi_map`

- **Caption:** Internal-dataset EGI 128-channel (HydroCel GSN) to 10-20 scalp-location mapping, taken from the egi_pair block of brain_region_raja.yaml. Results are reported throughout by 10-20 location; this table gives the native EGI index for each one.
- **Short slug:** `egi_to_1020_channel_map`
- **LaTeX source:** `e_result/exp1/tab_egi_channel_map.tex`
- **Output file:** `e_result/exp1/tab_egi_channel_map.tex (script comment: experiment_script/tab1_egi_channel_map.py)`
- **Result section:** Would belong under Experiment 1 > EEG Channel-Subset Analysis (Datasets)
- **Notes:** Orphaned: label tab:egi_map is defined but never \input nor \ref'd anywhere in the live or commented chain -- not even a commented-out \input exists for it. MANIFEST lists it as 'Table 1' (tab1_egi_channel_map.py); that is stale, it is not compiled at all in the current manuscript, and Table 1 in the current PDF is tab:f1_significance instead.

### Table n/a (not compiled) -- `tab:region_performance`

- **Caption:** Experiment 1 per-electrode detection performance collapsed to coarse scalp regions (Proposed-approach, median centre), each electrode scored inside the full-montage run rather than as a standalone single-electrode pipeline. Each region row averages the per-channel macro F1 over the electrodes it contains; regions follow the brain_region_raja.yaml/brain_region_cao2018.yaml assignment, so the frontopolar pair is included within frontal.
- **Short slug:** `region_collapsed_performance_table`
- **LaTeX source:** `e_result/exp1/tab_region_performance.tex`
- **Output file:** `e_result/exp1/tab_region_performance.tex (script comment: experiment_script/tab3_fig3_region_performance.py)`
- **Result section:** Would belong under Experiment 1 > Full-Montage Reference > Region-Collapsed Results
- **Notes:** Commented out of e_result/exp1/sec.tex together with its paragraph and figure (%\paragraph{Region-Collapsed Results} block, 'deemed redundant' per the inline note). Dangling cross-references to tab:region_performance/fig:region_performance remain live in the captions of tab_exp1_subset_summary.tex and tab_exp1_single_channel_region.tex, but those two tables are themselves also not compiled (see below), so no broken \ref reaches the compiled PDF. MANIFEST calls this 'Table 3 + Figure 3'; stale.

### Figure n/a (not compiled) -- `fig:region_performance`

- **Caption:** Per-electrode detection F1 under the full montage, shown as two stacked bar charts, Internal on top and Cao2018 on the bottom, with one bar per electrode of the 32-channel array, coloured by scalp region and labelled with its F1 value.
- **Short slug:** `region_collapsed_performance_figure`
- **LaTeX source:** `e_result/exp1/p04_per_electrode/paragraph_region_collapsed.tex (image: figures/fig_region_performance.pdf)`
- **Output file:** `figures/fig_region_performance.{pdf,png}`
- **Result section:** Would belong under Experiment 1 > Full-Montage Reference > Region-Collapsed Results
- **Notes:** Commented out together with tab:region_performance (see that row). Image asset still present on disk.

### Table n/a (not compiled) -- `tab:exp1_subset_summary`

- **Caption:** Experiment 1 channel-subset performance of Proposed-approach (median centre). Each subset is a self-contained detector: Stage A, Stage B and Stage C were all re-run on that channel subset alone. ... The All (full montage) row instead reports the best-channel-per-session oracle F1 used as the headline full-montage figure throughout the manuscript, shown for reference only.
- **Short slug:** `channel_subset_vs_montage_summary`
- **LaTeX source:** `e_result/exp1/tab_exp1_subset_summary.tex`
- **Output file:** `e_result/exp1/tab_exp1_subset_summary.tex (script comment: experiment_script/tab17_exp1_subset_summary.py)`
- **Result section:** Would belong under Experiment 1 > Regional Channel Subsets
- **Notes:** Explicitly commented out of e_result/exp1/sec.tex per an inline instruction ('Table 1 ... is disabled per instruction'). Not present at all in reproduce_manuscript.py MANIFEST (script tab17_exp1_subset_summary.py is referenced only in this file's own header comment, not in the manifest) -- a manifest gap for a script that does exist on disk under e_result/exp1's naming scheme.

### Figure n/a (not compiled) -- `fig:exp1_region_boxplot`

- **Caption:** Session-level macro F1 by channel-selection group (median centre), Internal versus Cao2018.
- **Short slug:** `region_subset_boxplot`
- **LaTeX source:** `e_result/exp1/sec.tex (commented block; image: figures/fig_exp1_region_boxplot.pdf)`
- **Output file:** `figures/fig_exp1_region_boxplot.{pdf,png}`
- **Result section:** Would belong under Experiment 1 > Regional Channel Subsets
- **Notes:** Commented out immediately after the (also commented) tab:exp1_subset_summary \input. MANIFEST lists this as 'Figure 1' (fig1_exp1_region_boxplot.py) and SCRIPTS_OVERVIEW.md agrees ('Figure 1'); both stale -- it is not compiled at all currently, and Figure 1 in the current PDF is fig:pipeline_flow.

### Table n/a (not compiled) -- `tab:exp1_single_channel_region`

- **Caption:** Single-electrode results of Proposed-approach (median centre) aggregated to the five scalp regions used throughout this section (Table 'exp1_subset_summary'; 'Posterior' is parietal union occipital). F1 (Single) averages each region's electrodes' own independent single-electrode detector; F1 (Subset) is the same region's self-contained multi-electrode subset rerun; F1 (Full) is the same electrodes scored inside the full-montage run.
- **Short slug:** `single_channel_region_aggregated`
- **LaTeX source:** `e_result/exp1/tab_exp1_single_channel_region.tex`
- **Output file:** `e_result/exp1/tab_exp1_single_channel_region.tex (script comment: experiment_script/tab21_exp1_single_channel_region.py)`
- **Result section:** Would belong under Experiment 1 > Single-Channel Operation > Region-Collapsed Results
- **Notes:** Commented out of e_result/exp1/sec.tex along with its paragraph (p07_single_channel/paragraph_region_collapsed.tex, which is live text on disk but not \input anywhere). Script tab21_exp1_single_channel_region.py is not present at all in reproduce_manuscript.py MANIFEST -- a manifest gap.

### Figure n/a (not compiled) -- `fig:exp1_single_channel_delta`

- **Caption:** Configuration effect for every electrode in the four curated anatomical regions (the same electrode set as Figure exp1_single_channel): single-electrode F1 minus the same electrode's full-montage F1, coloured by scalp region.
- **Short slug:** `single_channel_delta_vs_montage`
- **LaTeX source:** `e_result/exp1/sec.tex (commented block; image: figures/fig_exp1_single_channel_delta.pdf)`
- **Output file:** `figures/fig_exp1_single_channel_delta.{pdf,png}`
- **Result section:** Would belong under Experiment 1 > Single-Channel Operation > Channel-Context Comparison
- **Notes:** Commented out together with its paragraph (p07_single_channel/paragraph_channel_context.tex, live text on disk but not \input anywhere). Not present in reproduce_manuscript.py MANIFEST.

### Figure n/a (not compiled) -- `fig:exp1_coverage_curve`

- **Caption:** Detection F1 against the number of electrodes given to the pipeline. Each point is one channel subset; the dashed line marks the full-montage reference.
- **Short slug:** `f1_vs_electrode_count_curve`
- **LaTeX source:** `e_result/exp1/sec.tex (commented block; image: figures/fig_exp1_coverage_curve.pdf)`
- **Output file:** `figures/fig_exp1_coverage_curve.{pdf,png}`
- **Result section:** Would belong under Experiment 1 > Single-Channel Operation
- **Notes:** Commented out, standalone (no live paragraph references it). Not present in reproduce_manuscript.py MANIFEST.

### Table n/a (not compiled) -- `tab:channel_selection`

- **Caption:** Best-channel selection frequencies pooled over the four conditions (best-channel-per-session). The 5 most frequently selected electrodes are listed per dataset, with the count and the fraction of all session x condition selections.
- **Short slug:** `best_channel_selection_frequency_table`
- **LaTeX source:** `e_result/exp1/tab_channel_selection.tex`
- **Output file:** `e_result/exp1/tab_channel_selection.tex (script comment: experiment_script/tab11_fig9_channel_selection_frequency.py)`
- **Result section:** Would belong under Experiment 1 > 'Stability of the Channel Choice' subsubsection
- **Notes:** Entire subsubsection commented out of e_result/exp1/sec.tex, including p10_selection_frequency/paragraph, p11_oracle_cost/paragraph and p12_agreement/paragraph. NOTE: the \input for p10_selection_frequency/paragraph points to a file that does not exist on disk (writing/e_result/exp1/p10_selection_frequency/ has no paragraph.tex; only p11_oracle_cost/paragraph.tex and p12_agreement/paragraph.tex exist, both with real content). p12_agreement/paragraph.tex also references a table label 'tab:channel-robustness' that does not exist anywhere on disk (its generator tab12_channel_robustness.py was deliberately deleted per a MANIFEST comment: 'its only prose discussion ... is itself commented out of the compiled document, so the table had no active discussion'). This whole subsection is also the source data for discussion paragraph f_discussion/d5_channel_instability/paragraph.tex, which is commented out of f_discussion/discussion.tex with an explicit cross-referencing note. MANIFEST calls this table part of 'Experiment 4: strategy comparison'; disk-folder-vs-manuscript-numbering mismatch (see Figure 7 notes).

### Figure n/a (not compiled) -- `fig:channel_selection`

- **Caption:** Best-channel selection frequency, pooled over the four conditions.
- **Short slug:** `best_channel_selection_frequency_figure`
- **LaTeX source:** `e_result/result.tex (commented block at end of file; image: figures/fig_channel_selection.pdf)`
- **Output file:** `figures/fig_channel_selection.{pdf,png}`
- **Result section:** Would belong under a commented-out 'Operating Points' subsection at the end of Results
- **Notes:** Commented out at the very end of e_result/result.tex under a '%\subsection{Operating Points}' block, separate from (but same script/data as) tab:channel_selection above.

### Experiment 3

### Table n/a (not compiled) -- `tab:best-session`

- **Caption:** Best and worst Proposed-approach sessions and subject-level summary across 104 Internal+Cao2018 sessions (best-channel-per-session). F1 values are percentages.
- **Short slug:** `best_worst_median_session`
- **LaTeX source:** `e_result/exp4/tab_best_session.tex`
- **Output file:** `e_result/exp4/tab_best_session.tex (script comment: experiment_script/tab9_best_session.py)`
- **Result section:** Would belong under Experiment 3: Strategy Comparison
- **Notes:** Present on disk in the exp4/ folder alongside the live tab_f1_significance.tex, but not \input anywhere in e_result/exp4/sec.tex (not even as a commented-out line) -- it is simply absent from the section file. MANIFEST calls it part of 'Experiment 4' (disk-folder naming).

### Table n/a (not compiled) -- `tab:count_agreement`

- **Caption:** Agreement between the predicted blink count (TP+FP) and the true count (TP+FN) per session, pooled over Internal and Cao2018 (n=104) at the best-channel-per-session row. The mean count ratio measures systematic over- or under-counting (1.00 is ideal); Pearson r and Lin's concordance correlation coefficient (CCC) measure how closely the predicted count tracks the true count across sessions.
- **Short slug:** `blink_count_agreement_table`
- **LaTeX source:** `e_result/exp4/tab_count_agreement.tex`
- **Output file:** `e_result/exp4/tab_count_agreement.tex (script comment: experiment_script/tab7_fig8_count_agreement.py)`
- **Result section:** Would belong under Experiment 3: Strategy Comparison
- **Notes:** Not \input anywhere in e_result/exp4/sec.tex. Its companion figure asset figures/fig_count_agreement.{pdf,png} also exists on disk but likewise has no surviving .tex wrapper (see fig:count_agreement row below).

### Figure n/a (not compiled) -- `fig:count_agreement`

- **Caption:** (no caption source found -- no .tex wrapper file exists anywhere in the repo for this asset; VALUE_AUDIT.md references a deleted e_result/fig_count_agreement.tex wrapper)
- **Short slug:** `blink_count_agreement_figure`
- **LaTeX source:** `none (orphaned image asset only)`
- **Output file:** `figures/fig_count_agreement.{pdf,png}`
- **Result section:** n/a
- **Notes:** Same situation as fig:exp_boxplot: image files exist, no .tex include exists. Companion of tab:count_agreement (same generator script tab7_fig8_count_agreement.py per MANIFEST).

### Table n/a (not compiled) -- `tab:cross_dataset_gap`

- **Caption:** Cross-dataset generalisation gap (best-channel-per-session macro-F1, 30 s epochs), reported as percentages. Gap = Internal - Cao2018, in percentage points.
- **Short slug:** `cross_dataset_generalisation_gap`
- **LaTeX source:** `e_result/exp4/tab_cross_dataset_gap.tex`
- **Output file:** `e_result/exp4/tab_cross_dataset_gap.tex (script comment: experiment_script/tab6_cross_dataset_gap.py)`
- **Result section:** Would belong under Experiment 3: Strategy Comparison
- **Notes:** Not \input anywhere in e_result/exp4/sec.tex.

### Table n/a (not compiled) -- `tab:error-structure`

- **Caption:** Error-structure decomposition by condition (best-channel-per-session). Mean false positives (FP) and false negatives (FN) per session, pooled over 104 sessions. The regime column records which error type dominates.
- **Short slug:** `fp_fn_error_structure`
- **LaTeX source:** `e_result/exp4/tab_error_structure.tex`
- **Output file:** `e_result/exp4/tab_error_structure.tex (script comment: experiment_script/tab8_error_structure.py)`
- **Result section:** Would belong under Experiment 3: Strategy Comparison
- **Notes:** Not \input anywhere in e_result/exp4/sec.tex.

### Table n/a (not compiled) -- `tab:failure_analysis`

- **Caption:** The 5 lowest-F1 Proposed-approach sessions per corpus (best channel per session). GT is the ground-truth blink count (TP+FN) and GT/med is GT relative to the dataset median, which separates genuine detector failure from recordings that simply carry an atypical number of blinks.
- **Short slug:** `lowest_f1_sessions_failure_analysis`
- **LaTeX source:** `e_result/exp4/tab_failure_analysis.tex`
- **Output file:** `e_result/exp4/tab_failure_analysis.tex (script comment: experiment_script/tab10_failure_analysis.py)`
- **Result section:** Would belong under Experiment 3: Strategy Comparison
- **Notes:** Not \input anywhere in e_result/exp4/sec.tex.

### cross-experiment

### Table n/a (not compiled) -- `tab:exp_stats`

- **Caption:** Paired Wilcoxon signed-rank tests of Proposed-approach versus the best competing method (BLINKER-concat from the strategy comparison) on session-level F1, for each experiment and dataset.
- **Short slug:** `cross_experiment_wilcoxon_stats`
- **LaTeX source:** `e_result/exp_summary/tab_exp_stats.tex`
- **Output file:** `e_result/exp_summary/tab_exp_stats.tex (script comment: experiment_script/tab14_tab15_fig11_exp_summary.py)`
- **Result section:** Would belong under a cross-experiment summary subsection (none currently exists in result.tex)
- **Notes:** Not \input anywhere in e_result/result.tex, live or commented -- there is no summary subsection stub at all currently. Internally still uses disk-folder labels exp1/exp2/exp3 (matching the Stage-B-estimator/epoch-duration disk-folder scheme), not the compiled manuscript's Experiment 1/2/3 numbering.

### Table n/a (not compiled) -- `tab:exp_summary`

- **Caption:** Proposed-approach detection performance across the three experiments on the Internal and Cao2018 driving-EEG corpora. Macro-averaged F1 over all sessions (best-channel-per-session), reported as a percentage.
- **Short slug:** `cross_experiment_summary_table`
- **LaTeX source:** `e_result/exp_summary/tab_exp_summary.tex`
- **Output file:** `e_result/exp_summary/tab_exp_summary.tex (script comment: experiment_script/tab14_tab15_fig11_exp_summary.py)`
- **Result section:** Would belong under a cross-experiment summary subsection (none currently exists in result.tex)
- **Notes:** Not \input anywhere. Rows are labelled exp1/exp2/exp3 using the disk-folder scheme (exp1=channel selection, exp2=strategy comparison numbers reused here as 'Strategy comparison', exp3=epoch duration), which does not match the compiled manuscript's Experiment 1/2/3 section order (channel selection / epoch duration / strategy comparison). MANIFEST references a companion 'fig:exp_boxplot' from the same script; see the orphaned-asset note below.

### Figure n/a (not compiled) -- `fig:exp_boxplot`

- **Caption:** (no caption source found -- no .tex wrapper file exists anywhere in the repo for this asset)
- **Short slug:** `cross_experiment_boxplot`
- **LaTeX source:** `none (orphaned image asset only)`
- **Output file:** `figures/fig_exp_boxplot.{pdf,png}`
- **Result section:** n/a
- **Notes:** PDF/PNG files exist on disk (writing/figures/fig_exp_boxplot.{pdf,png}) but there is no surviving .tex file anywhere in writing/ that includes them with \includegraphics, so there is no label or caption to report. reproduce_manuscript.py MANIFEST still lists fig:exp_boxplot as produced by tab14_tab15_fig11_exp_summary.py; VALUE_AUDIT.md likewise mentions a now-deleted 'fig_exp_boxplot.tex' wrapper. Flagging for Agent 4 (cleanup) as a likely-deletable orphaned image pair, and for Agent 2 as a MANIFEST entry with no corresponding LaTeX to rename.

### n/a

### Table n/a (not compiled) -- `tab:exp3_estimator`

- **Caption:** Effect of the Stage-B threshold estimator on the Internal and Cao2018 driving-EEG corpora at 30 s epochs, for Fp1 and Fp2 reported separately (not averaged). Proposed-approach (median/MAD) and Proposed-Mean (mean/SD) are each scored inside the full 32-channel montage run.
- **Short slug:** `stageb_median_vs_mean_estimator`
- **LaTeX source:** `e_result/exp3/tab_threshold_estimator_stageb.tex`
- **Output file:** `e_result/exp3/tab_threshold_estimator_stageb.tex (script comment: experiment_script/tab19_exp3_threshold_estimator.py)`
- **Result section:** Would belong under a commented-out '%\subsection{Experiment 3: Effect of the Threshold Estimator at Stage B}' in e_result/result.tex
- **Notes:** Entire e_result/exp3/sec.tex (this table plus par1.tex, par2.tex) is commented out where included from e_result/result.tex. IMPORTANT naming collision: disk folder 'exp3' here means the Stage-B median-vs-mean estimator ablation, a DIFFERENT experiment from the compiled manuscript's numbered 'Experiment 3' (Strategy Comparison, disk folder exp4) and also different from the epoch-duration content that also uses 'exp3' in filenames (see Figure 7 / fig_exp3_epoch_duration notes) -- 'exp3' is overloaded across the repo. Companion discussion paragraph f_discussion/d3_estimator/paragraph.tex is also commented out of f_discussion/discussion.tex with an explicit cross-referencing note. MANIFEST labels this 'Experiment 3: Stage-B threshold estimator' (matching disk-folder naming, not manuscript section naming).

### Table n/a (not compiled) -- `tab:literature_comparison`

- **Caption:** Qualitative positioning of the present detector against prior single-channel and threshold-based blink/EOG detectors cited in this work. Because the prior studies use different datasets, blink definitions, sampling rates and especially different matching criteria (sample-level versus event-level), their reported metrics are not directly comparable to an event-level F1; such cells are marked 'n/r'.
- **Short slug:** `literature_qualitative_comparison`
- **LaTeX source:** `c_literature_review/tab_literature_comparison.tex`
- **Output file:** `c_literature_review/tab_literature_comparison.tex (script comment: experiment_script/tab16_literature_comparison.py)`
- **Result section:** Would belong under the Literature Review section
- **Notes:** The entire Literature Review section is commented out in access.tex (%\input{../c_literature_review/p001/paragraph} and p002 both commented), so this table, which is not even \input by p001/p002 themselves, has no path into the compiled document at all.
