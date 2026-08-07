# VALUE AUDIT — std=3.0 re-run (`runs_second_iteration/`)

**Date:** 2026-06-29
**Auditor:** claude-opus-4-8 (orchestrator)
**Source of truth:** `runs_second_iteration/` (validated std=3.0 re-run). Baseline: `runs/`.
**Frozen numbers file:** `writing/NUMBERS_std30.md` (regenerate with
`python experiment_script/compute_paper_numbers.py` and
`python experiment_script/compute_paper_numbers_addendum.py`).

## Headline aggregation (used for every four-condition comparison)

**best-channel-per-session**: for each `(session, condition)` take the single row with
the maximum `det_f1` across all available `selection` values (single channels *and*
frontal sub-montages), then average across sessions. Precision/recall are taken from
that same argmax-`det_f1` row. This matches the HANDOFF §2/§5.1(e) "best-channel-per-session"
figures (Raja 0.86–0.89, Cao2018 0.80–0.82) and reproduces the paper's original
oracle-best-channel framing. It is applied **identically** to all four conditions, so
comparisons are fair.

Cross-check vs HANDOFF "verified" claims (all reproduced): Raja PM = 0.8777 (∈0.86–0.89);
Cao PM = 0.8087 (∈0.80–0.82); per-channel single-channel means Raja E22=0.837, E9=0.834,
E3=0.752, E23=0.676; Cao FP1=0.777, FP2=0.756; best single (E22 0.84) ≫ best group
(frontal\_right 0.67); Cao FP1 0.78 ≫ frontal\_left 0.66.

---

## §0 Resolution of the Cao2018 = 0.8954 discrepancy

**Resolved → corrected.** The paper's `p002` value 0.8954 (and the whole p001/p002 number
set, e.g. pooled F1 0.8667) was produced from
`runs/exp41_cao_30s/exp41_strategy_comparison_results.csv` — a now-**deleted** older run
(pre-std30; the helper scripts `paper_error_structure_session.py` and
`paper_channel_selection_frequency.py` still point at this missing file). That file does
not exist any more, and **no aggregation of the current CSVs reproduces 0.8954**: the
oracle best-channel-per-session upper bound for Cao2018 Proposed-Med is **0.8087**
(`runs_second_iteration/`) / 0.7879 (`runs/`). The value is therefore stale and has been
**corrected** to the recomputed best-channel-per-session figure. This gap is present in the
baseline too, so it is not a regression of the new run.

---

## Conclusions that CHANGED (not just numbers) — narrative revisions required

| # | Old conclusion (paper) | New conclusion (`runs_second_iteration/`) | Affects |
|---|---|---|---|
| C1 | Cao2018 > Raja; cross-dataset gap **negative** (−0.065 PM) | **Raja > Cao2018**; gap **positive** (+0.069 PM) — direction flipped | e_result p002; f_discussion p004 |
| C2 | Proposed-Med **significantly** beats Proposed-Mean (p=1.4e-6) | PM vs PMean **not significant** after Bonferroni (p\_bonf=0.225); both proposed beat both baselines | e_result p001, p005; f_discussion p001, p002, p004 |
| C3 | Proposed-Med is **FN-heavy / conservative** (FP:FN 0.44) | PM is **balanced / mildly FP-heavy** (FP:FN 1.19); BLINKER extreme FP-heavy 31.4 | e_result p006; f_discussion p005; new Discussion Para D |
| C4 | Worst session catastrophic **F1=0.077** (Raja S16) | No catastrophe: min **F1=0.409** (Cao S31); Raja S16 best-channel F1=0.421 | e_result p007; §5.1(f); f_discussion Para C |
| C5 | 30 s epoch is the **best** duration | Durations 10–120 s all statistically equal to 30 s (range 0.011, 60 s marginally top); 30 s **retained** by convention | e_result p003; f_discussion p006 |
| C6 | Epoch-health filter improves both (~+0.05 Raja, +0.07 Cao) | **Dataset-dependent**: Cao +0.100, Raja −0.006 (neutral) | new exp7 paragraph; f_discussion Para C |

---

## Per-paragraph corrections (e_result)

### p001 — four-condition headline (pooled 104)
| Metric | OLD | NEW | Source |
|---|---|---|---|
| Proposed-Med P/R/F1 | 0.8987 / 0.8682 / 0.8667 | **0.8268 / 0.8794 / 0.8392** | exp2 both ds |
| Proposed-Mean P/R/F1 | 0.9046 / 0.8436 / 0.8534 | **0.8356 / 0.8604 / 0.8320** | exp2 |
| BLINKER-concat P/R/F1 | 0.7053 / 0.9742 / 0.7952 | **0.6153 / 0.9695 / 0.7242** | exp2 |
| MNE-annot P/R/F1 | 0.7656 / 0.7787 / 0.7372 | **0.6409 / 0.6133 / 0.5731** | exp2 |
Narrative: PM still highest F1, BLINKER still highest recall + lowest precision. **Softened**:
PM's margin over Proposed-Mean is no longer significant (C2).

### p002 — cross-dataset gap (per-dataset best-channel F1)
| Condition | OLD Raja / Cao / gap | NEW Raja / Cao / gap |
|---|---|---|
| Proposed-Med | 0.8305 / 0.8954 / −0.0648 | **0.8777 / 0.8087 / +0.0690** |
| Proposed-Mean | 0.8171 / 0.8822 / −0.0651 | **0.8671 / 0.8041 / +0.0630** |
| BLINKER-concat | 0.7588 / 0.8242 / −0.0654 | **0.7644 / 0.6924 / +0.0720** |
| MNE-annot | 0.6097 / 0.8383 / −0.2286 | **0.6526 / 0.5101 / +0.1424** |
**Direction flipped (C1).** Performance is now higher on Raja; proposed methods keep a
small consistent gap (~0.063–0.069); MNE far less stable (0.142).

### p003 — epoch duration (pooled best-channel F1)
OLD pooled @10/20/30/40/60 = 0.8458 / 0.8611 / **0.8667** / 0.8580 / 0.8497 (30 s best).
NEW pooled @10/20/30/40/50/60/120 = 0.8362 / 0.8380 / 0.8392 / 0.8383 / 0.8412 / **0.8432** / 0.8324.
All non-reference durations non-significant vs 30 s (two-sided Wilcoxon, Bonferroni ×6, all
p\_bonf > 0.4; range 0.011). **Revised** to "statistically flat; 30 s retained by convention" (C5).

### p004 — blink-type recall
OLD (event-level, all 4 conditions): 81,852 normal / 7,377 long / 89,229 total (8.3% long);
recall e.g. PM 0.8548/0.8230. NEW (`exp8`, **Proposed-Med only** — baselines not present in
the std30 exp8 CSV): GT pooled total **116,413**, normal **105,763**, long **10,650**
(**9.1% long**); PM best-channel recall normal **0.8814** vs long **0.7868** (pooled);
Raja 0.8967 / 0.7668; Cao 0.8693 / 0.8027. **Revised** to Proposed-Med normal-vs-long;
long blinks remain the residual weakness.

### p005 — Wilcoxon (pooled, Bonferroni ×6, two-sided)
| Pair | OLD p | NEW p / p\_bonf | Sig? |
|---|---|---|---|
| PM vs BLINKER-concat | 6.6e-6 | 2.33e-11 / **1.40e-10** | yes |
| PM vs MNE-annot | 1.3e-4 | 2.91e-11 / **1.75e-10** | yes |
| PMean vs BLINKER-concat | 2.3e-4 | 7.51e-10 / **4.51e-9** | yes |
| PMean vs MNE-annot | 4.7e-3 | 6.97e-11 / **4.18e-10** | yes |
| PM vs PMean | 1.4e-6 | 3.75e-2 / **0.225** | **NO** (changed, C2) |
| BLINKER vs MNE | — | 4.55e-2 / 0.273 | no |

### p006 — error structure (mean per-session FP/FN at best-channel row, pooled)
| Condition | OLD FP / FN / ratio | NEW FP / FN / ratio / regime |
|---|---|---|
| BLINKER-concat | 244.0 / 14.3 / 17.1 | **641.5 / 20.4 / 31.41 / FP-heavy** |
| MNE-annot | 95.6 / 190.9 / 0.50 | **207.6 / 531.8 / 0.390 / FN-heavy** |
| Proposed-Mean | 49.0 / 157.2 / 0.31 | **162.6 / 184.4 / 0.882 / FN-heavy** |
| Proposed-Med | 55.6 / 126.8 / 0.44 | **180.7 / 151.7 / 1.192 / balanced (mild FP)** |
(Raw counts scale up because the std30 re-run resamples/counts more events; the **regime**
is what matters.) **PM regime FN-heavy → balanced (C3).** Revised: PM is the most balanced
detector; BLINKER over-detects ~31:1.

### p007 — best/worst session & subject (Proposed-Med, pooled 104)
| Item | OLD | NEW |
|---|---|---|
| Session F1 range | 0.0767 – 1.0000 | **0.4088 – 0.9946** |
| Median session F1 | 0.9133 | **0.8808** |
| Best session | Cao S53 (1.0000) | **Cao S55/090930n (0.9946)** |
| Worst session | Raja S16/S29\_…034326\_3 (0.0767) | **Cao S31/061103n (0.4088)** |
| Best subject | Cao S55 (0.9930) | **Cao S55 (0.9946)** |
| Worst subject | Raja S16 (0.2115, 2 sess) | **Cao S31 (0.5244, 2 sess)** |
| Median subject | 0.8869 | **0.8420** |
**No catastrophic outlier anymore (C4).**

### p008 — channel robustness (argmax-F1 channel agreement)
| Item | OLD | NEW |
|---|---|---|
| all-four agreement (pooled) | 31.7% (33/104) | **19.2% (20/104)** |
| mean pairwise agreement (pooled) | 0.583 | **0.482** |
| Raja pairwise / all-four | 0.572 / 30.4% | **0.504 / 21.7% (10/46)** |
| Cao pairwise / all-four | 0.592 / 32.8% | **0.466 / 17.2% (10/58)** |
| two proposed agree | 87.5% | **89.1% Raja / 82.8% Cao** |

### p009 — channel-selection frequency
| Item | OLD | NEW |
|---|---|---|
| Raja (184 sel) | E9 48.9% (90), E22 39.7% (73), E3 11.4% | **E9 43.5% (80), E22 37.0% (68), E3 8.2% (15), E23 7.1% (13)** |
| Cao (232 sel) | FP1 62.1% (144), FP2 30.6% (71) | **FP1 52.6% (122), FP2 26.3% (61), F7 7.3% (17), F8 6.9% (16), F3 5.2% (12)** |
| within-subject modal fraction (median) | 0.75 both | **Raja 0.667 / Cao 1.000** |
| two proposed agree | 91.3% Raja / 84.5% Cao | **89.1% Raja / 82.8% Cao** |
| all-four agree | 30.4% Raja / 32.8% Cao | **21.7% Raja / 17.2% Cao** |

---

## Per-paragraph corrections (f_discussion)

- **p001** — F1 0.8667→**0.8392**, BLINKER 0.7952→**0.7242**, MNE 0.7372→**0.5731**; soften
  "significantly outperformed Proposed-Mean" (C2: now NS).
- **p002** — "Proposed-Med edges Proposed-Mean (0.8667 vs 0.8534)" → **0.8392 vs 0.8320, a
  small non-significant margin** (C2).
- **p003** — channel percentages updated (FP1 62.1→**52.6%**, FP2 30.6→**26.3%**; two-proposed
  91.3/84.5→**89.1/82.8%**). Frontal-sufficiency conclusion unchanged.
- **p004** — cross-dataset gap −0.065→**+0.069** (PM), −0.229→**+0.142** (MNE); narrative
  flipped to Raja-higher (C1).
- **p005** — long-blink recall 0.8230→**0.7868 (pooled)**; PM "best recall among conservative
  methods" reframed (C3 — PM now balanced; baselines absent from std30 exp8).
- **p006** — epoch-duration "30/40/60 stable, range 0.0170" → **10–120 s all equal to 30 s,
  range 0.011** (C5).
- **p007, p008, p009** — no stale numeric claims (qualitative); left as is / minor.

---

## New sections added (Phase 1/2)

- `e_result/tab_exp_summary.tex`, `fig_exp_boxplot.tex` + `plot_exp_boxplot.py` + figures,
  `tab_exp_stats.tex` — cross-experiment summary, box plot, Wilcoxon/effect-size/bootstrap.
- `e_result/p110…p150` per-experiment narrative paragraphs (exp1–5,7,8).
- `e_result/tab_region_performance.tex` + `p011/` + `plot_region_performance.py` — regional /
  single-channel.
- `e_result/tab_failure_analysis.tex` + `p012/` + `analyse_failure_sessions.py` — failure
  analysis (bottom-5 sessions, mechanism).
- `f_discussion/p010/` — five new discussion paragraphs (median-vs-mean, electrode
  recommendation, signal-quality/epoch-health, PERCLOS operating point, regional/single-channel).


---

## Failure-mechanism correction (§5.1f) — HANDOFF premise was from the OLD run

The HANDOFF assumed the worst session was Raja S16 at $F_1\approx0.077$--$0.084$ (catastrophic
under-detection, ~1,700 missed events) and proposed "anomalous ground truth" / "low amplitude"
as the mechanism. In the validated std=3.0 re-run this premise no longer holds and the
data-driven mechanism is different:

- **No catastrophic session.** Raja S16 best-channel $F_1 = 0.421$ (E9; tp=494, fp=32, fn=1328);
  the global worst is Cao2018 S31 at $0.409$. Minimum $F_1$ rose from 0.077 to 0.409.
- **Two opposite failure modes, not one.** Under-detection on a minority of high-GT sessions
  (Raja S16 GT 3.5x median, S24 2.1x, Cao S31 1.5x) AND over-detection on low-blink/noisy
  sessions (Cao S53 fp=737 vs 367 true blinks) — the latter dominates Cao2018 failures.
- **Low amplitude REFUTED.** Worst Raja session S16 robust frontopolar amplitude ≈ 27 µV vs
  ≈ 9 µV for a typical session — failures are not flat-signal cases.
- **Epoch-health filtering recovers the over-detection failures:** +0.58 (Cao S53), +0.50
  (Cao S31), +0.22 (Cao S42), +0.22 (Raja S1).
- **Affected fraction is small:** 1/46 Raja and 3/58 Cao sessions below $F_1=0.60$; 5/46 and
  12/58 below 0.70.

Reported in `e_result/p012/paragraph.tex` and discussion Para F; computed by
`experiment_script/analyse_failure_sessions.py`.

## Final compile status

`pdflatex main.tex` (x3) + `biber`: **exit 0, 39 pages, no undefined citations/references,
all figures embedded, 0 overfull boxes.** Six classic references added to
`references_from_csv.bib` (Rousseeuw & Croux 1993; Leys et al. 2013; Berka et al. 2007;
Jas et al. 2017 autoreject; Bigdely-Shamlo et al. 2015 PREP; Pl\"ochl et al. 2012).

---

# ROUND 2 (2026-06-30) — additional analyses, discussion, limitations

**Driver:** `HANDOFF_round2_additional_analysis.md`. Same source of truth
(`runs_second_iteration/`, std=3.0), same **best-channel-per-session** aggregation. No
detector re-runs; all numbers recomputed from existing CSVs. New frozen numbers written to
`writing/NUMBERS_round2.md` (`python experiment_script/compute_round2_addendum.py`).
Files edited in place were backed up to `*.bak_r2`.

## `temp_result_analysis/` verdict (handoff §A)
Confirmed **superseded, not integrated wholesale.** The temp files' alarm
(frontal "F1=0.3126" vs P=0.901/R=0.791; frontal\_left 0.831 vs frontal\_right 0.299) is the
diluted-per-channel-row artefact already resolved in Round 1. Their two real conclusions
(single ≥ group; channel choice ≫ nmin) were already in the paper at the correct
aggregation. Only the **ideas** were cherry-picked: fusion future-work (C2), hemisphere
rebuttal (C3/R3), long-decline framing (C5). Timing (R7/C4) was **not** added — no wall-clock
in the CSVs and the temp numbers are unverified; runtime reporting treated as out of scope.

## New result analyses (recomputed, frozen in NUMBERS_round2.md)
| ID | Finding | Numbers |
|---|---|---|
| R1 | Precision-recall operating points (best-channel, pooled 104) | PM P=0.8268/R=0.8794; PMean 0.8356/0.8604; BLINKER 0.6153/0.9695; MNE 0.6409/0.6133 |
| R2 | Predicted (TP+FP) vs true (TP+FN) blink count | PM ratio 1.11, r=0.936, CCC=0.935, BA bias +29; PMean 1.08/0.917; **BLINKER 1.99/0.863/CCC0.703 (≈2× over-count)**; MNE 0.94/**0.465**/0.425 (unreliable). exp8 cross-check PM Raja r=0.886 (seed reproduced). |
| R3 | Hemisphere symmetry (best-channel within group) | Raja frontal\_left **0.8536** vs frontal\_right **0.8459** (Δ0.008); Cao 0.7841 vs 0.7785 (Δ0.006). **No asymmetry** — rebuts temp-file artefact. |
| R4 | Within-subject consistency (33 subj ≥2 sess, 93 sess) | within-subject SD 0.081, between-subject SD 0.115, ICC(1) Raja 0.499 / Cao 0.283 — partly stable trait, partly session noise. |
| R5 | Epoch-health benefit structure | Cao corr(unfiltered F1, gain) **−0.795** (p<0.001); sessions <0.70 gain +0.234 vs +0.064 rest; Raja neutral (mean Δ −0.006, ns). Filter helps worst sessions most. |

## R3 artefact correction (explicit)
The apparent left–right asymmetry in the temp files (0.831 vs 0.299) is an **aggregation
artefact**: pooling a hemisphere's strong frontopolar electrode with its weak peripheral
channels lowers that side's pooled per-channel mean. At the matched best-channel-per-session
aggregation the hemispheres are equal (R3 numbers above). Documented in Discussion C3 (p011).

## New files
- `experiment_script/plot_pr_operating_points.py` → `figures/fig_pr_scatter.{pdf,png}` (R1)
- `experiment_script/plot_count_agreement.py` → `figures/fig_count_agreement.{pdf,png}` +
  `e_result/tab_count_agreement.tex` (R2)
- `experiment_script/compute_round2_addendum.py` → `NUMBERS_round2.md` (R3/R4/R5 + R2 check)
- `experiment_script/build_literature_comparison.py` →
  `c_literature_review/tab_literature_comparison.tex` (C6, qualitative; prior-work metric
  cells = "n/r", only our row carries numbers — **no metrics invented**)
- `e_result/fig_pr_scatter.tex`, `e_result/fig_count_agreement.tex` (figure wrappers)
- `e_result/p013/` (R1 narrative), `e_result/p014/` (R2 narrative)
- `f_discussion/p011/` (C1–C3, C5, C6), `f_discussion/p012/` (L1-future long-closure module)

## Edited existing files (backed up `*.bak_r2`)
- `e_result/result.tex` — new subsection "Operating Points and Count Fidelity"
  (fig\_pr\_scatter, p013, tab\_count\_agreement, fig\_count\_agreement, p014).
- `f_discussion/discussion.tex` — added p011, p012, tab\_literature\_comparison inputs.
- `f_discussion/p008/paragraph.tex` — **limitations promoted long eye-closure to the lead
  limitation** (L1: long recall 0.7868 vs 0.8814 normal; long F1 ≈ 0.54 Raja / 0.46 Cao;
  morphology root cause; ~9% of events) and consolidated L2–L6 (two corpora; single-channel;
  no baseline boundary comparison; GT dependence; no DL benchmark).
- `f_discussion/p010/paragraph.tex` — appended R4 (ICC/between-vs-within) and R5 (health
  benefit −0.795) sentences to the signal-quality paragraph (Para C).
- `main.tex` — added `\usepackage{float}`; literature table placed `[H]` at its C6 reference.

## Discussion additions (p011), each grounded + ≥1 \citep
- **C1** count fidelity (R2) — only the proposed conditions yield a usable event count;
  `zulkarnanie2022enhancements,dai2023detection`.
- **C2** fixed fusion underperforms (Exp1 ablation) → adaptive/weighted-fusion future work;
  `plochl2012combining,croft2000removal`; cross-ref Para E + Table~\ref{tab:exp1_channel_ablation}.
- **C3** hemisphere-agnostic placement (R3), artefact correction; `croft2000removal`.
- **C5** long-blink decline systematic across corpora (Raja 0.897→0.767, Cao 0.869→0.803,
  pooled ~0.09); `dai2023detection`.
- **C6** literature positioning (Table~\ref{tab:literature_comparison}); qualitative, non-comparable
  caveat tied to boundary-tolerance F1 spread 0.93→0.26; `chang2016detection,tran2021detection,
  kleifges2017blinker`.

## Long-blink through-line
C5 (systematic decline) → p008 L1 (lead limitation) → p012 L1-future (dual-mode
suppression/plateau module; targets long recall ≥0.80, long F1 ≥0.70; referenced as a
**separate** contribution per `long_blink_detection_report.md`, **not** evaluated in this
paper — the validated 0.72 dual-mode figure is deliberately not quoted as a paper result).
The optional split-vs-undetected long-blink decomposition was **not** done: the exp8 CSV
carries only per-session `det_fn` for the long category, not the per-event match structure
needed to separate "entirely undetected" from "split/merged".

## No citations invented / no numbers fabricated
All `\citep` keys verified present in `references_from_csv.bib`; no new bib entries added (all
keys were already cited). C6 prior-work metric cells are "n/r" because the
repository holds no extracted comparable event-level metrics (the deep-research report is a
narrative draft, not a metrics table).

## Final compile status (Round 2)
`pdflatex` ×2 → `biber` → `pdflatex` ×2: **exit 0, 45 pages, 0 undefined citations/references,
0 rerun warnings.** 9 overfull \hbox remain, **all pre-existing** (2 in result.tex prose,
1 in `tab_exp_summary`, 6 in long-title bibliography entries); the Round-2 additions introduce
**zero net overfull boxes**. New figures embedded as vector PDFs; literature table anchored at
its discussion reference (p.\ 39) via `[H]`.

---

# ROUND 3 (2026-06-30) — Experiment 1 channel-by-channel refactor + reproducibility framework

**Driver:** user request — present Experiment 1 per channel within each region
(`proposed_median_<region>_<channel>`), **no region-level aggregation**; surface the Raja
EGI-to-10--20 mapping (`32_ch.csv`, Raja/EGI hardware only; Cao2018 is native 10--20); and
build a script that reproduces every manuscript table/figure from `runs_second_iteration/`.

## The data was already channel-by-channel
Confirmed the Experiment-1 CSV already stores per-channel results: with `selection=='all'`
each row is one `(session, channel_in_group)` with its own `det_precision/recall/f1`. So the
refactor is a pure presentation/extraction change — **no detector re-run**. Per-channel value =
mean over sessions of that channel's `det_f1` at `selection=='all'`, `center_method=='median'`.
Channel→region from `brain_region_{raja,cao2018}.yaml`; EGI→10--20 from `32_ch.csv`.

## Aggregation-artifact correction (important)
The Round-1/2 claim "best single channel **beats** the multi-channel group" was an artifact of
comparing single-channel-bps ($0.837$) against a **diluted pooled-channel** group mean
($0.666$). At a fair (best-channel-per-session) comparison the full-cap montage ($0.882$ Raja,
$0.805$ Cao) slightly **exceeds** the best single channel ($0.868$, $0.795$). Corrected
everywhere to the honest claim: **a single frontopolar electrode is *sufficient* (≈ full-cap,
within ~0.01)**, and the steep within-frontal per-channel gradient (Raja frontal\_left Fp1
$0.862$ → F7 $0.073$) explains why equal-weight fusion adds little.

## Per-channel numbers now used in prose (selection=='all', median)
Raja frontal: Fp2/E9 **0.868**, Fp1/E22 **0.862**, E3 0.801, E23 0.734, F3/E24 0.451,
F4/E124 0.446, F7/E33 0.073. No non-frontal Raja channel > 0.11.
Cao frontal: FP1 **0.795**, FP2 **0.783**, F7 0.596, F3 0.589, F8 0.589, F4 0.574; best
non-frontal FC3 0.438. Hemispheres equal at channel level (Fp1 0.862 vs Fp2 0.868; FP1 0.795
vs FP2 0.783).

## Files
- **New:** `e_result/tab_egi_channel_map.tex` (Table~\ref{tab:egi_map}, from `32_ch.csv`).
- **Refactored (per-channel):** `e_result/tab_exp1_channel_ablation.tex` — now
  channel-by-channel within region with EGI + 10--20 columns, no group rows
  (`regen_paper_tables.py`, backup `*.bak_chrefactor`).
- **Removed:** `e_result/tab_region_performance.tex` (region-aggregate `non-frontal mean` row;
  superseded by the per-channel table). `plot_region_performance.py` now emits only the figure.
- **Narrative (backups `*.bak_chrefactor`):** `e_result/pe1`, `e_result/p011`, the Exp1
  Design/Findings in `result.tex`, discussion `f_discussion/p010` (Para B ref + Para E),
  `f_discussion/p011` (C2 fusion, C3 hemisphere) — all reframed channel-by-channel and corrected.
- **New framework:** `experiment_script/reproduce_manuscript.py` — manifest of 23 data-driven
  artifacts (label → script → source CSV(s) → aggregation); commands `list`, `provenance`,
  `build [--only/--label/--dry-run]`, `custom-example`; importable helpers `load`,
  `best_per_session`, `per_channel`. Legacy non-data-driven floats declared separately.

## Compile status (Round 3)
`pdflatex` ×2 → `biber` → `pdflatex` ×2: **exit 0, 46 pages, 0 undefined citations/references.**
9 overfull \hbox, all pre-existing. Table~11 (EGI map) and Table~12 (per-channel ablation)
render cleanly (p.\ 24--25); per-channel figure and corrected single-channel narrative on
p.\ 29--30. No stale single-channel/group numbers remain in any manuscript paragraph (verified
by grep; old values survive only in `NUMBERS_std30.md`/`VALUE_AUDIT.md` as historical data).
