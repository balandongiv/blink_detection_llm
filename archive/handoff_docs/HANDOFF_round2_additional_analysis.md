

# HANDOFF — Round 2: Additional Analyses, Discussion, and `temp_result_analysis` Verdict

**Prepared:** 2026-06-30
**Prepared by:** claude-opus-4-8 (post-audit orchestrator)
**Prereq reading (in order):** `HANDOFF_std30_academic_writing.md` → `writing/VALUE_AUDIT.md` → `writing/NUMBERS_std30.md`
**Status of the paper:** Round-1 audit complete. `pdflatex writing/main.tex` compiles cleanly (39 pp, no undefined refs/cites). All numbers are frozen at the **best-channel-per-session** aggregation on `runs_second_iteration/` (std=3.0).

This handoff scopes the **next** round: (A) a verdict on whether `temp_result_analysis/` is worth integrating, (B) additional **result** analyses the CSVs still support, (C) additional **discussion** paragraphs worth adding, and (D) a **limitations** section led by the long-blink weakness. Everything below is grounded in the existing `runs_second_iteration/` CSVs — no re-running of the detector is required except where explicitly flagged (R7 timing).

---

## 0. TL;DR

- **`temp_result_analysis/` (exp8.md, nmin.md): mostly SUPERSEDED, do NOT integrate wholesale.** Both files are LLM critiques of *raw, diluted console output*. Their central alarm — the "frontal F1 = 0.3126 vs P=0.901/R=0.791" mismatch and "is single-channel really > frontal group?" — is the **diluted-per-row vs best-channel aggregation** confusion that Round 1 already **resolved** (see `VALUE_AUDIT.md`). The `0.3126` is simply the *first* of the seven per-channel frontal `det_f1` values (a weak channel, E124), never a group score. **Their two real conclusions (single ≥ group; channel choice ≫ nmin) are already in the paper at the correct aggregation.** They do, however, surface **3–4 genuinely new, integrable ideas** (fusion-design future work, hemisphere rebuttal, a timing benchmark, and a "consistent relative decline" framing for long blinks). Cherry-pick those; discard the rest.
- **Six new result analyses are feasible from the existing CSVs** (Section B). The two highest-value are **R1 (precision–recall operating-point scatter)** and **R2 (predicted-vs-ground-truth blink-count agreement)** — R2 directly *validates* the blink-rate/PERCLOS claim in Discussion Para D and is novel.
- **Five new discussion paragraphs** are warranted (Section C), four of which are grounded in the new analyses. The **multi-channel fusion** future-work paragraph (C2) needs no new analysis — it builds directly on the **Experiment 1 region/per-channel ablation** already in the paper.
- **A limitations section is needed (Section D), led by the long-blink weakness** — Proposed-Med misses long eye closures (recall 0.79 vs 0.88 normal; long $F_1$ ~0.5), the root cause is documented, and the repo already has a validated **dual-mode detector** as the future fix. Long blink is the through-line: C5 (systematic decline) → L1 (lead limitation) → L1-future (dedicated long-closure module).
- **Literature positioning (C6): we do NOT yet have any graph or quantitative comparison** to other single-channel/threshold detectors — only narrative lit-review paragraphs. Section C6 specifies how to build one (and the non-comparability caveats).

---

## 1. Current state — what is already done (do not redo)

Result section now contains: strategy comparison (p001/p005), cross-dataset gap (p002), epoch duration (p003), blink-type recall (p004), error structure (p006), per-session variability (p007), channel robustness (p008), channel-selection frequency (p009), channel ablation, **Summary Across Experiments** (`tab_exp_summary`, `fig_exp_boxplot`, `tab_exp_stats`, narratives `pe1–pe8`), **Region & single-channel** (`tab_region_performance`, `fig_region_performance`, p011), **Failure analysis** (`tab_failure_analysis`, p012).
Discussion now contains p001–p009 (revised) + **p010** (seven paragraphs: median-vs-mean, electrode montage, signal-quality, PERCLOS operating point, regional/single-channel, failure-mode QC, boundary tolerance).

So the following are **already covered** and must NOT be re-proposed: single-channel sufficiency, frontal/frontopolar dominance, channel-selection-≫-nmin, long-blink weakness, error-regime balance, epoch-health benefit, failure mechanism.

---

## 2. (A) Verdict on `temp_result_analysis/`

| Claim in temp files | Verdict | Reason / where it already lives |
|---|---|---|
| "Combined-channel output is not interpretable as one group F1"; P/R/F1 mismatch (0.3126 vs harmonic 0.842) | **RESOLVED — do not re-open** | The `0.3126` is the first per-channel `det_f1` of the frontal group, not a group score. Round 1 replaced all diluted per-row means with **best-channel-per-session**; see `VALUE_AUDIT.md §Headline aggregation`. |
| "Single channels outperform the frontal group" | **Already integrated** | `p011`, `tab_region_performance`, Discussion Para E — at correct aggregation (E22 0.837 ≫ fixed frontal\_right group 0.666). |
| "Channel selection matters far more than nmin" | **Already integrated** | `pe1`, `pe5`, `p011`. |
| "Long condition is the clearest reproducible weakness (~40% relative decline both datasets)" | **Partially integrated — ADD framing** | `p004`/`pe8`/Para D report long < normal recall. The *cross-dataset consistency of the relative decline* is a nice robustness framing worth one sentence (see C5). |
| "Left–right asymmetry: frontal\_left 0.831 vs frontal\_right 0.299" | **ARTIFACT — reject** | That 0.299 is again a diluted first-value. At best-channel-per-session the hemispheres are equal: Raja frontal\_left **0.854** vs frontal\_right **0.846** (Δ0.008). Optionally rebut explicitly (R3/C3). |
| "Multi-channel fusion underperforms; design adaptive/weighted fusion" | **Worth ADDING (future work)** | Not yet discussed as a design direction; see C2. |
| "Computational robustness ~2.35 s/session (Raja), 7.45 s (Cao)" | **Worth ADDING but numbers UNVERIFIED** | No timing exists in the CSVs (`summary.json` has no wall-clock). Do **not** cite the temp numbers; run a benchmark (R7) then add C4. |
| "Essential reporting correction: one row per result + aggregation column" | **Already satisfied** | `VALUE_AUDIT.md` + `NUMBERS_std30.md` document the aggregation explicitly. |

**Bottom line:** integrate ~4 *ideas* from these files (C2 fusion, C3 hemisphere, C4 timing, C5 long-decline framing); do not import their tables/conclusions, which were computed on diluted output.

---

## 3. (B) Proposed NEW result analyses (ranked)

All use `runs_second_iteration/` only. "Best-channel-per-session" = argmax `det_f1` over selections per session, then mean — identical to Round 1.

### R1 — Precision–recall operating-point scatter *(high value, trivial)*
- **What:** per-session (precision, recall) scatter for the four conditions; overlay the four condition means and iso-$F_1$ contours.
- **Why:** visualises *why* Proposed-Med wins — it sits in the high-P/high-R corner while BLINKER-concat clusters at high-recall/low-precision and MNE-annot at low/low. Complements `tab_error-structure` with a picture.
- **Data:** exp2 best-channel rows, `det_precision`/`det_recall`.
- **Deliverable:** `experiment_script/plot_pr_operating_points.py` → `writing/figures/fig_pr_scatter.{pdf,png}` + `e_result/fig_pr_scatter.tex` + 2–3 sentence paragraph (extend p001 or new `p013`).

### R2 — Predicted-vs-ground-truth blink-count agreement *(highest value, novel, trivial)*
- **What:** for each session, predicted blink count vs true count, per condition. Predicted $= \mathrm{TP}+\mathrm{FP}$, truth $= \mathrm{TP}+\mathrm{FN}$ (both directly in exp2). Report Pearson/Lin's concordance + a Bland–Altman plot.
- **Why:** **directly validates the blink-rate / PERCLOS usability argument in Discussion Para D** with a count-level (not just event-matching) metric. Expected: BLINKER-concat massively over-counts (ratio ≫1), MNE under-counts, Proposed-Med ≈ 1:1. Verified seed: PM predicted-vs-GT correlation $r=0.886$ on Raja (exp8 `n_predicted` vs `n_gt_total`); the all-condition version is derivable from exp2.
- **Data:** exp2 (`det_tp`,`det_fp`,`det_fn`) for all four conditions; exp8 (`n_predicted`,`n_gt_total`) as a cross-check for Proposed-Med.
- **Deliverable:** `experiment_script/plot_count_agreement.py` → `fig_count_agreement.{pdf,png}` + `tab_count_agreement.tex` (mean predicted/true ratio + correlation per condition) + `p014` paragraph. Feeds Discussion C1.

### R3 — Hemisphere-symmetry check *(quick, rebuts the temp artifact)*
- **What:** frontal_left vs frontal_right best-channel-per-session, both corpora.
- **Why:** rebuts the temp-file "huge asymmetry" claim and supports the montage recommendation (placement need not pick a hemisphere). Seed: Raja 0.854 vs 0.846; compute Cao too.
- **Deliverable:** one row in `tab_region_performance` (or a sentence in p011) + Discussion C3. No figure needed.

### R4 — Within-subject consistency *(easy, robustness)*
- **What:** for subjects with ≥2 sessions, within-subject SD of best-channel $F_1$ and the intraclass correlation (subject vs session variance).
- **Why:** strengthens p007's variability claim — is variance mostly *between* subjects (stable trait) or *within* subject (session noise)? Ties to the signal-quality discussion (Para C).
- **Data:** exp2 PM best-channel rows grouped by `session.split('/')[0]`.
- **Deliverable:** extend `analyse_failure_sessions.py` or a small script; 2 sentences in p007 or new `p015`.

### R5 — Epoch-health: *which* sessions benefit *(easy, ties failure↔health)*
- **What:** correlate the per-session health-effect ($F_1^{on}-F_1^{off}$, exp7) with baseline $F_1$ and GT count.
- **Why:** tests the claim that health filtering helps the *worst/noisiest* sessions most (Round-1 failure analysis showed the over-detection failures were recovered +0.5 by health filtering). A negative correlation (low-$F_1$ sessions gain most) is the expected, publishable result.
- **Data:** exp7 (`use_epoch_health`) joined to exp2 PM best-channel $F_1$.
- **Deliverable:** scatter `fig_health_benefit.{pdf,png}` + 2 sentences appended to Para C or `pe7`.

### R6 — Montage-size vs performance curve *(optional, figure-only)*
- **What:** $F_1$ vs number of channels in the selection (1 → full cap), both corpora.
- **Why:** turns `tab_exp1_channel_ablation` into a one-glance "diminishing returns" figure showing a single channel already captures ~95% of full-cap $F_1$.
- **Deliverable:** `fig_montage_size.{pdf,png}`; optional, only if a figure is wanted.

### R7 — Computational-cost benchmark *(MEDIUM effort — requires a timed run)*
- **What:** wall-clock per session for the full pipeline at 30 s epochs, both corpora, on stated hardware.
- **Why:** converts the existing qualitative "cheap for real-time" claim (p006/p009/Para) into a quantified one. **No timing is stored in the CSVs**, so this needs a dedicated benchmark script (re-run detection on, say, 5 sessions/corpus and time it). Do **not** use the unverified temp-file numbers.
- **Deliverable:** `experiment_script/benchmark_runtime.py` → a small table; feeds Discussion C4. Flag if hardware/runtime reporting is out of scope.

### Out of scope / not recommended
- **Stage-A / epoch-level metrics** (exp4 `stageA_*`, `pct_flagged`, `n_flagged`): **forbidden** by the reporting rule (`feedback_reporting_metrics`: only `det_precision/recall/f1`). Do not surface.
- **Baseline boundary-tolerance comparison** (exp4): exp4 contains Proposed-Med only, so "does PM degrade more gracefully than baselines?" **cannot** be answered — state it as a limitation, do not fabricate a comparison.
- **nmin / long-threshold sweeps beyond what exists:** exp5 already covers nmin {1,2,3,5}; exp8 has a single 0.5 s long threshold — no sweep possible.

---

## 4. (C) Proposed NEW discussion paragraphs

Append to `writing/f_discussion/p010/paragraph.tex` (or a new `p011`), every claim grounded in a recomputed number and ≥1 `\citep{}`.

- **C1 — Count fidelity for blink-rate and PERCLOS (grounded in R2).** The strongest *quantitative* support for Para D: show that Proposed-Med's predicted blink count tracks the true count near 1:1 (corr ≈ 0.89) while BLINKER-concat's count is inflated, so only the balanced detector yields a usable blink-rate input. Cite `zulkarnanie2022enhancements`, `dai2023detection`.
- **C2 — Multi-channel fusion as future work (from temp files), built on the Experiment 1 channel-selection ablation.** This paragraph does **not** need any new analysis — its empirical basis already exists in the paper. Experiment 1 already characterises detection **by region and by individual channel** (`tab_exp1_channel_ablation`, `tab_region_performance`, `fig_region_performance`, paragraphs `pe1`/`p011`): it shows that within the frontal group the per-channel $F_1$ ranges widely (Raja E22 0.837 / E9 0.834 down to E33 0.055; Cao FP1 0.777 down to F4 0.490), and that the best **fixed** multi-channel group (frontal\_right 0.666 Raja, frontal\_left 0.661 Cao) sits well below the best single channel. **Cite these existing results explicitly** as the reason fusion currently underperforms: a fixed montage that gives equal weight to strong frontopolar and weak/peripheral frontal electrodes dilutes the blink evidence. Then frame the constructive future direction — an **adaptive, channel-quality-weighted or robust-median fusion with a small inter-channel timing tolerance**, which could exploit the redundancy the ablation reveals (E22≈E9) without the dilution of unweighted averaging, and so potentially exceed single-channel performance. Constructive future work, not a present claim. Cite `plochl2012combining` (multi-channel artifact structure) + one spatial-filtering/ICA blink reference; cross-reference Discussion Para E and the Experiment 1 ablation tables.
- **C3 — Hemisphere-agnostic placement (grounded in R3).** Left and right frontopolar montages perform equally (Δ≈0.01), so the minimal-montage recommendation (Para B) does not depend on hemisphere — any frontopolar electrode of either side suffices. Explicitly correct the apparent asymmetry as an aggregation artefact. Cite `croft2000removal`.
- **C4 — Computational cost & real-time feasibility (grounded in R7, only if benchmarked).** Replace the qualitative "lightweight" wording with measured per-session time, supporting deployment on in-vehicle / wearable hardware. Cite a real-time fatigue-monitoring reference (`alyan2023blink` or `berka2007eeg`).
- **C5 — Long-blink decline is systematic and cross-corpus (extends Para D).** One sentence: the relative drop from normal to long-blink recall is consistent across both corpora (~0.09 absolute on both), so it is a property of the detector's morphology assumptions rather than a dataset effect — reinforcing long-blink recall as the priority target. Cite the exp8 result.

### C6 — Positioning vs the broader single-channel threshold-detector literature

**Do we already have a graph or detailed analysis for this? NO.** This is currently a gap. Audited state:
- `writing/c_literature_review/` contains only narrative paragraphs (`p001`, `p002`) — no quantitative head-to-head.
- There is **no comparison table or figure** anywhere in `writing/` that places our $F_1$ against other detectors' reported $F_1$; the only numeric tables compare *our four conditions* to each other (`tab_exp1_main`, etc.), all on our own data.
- `writing/deep-research-report.md` and `references_from_csv.bib` (≈40+ blink/EOG detector papers, e.g. `chang2016detection`, `tran2021detection`, `valderrama2018automatic`, `agarwal2019blink`, `wang2025sliding`) hold the raw material but their reported metrics have **not** been extracted into a comparable form.

**Why it is only partly comparable (state as a caveat, do not over-claim).** Reported numbers across that literature use different datasets, blink definitions, sampling rates, and especially different matching criteria (sample-level vs event-level; our event-level IoU matters — see `tab_boundary_tolerance`, where $F_1$ ranges from 0.93 at loose to 0.26 at strict overlap). A raw $F_1$-vs-$F_1$ ranking would therefore be misleading.

**Proposed deliverable (do this for C6):**
1. `experiment_script/build_literature_comparison.py` → `writing/c_literature_review/tab_literature_comparison.tex`: one row per prior single-channel / threshold-based blink or EOG detector, with columns *Method · Signal/Channel · Dataset · Matching criterion · Reported metric (value)* and a final row for **this work** (best-channel $F_1$ 0.84 Raja / 0.78 Cao at event-level IoU 0.1–0.2). Extract values **only** from papers already in `references_from_csv.bib`; mark non-comparable cells "n/r".
2. Optional figure `fig_literature_positioning.{pdf,png}`: a 1-D strip/forest plot of reported $F_1$ with our result highlighted and a footnote on non-comparability.
3. A discussion paragraph that positions our result *qualitatively* ("competitive with reported single-channel threshold detectors while being evaluated under a strict event-level criterion and validated on two driving corpora") rather than asserting a numeric win.

**Risk/feasibility:** medium — the bottleneck is faithfully extracting and labelling each prior metric. Include a row only when the source paper states a metric you can cite; otherwise omit. Do not invent or estimate numbers.

---

## 5. (D) Limitations of this study — long-blink is the priority

Round-1 discussion `p008` lists generic limitations. Round 2 should **promote the long eye-closure weakness to the headline limitation** and add a dedicated future-work paragraph, then consolidate the rest.

### L1 — Long eye-closure detection is the primary limitation *(lead with this)*
- **Evidence (existing CSVs):** Proposed-Med long-blink recall **0.7868** pooled vs **0.8814** normal (`p004`/`pe8`/exp8); long-blink $F_1$ collapses to ~**0.54** (Raja) / **0.46** (Cao) because the rare long events are swamped by false positives. The decline is **systematic and cross-corpus** (~0.09 absolute on both — see C5), i.e. a property of the detector, not a dataset effect.
- **Root cause is known and documented** in `writing/long_blink_detection_report.md`: the normal-blink morphology filters (FitBlinks shape filter, width-outlier rejection, pAVR velocity filter) are tuned for 100–400 ms reflex blinks and actively reject sustained ≥0.5 s closures.
- **Why it matters:** long closures are the core constituent of **PERCLOS**, the regulatory-grade drowsiness measure — so this limitation bears directly on the paper's fatigue-monitoring motivation. Frame it honestly: a strong overall $F_1$ partly masks this, because normal blinks dominate the event count (~91%).

### L1-future — Dedicated long-closure module *(the future investigation requested)*
- The repo already **prototyped and validated the fix**: a **dual-mode detector** = existing pipeline for normal blinks + a parallel sustained-**suppression/plateau** module ("Module B") for long closures, merged into one event stream (`long_blink_detection_report.md §6`; validated at long recall ≈ 0.72, **+16.6 pp** over the 0.55 single-mode baseline — see project memory).
- The future-work paragraph should: (a) attribute the gap to the morphology assumption; (b) point to a suppression-hold/plateau-detection module merged with the normal-blink output (target: long recall ≥ 0.80, long $F_1$ ≥ 0.70); (c) position it as the natural next step toward PERCLOS-grade scoring. **Do not** present dual-mode results as part of *this* paper — it is a separate contribution; reference it only as the planned extension.
- **Optional supporting analysis (grounded, no re-run):** within `blink_category=='long'`, decompose the misses — how much of the long-blink `det_fn` is long closures *entirely undetected* vs *split/merged* into shorter events — to substantiate the morphology-assumption claim from the current exp8 data.

### L2–L6 — consolidate the remaining limitations
- **L2** Two driving corpora only (Raja, Cao2018); other paradigms/devices/populations untested.
- **L3** Single-channel, amplitude-threshold design: no spatial or waveform-morphology information; fixed multi-channel fusion is not yet beneficial — and the Experiment 1 region/per-channel ablation explains *why* (ties to **C2**).
- **L4** No baseline boundary-tolerance comparison: exp4 ran Proposed-Med only, so the graceful-degradation claim (`pe4`) cannot be contrasted against baselines — state plainly rather than implying superiority.
- **L5** Ground-truth dependence: a few sessions carry atypical blink counts (failure analysis `p012`) and annotations are dataset-specific.
- **L6** No deep-learning benchmark (already in `p008`/`p009`; keep).

**Deliverable:** fold L1 + L1-future into the discussion (extend `p008` or add a limitations paragraph + a future-work paragraph), optionally add the split-vs-undetected long-blink decomposition. Long blink is the through-line connecting **C5** (systematic decline) → **L1** (headline limitation) → **L1-future** (dual-mode extension).

---

## 6. Constraints (unchanged from Round 1 — re-stated)

- Report **only** `det_precision`/`det_recall`/`det_f1`; **never** Stage A, `stageA_*`, `pct_flagged`, or any epoch-level metric.
- **Never** name internal parameters (std_threshold, k, MAD multiplier) in the prose.
- **Never** modify `runs/`; never print `bot_telegram.md`.
- Use **best-channel-per-session** for every headline/comparison number, identical across conditions, so new numbers stay consistent with `NUMBERS_std30.md`. Recompute, don't copy stale values.
- `\citep{}` only; third person past tense in results, present permitted in discussion.
- Run scripts in the `double_threshold_algo` conda env.
- Back up any edited existing file to `*.bak_r2` before overwriting; log every change in `writing/VALUE_AUDIT.md` under a new "Round 2" section.

---

## 7. Definition of Done (Round 2)

**Analyses (pick the high-value ones first: R1, R2, R3; R4–R6 optional; R7 only if runtime reporting is in scope):**
- [ ] `experiment_script/plot_pr_operating_points.py` → `fig_pr_scatter.{pdf,png}` + wrapper (R1)
- [ ] `experiment_script/plot_count_agreement.py` → `fig_count_agreement.*` + `tab_count_agreement.tex` (R2)
- [ ] Hemisphere row/sentence (R3); within-subject + health-benefit if pursued (R4/R5)
- [ ] New result paragraphs (`p013`/`p014`/…) wired into `result.tex`
- [ ] (C6) `experiment_script/build_literature_comparison.py` → `c_literature_review/tab_literature_comparison.tex` (+ optional `fig_literature_positioning.*`) — **note: no such graph/table exists yet**; build only from papers already in `references_from_csv.bib`

**Discussion & limitations:**
- [ ] C1–C3 + C5 appended (C4 only with a real benchmark); C6 positioning paragraph; ≥1 `\citep` each, grounded in recomputed numbers
- [ ] (D) Limitations: long-blink promoted to lead limitation (L1) + dedicated long-closure future-work paragraph (L1-future, referencing `long_blink_detection_report.md` / dual-mode detector); L2–L6 consolidated. Optional long-blink split-vs-undetected decomposition.

**Integrate & compile:**
- [ ] `result.tex` / `discussion.tex` updated; `pdflatex` (×2) + `biber` compiles with no undefined refs
- [ ] `VALUE_AUDIT.md` Round-2 section lists every new number, file, and the R3 artefact correction

**Verification seeds already computed (cross-check against these):**
- R2: Proposed-Med predicted-vs-GT correlation = **0.886** (Raja, exp8).
- R3: Raja frontal_left = **0.8536**, frontal_right = **0.8459** (best-channel-per-session) — no real asymmetry.
- Hemisphere/region/headline numbers: see `writing/NUMBERS_std30.md`.

---

*Generated 2026-06-30 from the audited std=3.0 results. Round 1 deliverables and the frozen numbers are the authority; this round only adds, it does not revise the Round-1 conclusions.*
