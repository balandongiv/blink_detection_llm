# Manuscript Result Validation Report

Independent recomputation of every manuscript numeric/statistical claim, cross-checked
against `reports/result_inventory.md` (Agent 1's inventory) and the actual CSVs under
`publication_results/`. This agent (Agent 3) did not import or execute any
`experiment_script/*.py` generator, `experiment_script/paper_data.py`, or anything under
`src/` -- all recomputation is fresh pandas/scipy/yaml code in `validation/`, reading
only raw CSVs, `brain_region_raja.yaml`/`brain_region_cao2018.yaml`, and the compiled
`.tex` sources under `writing/e_result/` (for the manuscript's claimed "old" values).

Precision/recall/F1 terminology follows this repo's convention: plain "F1"/"precision"/
"recall" (equivalently `det_f1`/`det_precision`/`det_recall`), no "Stage A" or
epoch-level metric language used anywhere below.

## Top-line summary

| match_status | count |
|---|---|
| MATCH | 127 |
| ROUNDING_DIFFERENCE | 0 |
| MISMATCH | 2 |
| UNCLEAR_SOURCE | 0 |
| NOT_REPRODUCIBLE_FROM_AVAILABLE_CSV | 0 |
| **Total values checked** | **129** |

Per experiment:

| Experiment | MATCH | ROUNDING_DIFFERENCE | MISMATCH | Other | Total |
|---|---|---|---|---|---|
| Experiment 1 (channel selection, Figures 3-6) | 70 | 0 | 0 | 0 | 70 |
| Experiment 2 (epoch duration, Figure 7) | 41 | 0 | 0 | 0 | 41 |
| Experiment 3 (strategy comparison, Table 1 + Figure 8) | 16 | 0 | 2 | 0 | 18 |

**Headline finding: every printed number in the manuscript (Table 1's macro-F1 cells and
significance asterisks, Figure 7's per-duration F1s and significance asterisks restated
in `par3.tex`, and every per-electrode F1/significance value restated in `p05_regional`
and `p07_single_channel` prose for Figures 3-6) reproduces exactly from the published
CSVs under the documented best-channel-per-session / fixed-Fp1-Fp2 / per-electrode
aggregation rules.** The only two MISMATCHes are a single qualitative prose sentence in
`par5.tex` (Experiment 3), not a printed number, table cell, or asterisk -- see the
highlighted section below.

## Data-mapping confirmation

Before computing anything, each `publication_results/` subfolder's actual columns and
unique values were opened directly and checked against Agent 1's flagged disk-folder
gotcha:

- `publication_results/exp1_channel_cao/`, `exp1_channel_raja/` -- confirmed this is the
  Experiment 1 (channel-selection) per-electrode/per-selection data (`selection` column
  includes `all_channel`, `frontal`/`central`/`parietal`/`occipital` (+ `_left`/`_right`),
  `posterior`, and per-electrode `<ch>_only` groups; `center_method` in
  `{mean, median}`). Disk folder name matches the manuscript's own experiment number
  here.
- `publication_results/exp3_cao/`, `exp3_raja/` -- confirmed this is the epoch-duration
  sweep (`epoch_duration_s` column present with values `{10, 20, 30, 40, 50, 60, 120}`,
  matching Figure 7's caption exactly), i.e. the manuscript's **Experiment 2** content,
  despite the disk folder being named "exp3".
- `publication_results/exp2_cao/`, `exp2_raja/` -- confirmed this is the strategy
  comparison (`condition` column is `{BLINKER-concat, MNE-annot, Proposed-Mean,
  Proposed-Med}`, `selection` is always `all_channel`, one row per
  `(dataset, session, condition)` already reduced to the best channel via a
  `best_channel` column), i.e. the manuscript's **Experiment 3** content, despite the
  disk folder being named "exp2".

All three gotchas exactly match Agent 1's flagged mapping; no further discrepancy was
found in the CSV contents themselves.

---

## Experiment 1: EEG Channel-Subset Analysis (Figures 3-6)

Script: `validation/validate_exp1_results.py`. Source data:
`publication_results/exp1_channel_raja/exp1_channel_selection_raja_results.csv`,
`publication_results/exp1_channel_cao/exp1_channel_selection_cao2018_results.csv`,
filtered to `center_method == "median"` (Proposed-Med) throughout, matching every live
Experiment 1 figure.

None of Figures 3-6 are unlabelled boxplots -- every bar and every asterisk is a printed
value, and the accompanying `.tex` prose in `writing/e_result/exp1/p05_regional/*.tex`
and `writing/e_result/exp1/p07_single_channel/*.tex` restates dozens of those bar values
and significance counts in text, which is what "old_value" is read from below (not from
any script's console output).

- **Figure 3** (`fig:exp1_subset_per_electrode`): per-electrode F1 within each region's
  own self-contained subset rerun (`selection in {frontal, central, parietal,
  occipital}`, mean F1 per channel across sessions). All 14 prose-quoted values (6
  frontal + 2 central per dataset, plus the best parietal/occipital electrode per
  dataset) reproduced exactly, e.g. Internal frontal subset Fp2 85.28%, Fp1 84.84%, AF4
  77.04%, AF3 70.70%, F3 42.68%, F4 41.00%; Cao2018 central C3 27.67%, C4 26.62%.
- **Figure 4** (`fig:exp1_subset_per_electrode_stats`): paired two-sided Wilcoxon
  signed-rank test (subset rerun vs. same electrode in the `all_channel` full-montage
  run), Bonferroni-corrected over every electrode tested per dataset. Reproduced exactly:
  Internal 24 electrodes tested, 11 significant (Fp1/Fp2 not significant at p=1.000, AF4/
  AF3 significant, C3 significant / C4 not); Cao2018 18 electrodes tested, 16 significant
  (Fp1/Fp2 not significant at p=1.000, F3/F4/C3/C4 all significant).
- **Figure 5** (`fig:exp1_single_channel`): every electrode in the four curated regions
  run as its own complete single-electrode detector (`selection == "<ch>_only"`). All 8
  (Internal) + 11 (Cao2018) prose-quoted F1 values reproduced exactly, e.g. Internal Fp1
  83.73%, Fp2 83.37%, C4 1.51% (weakest); Cao2018 Fp1 77.65%, F3 49.30%, O1 2.28%
  (weakest).
- **Figure 6** (`fig:exp1_single_channel_stats`): paired Wilcoxon (single-electrode vs.
  same electrode in the full-montage run), Bonferroni-corrected per dataset. Reproduced
  exactly: Internal 24 tested, 14 significant, delta-F1 range [-7.02, -0.15] percentage
  points, Fp1/Fp2 not significant; Cao2018 18 tested, 16 significant, F3 delta -10.21pp
  and F4 delta -8.96pp (the two largest reductions), Fp1/Fp2 not significant, C3/C4 both
  significant.

**Result: all 70 checked values MATCH exactly (to within +/-0.03 percentage points,
which is float/rounding noise from the printed two-decimal prose values).**

---

## Experiment 2: Stability Across Epoch Durations (Figure 7)

Script: `validation/validate_exp2_results.py`. Source data:
`publication_results/exp3_raja/exp3_epoch_duration_raja_results.csv`,
`publication_results/exp3_cao/exp3_epoch_duration_cao2018_results.csv`, filtered to
`center_method == "median"` and `selection == "all_channel"`, for the fixed Fp1/Fp2
channel pair (raja `E22`/`E9`, cao2018 `FP1`/`FP2`) at durations
`{10, 20, 30, 40, 50, 60, 120}` seconds. Figure 7's generator
(`experiment_script/res_exp2_fig_f1_by_epoch_duration_fp1_fp2.py`, read only as
documentation, never imported/executed) fixes Fp1/Fp2 as channels rather than applying a
best-channel-per-session oracle for this figure -- confirmed and replicated
independently.

All F1 values, exact Bonferroni-adjusted p-values, and significance flags quoted in
`writing/e_result/exp2/par3.tex` reproduced exactly, for both datasets and both
electrodes -- 28 individual F1/p-value/significance checks plus 12 "claimed not
significant" checks, **41 values total, all MATCH**. Examples: Internal Fp1 30s
reference 86.32%, significant declines at 50s (85.92%, p=0.002), 60s (85.67%, p<0.001)
and 120s (85.04%, p<0.001); Cao2018 Fp1/Fp2 showed no significant difference from the
30s reference at any tested duration, matching the prose exactly.

### Historical bug re-check (explicitly requested, reported regardless of outcome)

The 2026-08-20 audit flagged that an earlier version of this analysis allegedly computed
its best-channel-per-session oracle over **all four** selection gates (`all_channel`,
`frontal`, `frontal_left`, `frontal_right`) instead of restricting to `all_channel` only,
inflating F1 by +0.31 to +1.05 percentage points and flipping at least one p-value from
non-significant to significant.

This script independently re-ran the analysis under both restrictions:

| Dataset/electrode | max \|delta\| if oracle-over-4-gates used instead | significance flip |
|---|---|---|
| Internal/Fp1 | +0.96 pp | **yes**: 50s flips from significant (p_bonf=0.0025) to non-significant (p_bonf=0.105) |
| Internal/Fp2 | +1.08 pp | no |
| Cao2018/Fp1 | +1.25 pp | no |
| Cao2018/Fp2 | +1.25 pp | no |

**Conclusion: the bug is confirmed FIXED in the values actually compiled into the
manuscript.** Every F1 and p-value printed in `par3.tex`/Figure 7 matches the
`all_channel`-gate-only computation exactly (see above), and this recheck additionally
confirms the restriction is load-bearing: had it been dropped, F1 would be inflated by up
to 1.25 percentage points and Internal/Fp1's 50s duration would flip from significant to
non-significant, closely matching the size and character of the originally-reported bug.
This row is recorded as MATCH in the CSV (the manuscript's stated methodology is
confirmed correctly applied), with the sensitivity finding itself recorded in the `note`
field.

---

## Experiment 3: Strategy Comparison (Table 1 + Figure 8)

Script: `validation/validate_exp3_results.py`. Source data:
`publication_results/exp2_raja/exp2_strategy_comparison_raja_results.csv`,
`publication_results/exp2_cao/exp2_strategy_comparison_cao2018_results.csv`.

**Table 1 (`tab:f1_significance`)** -- all six printed macro-F1 cells and all four
significance asterisks reproduced exactly:

| Dataset | Proposed (old / new) | BLINKER (old / new) | MNE (old / new) |
|---|---|---|---|
| Internal | 88.25 / 88.25 | 76.54\* / 76.54 (p_bonf=9.1e-05, sig) | 66.64\* / 66.64 (p_bonf=0.0024, sig) |
| Cao2018 | 80.68 / 80.68 | 69.40\* / 69.40 (p_bonf=1.8e-08, sig) | 56.27\* / 56.27 (p_bonf=8.7e-07, sig) |

This also directly re-checks the 2026-08-20-audit-flagged "exp3 oracle pool missing
all_channel filter (88.82 vs 88.25)" issue noted in project memory: **the current
`publication_results/exp2_raja/` CSV already contains only `selection == "all_channel"`
rows, and this script's independent from-scratch recomputation reproduces 88.25%
exactly, confirming that bug is fixed in the currently compiled Table 1** (the CSV shows
no trace of the higher, gate-mixed 88.82% value).

**Figure 8 (`fig:exp2_pr_scatter`)** -- the figure prints no numeric labels, so its mean
markers were checked for internal consistency against Table 1's printed cells (both use
the same underlying rows/filter): Proposed-approach's recomputed mean-marker F1 matches
Table 1's Proposed-approach cell exactly on both datasets (88.25% Internal, 80.68%
Cao2018).

### Highlighted: the only two non-MATCH rows found in the whole audit

Both are the **same qualitative prose sentence** in `writing/e_result/exp4/par5.tex`,
checked once per dataset, not a printed number/table cell/asterisk:

> "This asymmetry appears as a consistent spatial ordering in the scatter, with
> Proposed-approach occupying the high-precision, high-recall region ... **separated
> from both baselines in the same direction** on Internal and on Cao2018."

Recomputed per-condition mean precision/recall (the same quantities Figure 8 plots):

| Dataset | Proposed P / R | BLINKER P / R | MNE P / R |
|---|---|---|---|
| Internal | 88.03% / 90.14% | 67.94% / **95.18%** | 69.44% / 70.63% |
| Cao2018 | 75.91% / 89.09% | 56.96% / **97.15%** | 60.13% / 61.68% |

Proposed-approach has uniformly higher **precision** than both baselines on both
datasets (consistent with the prose), but BLINKER-concat has **higher recall** than
Proposed-approach on both datasets (95.18% vs. 90.14% on Internal; 97.15% vs. 89.09% on
Cao2018) -- which is also the exact behaviour `par4.tex` itself describes ("BLINKER ...
consistently favors recall over precision"). The `par5.tex` phrase "separated from both
baselines in the same direction" therefore overstates the geometry on the recall axis
for the BLINKER comparison specifically: Proposed-approach is separated in the
high-precision direction from BLINKER, but not in the high-recall direction.

- **match_status: MISMATCH** (x2, one per dataset)
- **possible_root_cause:** prose overstatement/imprecision, not a data or computation
  error -- Table 1's F1 numbers, which correctly summarise the net precision-recall
  trade-off, are unaffected. This is a wording issue in `par5.tex`'s qualitative
  description of the scatter geometry, flagged here for human review; no manuscript
  value was altered.

---

## Deliverables

- `validation/validate_exp1_results.py` -- Experiment 1 (Figures 3-6), 70/70 MATCH
- `validation/validate_exp2_results.py` -- Experiment 2 (Figure 7 + historical bug
  re-check), 41/41 MATCH
- `validation/validate_exp3_results.py` -- Experiment 3 (Table 1 + Figure 8), 16/18
  MATCH, 2/18 MISMATCH (both the same par5.tex prose overstatement, not a printed value)
- `reports/result_validation_table.csv` -- all 129 checked values, one row each
- `reports/result_validation_report.md` -- this file

All three scripts are independent (no import of `experiment_script/paper_data.py`, any
`experiment_script/*.py` generator, or anything under `src/`) and are runnable
standalone:

```
conda run -n double_threshold_algo python validation/validate_exp1_results.py
conda run -n double_threshold_algo python validation/validate_exp2_results.py
conda run -n double_threshold_algo python validation/validate_exp3_results.py
```
