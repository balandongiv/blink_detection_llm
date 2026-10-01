# Response to Reviewers

Below we address each deduplicated issue raised in the two audit reports.
All changes are marked with `\rev{...}` (red text) in the manuscript.
No new experiments were conducted; every issue was addressed through
correction, clarification, disclosure, or narrowing of claims.

---

## I01 — Epoch screening not isolated as cause (NARROW)

**Concern:** The manuscript attributed the F1 advantage to epoch screening,
but the proposed and baseline configurations differ in calibration pool,
centre estimator (median/MAD vs mean/SD), sensitivity multiplier (k=3.0
vs k=1.5), and multichannel gating.

**Action:** All causal language was rewritten to configuration-level
comparisons. Phrases such as "the improvement came from epoch screening"
were replaced with "the proposed configuration achieved higher F1 than
the examined baselines." The abstract, introduction, results, discussion,
and conclusion now consistently frame the comparison at the configuration
level and note that a matched ablation would be needed to isolate the
contribution of epoch screening. A controlled ablation was added to
future work (Section IV-C).

**Files changed:** abstract.tex, p005/paragraph.tex, exp3/par1.tex,
exp3/par4.tex, d3_main_implication/paragraph.tex,
d5_limitations/paragraph.tex, d6_future/paragraph.tex, g_conclusion/p1.tex

---

## I02 — Oracle best-channel disclosure (DISCLOSE)

**Concern:** The headline F1 scores use a retrospective best-channel-per-session
rule that requires reference labels and is not deployable.

**Action:** The abstract now states "under a retrospective
best-channel-per-session (oracle) protocol." Table I caption discloses
the oracle. Exp3 par2 adds a full paragraph explaining that the oracle
rule does not simulate prospective, label-free channel selection and
that the same oracle was applied to every condition. The limitations
paragraph reiterates this disclosure.

**Files changed:** abstract.tex, exp3/par2.tex, exp3/tab_f1_significance.tex,
d5_limitations/paragraph.tex

---

## I03 — Session counts (FIX)

**Concern:** The text reported 62 Cao2018 sessions and 108 total, but
only 58 and 104 were analysed.

**Action:** The dataset section now reads "108 available recording sessions,
of which 104 were analysed" and "58 sessions marked as complete and excluded
four sessions with incomplete annotations."

**Files changed:** d_method/material/dataset.tex

---

## I04 — BLINKER comparator scope (FIX)

**Concern:** The manuscript named the baseline "BLINKER" without
clarifying that only the initial threshold-crossing stage was used,
not the full published pipeline (morphological fitting, channel selection).

**Action:** Every occurrence was changed to "BLINKER-style" or
"BLINKER-style initial-threshold baseline (threshold-crossing stage only)."
The exp3 par2 now contains a dedicated paragraph explaining that the
morphological fitting and automatic channel selection steps were not used.

**Files changed:** abstract.tex, p007/paragraph.tex, exp3/par1–par4.tex,
exp3/tab_f1_significance.tex, exp3/sec.tex, d3_main_implication/paragraph.tex,
d5_limitations/paragraph.tex, g_conclusion/p1.tex

---

## I05 — Sensitivity multiplier k=3.0 undisclosed (DISCLOSE)

**Concern:** The manuscript did not report the specific sensitivity
multiplier or how it was selected.

**Action:** Section II-B now states: "In the present study, k=3.0 was
used for the proposed configurations. This value was selected by a sweep
over candidate values on the evaluation corpora (see Section IV for
discussion of this limitation). The BLINKER-style baseline used a
different threshold rule with k=1.5." The limitations paragraph
notes the asymmetry and absence of a held-out development set.

**Files changed:** d_method/step2_get_threshold_candidates.tex,
d5_limitations/paragraph.tex

---

## I06 — MNE event-to-interval conversion (DISCLOSE)

**Concern:** The manuscript did not describe how MNE's point events
were converted to blink intervals.

**Action:** Exp3 par2 now documents that `find_eog_events` internally
applies a 1-10 Hz band-pass filter, returns point events (peak sample
indices), and each event was converted to an interval by extending
+/-100 ms around the detected peak, yielding fixed 200 ms predicted
blink windows.

**Files changed:** e_result/exp3/par2.tex

---

## I07 — Participant counts and session independence (DISCLOSE)

**Concern:** The number of participants was not reported, and sessions
from the same participant were treated as independent.

**Action:** The dataset section now reports 17 Internal participants
and 27 Cao2018 participants. Table I caption includes participant
counts. The statistical methods section notes that multiple sessions from
the same participant were treated as independent observations and
references this as a limitation. The limitations paragraph discusses
the need for participant-clustered or mixed-effects analyses.

**Files changed:** d_method/material/dataset.tex,
d_method/material/eval_stat.tex, exp3/tab_f1_significance.tex,
d5_limitations/paragraph.tex

---

## I08 — Dilution mechanism language (FIX)

**Concern:** The threshold-dilution mechanism was stated as established
fact rather than hypothesis.

**Action:** All dilution language now uses "consistent with, but does
not prove" or "hypothesised mechanism" phrasing. The introduction
(p005) uses "We hypothesised that" rather than asserting the mechanism.
Results par4 explicitly states: "The recall bias of the BLINKER-style
baseline is consistent with, but does not prove, the hypothesised
pooled-threshold mechanism."

**Files changed:** p005/paragraph.tex, exp3/par1.tex, exp3/par4.tex,
d3_main_implication/paragraph.tex

---

## I09 — Channel mapping E83/E84 (DISCLOSE)

**Concern:** The Internal montage mapping contained a P5/P8 labelling
inconsistency and an E84/E83 error.

**Action:** The dataset section now discloses the EGI-to-10-20 mapping
for the five electrodes of interest and notes: "An earlier version of
the configuration assigned O2 to sensor E84 rather than the correct E83;
this was identified and corrected." The limitations paragraph notes that
the error could have influenced epoch selection in earlier analyses.

**Files changed:** d_method/material/dataset.tex,
d5_limitations/paragraph.tex

---

## I10 — Exact p-values (FIX)

**Concern:** The text promised exact p-values in an appendix but did
not deliver them.

**Action:** The promise of an appendix table was removed. P-values are
reported inline as "adjusted p < 0.05."

**Files changed:** Verified no remaining promise of exact p-values in
active text.

---

## I11 — Nonsignificance and equivalence (NARROW)

**Concern:** Nonsignificant differences were interpreted as evidence of
equivalence for single-electrode performance.

**Action:** The conclusion now reads "showed smallest reduction relative
to full-montage performance, although formal equivalence was not tested."

**Files changed:** g_conclusion/p1.tex

---

## I12 — "Adaptive" wording (FIX)

**Concern:** "Adaptive" implied per-epoch thresholds, when the pipeline
estimates one threshold per session from selected epochs.

**Action:** Changed to "Epoching enables candidate-pool selection" in
the pipeline overview. Removed the misleading "makes thresholds adaptive"
phrasing.

**Files changed:** d_method/m_pipeline_overview.tex

---

## I13 — Ground-truth modality difference (DISCLOSE)

**Concern:** Internal labels used synchronised video + eye-aspect-ratio,
while Cao2018 labels relied on EEG morphology alone.

**Action:** The limitations paragraph now explicitly states: "The
Internal labels were anchored to synchronised video and the
eye-aspect-ratio signal, whereas the Cao2018 labels relied on EEG
morphology alone; this difference in annotation modality limits the
comparability of absolute scores across the two corpora."

**Files changed:** d5_limitations/paragraph.tex

---

## I14 — Candidate epochs not shown to be blink-enriched (NARROW)

**Concern:** Stage A selects epochs with high peak-to-peak amplitude,
but no analysis confirmed these are specifically blink-enriched rather
than artefact-enriched.

**Action:** The limitations paragraph notes: "The blink-enrichment of
candidate epochs selected by Stage A was not quantified, so the extent
to which the selected pool is specific to blink-related activity, as
opposed to other high-amplitude artefacts, remains unestablished."

**Files changed:** d5_limitations/paragraph.tex

---

## I15 — Stage C specification (DISCLOSE)

**Concern:** The blink-extraction stage lacked sufficient detail for
reproduction.

**Action:** Section II-C now specifies: positive-polarity crossings,
minimum duration of 50 ms, no merging of adjacent events, epoch-boundary
truncation, and all-epoch fallback when no candidate epochs are selected.

**Files changed:** d_method/step3_get_blink_regions.tex

---

## I16 — IoU >= 0.1 justification (JUSTIFY)

**Concern:** The IoU threshold of 0.1 is permissive compared to
object-detection standards.

**Action:** The evaluation metrics section now justifies the choice:
"chosen to ensure event-level correspondence while accommodating onset
and offset variability." A stricter threshold sweep is noted implicitly
as possible future work.

**Files changed:** d_method/material/eval_metric.tex

---

## I17 — MNE internal filtering (DISCLOSE)

**Concern:** It was unclear whether MNE applied additional internal
filtering to the already-filtered input signal.

**Action:** Exp3 par2 now documents that `find_eog_events` "internally
applies a 1-10 Hz band-pass filter to the input signal." The call
arguments (l_freq=1.0, h_freq=20.0 for preprocessing; default threshold)
were verified from code.

**Files changed:** e_result/exp3/par2.tex

---

## I18 — Missing uncertainty in headline table (NARROW)

**Concern:** Table I reported only mean F1 without any measure of
dispersion.

**Action:** Standard deviations were computed from existing result
CSVs and added to Table I. Internal Proposed: 88.25 +/- 10.10,
BLINKER-style: 76.54 +/- 20.10, MNE: 66.64 +/- 35.98; Cao2018
Proposed: 80.68 +/- 13.04, BLINKER-style: 69.40 +/- 19.39,
MNE: 56.27 +/- 32.45.

**Files changed:** exp3/tab_f1_significance.tex

---

## I19 — "Naturalistic driving" (FIX)

**Concern:** Both corpora are simulated (lane-keeping) tasks, not
naturalistic driving.

**Action:** The title, abstract, keywords, and all body text were
changed from "naturalistic driving" to "simulated driving" or
"simulated-driving."

**Files changed:** main.tex (title, keywords), abstract.tex, dataset.tex

---

## I20 — Ethics/consent (DISCLOSE)

**Concern:** No ethics committee approval or consent statement was
provided.

**Action:** The dataset section now includes a paragraph stating:
UTP Research Ethics Committee approval for the Internal dataset,
written informed consent from all participants, and that Cao2018
is distributed under a CC BY 4.0 licence.

**Files changed:** d_method/material/dataset.tex

---

## I21 — BLINKER formula misattribution (NARROW)

**Concern:** The manuscript incorrectly attributed the MAD-based formula
to BLINKER, when BLINKER's initial detection stage uses mean + 1.5 SD.

**Action:** Section II-B now correctly states: "differs from the
initial-detection threshold of [BLINKER], which uses the arithmetic
mean plus 1.5 standard deviations."

**Files changed:** d_method/step2_get_threshold_candidates.tex

---

## I22 — Grammar and typos (FIX)

**Concern:** Several grammatical errors ("which is removes",
"from each of the channel's", "marphological", "which can be express").

**Action:** All identified errors were fixed in the respective files.

**Files changed:** d_method/m_pipeline_overview.tex,
d_method/step1_select_bad_epoch.tex, d_method/step2_get_threshold_candidates.tex

---

## I23 — Preprocessing order (DISCLOSE)

**Concern:** The code implements epoching before per-epoch filtering
and resampling, contradicting the continuous-first description in
Section II.

**Action:** The pipeline overview now discloses: "In the present
implementation, epoching precedes per-epoch filtering..." The
limitations paragraph notes this may introduce duration-dependent
edge effects.

**Files changed:** d_method/m_pipeline_overview.tex,
d5_limitations/paragraph.tex

---

## I24 — Median-vs-mean ablation nonsignificant (DISCLOSE)

**Concern:** The Proposed-Mean vs Proposed-Med comparison was
nonsignificant but not discussed.

**Action:** The limitations paragraph notes: "The median-versus-mean
Stage B comparison (Proposed-Mean versus Proposed-approach) yielded
nonsignificant differences on both corpora, consistent with the centre
estimator not being the primary driver of the performance advantage."

**Files changed:** d5_limitations/paragraph.tex

---

## I25 — Empty repository (DECLINE)

**Concern:** The repository link leads to an empty repo.

**Action:** The introduction now reads: "intend to release...repository
will be populated upon acceptance." This is a release task, not a
manuscript content issue.

**Files changed:** b_intro/p007/paragraph.tex

---

## I26 — "Among the first" novelty claim (NARROW)

**Concern:** The priority claim is unsupported.

**Action:** Replaced with "evaluate a candidate-epoch-conditioned
composition" without any priority claim.

**Files changed:** b_intro/p007/paragraph.tex

---

## I27 — Hardware-independence claim (NARROW)

**Concern:** Consistent ranking across two corpora does not establish
hardware independence, because the corpora also differ in population,
task details, and annotation modality.

**Action:** The discussion now states: "hardware effects cannot be
separated from other corpus differences." The conclusion reads:
"restricted to two simulated-driving corpora...cannot isolate hardware
effects from other corpus differences."

**Files changed:** d3_main_implication/paragraph.tex, g_conclusion/p1.tex

---

## I28 — Intro roadmap paragraph (FIX)

**Concern:** The final paragraph of the introduction contained
boilerplate describing BLINKER's structure rather than this paper's.

**Action:** Replaced with a correct four-section roadmap: "Section II
describes...Section III presents...Section IV discusses...Section V
concludes."

**Files changed:** b_intro/p008/paragraph.tex
