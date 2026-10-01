# Findings from inspection of the epoch-aware EEG blink manuscript

**Manuscript:** Epoch-Aware Threshold Estimation for Blink Detection in Naturalistic Driving EEG  
**Version reviewed:** main(20261001-095450).pdf, 15 pages  
**Review date:** 1 October 2026  
**Report type:** Preliminary scientific and editorial findings from manuscript inspection, with targeted primary-source checks.

## Scope and evidence limits

This report documents findings from reading the attached manuscript, examining its equations and numerical tables, inspecting selected rendered pages, and checking relevant official sources. Page numbers below refer to the PDF, whose printed numbering is the same.

This is not the completed 14-specialist audit described in the separate audit prompt. The repository, raw EEG, event predictions, annotation files, subject identifiers, and statistical outputs were not audited or executed. Bibliographic metadata, sentence-by-sentence citation support, and the full novelty literature have not been exhaustively verified. No performance score or p-value was independently reproduced.

“Confirmed” means the reporting inconsistency or stated procedure is visible in the PDF. It does not establish that the underlying data or implementation are wrong. Missing reporting is distinguished from a procedure demonstrably not performed. No Critical issue is established by the evidence available here.

## Overall assessment

The manuscript reports a promising offline detector evaluated on two driving corpora, with useful comparisons of full-montage, regional, and single-electrode operation. Its main scientific vulnerability is attribution: the reported comparison does not isolate candidate-epoch screening from other detector differences. The claim that screening is the principal cause of improvement therefore exceeds the evidence presented.

The headline scores also use a reference-label-dependent best-channel rule for each session. They describe an oracle benchmark rather than the performance of a prespecified channel or a deployable channel-selection policy. This does not make the reported numbers false, but their meaning needs to be explicit in the abstract and conclusions.

Several reporting inconsistencies can be corrected immediately. Others require checking code or existing result files before deciding whether new analysis is necessary.

## Prioritized findings

| ID | Severity | Evidence status | Finding | Main action |
|---|---|---|---|---|
| F01 | Major | Supported concern | The comparison does not isolate epoch screening as the cause of improvement | Controlled S = B versus S = E ablation, or narrower attribution |
| F02 | Major | Confirmed procedure; bias magnitude unverified | Headline results choose the highest-F1 channel using reference labels in each session | Report fixed-channel results and disclose oracle selection |
| F03 | Major | Confirmed reporting inconsistency | 62 public sessions, 46 Internal sessions, and 104 total do not reconcile; figures report 58 public sessions | Provide actual inclusion counts by experiment |
| F04 | Major | Confirmed restricted baseline | BLINKER comparison omits morphology fitting and automatic channel selection | Name the adaptation accurately and limit superiority claims |
| F05 | Major | Confirmed missing reporting | Numerical k and its selection procedure are not specified | Recover settings from actual experiment configurations |
| F06 | Major | Confirmed missing reporting | MNE peak events are scored as intervals without a described conversion | Specify the conversion and inspect fairness |
| F07 | Major | Supported concern | Session pairing does not establish independence across participants or recording segments | Recover subject/session mapping and check inference |
| F08 | Moderate | Confirmed wording conflict | Threshold dilution is described as producing opposing detection effects | Align mechanism claims and test them directly |
| F09 | Moderate | Confirmed inconsistency | Internal channel list uses P5, results use P8, and plots use E83 | Reconcile channel mappings against actual inputs |
| F10 | Moderate | Confirmed reporting error | Text promises exact adjusted p-values absent from appendix tables | Add p-value columns or correct the text |
| F11 | Moderate | Supported interpretation concern | Nonsignificant reductions do not establish equivalent reduced-channel performance | Report paired uncertainty and avoid equivalence language |
| F12 | Moderate | Confirmed implementation ambiguity | Epoching is described as local adaptation, although Stage B pools selected epochs | Explain the actual level of adaptation |
| F13 | Moderate | Confirmed limitation | Two corpora use different annotation modalities and onset/offset definitions | Interpret cross-corpus comparisons cautiously |
| F14 | Moderate | Supported concern | High-amplitude candidate selection is not shown to be blink-specific | Quantify candidate-epoch enrichment and artifacts |
| F15 | Moderate | Confirmed missing reporting | Stage C duration, polarity, merging, and boundary rules are unspecified | Complete the detector definition |
| F16 | Moderate | Confirmed limitation | IoU ≥ 0.1 demonstrates permissive overlap matching, not precise timing | Add sensitivity and timing-error analyses if timing is claimed |
| F17 | Moderate | Supported concern | Shared external filtering may not equal shared effective filtering | Inspect MNE filter arguments and software version |
| F18 | Moderate | Confirmed missing uncertainty | Headline table reports means and stars without dispersion or effect uncertainty | Add variability and paired effect estimates |
| F19 | Moderate | Supported scope concern | Naturalistic driving terminology requires clarification for simulator data | Clarify the setting in title and abstract |
| F20 | Moderate | Confirmed reporting gap | Internal participant count and ethics/consent statements are not reported in this PDF | Add verifiable study information |
| F21 | Moderate | Incomplete verification | Reference details and claim support require systematic checking | Complete the separate citation and novelty audits |
| F22 | Minor | Confirmed editorial issues | Broken sentences, typographical errors, and terminology inconsistencies | Correct wording after scientific revisions |

## Detailed evidence and recommended corrections

### F01. Epoch screening is not isolated as the source of improvement

**Location:** Strategy Comparison, pp. 9–10; Conclusion, p. 11.  
**Confidence:** High that the presented experiments do not isolate the component; the true component effect remains unknown.

The proposed method uses a median-based robust threshold estimated from selected epochs. The comparison methods have different threshold rules and implementations. Experiment 1 changes channel inputs, Experiment 2 changes epoch duration, and Experiment 3 compares different methods. None is a same-detector comparison that changes only the threshold-estimation pool.

The Conclusion nevertheless identifies epoch screening as the principal methodological contribution supported by performance. The experiments establish the performance of a configuration; they do not uniquely identify screening as the cause of its advantage.

**Required correction:** Compare the proposed detector with S = B and S = E while keeping median centering, MAD scaling, k, filtering, channel policy, Stage C, and scoring identical. If this cannot be done, describe the performance of the complete proposed configuration and remove causal attribution to screening alone.

### F02. Headline performance uses ground-truth-dependent channel selection

**Location:** Strategy Comparison, pp. 9–10; Table I and Figure 9, p. 10; Abstract, p. 1.  
**Confidence:** High.

For each method and session, the manuscript retains the channel with the highest F1. Because F1 is calculated against reference annotations, this channel choice uses the evaluation labels. The 88.25% and 80.68% values are session means of method-specific channel maxima.

Giving all methods the same selection opportunity does not establish that their selection gains are equal. Methods can have different channel variability. These values also cannot be treated as the performance of a detector that selects a channel without labels.

**Required correction:** Name this an oracle best-channel benchmark. Report prespecified Fp1 and Fp2 comparisons for all methods using the same sessions. If practical channel selection is claimed, evaluate a label-free rule separately. Disclose the oracle estimator in the abstract.

The difference between the headline values and fixed-electrode full-montage values is not itself a contradiction: they are different estimands.

### F03. Session counts are internally inconsistent

**Location:** Datasets, p. 4; Figures 5 and 7, pp. 7 and 9.  
**Confidence:** High.

| Reported quantity | Value |
|---|---:|
| Internal sessions | 46 |
| Cao2018 sessions in Methods | 62 |
| Stated total | 104 |
| Cao2018 sessions in Figures 5 and 7 | 58 |
| Arithmetic total if all 62 public sessions were used | 108 |
| Arithmetic total if 58 public sessions were used | 104 |

The public dataset publication reports 62 available sessions from 27 subjects [S1]. That supports the source-dataset count; it does not establish how many the present study analyzed.

**Required correction:** Distinguish available recordings from included recordings. If 58 were analyzed, state the four exclusions and reasons, and verify the number of participants retained. If different experiments use different session sets, report each set explicitly. The exclusion explanation cannot be inferred from the arithmetic alone.

### F04. The comparator is an abbreviated BLINKER implementation

**Location:** Strategy Comparison, p. 9; Abstract, p. 1; Table I, p. 10.  
**Confidence:** High.

The manuscript explicitly omits BLINKER's morphology fitting and automatic channel selection. The original publication includes additional candidate evaluation and signal selection [S2]. Therefore, this comparison measures an adaptation of the threshold stage rather than the complete published pipeline.

**Required correction:** Use a label such as “BLINKER threshold-stage adaptation” consistently. State that the comparison addresses threshold strategies. If superiority over complete BLINKER is retained as a claim, evaluate the complete method with a suitable configuration.

A controlled component comparison is legitimate; broad naming and interpretation must match its scope.

### F05. The actual multiplier k is not reported

**Location:** Equation (7), p. 4; experimental descriptions, pp. 6–10.  
**Confidence:** High.

The manuscript defines k > 0 but does not provide the numerical setting used for the reported proposed-method results, its selection procedure, or any dataset-specific settings. This prevents exact replication and leaves the multiplier-confounding question unresolved.

**Required correction:** Recover the settings from the actual configurations. Report whether k was fixed in advance, informed by earlier data, or chosen using these evaluation labels. Do not insert 3.0 merely because it was used as an example in the audit request.

The original BLINKER article describes initial candidate detection at 1.5 standard deviations above the signal mean, and robust-statistic criteria elsewhere [S2]. Establish which exact dispersion formula the adaptation implemented before attributing it to that source.

### F06. MNE events are converted to scored intervals without a described rule

**Location:** Evaluation Metrics, p. 5; Strategy Comparison, p. 9.  
**Confidence:** High that the conversion is not reported; its correctness is unverified.

The manuscript scores predicted onset/offset intervals using IoU. It identifies the MNE comparator as `mne.preprocessing.find_eog_events`, whose documented return is an event array [S3]. The PDF does not explain how those events acquire interval boundaries.

**Required correction:** Report whether intervals use fixed widths, threshold crossings, local waveform landmarks, or another rule. State durations and merging behavior. Check whether the conversion systematically favors or penalizes MNE relative to detectors that directly return regions.

### F07. The true independent experimental unit needs clarification

**Location:** Datasets, p. 4; Internal annotation, p. 5; significance analyses, pp. 6–10.  
**Confidence:** High for missing Internal identifiers; medium for the effect on inference.

Cao2018 is described as 62 sessions from 27 participants. Internal “sessions” correspond to 30-minute video segments. The PDF does not give the Internal participant count or establish whether several segments originate from the same participant or recording.

The Wilcoxon analyses pair conditions by session. This controls within-session comparison, but independence between paired differences still needs attention when participants contribute multiple sessions.

**Required correction:** Supply participant → recording → segment identifiers. Check subject-level summaries or subject-blocked uncertainty estimates. Do not treat 104 segments/sessions as 104 independent people. Session-averaged performance remains a valid descriptive quantity if labeled correctly.

### F08. The dilution mechanism is described inconsistently

**Location:** Introduction, p. 2; Strategy Comparison, p. 9; Discussion, p. 11.  
**Confidence:** High for wording conflict; the correct mechanism needs evidence.

The Introduction suggests clean epochs suppress blink detection. The strategy comparison explains BLINKER dilution as lowering the threshold, consistent with more false detections, while describing MNE's failure through sensitivity to a large signal excursion.

These can be different mechanisms, but the manuscript presents a common pooling rationale without sufficiently separating them. Changes in mean, median, MAD, and signal range need not move thresholds in the same direction.

**Required correction:** Explain the expected precision/recall effect separately for each rule. Report actual threshold changes and candidate-epoch enrichment if claiming a mechanism. Use “consistent with” for an interpretation that has not been isolated experimentally.

### F09. Internal channel identities do not reconcile

**Location:** Internal montage list and Figure 2, p. 4; results/plots, pp. 6–9; Tables II and IV, pp. 14–15.  
**Confidence:** High for inconsistent labels; the correct mapping is unknown.

The Internal channel list includes P5, while Figure 2, results, and appendix tables include P8. Several plots also show E83 instead of the conventional label used elsewhere. The manuscript does not explain these substitutions.

**Required correction:** Create a definitive table of raw EGI electrode ID, conventional name, channel supplied to each experiment, and plot label. Regenerate figure/table labels from that mapping. Do not assume E83 is a particular location without checking the actual montage.

Also explain why 24 Internal and 18 public electrodes are reported in the curated regional analyses while 32 channels are supplied to full-montage screening.

### F10. Exact p-values promised in Results are missing from the appendix

**Location:** Regional results, p. 7; single-electrode results, p. 8; Tables II–V, pp. 14–15.  
**Confidence:** High; Table II/III layout was also inspected visually.

The text states that appendix tables provide exact adjusted p-values, including values near the corrected threshold. The tables instead contain F1, ΔF1, and a significance column with asterisks; no numeric p-value column appears.

**Required correction:** Add adjusted p-values from the actual statistical output and report the test implementation. Alternatively, remove statements that exact values are available. Do not infer p-values from asterisks.

Small differences between ΔF1 and subtraction of displayed two-decimal means can result from calculating differences before rounding; these are not established arithmetic errors.

### F11. Nonsignificance is being used too strongly for reduced-channel claims

**Location:** Single-electrode results, p. 8; Discussion, p. 10; Conclusion, p. 11.  
**Confidence:** High.

The absence of a significant difference at Fp1/Fp2 is emphasized as support for reduced-channel operation. However, the reported point estimates show reductions:

| Dataset | Electrode | Full montage F1 (%) | Single-electrode F1 (%) | Reported ΔF1 (percentage points) |
|---|---|---:|---:|---:|
| Internal | Fp1 | 86.32 | 83.73 | −2.59 |
| Internal | Fp2 | 86.82 | 83.37 | −3.45 |
| Cao2018 | Fp1 | 79.68 | 77.65 | −2.03 |
| Cao2018 | Fp2 | 78.45 | 75.59 | −2.86 |

Bonferroni-adjusted nonsignificance does not demonstrate equivalence. “Retained most of the performance” can describe these point estimates, but “no loss,” equivalence, or non-inferiority requires stronger evidence.

**Required correction:** Report the reductions and paired confidence intervals. If practical equivalence is a central claim, specify a defensible margin and use an appropriate analysis. Otherwise, frame the finding as a channel-count/performance trade-off.

### F12. Local adaptation wording does not match the pooled threshold equations

**Location:** Preprocessing, p. 2; Stage B, pp. 3–4; Figure 1, p. 3.  
**Confidence:** High.

The preprocessing text implies each short epoch is its own local statistical context. Stage B instead pools selected epochs and estimates one threshold per channel for application across all epochs. Epoch-aware selection is not the same as an epoch-specific threshold.

**Required correction:** State: “Epoching supports candidate-segment selection; samples from selected epochs are then pooled to estimate one threshold per channel for the recording.” Retain “epoch-aware” only with that operational definition.

### F13. Ground-truth definitions differ between corpora

**Location:** Ground-Truth Annotation, pp. 4–5; limitations, p. 11.  
**Confidence:** High; the manuscript already acknowledges part of this limitation.

Internal labels use visible eyelid movement and EAR, with an EOG timing check. Public labels use transient EEG deflections and return to baseline. These are different physical boundary definitions. Public raters view Fp1/Fp2 by default, making frontal waveform salience a potential source of annotation bias.

The second rater reviews the first rater's labels rather than creating an independent annotation set. The PDF correctly states that no inter-rater agreement statistic was calculated, although “reviewed independently” may be misunderstood.

**Required correction:** Preserve the honest description. Describe reference events by modality and interpret cross-dataset score differences accordingly. If agreement uncertainty needs measurement, collect a separately blinded duplicate-annotation subset; do not manufacture agreement from consensus labels.

### F14. Candidate epochs are not demonstrated to be blink-enriched

**Location:** Stage A, pp. 2–3; Discussion, p. 11.  
**Confidence:** High that enrichment statistics are absent; the selection quality is unknown.

Stage A selects epochs with large excursions in any supplied channel. Such excursions can represent blinks or other artifacts. The autoreject explanation describes an objective designed for noisy-trial rejection [S4]; repurposing its thresholds as a blink-candidate screen needs an empirical check.

**Required correction:** Report selected-epoch proportion, proportion of true-blink epochs selected, blink density in selected/nonselected epochs, and representative non-blink excursions. Do not interpret every unselected blink epoch as a final false negative: Stage C searches all valid epochs.

### F15. Stage C is insufficiently specified for replication

**Location:** Preprocessing, p. 2; Extraction of Blink Regions, p. 4.  
**Confidence:** High.

The preprocessing text refers to a minimum-duration gate, but the extraction description does not give its value. It also lacks polarity handling, crossing-to-interval rules, gap merging, refractory periods, cross-epoch handling, empty candidate-pool behavior, and zero-MAD safeguards.

**Required correction:** Add a compact algorithm or pseudocode with exact settings and boundary conventions. Explain treatment of final incomplete epochs and timestamp offsets. Retrieve details from the implementation rather than choosing new settings silently.

### F16. IoU 0.1 is permissive and does not establish precise timing

**Location:** Evaluation Metrics, p. 5.  
**Confidence:** High for the threshold; sensitivity of scores is unknown.

The scoring accepts one-to-one matches at IoU ≥ 0.1. This is a legitimate declared event-matching rule, but it can accept substantial onset/offset mismatch. It does not alone validate precise blink-duration estimation.

**Required correction:** Explain why this overlap level is suitable. If accurate timing or fatigue-relevant duration features are claimed, report stricter-overlap sensitivity and onset/offset or duration errors. State matching order, tie handling, and zero-denominator conventions.

### F17. Effective preprocessing of MNE remains uncertain

**Location:** Strategy Comparison, p. 9.  
**Confidence:** High for the documentation check; low for whether the implementation has a problem.

All methods receive external 1–20-Hz preprocessing. Current official MNE documentation lists internal filtering defaults of 1–10 Hz for the named function [S3]. The PDF does not list the call arguments or software version.

**Required correction:** Inspect the exact call. Report any internal refiltering. Shared external inputs do not guarantee identical effective passbands; this is a verification question rather than a demonstrated code error.

### F18. Uncertainty and paired effect magnitude are incompletely reported

**Location:** Table I and strategy significance results, p. 10; epoch-duration results, pp. 8–9.  
**Confidence:** High.

The headline table reports means and significance marks but no variability, confidence intervals, or paired effect estimates. Figure 9 shows session variation in precision/recall, but it does not replace uncertainty for the F1 difference.

**Required correction:** Add descriptive variability and uncertainty for paired differences, accounting for participant grouping where possible. For epoch-duration stability, describe observed magnitudes and their uncertainty rather than relying exclusively on significance.

The harmonic mean of mean precision and mean recall need not equal the mean of session F1 values. These reported quantities should not be treated as inconsistent merely because that calculation differs.

### F19. Title and application scope need sharper wording

**Location:** Title/Abstract, p. 1; Datasets, p. 4; limitations/conclusion, p. 11.  
**Confidence:** High for simulated-task descriptions; title interpretation is an editorial judgment.

Both corpora involve simulated lane keeping. “Naturalistic driving EEG” may be read as on-road data unless the simulator setting is explicit. The Discussion appropriately acknowledges offline evaluation and the absence of real-driving deployment validation.

**Required correction:** Define “naturalistic” or use “simulated driving EEG.” Keep blink-detection findings separate from demonstrated improvements in fatigue classification, warning reliability, or online performance, none of which is directly tested here.

### F20. Internal cohort and ethics reporting need completion

**Location:** Datasets and annotation, pp. 4–5; manuscript as a whole.  
**Confidence:** High for absent reporting in this PDF.

The PDF does not report the Internal participant count, demographic summary, approval identifier, or consent statement. This is a reporting gap and does not imply approval or consent was absent.

**Required correction:** Add the verified cohort description, ethics committee/approval identifier, consent procedure, and an accurate availability statement for data and labels, including any restrictions.

### F21. Citation correctness and novelty remain incompletely established

**Location:** Introduction/Discussion and references, pp. 1–2 and 10–13.  
**Confidence:** High for incomplete review coverage; individual citation-support verdicts remain pending.

References [8] and [17] have limited bibliographic information in the PDF. Several claims deserve targeted checks: the pooling/dilution rationale attributed to [10, 24], the Stage B interpretation of [15], and the justification for epoch-duration choices using [33–37]. These are audit priorities, not confirmed unsupported citations.

The targeted checks in this report establish only limited facts about the public corpus, BLINKER components, MNE API, and autoreject objective. They do not establish novelty or verify all 49 references.

**Required correction:** Complete the full claim-to-source ledger and reference metadata audit. Compare closest prior adaptive/epoch-based blink methods before retaining first/among-the-first language. Do not label inaccessible or incomplete references fabricated.

### F22. Local wording and presentation need correction

**Location:** Methods, pp. 2–4; Strategy Comparison, pp. 9–10; single-channel cross-reference, p. 7.

| Location | Problem | Suggested action |
|---|---|---|
| Preprocessing, p. 2 | “which is removes” | Use “which removes” or rewrite the sentence |
| Stage A, p. 3 | “from each of the channel’s.” is incomplete | Specify the actual data and optimization procedure |
| Stage A, p. 3 | Duplicated/incomplete introduction to Equation (2) | Replace with one sentence defining candidate epochs |
| Stage B, p. 4 | “which can be express as below” | Use “defined as follows” |
| Strategy comparison, p. 9 | “blink marphological-fitting” | Correct spelling and identify omitted operations precisely |
| Strategy comparison, p. 10 | Missing space in “channel.Session” | Separate the sentences |
| Single-channel results, p. 7 | “Figure 7; Figure 6” cross-reference is awkward | Cite Figure 6 for absolute performance and Figure 7 for the paired comparison |
| Several sections | Macro-F1 can be mistaken for class-macro F1 | Define “session-mean event F1” clearly and use it consistently |

## Claim-to-evidence assessment

| Major claim | What the PDF provides | Assessment |
|---|---|---|
| Proposed configuration achieved 88.25%/80.68% F1 | Table I and described oracle selection | Reported, not independently reproduced; estimator must be explicit |
| Epoch screening caused the gain | Comparison with different baseline implementations | Not isolated by presented experiments |
| Proposed detector outperformed BLINKER | Comparison with threshold-stage adaptation | Supported only for the examined adaptation and oracle protocol |
| Frontopolar sites are useful for this detector | Consistent reported rankings across configurations | Descriptively supported, subject to public-label dependence and mapping checks |
| A single electrode preserves performance | Lower means with nonsignificant corrected tests | Trade-off supported; equivalence not established |
| Performance is stable across epoch durations | Small reported changes at Fp1/Fp2 in full-montage runs | Limited descriptive support; does not cover all channels or configurations |
| Candidate screening avoids dilution | Mechanistic rationale without direct same-detector ablation | Plausible explanation requiring verification |
| Findings are independent of recording system | Two corpora with different devices and other differences | Cross-corpus consistency reported; device effect not isolated |
| Detector improves practical fatigue monitoring | Blink detection only; deployment remains future work | Application implication, not directly tested |

## Minimum useful additional analysis

### 1. Isolate screening

Compare S = E with S = B using identical median/MAD/k and Stage C. Use the same recordings, channels, filters, and matching. Report paired F1, precision, recall, thresholds, and selected-epoch proportion.

If k selection is part of the explanation, use a common prespecified sweep. Values such as 1.5 and 3.0 are illustrative until the actual study settings are confirmed. Protect evaluation labels when choosing a final setting.

### 2. Separate oracle from practical channel performance

Report all methods at fixed Fp1 and Fp2, alongside the existing oracle comparison. Quantify each method's oracle gain. Do not assume identical best-channel selection opportunities yield identical selection bias.

### 3. Resolve scoring and independence

Recover event-to-interval conversion, matching code, actual included-session IDs, and participant grouping. Use these to verify matching sensitivity and the statistical unit. Reanalysis depends on what those files show.

### 4. Make existing results fully traceable

Correct counts and channel labels, add exact adjusted p-values if promised, disclose numerical settings, and add uncertainty. These tasks may be possible from existing experiment outputs without rerunning EEG processing.

## Suggested narrower conclusion pending resolving analyses

> Under the evaluated offline protocol, the proposed median-based pipeline achieved higher session-mean event F1 than the examined BLINKER threshold-stage adaptation and MNE comparator. These comparisons used the highest-F1 channel for each method and session, selected using reference annotations. Frontopolar electrodes gave the strongest reported detection performance, although single-electrode operation reduced the mean F1 relative to full-montage operation. A controlled ablation is needed to determine how much of the performance advantage is attributable specifically to candidate-epoch screening.

This wording does not replace the manuscript automatically. It illustrates what the current evidence can support without asserting a component effect that has not been isolated.

## Verified strengths and issues not established

- The PDF explicitly states one-to-one event matching and equal session weighting.
- Regional and single-electrode experiments rerun the complete detector rather than merely selecting outputs from a fixed full-montage run.
- The annotation description candidly distinguishes review-and-consensus from independent duplicate annotation and acknowledges modality limitations.
- The Discussion acknowledges offline operation and untested real-driving deployment.
- Bonferroni family definitions are reported for several comparisons, although implementation and inferential independence remain unverified.
- Headline versus fixed-electrode scores are different estimands, not automatically numerical errors.
- Small appendix subtraction discrepancies can be explained by rounding; raw values are needed before declaring errors.
- There is no evidence here establishing fabricated references, misconduct, invalid raw data, or incorrect code.

## Recommended revision order

1. Confirm included-session and participant identifiers; reconcile all counts.
2. Recover k and complete baseline/Stage C configurations, including MNE intervals.
3. Add fixed-channel comparisons and the screening-only ablation if retaining the causal claim.
4. Check participant dependence and add paired uncertainty.
5. Reconcile electrode names, p-value reporting, and figure/table labels.
6. Narrow abstract/conclusion language to the verified estimator, baseline scope, and simulator setting.
7. Complete citation/metadata/novelty verification, then polish prose and captions.

## External sources checked

These sources support the limited points identified above. They are not a complete bibliography audit. Accessed 1 October 2026.

- **[S1] Cao et al. (2019), public corpus description.** Reports 62 available sessions from 27 subjects. [Scientific Data](https://www.nature.com/articles/s41597-019-0027-4), DOI: 10.1038/s41597-019-0027-4.
- **[S2] Kleifges et al. (2017), original BLINKER method.** Relevant sections: preprocessing/potential blink detection, blink landmarks, and best-signal selection. [Original article](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2017.00012/full), DOI: 10.3389/fnins.2017.00012.
- **[S3] Official MNE documentation, `find_eog_events`.** Checked filtering arguments, default threshold description, and event return type. [API documentation](https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html). The actual study version and arguments remain unknown.
- **[S4] Official autoreject explanation.** Describes threshold optimization for noisy-epoch rejection. [Explanation](https://autoreject.github.io/v0.2/explanation.html). The manuscript's exact screening routine remains unverified.

## Inputs needed to resolve remaining scientific concerns

- Included-session lists by experiment, with participant and parent-recording identifiers.
- Experiment configurations, numerical k, software versions, and fixed code commit.
- Reference event intervals and per-method predictions, including MNE interval conversion.
- Per-session/per-channel metric files and full statistical outputs.
- Raw-ID-to-conventional-electrode mapping and figure-generation inputs.
- Existing ablation and sensitivity outputs, if any.
- Verified Internal ethics, consent, cohort, and availability details.

Recommended analyses in this report have not been executed. Corrected counts, channel mappings, p-values, or outcomes must come from those authoritative inputs.
