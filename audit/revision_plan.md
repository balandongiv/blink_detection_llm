# Revision Plan

**Constraint:** NO new experiments. All issues addressed through correction,
clarification, disclosure, or narrowing of claims using only existing results
and code.

**Source reports:**
- Report 1 (R1): `audit/Epoch_Aware_Blink_Manuscript_Findings.md` (F01–F22)
- Report 2 (R2): `audit/main_adversarial_peer_review.md` (A01–A22)

---

## Deduplicated Issue List

| ID | Source(s) | Category | Summary | Action |
|----|-----------|----------|---------|--------|
| I01 | F01, A01 | NARROW | Epoch screening not isolated as cause of improvement; confounded with centre, k, gate | Rewrite causal claims as configuration-level; add to Limitations |
| I02 | F02, A02 | DISCLOSE | Headline F1 uses oracle best-channel-per-session | Strengthen oracle disclosure in Abstract + Table I caption |
| I03 | F03, A07 | FIX | Session counts: 62 vs 58 Cao; 104 vs 108 total | Fix text: 58 analysed + 4 excluded (incomplete) |
| I04 | F04, A05 | FIX | BLINKER comparator misnamed; only threshold stage used | Rename to "BLINKER-style" consistently; clarify scope |
| I05 | F05, A06 | DISCLOSE | k=3.0 not reported; selection via same-suite sweep | Disclose k=3.0, sweep, and note as limitation |
| I06 | F06, A11 | DISCLOSE | MNE event-to-interval conversion undescribed | Document ±100 ms half-window |
| I07 | F07, A08 | DISCLOSE | Session pairing; Internal participant count missing | Disclose 17 Internal / 27 Cao participants |
| I08 | F08 | FIX | Threshold dilution described inconsistently | Use "consistent with" language |
| I09 | F09, A03 | DISCLOSE | Channel mapping: P5/P8/E83/E84 inconsistency | Disclose mapping and E84 error; note as limitation |
| I10 | F10 | FIX | Exact p-values promised but absent | Remove promise; report p-values inline |
| I11 | F11, A14 | NARROW | Nonsignificance ≠ equivalence for single-electrode | Soften to trade-off language |
| I12 | F12 | FIX | "Adaptive" wording implies per-epoch thresholds | Correct to "session-specific, candidate-conditioned" |
| I13 | F13, A09 | DISCLOSE | Ground-truth modalities differ between corpora | Strengthen cross-corpus caveat |
| I14 | F14, A12 | NARROW | Candidate epochs not shown to be blink-enriched | Note as limitation |
| I15 | F15, A13 | DISCLOSE | Stage C insufficiently specified | Add >50 ms, positive polarity, no merging |
| I16 | F16, A10 | JUSTIFY | IoU ≥ 0.1 permissive | Justify as event-level; note stricter as future work |
| I17 | F17, A11 | DISCLOSE | MNE effective filtering uncertain | Document call arguments and version |
| I18 | F18, A14 | NARROW | Missing uncertainty in headline table | Add SD if available; note missing CIs as limitation |
| I19 | F19, A19 | FIX | "Naturalistic driving" overstates simulated tasks | Change to "simulated driving" throughout |
| I20 | F20, A17 | DISCLOSE | Ethics/consent/participant count missing | Add ethics and consent statements |
| I21 | F21, A20 | NARROW | Citation/novelty issues | Fix BLINKER misattribution; soften novelty |
| I22 | F22, A13 | FIX | Grammar/typo errors | Fix all identified errors |
| I23 | A04 | DISCLOSE | Preprocessing order: code epochs before filtering | Disclose actual order; note as limitation |
| I24 | A15 | DISCLOSE | Nonsignificant median-vs-mean ablation omitted | Note in Limitations |
| I25 | A16 | DECLINE | Empty repository | Release task, not manuscript revision |
| I26 | A18 | NARROW | "Among the first" novelty claim | Remove priority claim |
| I27 | A22 | NARROW | Hardware-independence claim | Restrict to "consistent ranking" |
| I28 | — | FIX | Intro p008 contains BLINKER boilerplate | Rewrite roadmap paragraph |

---

## Actions by File

### `writing/IEEE-TJ-color-latex-template/main.tex`
- I19: Title → "simulated driving"
- Add `\rev` command to preamble

### `writing/a_abstract/abstract.tex`
- I02: Add oracle qualifier
- I04: BLINKER-style naming
- I19: "simulated driving"

### `writing/b_intro/p005/paragraph.tex`
- I08: Soften dilution mechanism to hypothesis

### `writing/b_intro/p007/paragraph.tex`
- I04: BLINKER-style naming
- I21: Fix BLINKER formula misattribution
- I26: Remove "among the first" claim

### `writing/b_intro/p008/paragraph.tex`
- I28: Rewrite roadmap paragraph

### `writing/d_method/m_pipeline_overview.tex`
- I12: Fix "adaptive" wording
- I22: Fix "which is removes"
- I23: Disclose actual preprocessing order

### `writing/d_method/step1_select_bad_epoch.tex`
- I22: Fix "from each of the channel's", duplicated sentence

### `writing/d_method/step2_get_threshold_candidates.tex`
- I05: Disclose k=3.0
- I22: Fix "which can be express"

### `writing/d_method/step3_get_blink_regions.tex`
- I15: Add Stage C specification details

### `writing/d_method/material/dataset.tex`
- I03: Fix session counts
- I07: Add participant counts
- I09: Channel mapping disclosure
- I19: "simulated driving"
- I20: Ethics/consent

### `writing/d_method/material/eval_metric.tex`
- I16: Justify IoU ≥ 0.1

### `writing/d_method/material/eval_stat.tex`
- I07: Note session-as-unit limitation

### `writing/e_result/exp3/par1.tex`
- I04: BLINKER-style naming
- I08: Soften dilution language

### `writing/e_result/exp3/par2.tex`
- I04: BLINKER-style naming
- I06: MNE event-to-interval ±100 ms disclosure
- I17: MNE internal 1–10 Hz bandpass disclosure

### `writing/e_result/exp3/par3.tex`
- I04: BLINKER-style naming

### `writing/e_result/exp3/par4.tex`
- I04: BLINKER-style naming
- I01: Remove causal attribution

### `writing/e_result/exp3/sec.tex`
- I04: BLINKER-style in figure caption
- I02: Oracle qualifier in figure caption

### `writing/e_result/exp3/tab_f1_significance.tex`
- I04: BLINKER-style naming
- I18: Add SD values
- I02: Oracle disclosure in caption
- I07: Participant counts in caption

### `writing/f_discussion/d3_main_implication/paragraph.tex`
- I01: Configuration-level language
- I04: BLINKER-style naming
- I27: Restrict hardware claim

### `writing/f_discussion/d5_limitations/paragraph.tex`
- I01, I05, I07, I09, I13, I14, I23, I24: Expand limitations

### `writing/f_discussion/d6_future/paragraph.tex`
- I01: Add ablation as future work

### `writing/g_conclusion/p1.tex`
- I01: Remove causal attribution
- I11: Soften single-electrode claims
- I19: "simulated driving" context
- I27: Restrict hardware claim

### `writing/IEEE-TJ-color-latex-template/main.tex` (keywords)
- I19: "simulated driving" keyword
