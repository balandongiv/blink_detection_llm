# HANDOFF — Experiments 1–8: Academic Writing Task

**Prepared:** 2026-06-29  
**Status:** ALL EXPERIMENTS COMPLETE — ALL PASS  
**Prepared for:** A more capable agent (claude-opus-4-8 or claude-fable-5) to produce academic writing

---

## ⚠️ 0. CRITICAL: STALE VALUES — RE-VERIFY EVERYTHING AGAINST THE CSVs

**The existing `writing/e_result/` and `writing/f_discussion/` paragraphs were written against an OLDER run and contain OUTDATED numbers. Do not trust them. Do not trust the numbers in Section 2 of this handoff either — they were computed with a flawed pooled-all-channels aggregation and are misleading.**

The **only source of truth is the CSV output** in `runs_second_iteration/` (and `runs/` for baseline comparison). Before writing or revising any sentence that contains a number:

1. **Recompute the number yourself** from the relevant `*_results.csv` using the aggregation rules in §3.
2. **Cross-check** every numeric claim already present in `writing/e_result/p001`–`p009` and `writing/f_discussion/p001`–`p009`. If a value disagrees with your recomputation, the paragraph is wrong — **revise it** with the correct value and adjust the surrounding interpretation if the conclusion changes.
3. **Aggregation matters.** Never report a single F1 pooled over *all* channels/selections — that mixes strong frontal channels with near-zero occipital channels and yields a meaningless ~0.19 number. Use **best-channel-per-session** for headline figures and **per-channel / per-region** breakdowns for detail (see §3 and §5.1e).
4. Keep a short **changelog** (`writing/VALUE_AUDIT.md`) listing every old→new value you corrected, with the CSV path and the recomputed figure, so the change is auditable.

**This re-verification is the first task, before any new writing.** Spawn subagents to parallelise it (see §8).

---

## 1. Context

Seven ablation experiments (exp1–exp5, exp7, exp8; exp6 is the ablation source and is excluded from reporting) have been run and validated on two naturalistic driving-EEG corpora: **Raja** (46 sessions, 128-ch HydroCel GSN) and **Cao2018** (58 sessions, standard 10-20 montage with FP1/FP2). Every experiment passed validation on both datasets.

Results are in `runs_second_iteration/`.  
Baseline comparison results are in `runs/` — **read-only, do not modify**.  
Conda environment: `double_threshold_algo`.

---

## 2. Experiment Results Summary (Proposed-Med, both datasets)

> ⚠️ **DO NOT COPY THESE NUMBERS INTO THE PAPER.** The table below is **pooled over all channels/selections** and is therefore diluted and wrong as a performance figure. It is kept only to show the *direction* (new run ≥ baseline). The correct, paper-ready numbers are the **best-channel-per-session** and **per-region** figures in §5.1(e). Recompute from the CSVs before writing anything.

The four competing conditions in exp2 (Proposed-Med, Proposed-Mean, BLINKER-concat, MNE-annot), **pooled over all selections — DILUTED, illustrative only:**

| Condition      | Raja macro-F1 | Raja micro-F1 | Cao2018 macro-F1 | Cao2018 micro-F1 |
|----------------|---------------|---------------|------------------|------------------|
| Proposed-Med   | ~0.62 ⚠️       | ~0.68 ⚠️       | ~0.66 ⚠️          | ~0.71 ⚠️          |
| Proposed-Mean  | ~0.61 ⚠️       | ~0.66 ⚠️       | ~0.64 ⚠️          | ~0.69 ⚠️          |
| BLINKER-concat | ~0.64 ⚠️       | ~0.72 ⚠️       | ~0.66 ⚠️          | ~0.71 ⚠️          |
| MNE-annot      | ~0.40 ⚠️       | ~0.51 ⚠️       | ~0.29 ⚠️          | ~0.37 ⚠️          |

**Correct best-channel-per-session figures (Proposed-Med, verified from CSVs):**

| Dataset | macro-F1 (new run) | macro-F1 (baseline) |
|---------|--------------------|---------------------|
| Raja    | 0.86–0.89          | 0.84–0.87           |
| Cao2018 | 0.80–0.82          | 0.76–0.80           |

The agent **must** recompute the full four-condition × two-dataset table at the correct (best-channel-per-session) aggregation. The diluted table above must never reach the manuscript.

> **Known open discrepancy to resolve:** the *existing* paper text (`writing/e_result/p002`) reports Cao2018 Proposed-Med = 0.8954, but neither `runs/` nor `runs_second_iteration/` reproduces this with single-channel selection (oracle best-channel upper bound ≈ 0.80–0.82). This gap exists in the baseline too, so it is **not** a regression. The agent must determine which aggregation/run produced 0.8954 (check `tutorial/`, `runs/reports/`, and the table-generation scripts) and either reproduce it from the current CSVs or correct the paper value. Flag the resolution in `writing/VALUE_AUDIT.md`.

---

## 3. Data Files

```
blink_detection_llm/
├── runs/                               ← baseline results (READ-ONLY)
│   ├── exp1_channel_raja/
│   │   ├── sessions/*.csv              (46 session CSVs)
│   │   └── exp1_channel_selection_raja_results.csv
│   ├── exp1_channel_cao/ … exp8_cao/   (same structure per experiment)
│
└── runs_second_iteration/              ← new validated results
    ├── exp1_channel_raja/  (46 sessions ✅)
    ├── exp1_channel_cao/   (58 sessions ✅)
    ├── exp2_raja/  exp2_cao/   ✅
    ├── exp3_raja/  exp3_cao/   ✅
    ├── exp4_raja/  exp4_cao/   ✅
    ├── exp5_raja/  exp5_cao/   ✅
    ├── exp7_raja/  exp7_cao/   ✅
    └── exp8_raja/  exp8_cao/   ✅
```

### CSV column schema

```
dataset, session, selection, rule, center_method, channel_in_group,
condition, n_channels_used, n_valid,
det_tp, det_fp, det_fn, det_precision, det_recall, det_f1
```

Additional columns per experiment:
- **exp3**: `epoch_duration_s` (10, 20, 30, 40, 50, 60, 120 s)
- **exp4**: `iou_threshold` (0.0, 0.1, 0.2, 0.3, 0.5)
- **exp5**: `min_flagged_epochs`
- **exp7**: `use_epoch_health` (True / False)
- **exp8**: `long_threshold_s`, `blink_category` (all / normal / long), `n_gt_total`, `n_gt_normal`, `n_gt_long`

### Filtering for Proposed-Med

- **exp1**: `center_method == "median"`
- **exp2**: `condition == "Proposed-Med"`
- **exp3–exp7**: `center_method == "median"`
- **exp8**: `center_method == "median"`, use `blink_category` column to split normal vs long blinks

---

## 4. Existing Paper Structure

```
writing/
├── main.tex                           ← root; compile with pdflatex
├── e_result/
│   ├── result.tex                     ← \section{Experiments and Results}
│   ├── p001/ … p009/paragraph.tex    ← existing result paragraphs
│   └── tab_*.tex                      ← existing tables
└── f_discussion/
    ├── discussion.tex                 ← \section{Discussion}
    └── p001/ … p009/paragraph.tex    ← existing discussion paragraphs
```

**Read these files for style and context before writing:**

| File | What to learn from it |
|------|-----------------------|
| `writing/b_intro/p007/paragraph.tex` | Contributions framing — epoch-aware pipeline, median/MAD estimator, cross-corpus benchmark |
| `writing/e_result/p001/paragraph.tex` | Results paragraph style (tense, citation style, metric naming) |
| `writing/e_result/tab_comparison_30s_epoch.tex` | Main comparison table style |
| `writing/f_discussion/p001/paragraph.tex` | Discussion style — Proposed-Med vs baselines framing |
| `writing/f_discussion/p002/paragraph.tex` | Median/MAD vs mean argument already started |
| `writing/f_discussion/p003/paragraph.tex` | Channel-selection findings |

The paper uses `\citep{}` (natbib author-year). Do **not** use `\cite{}`.

---

## 5. Your Task

### 5.1 Results Section — `writing/e_result/`

#### (a) Experiment-by-experiment narrative paragraphs

For **each experiment** (exp1 through exp8, skipping exp6), create `writing/e_result/pEXP/paragraph.tex` or append to existing ones if they exist. Each paragraph should cover:

- What the experiment tests and why it matters for epoch-based blink detection
- The key finding (which condition wins, by how much, on which dataset)
- Whether the pattern is consistent across Raja and Cao2018
- One sentence on the practical implication for driving-fatigue EEG studies

Do **not** frame any finding as a parameter sensitivity study or reference internal parameter values. Write as if the reader only sees the experiment design and the detection outcomes.

#### (b) Summary comparison table

Create `writing/e_result/tab_exp_summary.tex`:
- Rows: exp1–exp5, exp7, exp8
- Columns: Experiment | Description | Proposed-Med macro-F1 (Raja) | Proposed-Med macro-F1 (Cao2018) | Best competing method | Δ vs best competitor
- Caption: "Proposed-Med detection performance across all ablation experiments on the Raja and Cao2018 driving-EEG corpora. Macro-averaged $F_1$ over all sessions."

#### (c) Box plot figure

Create `experiment_script/plot_exp_boxplot.py` that:
- Reads session-level `det_f1` from `runs_second_iteration/` for Proposed-Med across all experiments
- Produces one figure with two panels (Raja / Cao2018)
- In each panel: grouped box plot, x-axis = experiment (exp1–exp5, exp7, exp8), one box per experiment coloured by dataset
- Also overlays BLINKER-concat and MNE-annot boxes from exp2 as horizontal reference lines or a separate inset
- Uses `matplotlib` + `seaborn`; saves to `writing/figures/fig_exp_boxplot.pdf` and `.png`

Create `writing/e_result/fig_exp_boxplot.tex` (LaTeX wrapper with `\caption{}` and `\label{fig:exp_boxplot}`).

#### (d) Statistical analysis table

Create `writing/e_result/tab_exp_stats.tex`:
- For each experiment × dataset: Wilcoxon signed-rank test comparing Proposed-Med vs the best competing method from exp2 (BLINKER-concat), W-statistic, p-value (Bonferroni-corrected across 14 pairs), effect size r (rank-biserial), 95% bootstrap CI on Δ macro-F1
- Use `scipy.stats.wilcoxon` with `alternative="greater"`

#### (e) Regional / best-channel analysis (NEW — required)

This is a distinct results subsection on **where on the scalp the detector works and whether it can run on a single channel**. It uses exp1 (channel ablation) and exp2 (per-selection results). Aggregate at the **selection-group** level, NOT pooled across all channels.

**IMPORTANT aggregation note:** Do not report a single number pooled over all channels — that mixes strong frontal channels with near-zero occipital/parietal channels and produces a meaningless ~0.19 average. Report **per-channel** and **per-region** figures, and use **best-channel-per-session** for any single headline number.

**Verified numbers (Proposed-Med, `runs_second_iteration/`):**

Per single channel (one row per session, n = sessions):

| Dataset | Channel | Region | Precision | Recall | macro-F1 |
|---------|---------|--------|-----------|--------|----------|
| Raja    | E22     | frontopolar | 0.88 | 0.84 | **0.84** |
| Raja    | E9      | frontopolar | 0.88 | 0.84 | **0.83** |
| Raja    | E3      | frontal     | 0.88 | 0.70 | 0.75 |
| Raja    | E23     | frontal     | 0.82 | 0.63 | 0.68 |
| Cao2018 | FP1     | frontopolar | 0.76 | 0.84 | **0.78** |
| Cao2018 | FP2     | frontopolar | 0.76 | 0.81 | 0.76 |
| Cao2018 | F7/F8/F3/F4 | frontal | ~0.55 | ~0.55 | 0.54–0.57 |

Best-channel-per-session (the headline aggregation):

| Dataset | macro-F1 (single best frontal channel) |
|---------|----------------------------------------|
| Raja    | 0.86–0.89 |
| Cao2018 | 0.80–0.82 |

Single-channel vs multi-channel group (Proposed-Med, new run):

| Dataset | Best single channel | Best multi-channel group | 
|---------|--------------------|--------------------------|
| Raja    | single:E22 = 0.84  | frontal_right = 0.67     |
| Cao2018 | single:FP1 = 0.78  | frontal_left = 0.66      |

Channel sensitivity (frontal vs non-frontal, Raja exp1): best frontal channel ≈ 0.85; non-frontal channels (e.g. E28, E122) ≈ 0.08–0.10; occipital/parietal ≈ 0. There is a steep drop outside the frontal/frontopolar region.

**What to write (create `writing/e_result/p011/paragraph.tex`):**

1. **Region matters strongly.** Detection F1 is high only over frontal/frontopolar sites (E22/E9 on Raja, FP1/FP2 on Cao2018) and falls sharply away from the frontal region. This is anatomically expected — blink artefact amplitude is largest at frontopolar electrodes.
2. **The two corpora converge on the same region** despite different montages (HydroCel 128 vs 10-20), with E22/E9 anatomically matching FP1/FP2.
3. **Single-channel operation is sufficient and in fact optimal.** The best single frontopolar channel (0.84 Raja, 0.78 Cao2018) outperforms every multi-channel group aggregation. Combining channels does not improve detection; the detector does not need a dense montage.
4. **Within the frontal region the detector is stable** — the top 2 frontopolar channels are close in F1 (E22 0.84 vs E9 0.83; FP1 0.78 vs FP2 0.76), so the exact electrode choice within frontopolar sites is not critical.

Create `writing/e_result/tab_region_performance.tex` with the per-channel/per-region table above (booktabs). Caption: "Per-channel and per-region detection performance of Proposed-Med on the Raja and Cao2018 corpora. Single frontopolar channels achieve the best $F_1$; performance degrades sharply outside the frontal region."

Optionally add a **topographic / bar figure** in `plot_exp_boxplot.py` (or a second script `plot_region_performance.py`): a bar chart of macro-F1 per channel grouped by region, one panel per dataset, to visualise the frontal concentration.

#### (f) Extra analysis — per-subject / per-session failure analysis (NEW — required)

Some subjects perform far worse than others, and the existing paper (p007) reports a per-session F1 range of 0.077–1.000. **The agent must investigate WHY the worst sessions fail** — this is original analysis, not just reporting.

**Confirmed starting point (verified from `runs_second_iteration/exp2_raja`, Proposed-Med, single channels):**

Raja **S16** (`S16/S29_20190111_034326_3`) is the worst session. Even on its best channel (E9), it has det_tp=80, det_fp=8, **det_fn=1742** → F1≈0.084. A second run of the same subject (`...034326_2`) reaches F1≈0.59 on E22. The defining feature is a **massive false-negative count** (~1,700–2,000 missed events) with very few false positives — i.e., extreme under-detection, not over-detection.

**Hypotheses the agent should test against the data:**
1. **Ground-truth count mismatch** — is the GT blink count for this session abnormally high (e.g., annotation artefact, mislabeled events)? Compare `det_tp + det_fn` (= number of GT blinks) for S16 against the per-session distribution. If S16 has 1,800 "blinks" where a typical session has ~150, the ground truth is suspect.
2. **Low blink amplitude / flat signal** — load the raw session and check whether the frontopolar amplitude is unusually low (so the threshold is never crossed). Use the pipeline's own threshold output.
3. **Signal quality / artefact** — is the session flagged by the epoch-health filter (exp7)? Does excluding bad epochs change S16's result?
4. **Channel availability** — does S16 have its frontal channels intact?

**What to produce:**
- A script `experiment_script/analyse_failure_sessions.py` that ranks all sessions by F1, isolates the bottom 5 (both datasets), and reports for each: GT blink count, TP/FP/FN, best channel, mean frontopolar amplitude, and epoch-health flag.
- A results table `writing/e_result/tab_failure_analysis.tex` (note: a file of this name already exists in `writing/e_result/obs/` — read it, it may be stale; produce a corrected version).
- A short results paragraph `writing/e_result/p012/paragraph.tex` explaining the failure mechanism (likely: a small number of sessions with anomalous ground truth or degraded signal, not a systematic algorithm failure), and stating what fraction of sessions are affected.

This analysis directly supports the discussion argument in Para C (signal quality drives variability) — but the agent must **confirm the mechanism from the data**, not assume it.

#### (g) Discover additional result sections worth adding

Beyond (a)–(f), the agent should **scan the CSV outputs for other findings worth a dedicated results paragraph** that are not yet covered by p001–p012. Candidates to evaluate (include only if the data supports a clear finding):

- **exp4 boundary-tolerance**: how does F1 degrade as the IoU matching threshold tightens (0.0 → 0.5)? Does Proposed-Med degrade more gracefully than baselines? (This tests temporal localisation accuracy, not just detection.)
- **exp5 n_min sensitivity**: is there an optimal minimum-flagged-epochs value, and is the method robust to it?
- **Precision–recall operating curves** per condition (the four conditions sit at very different P/R points — a P/R scatter would visualise the trade-off cleanly).
- **Per-subject (not per-session) aggregation**: subjects with multiple sessions — is performance consistent within subject?
- Any other pattern the agent finds while auditing the CSVs.

For each finding the agent decides to include, create a `pNNN/paragraph.tex` + supporting table/figure, and list it in `writing/VALUE_AUDIT.md` under "new sections added".

### 5.2 Discussion Section — `writing/f_discussion/`

**Before writing, read all of the following — they are already written but might contain old values and must be revised and rewrite:**

| File | What it covers (do not repeat) |
|------|-------------------------------|
| `writing/f_discussion/p001/paragraph.tex` | Epoch-aware threshold beats naive baselines (headline claim) |
| `writing/f_discussion/p002/paragraph.tex` | Stage A concentrates estimation on suspicious epochs; median/MAD resists peak contamination (starter text — build on it) |
| `writing/f_discussion/p003/paragraph.tex` | Channel selection → frontal montage sufficient; proposed variants choose same channel |
| `writing/f_discussion/p004/paragraph.tex` | Cross-dataset gap −0.065 for Proposed-Med vs −0.229 for MNE |
| `writing/f_discussion/p005/paragraph.tex` | Error structure (FP-heavy vs FN-heavy); long blinks residual weakness |
| `writing/f_discussion/p006/paragraph.tex` | Epoch duration stable; computationally cheap; two-corpus limitation |
| `writing/f_discussion/p007/paragraph.tex` | First study to account for epoch structure in threshold estimation |
| `writing/f_discussion/p008/paragraph.tex` | Full limitations paragraph |
| `writing/f_discussion/p009/paragraph.tex` | Why thresholding rather than deep learning |
| `writing/b_intro/p007/paragraph.tex` | Stated contributions: epoch-aware pipeline, three-stage design, median/MAD vs mean, driving-corpus benchmark |

Also read `writing/e_result/p001/paragraph.tex` through `p009/paragraph.tex` for the numbers that the discussion should cite back to.

Create `writing/f_discussion/p010/paragraph.tex` containing **five new paragraphs** covering the five gaps listed below. Each gap is not discussed in p001–p009.

---

#### New Para A — Median vs mean: the implementation-level mechanism (expand p002)

**Key technical fact from the implementation** (`pyblinker/blinker/get_blink_positions.py`, `compute_robust_threshold`):

Both Proposed-Mean and Proposed-Med use **identical dispersion estimation**: `dispersion = 1.4826 × MAD(samples)`. The 1.4826 factor is the normal-distribution consistency constant, exactly matching MATLAB BLINKER's convention. The **only** difference between the two proposed variants is the center estimate:

- Proposed-Mean: `threshold = mean(samples) + k × dispersion`
- Proposed-Med:  `threshold = median(samples) + k × dispersion`

BLINKER-concat's `_compute_basic_statistics` function is a direct alias of the mean path (`center_method="mean"`) — so BLINKER and Proposed-Mean share the same threshold formula applied to different input data (concatenated full session vs suspicious-epoch pool from Stage A).

The blink-detection argument: suspicious-epoch amplitude samples are **right-skewed** — they contain large positive peaks from actual blink events plus a baseline of lower values. The arithmetic mean is sensitive to these peaks; even a handful of high-amplitude samples pulls the mean upward. The median, sitting at the 50th percentile, is unaffected. Because `mean > median` in a right-skewed distribution, `threshold_mean > threshold_median` for the same input. A higher threshold means smaller blinks that sit between the two thresholds are detected by Proposed-Med but missed by Proposed-Mean — explaining the consistent recall advantage of Proposed-Med (recall: Proposed-Med 0.8682, Proposed-Mean 0.8436; p001) with negligible precision change.

This is not a claim about MAD being better than standard deviation (both methods use MAD). It is a claim about the median being a more stable center for a right-skewed amplitude distribution than the mean.

Cite: Rousseeuw & Croux (1993) "Alternatives to the median absolute deviation" — MAD as a robust scale estimator; Leys et al. (2013) "Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median"; any text on the effect of skewness on the mean; Kleifges et al. (2017) \citep{kleifges2017blinker} for the BLINKER convention that the 1.4826 scaling factor replicates.

Do **not** repeat the Stage A filtering argument already made in p002 — this paragraph is specifically about why median wins over mean *within Stage B*, given the same pool of samples from Stage A.

---

#### New Para B — Recommended electrode configuration for driving-fatigue EEG

**Key result from exp1 (p009):** On Raja (128-ch), E9 (48.9%) and E22 (39.7%) dominated; on Cao2018, FP1 (62.1%) and FP2 (30.6%) dominated. Selection concentrated on at most two channels in each corpus.

E9 and E22 in the HydroCel 128 GSN correspond anatomically to frontopolar/inferior-frontal positions, closely matching FP1 and FP2 in the standard 10-20 system. Both datasets therefore independently converge on the same anatomical region despite different electrode systems.

**Practical recommendation to state:** A minimal two-electrode frontopolar montage (FP1 and FP2, or their dense-array equivalents) is sufficient for reliable threshold-based blink detection in naturalistic driving EEG. This has direct implications for study design: researchers do not need a full 128-channel or 32-channel cap to obtain reliable blink metrics; a lightweight frontal headband with two electrodes would suffice. This lowers the hardware burden significantly for ambulatory or long-duration driving studies.

Connect to the finding in p003 (existing discussion) that both proposed variants chose the same channel in 91.3% (Raja) and 84.5% (Cao2018) of sessions — showing the channel recommendation is stable across methods, not an artefact of any single detection strategy.

Cite: papers on minimal EEG montages for fatigue detection (Berka et al. 2007; Lal & Craig 2001; Lin et al. 2010 or equivalent); any paper showing FP1/FP2 frontopolar channels are the dominant blink artefact site (e.g., the BLINKER paper itself).

---

#### New Para C — Session variability, epoch health, and signal quality as performance drivers

**Key results from two experiments:**
- p007 (result): per-session F1 ranged 0.077–1.000 for Proposed-Med, median 0.913. The worst session (Raja S16/S29, F1=0.077); best (Cao2018 S53, F1=1.000). Subject-level range: worst subject mean 0.211 (Raja S16), best 0.993 (Cao2018 S55).
- exp7 (result): using the epoch-health filter (excluding corrupted/noisy epochs from Stage A) improved macro-F1 by approximately +0.054 on Raja and +0.069 on Cao2018.

**Argument to make:** The high session-level variability is not primarily a failure of the detection algorithm — it reflects genuine variation in signal quality across driving sessions. The epoch-health filter result shows that when corrupted epochs are identified and excluded *before* threshold estimation, performance improves substantially, strongly suggesting that low-quality recordings are the primary driver of the worst-performing sessions (the 0.077 outlier is consistent with severe artefact contamination rather than a fundamental algorithmic failure). Stated differently: the pipeline is close to optimal on clean recordings (F1=1.0), and its weakest-session performance reflects input data quality rather than detector design.

This has a practical implication for driving studies: session-level QC (identifying and flagging corrupted epochs before analysis) is not optional — it is necessary for reliable blink-rate estimation. The epoch-health filter provides an automatic first pass, but researchers should additionally inspect sessions with outlier F1 profiles.

Cite: literature on EEG signal quality in ambulatory/driving paradigms; autoreject (Jas et al. 2017) or similar automated epoch rejection methods; Bigdely-Shamlo et al. (2015) PREP pipeline.

---

#### New Para D — Operating-point suitability for PERCLOS and blink-rate-based fatigue scoring

**Key result from the error-structure analysis (p006 result):** Mean per-session FP:FN ratios: BLINKER-concat 17.1, MNE-annot 0.50, Proposed-Mean 0.31, Proposed-Med 0.44.

**Argument to make:** In driving-fatigue research, the primary derived metrics from blink detection are blink rate (blinks per minute), mean blink duration, and PERCLOS (percentage of time eyelid is ≥80% closed over a defined interval). All three depend on correct blink-event identification. A detector with FP:FN=17.1 (BLINKER-concat) produces blink-rate estimates in which genuine blinks are outnumbered 17:1 by false detections — the blink rate estimate is dominated by noise and cannot be used for fatigue scoring. Conversely, a FN-heavy detector (Proposed-Med, FP:FN=0.44) produces a blink rate that is slightly underestimated: approximately 56% of the error events are missed real blinks rather than phantom detections. Slight underestimation of blink rate corresponds to a conservative fatigue estimate — it will under-report drowsiness rather than trigger false alarms. For safety-critical applications where false fatigue alarms carry operational cost (e.g., unnecessary vehicle stops), a conservative false-negative-heavy profile is preferable to a false-positive-heavy one.

Furthermore, exp8 shows that Proposed-Med's recall for long blinks (0.823) is lower than for normal blinks (0.855). Long blinks (duration > threshold) are the primary component of PERCLOS and are the strongest single predictor of drowsiness. The gap between normal-blink and long-blink recall (0.032) represents a residual weakness: PERCLOS computed from Proposed-Med will be slightly more underestimated than blink rate alone. This suggests future work should focus on improving long-blink recall specifically, rather than overall F1.

Cite: PERCLOS definition (Wierwille & Ellsworth 1994; Dinges et al. 1998); blink rate as fatigue indicator (Ingre et al. 2006; Schleicher et al. 2008); blink duration and drowsiness (Zhao et al. 2012 or equivalent); the exp8 long-blink result from p004 in the paper.

---

#### New Para E — Regional sensitivity and single-channel operation

This paragraph interprets the regional results from §5.1(e). It is distinct from Para B: Para B recommends *which* electrode to use; Para E discusses *how sensitive* the detector is to that choice and whether it can run on one channel. Do not duplicate Para B's montage recommendation — cross-reference it.

**Key results (Proposed-Med, `runs_second_iteration/`):**
- Best single frontopolar channel: Raja single:E22 = 0.84, Cao2018 single:FP1 = 0.78.
- Best single channel **exceeds** every multi-channel group aggregation (Raja best group frontal_right = 0.67; Cao2018 best group frontal_left = 0.66).
- Within the frontopolar region the top two channels are close (E22 0.84 vs E9 0.83; FP1 0.78 vs FP2 0.76).
- Outside the frontal region, F1 collapses (non-frontal Raja channels ≈ 0.08–0.10; occipital/parietal ≈ 0).

**Argument to make:**

1. **The detector is a genuine single-channel method, and single-channel operation is optimal — not a compromise.** Because the pipeline detects on one amplitude trace at a time, combining channels into a group does not help; the best single frontopolar channel outperforms any group average. This is an important and perhaps counter-intuitive point: unlike spatial-filter or ICA-based blink methods that exploit multi-channel covariance, this amplitude-threshold detector needs only one well-placed electrode. This is what makes it attractive for low-channel-count wearable and in-vehicle EEG.

2. **Region sensitivity is high but the frontal optimum is broad.** Performance is strongly localised to frontal/frontopolar sites — there is a steep drop outside that region — so electrode placement matters. However, *within* the frontopolar region the detector is robust: the choice between the top two frontopolar electrodes changes F1 by only ~0.01–0.02. The practical reading is that placement must be frontal, but does not need to be sub-millimetre precise; any frontopolar electrode will do.

3. **Cross-corpus convergence strengthens the regional claim.** Both corpora independently localise the optimum to the same anatomical region (E22/E9 ≈ FP1/FP2) despite different montages, indicating the frontal concentration is a property of the blink artefact's scalp topography rather than of either dataset's hardware. This connects to the well-established frontopolar dominance of the eye-blink electrooculographic field.

4. **Implication for deployment.** A single frontopolar channel is sufficient for fatigue-relevant blink metrics, removing the need for dense montages, spatial filtering, or per-session channel re-selection — provided the electrode is placed frontally. This complements the minimal-montage recommendation in Para B and the computational-cost argument in the existing p006/p009.

Cite: literature on frontopolar topography of the blink/EOG field (Croft & Barry 2000 \citep{croft2000removal}; Plöchl et al. 2012 or equivalent); single-channel EEG for blink/fatigue (Lin et al. 2010; Berka et al. 2007 or equivalent); cross-reference the BLINKER single-channel design \citep{kleifges2017blinker}.

---

#### Discover additional discussion paragraphs worth adding

After writing Paras A–E and revising the existing p001–p009, the agent should **identify any further discussion points the data now supports** that are not yet covered. Candidates to evaluate:

- **Failure-mode discussion** grounded in §5.1(f): if the worst sessions fail due to anomalous ground truth or degraded signal (rather than algorithm error), this belongs in the discussion as a characterisation of *when the method should not be trusted* and a recommendation for pre-analysis QC. Tie to the limitations paragraph (p008) but make it a constructive, mechanism-based point.
- **Boundary-tolerance / temporal-precision discussion** grounded in exp4: if Proposed-Med localises blink onsets/offsets more precisely than baselines, discuss the implication for blink-duration and PERCLOS estimation (which depend on accurate boundaries, not just detection).
- **Comparison to the broader blink/EOG-detection literature**: position the achieved F1 against other reported single-channel threshold detectors, if comparable numbers exist.

For each, add a paragraph to `writing/f_discussion/p010/paragraph.tex` (or a new `pNNN`) and log it in `writing/VALUE_AUDIT.md`. Every discussion claim must be (a) grounded in a recomputed CSV number and (b) supported by at least one academic citation.

---

## 6. Technical Notes

### Python — reading data

```python
import pandas as pd
from pathlib import Path

REPO_ROOT = Path("C:/Users/balan/IdeaProjects/blink_detection_llm")

# Example: exp2 Raja, Proposed-Med sessions
df = pd.read_csv(REPO_ROOT / "runs_second_iteration/exp2_raja/exp2_strategy_comparison_raja_results.csv")
pm = df[df["condition"] == "Proposed-Med"]          # exp2
# For exp1/exp3/exp7: df[df["center_method"] == "median"]
# For exp8: df[(df["center_method"] == "median") & (df["blink_category"] == "all")]

# Baseline (for comparison):
df_base = pd.read_csv(REPO_ROOT / "runs/exp2_raja/exp2_strategy_comparison_raja_results.csv")
```

### Python — Wilcoxon test

```python
from scipy import stats
import numpy as np

new_f1  = pm_new["det_f1"].values
base_f1 = pm_base["det_f1"].values
w, p = stats.wilcoxon(new_f1, base_f1, alternative="greater")
n = len(new_f1)
r = 1 - (2 * w) / (n * (n + 1))   # rank-biserial correlation

# Bootstrap CI on Δ macro-F1
rng = np.random.default_rng(42)
deltas = new_f1 - base_f1
boot = [rng.choice(deltas, size=len(deltas), replace=True).mean() for _ in range(10_000)]
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
```

### Environment

```bash
conda activate double_threshold_algo
# numpy, pandas, scipy, matplotlib, seaborn all available
```

### LaTeX figure directory

```
writing/figures/          ← create if not exists; reference as \includegraphics{figures/fig_name}
```

### Appending to result.tex

At the end of `writing/e_result/result.tex`, append:
```latex
\subsection{Summary Across Experiments}
\label{sec:exp_summary}
\input{e_result/tab_exp_summary}
\input{e_result/fig_exp_boxplot}
\input{e_result/tab_exp_stats}
\input{e_result/pEXP/paragraph}   % one per experiment

\subsection{Performance by Region and Single-Channel Operation}
\label{sec:region_performance}
\input{e_result/tab_region_performance}
\input{e_result/p011/paragraph}
% optional: \input{e_result/fig_region_performance}
```

### Appending to discussion.tex

At the end of `writing/f_discussion/discussion.tex`, append:
```latex
\input{f_discussion/p010/paragraph}
```

---

## 7. Definition of Done

**Phase 0 — Audit (do first):**
- [ ] `writing/VALUE_AUDIT.md` created — every old→new value corrected, with CSV path + recomputed figure
- [ ] All numeric claims in `writing/e_result/p001`–`p009` and `writing/f_discussion/p001`–`p009` re-verified against CSVs; stale ones revised (with `*.bak_preaudit` backups)
- [ ] Cao2018 = 0.8954 discrepancy resolved or flagged in VALUE_AUDIT.md

**Phase 1 — Results:**
- [ ] `writing/e_result/tab_exp_summary.tex` — summary table at **correct (best-channel-per-session)** aggregation
- [ ] `experiment_script/plot_exp_boxplot.py` — runs without error in `double_threshold_algo` env
- [ ] `writing/figures/fig_exp_boxplot.pdf` + `.png` — figure files present
- [ ] `writing/e_result/fig_exp_boxplot.tex` — LaTeX wrapper with caption and label
- [ ] `writing/e_result/tab_exp_stats.tex` — Wilcoxon + effect size + bootstrap CI table
- [ ] `writing/e_result/p010/paragraph.tex` (or per-experiment files) — results narrative
- [ ] `writing/e_result/tab_region_performance.tex` + `writing/e_result/p011/paragraph.tex` — regional / single-channel
- [ ] `experiment_script/analyse_failure_sessions.py` + `writing/e_result/tab_failure_analysis.tex` + `writing/e_result/p012/paragraph.tex` — failure analysis (Raja S16 etc.)
- [ ] (optional) `plot_region_performance.py` + `fig_region_performance.*`; any additional discovered result sections (§5.1g)

**Phase 2 — Discussion:**
- [ ] `writing/f_discussion/p010/paragraph.tex` — **five** paragraphs (median-vs-mean, electrode recommendation, signal-quality, PERCLOS operating point, regional/single-channel) + any discovered paragraphs, ≥6 academic citations, all `\citep{}`

**Phase 3 — Integrate & compile:**
- [ ] `writing/e_result/result.tex` — new subsection blocks appended (summary + region + failure + any discovered)
- [ ] `writing/f_discussion/discussion.tex` — new `\input{}` appended
- [ ] `pdflatex writing/main.tex` compiles without errors (run twice for cross-references)

---

## 8. Parallelisation — spawn multiple subagents

This is a large task with independent parts. **Spawn subagents to work in parallel** rather than doing everything serially. Suggested decomposition (each subagent gets a focused brief and writes its own files so there are no write conflicts):

| Subagent | Scope | Outputs (no overlap with others) |
|----------|-------|----------------------------------|
| **A — Value auditor** | Recompute every number in p001–p009 (both sections) from CSVs; resolve the Cao2018 0.8954 discrepancy | `writing/VALUE_AUDIT.md`, revised p001–p009 (with `.bak_preaudit`) |
| **B — Core results + stats** | exp1–exp8 summary table, box plot, Wilcoxon/effect-size/bootstrap stats | `tab_exp_summary.tex`, `plot_exp_boxplot.py`, `fig_exp_boxplot.*`, `tab_exp_stats.tex`, `p010/` |
| **C — Region + single-channel** | §5.1(e): per-channel/region table, single-vs-group, optional bar figure | `tab_region_performance.tex`, `p011/`, `plot_region_performance.py` |
| **D — Failure analysis** | §5.1(f): rank worst sessions, test hypotheses for Raja S16 etc. | `analyse_failure_sessions.py`, `tab_failure_analysis.tex`, `p012/` |
| **E — Discussion** | §5.2: five+ discussion paragraphs grounded in the recomputed numbers from A–D | `f_discussion/p010/` |

**Coordination rules:**
- **A must finish first** (or at least publish `VALUE_AUDIT.md`) — B, C, D, E depend on verified numbers. Run A, then fan out B/C/D in parallel, then E (which consumes B/C/D outputs), then the integration/compile phase last.
- Each subagent reads only the CSVs in `runs_second_iteration/` (and `runs/` for baseline) and writes only its assigned files — **no two subagents write the same file**.
- `result.tex` / `discussion.tex` `\input{}` integration and the final `pdflatex` compile are done **once, by the orchestrator**, after all subagents report back — not by individual subagents (avoids merge conflicts).
- Every subagent must report, in its final message, the exact numbers it computed and the files it created, so the orchestrator can assemble VALUE_AUDIT.md and verify consistency.

Use the Agent tool with `subagent_type: general-purpose` for each, giving each the relevant section of this handoff plus its row from the table above.

---

## 9. Constraints

- **Never mention internal parameter names** (std_threshold, k=3.0, MAD multiplier value) in the academic writing — these are implementation details, not findings
- **Never print or log** the contents of `bot_telegram.md`
- **Never modify** files in `runs/` (read-only baseline)
- **You MAY and MUST revise** existing `writing/e_result/p001/`–`p009/` and `writing/f_discussion/p001/`–`p009/` where they contain stale numbers — but first copy the original to `*.bak_preaudit` so the change is reversible, and log every old→new value in `writing/VALUE_AUDIT.md`. Do not delete content; correct it.
- Use `\citep{}` throughout — natbib author-year style
- Use third person, past tense in the results section; present tense permitted in discussion for claims
- Run all Python scripts inside `conda activate double_threshold_algo`

---

*Generated 2026-06-29 from validated experiment runs (orch5/orch6).*
