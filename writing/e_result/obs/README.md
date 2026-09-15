# writing/e_result/obs/

LaTeX source and image assets moved out of the active `writing/e_result/` tree on
2026-09-15 because they are not `\input` anywhere in the live `access.tex` -> `result.tex`
chain -- either sitting behind a commented-out `\input`/`\paragraph`, or never referenced
at all. Nothing was deleted; every `.tex` file moved via `git mv`, so its history and the
original path are one `git log --follow` away. See `reports/result_inventory.md` for the
line-by-line audit (which `\input` is commented, and where) that this move is based on,
and `experiment_script/obs/README.md` for the matching Python-script moves.

Confirmed by grepping every `\input{` line under `writing/` before moving anything (see
`reports/result_inventory.md`'s "On disk but not compiled" section): a file below is here
only if its `\input` is commented out, or does not exist at all, anywhere in the tree that
`writing/ACCESS_latex_template_20260513/access.tex` actually compiles.

## `exp1/`

Commented out of `writing/e_result/exp1/sec.tex`, each behind an explicit "disabled per
instruction, re-enable by uncommenting if needed again" note:

- `tab_egi_channel_map.tex` -- **never referenced at all**, not even a commented `\input`
  (the one exception to the "commented out" rule above). Companion of
  `experiment_script/obs/tab1_egi_channel_map.py`.
- `tab_region_performance.tex`, `p04_per_electrode/paragraph_region_collapsed.tex` --
  Region-Collapsed Results (full montage). Companion of `obs/tab3_fig3_region_performance.py`.
  The figure assets (`figures/fig_region_performance.{pdf,png}`) were left in place since
  the commented `\includegraphics` call is inside the moved paragraph file, not `sec.tex`
  itself -- restoring this one file restores the figure too.
- `paragraph_region_collapsed_p05.tex` (originally `p05_regional/paragraph_region_collapsed.tex`,
  renamed here only to avoid a name collision with the file above) -- a second,
  region-collapsed paragraph nested under the Regional Channel Subsets subsection.
- `tab_exp1_subset_summary.tex` -- channel-subset vs. full-montage summary table.
  Companion of `obs/tab17_exp1_subset_summary.py`.
- `p07_single_channel/paragraph_region_collapsed.tex`, `tab_exp1_single_channel_region.tex` --
  Region-Collapsed Results for the Single-Channel Operation subsection. Companion of
  `obs/tab21_exp1_single_channel_region.py`.
- `p07_single_channel/paragraph_channel_context.tex` -- Channel-Context Comparison paragraph
  (its figure, `fig:exp1_single_channel_delta`, is `obs/fig14_exp1_single_channel_delta.py`).
- `tab_channel_selection.tex` -- best-channel selection frequency table (the whole "Stability
  of the Channel Choice" subsubsection is commented out). Companion of
  `obs/tab11_fig9_channel_selection_frequency.py`.
- `p11_oracle_cost/paragraph.tex`, `p12_agreement/paragraph.tex` -- the two surviving
  paragraphs of that same commented-out subsubsection (a third, `p10_selection_frequency/
  paragraph.tex`, was `\input` but never existed on disk at all).

Not moved: `fig_exp1_region_boxplot.{pdf,png}` and `fig_channel_selection.{pdf,png}` stay in
`writing/figures/` -- their commented `\includegraphics` calls live directly inside
`e_result/exp1/sec.tex` and `e_result/result.tex` respectively (files that are otherwise
live), not in a file that moved here.

## `exp3/`

The entire Stage-B median-vs-mean threshold-estimator ablation. `e_result/exp3/sec.tex` is
never `\input` from `result.tex` (`% \input{e_result/exp3/sec}`, commented), so `par1.tex`,
`par2.tex`, `sec.tex` and `tab_threshold_estimator_stageb.tex` all moved together. Companion
of `obs/tab19_exp3_threshold_estimator.py`. Note this "exp3" is a third, unrelated meaning of
that folder name in this repo -- distinct from both the epoch-duration and strategy-comparison
uses documented in `experiment_script/SCRIPTS_OVERVIEW.md`.

## `exp4/`

Five tables that live on disk in the `exp4/` folder (alongside the still-live
`tab_f1_significance.tex`) but are never `\input` by `e_result/exp4/sec.tex` at all -- not
even a commented line:

- `tab_best_session.tex` (companion of `obs/tab9_best_session.py`)
- `tab_count_agreement.tex` (companion of `obs/tab7_fig8_count_agreement.py`)
- `tab_cross_dataset_gap.tex` (companion of `obs/tab6_cross_dataset_gap.py`)
- `tab_error_structure.tex` (companion of `obs/tab8_error_structure.py`)
- `tab_failure_analysis.tex` (companion of `obs/tab10_failure_analysis.py`)

## `exp_summary/`

`tab_exp_stats.tex` and `tab_exp_summary.tex` -- a cross-experiment summary that was never
wired into `result.tex` (no `\input`, live or commented; no summary subsection stub exists).
Both companions of `obs/tab14_tab15_fig11_exp_summary.py`. The source folder
`e_result/exp_summary/` was removed after the move since it was left empty.

## `r2_operating_points/`

`paragraph.tex` -- not referenced anywhere in `writing/`, live or commented, under any
filename. The source folder `e_result/r2_operating_points/` was removed after the move.

## `c_literature_review/`

`tab_literature_comparison.tex` -- the entire Literature Review section is commented out of
`access.tex` (`%\input{../c_literature_review/p001/paragraph}` / `p002`), so this table,
which is not even `\input` by those paragraphs themselves, has no path into the compiled
document at all. Companion of `obs/tab16_literature_comparison.py`.

## `figures/`

Two orphaned image pairs with **no surviving `.tex` wrapper anywhere in the repo** (so they
carry no label or caption to restore alongside them if ever needed again):

- `fig_exp_boxplot.{pdf,png}` -- companion of `obs/tab14_tab15_fig11_exp_summary.py`.
- `fig_count_agreement.{pdf,png}` -- companion of `obs/tab7_fig8_count_agreement.py`
  (distinct from `tab_count_agreement.tex` above, which did have a wrapper and moved with
  its own entry).

## Restoring something from here

1. `git mv` the file(s) back to their original path (shown by `git log --follow <path>` on
   the file in this folder).
2. Uncomment the corresponding `\input`/`\paragraph`/`\subsection` line in the relevant
   `sec.tex` or `result.tex`.
3. If the companion Python script was also moved (see `experiment_script/obs/README.md`),
   move it back too and undo its `sys.path.insert(0, ... .parent.parent)` back to
   `.parent` (it was adjusted for the extra `obs/` directory depth when moved).
4. Recompile and re-run `experiment_script/reproduce_manuscript.py check`.
