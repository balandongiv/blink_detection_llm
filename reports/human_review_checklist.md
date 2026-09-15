# Human Review Checklist

Short, decision-focused. Full detail behind each item is linked.

## 1. Prose overstatement (needs a wording decision)

**`writing/e_result/exp4/par5.tex`** claims the proposed method is "separated from both baselines in the same direction" on precision and recall. Independently recomputed numbers show this is true for precision but **not** for recall: BLINKER-concat has higher recall than the proposed method on both datasets (Internal 95.18% vs 90.14%; Cao2018 97.15% vs 89.09%). No printed number in the manuscript is wrong — this is a wording fix, e.g. restricting the claim to precision, or to comparing against MNE-annot only.
→ `reports/result_validation_table.csv` (2 MISMATCH rows), `reports/result_validation_report.md`

## 2. Two orphaned figure assets (needs a delete-or-restore decision)

`writing/figures/fig_exp_boxplot.{pdf,png}` and `writing/figures/fig_count_agreement.{pdf,png}` exist on disk with **no surviving `.tex` wrapper anywhere** — no caption, no label, no path back into the manuscript. `VALUE_AUDIT.md` confirms their wrappers were deleted previously. Not deleted in this pass (per the no-delete constraint); decide whether to permanently remove them or restore a wrapper.
→ `reports/result_inventory.md` ("On disk but not compiled" section, `fig:exp_boxplot` / `fig:count_agreement` rows)

## 3. 16 scripts marked UNCERTAIN — re-enable or drop?

16 generator scripts sit behind commented-out manuscript sections (mostly with inline notes like "disabled per instruction... re-enable by uncommenting if needed again"). None were moved — this is a content decision on whether those sections return to the manuscript, not something safe for an agent to decide.
→ `reports/obsolete_scripts.csv`, `experiment_script/obs/README.md`

## 4. Missing `writing/FIGURE_TABLE_MAP.md`

Referenced by `experiment_script/reproduce_manuscript.py`'s own docstring as "the authority" for figure/table numbering, but does not exist on disk. Not recreated in this pass (documentation task, out of this audit's scope) — flagging so it doesn't silently stay missing.

## Not flagged (checked and fine)

- All other 127 independently-recomputed values MATCH exactly (0 rounding differences).
- Manuscript recompiles cleanly, same page count as before cleanup.
- `reproduce_manuscript.py check` passes after all renames.
- Pre-existing test failures (`tests/test_kleifges_masterlist_regression.py` 40s/60s, one exp1 lane-summary test) are unrelated to this cleanup — see `reports/final_cleanup_summary.md`'s Reproducibility/test status section for why.
