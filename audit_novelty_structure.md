# Novelty, manuscript-quality, visual, ethics, and adversarial-review audit

**Manuscript reviewed:** *Epoch-Aware Threshold Estimation for Blink Detection in Naturalistic Driving EEG*  
**Artifact reviewed:** `writing/IEEE-TJ-color-latex-template/main.pdf`, 15 pages, build dated 1 October 2026  
**Literature-search cutoff:** 1 October 2026  
**Scope of this report:** novelty/prior art; title, abstract, keywords, argument and section flow; discussion, limitations, and conclusion; every figure, table, and caption; terminology; ethics/reporting; state-of-the-art context; skeptical-reviewer simulation; and editorial triage. Statistical and code findings are noted where they directly affect these areas, but a full statistical/code audit belongs in the consolidated report.

## 1. Bottom-line assessment

The potentially publishable contribution is a **simple, interpretable composition**: an autoreject-derived cross-validated peak-to-peak screen selects candidate epochs, samples from those epochs feed a BLINKER-inspired robust amplitude threshold, and that per-channel threshold is then applied across the session. The dual-corpus driving evaluation and explicit channel/epoch-duration analyses are useful validation work.

The manuscript does **not yet demonstrate that epoch screening caused the reported improvement**. The comparison changes the sample pool, location estimator, dispersion estimator, multiplier, event extraction rules, and large parts of the baseline pipelines simultaneously. BLINKER is represented only by its initial threshold-crossing stage, with its morphology fitting and automatic channel selection removed (PDF p. 9); all methods are then scored at the **reference-label-selected best channel in each session** (pp. 9–10). The paper nevertheless concludes that epoch screening is the “principal methodological contribution” (p. 11). That attribution is unsupported without a factorial ablation.

The work is therefore best characterized as **incremental methodological/engineering novelty plus validation novelty**, not yet as a demonstrated new blink-detection principle. Its strongest distinctive element is the exact *candidate-epoch-conditioned threshold calibration* sequence in two simulated-driving corpora. Its greatest novelty threat is extensive overlap with autoreject, BLINKER, and prior adaptive/unsupervised single-channel blink detectors, several of which are missing from the related-work argument. Its greatest editorial threat is that the title/abstract/results imply a naturalistic, reliable detector comparison while the evidence is an offline simulated-driving, oracle-channel analysis against incomplete baseline stages.

## 2. Editorial triage

| ID | Severity | PDF evidence | Concern | Consequence | Minimum correction |
|---|---|---|---|---|---|
| NS-01 | **CRITICAL** | Strategy comparison, pp. 9–10; Conclusion, p. 11 | The manuscript attributes the advantage to epoch screening, but the proposed and comparator conditions differ in several other ways. No all-epochs-versus-candidate-epochs ablation with an identical threshold formula is reported. | The central causal/mechanistic conclusion is not identified. | Run a controlled factorial ablation: same median/MAD estimator and same `k` with candidate epochs versus all epochs; independently vary estimator and `k`; keep extraction/post-processing fixed. Rewrite causal claims until then. |
| NS-02 | **CRITICAL** | p. 9: BLINKER morphology fitting and automatic channel selection were not used; p. 10/Table I | The paper labels a threshold-crossing fragment “BLINKER” and compares it with the complete proposed pipeline. | Baseline fairness and the magnitude of the reported advantage are not interpretable as superiority over established BLINKER. | Compare the full published BLINKER pipeline, and separately label an ablation “BLINKER initial-threshold stage.” Explain any infeasible components. |
| NS-03 | **CRITICAL** | pp. 9–10; Fig. 9 caption; Table I caption | Each method/session is evaluated at the channel with the highest reference-label F1. This is outcome-selected oracle performance. | Headline F1 is optimistic and not achievable without labels at deployment; channel-selection error is excluded. | Report prespecified-channel (Fp1 and Fp2), fixed channel selected on training/development data, and/or nested selection results. Rename current result “per-session oracle-channel upper bound.” |
| NS-04 | **MAJOR** | Title and Abstract, p. 1; dataset description, pp. 4–5 | Both corpora are simulated lane-keeping tasks, yet the title/abstract call them “naturalistic driving.” | The ecological setting is overstated. | Replace with “simulated-driving EEG” unless a defensible operational definition of naturalistic simulation is supplied. |
| NS-05 | **MAJOR** | Abstract, p. 1; Discussion/Conclusion, p. 11 | “More reliable” is claimed despite no reliability study, no independent repeat annotation, no calibration/retest analysis, and uncertain EEG-only labels for Cao2018. | “Reliable” is stronger than the evidence and conflates higher oracle F1 with reliability. | Use “higher event-level F1 under the evaluated offline protocol.” Reserve reliability for repeatability/agreement evidence. |
| NS-06 | **MAJOR** | Dataset, p. 4 (62 + 46); figures/results (58 Cao2018); total reported as 104 | The paper reports 104 sessions total, describes 62 public plus 46 internal (=108), and later plots 58 public sessions without explaining four exclusions in the PDF. | Cohort flow, selection bias, and exact analysis population cannot be assessed. | Add a participant/session flow table, reasons and timing for all exclusions, participant IDs per session, and the distinction between available (108) and analyzed (104) recordings. |
| NS-07 | **MAJOR** | Dataset/annotation, pp. 4–5 | The internal number of participants, demographics, consent/ethics approval, recruitment, and repeated-session structure are absent; “session” is also said to correspond to a 30-min video segment. | Human-subject provenance and independence are opaque; session-level inference may be pseudoreplicated. | Report participants and sessions separately, demographics, protocol/eligibility, ethics committee and approval ID, consent, and within-participant clustering. |
| NS-08 | **MAJOR** | Methods, pp. 2–5 | The statistical-analysis subsection is absent even though Wilcoxon tests, Bonferroni correction, and rank-biserial effects are described/results claimed elsewhere. Stage C also lacks executable event-extraction rules. | The study is not reproducible from the paper and inferential choices appear post hoc. | Restore a complete prespecified Statistical Analysis section; specify polarity, crossing/merging, minimum duration, boundary handling, `k`, empty-candidate behavior, software/version, and all family definitions. |
| NS-09 | **MAJOR** | Intro, p. 2; Strategy Discussion, pp. 9–11 | The “dilution” account is internally unstable: lowering a BLINKER threshold predicts more false positives, while the Introduction says pooling clean epochs can suppress detection/produce under-detection. The paper treats different baseline failure mechanisms as one epoch-pooling effect. | The theoretical gap and mechanistic interpretation are not coherent. | Separate low-threshold false-positive dilution from range-threshold under-detection; state them as hypotheses; measure and report the actual thresholds and threshold distributions. |
| NS-10 | **MAJOR** | Intro, pp. 1–2 | Closest prior work is not adequately discussed: Agarwal & Sivakumar’s unsupervised single-channel *Blink* (2019), Chang et al.’s online individualized adaptive detector (2016), later event detectors (2025–2026), and ARMBR’s cross-validated blink thresholding (2025). | “Among the first” and the asserted gap are not supported by a sufficiently current prior-art analysis. | Add a Related Work subsection and a component-by-component comparison; narrow novelty to the exact candidate-epoch-conditioned composition and driving validation. |
| NS-11 | **MAJOR** | Fig. 8, p. 9 | The y-axis begins at 70%, visually magnifying changes of 0.1–1.3 percentage points; no uncertainty or paired session distributions are shown. | Readers can overestimate practical epoch-duration effects. | Use a 0–100 axis or clearly marked zoom plus a difference-from-30-s panel with paired distributions and confidence intervals. |
| NS-12 | **MAJOR** | Fig. 2, p. 4 | Caption says “the 32 electrodes used,” but the two corpora have different 32-channel lists, Cao includes A1/A2 mastoids that are not plotted as scalp sites, and several channels are excluded from regional analyses without being identified in the active text. | Montage and region-subset definitions are ambiguous and not reproducible. | Show two montage panels or the explicit union; mark unassigned/mastoid/reference sites; list exact regional membership in a table. |
| NS-13 | **MAJOR** | Discussion, p. 11 | The manuscript confidently assigns BLINKER’s errors to dilution and MNE’s to single excursions without recording thresholds or performing the relevant ablations. | Post-hoc mechanism storytelling is presented as explanation. | Change to “consistent with, but does not establish”; add threshold logging, artifact-stratified error analysis, and controlled ablations. |
| NS-14 | **MAJOR** | Appendix text, pp. 14–15; Results, pp. 7–8 | Main text says the appendix gives exact adjusted p-values, but Tables II–V contain only F1, delta, and a significance star. Sample sizes and effect sizes are absent. | Traceability and uncertainty reporting are materially incomplete. | Add `n`, adjusted exact p, rank-biserial effect size and interval for every comparison; or remove the false claim. |
| NS-15 | **MODERATE** | Results, pp. 5–10 | The central strategy comparison appears last, after approximately four pages of channel-subset results; several figures repeat the same electrode ranking. | The manuscript buries its main methodological claim and reads as exploratory channel mapping. | Present the strategy comparison first, then the causal ablation, then channel and epoch-duration secondary analyses. Consolidate Figs. 3–7. |
| NS-16 | **MODERATE** | End matter, p. 11 onward | No dedicated Ethics, Data Availability, Code Availability, Conflict of Interest, Author Contributions, or reproducible environment statements appear. | Reporting is incomplete for human EEG/video research and code-based method validation. | Add dedicated declarations, immutable code release/commit/DOI, dataset-access terms, and label availability. |
| NS-17 | **MAJOR** | Contribution paragraph/footnote, p. 2 | The manuscript says source, baseline, and experiment code are released, but the linked public repository displayed “This repository is empty” when checked on 1 October 2026. | The reproducibility contribution is currently false and readers cannot regenerate results. | Populate and archive the exact version before submission, then cite a commit and DOI; until then, remove the release claim. |

## 3. Prior-art and novelty assessment

### 3.1 Search method and caution

The search used publisher pages, PubMed/PMC, IEEE-linked manuscripts, official software documentation, and the OHBM reporting materials, covering literature available through 1 October 2026. Queries combined EEG, blink/eyeblink, event detection, artifact detection, threshold, adaptive/unsupervised, epoch/window, driving, cross-validation, and single-channel/frontopolar. This was a targeted adversarial search, not a registered systematic review; therefore “first” claims remain inappropriate.

### 3.2 Closest prior-art matrix

Raw performance values below are **not directly comparable** because datasets, labels, units of analysis, matching rules, and channel-selection protocols differ.

| Feature | Current manuscript | BLINKER, Kleifges et al. 2017 | Chang et al. 2016 (single prefrontal) | Chang et al. 2016 (real-time adaptive) | *Blink*, Agarwal & Sivakumar 2019 | ARMBR, McCloy et al. 2025 | Rejer & Gago 2025 / Zhong et al. 2026 |
|---|---|---|---|---|---|---|---|
| Task | Offline blink-region detection in simulated-driving EEG | Automated blink/ocular-index extraction across large EEG/EOG/IC corpora | Single-prefrontal blink artifact range detection | Unsupervised online single-prefrontal blink detection | Fully automated unsupervised single-channel event timing | Blink detection as first stage of multichannel artifact removal | CNN event detection across setups / portable two-channel blink-movement classification |
| Data | Internal: 46 30-min “sessions/segments,” participants not stated; Cao: 58 analyzed sessions from 27 participants | >2,000 datasets from 8 labs; video verification on subsets | 24 healthy participants | 24 participants | Four datasets, 12–20 users per dataset, >2,300 annotated blinks, two headsets/activities | Semi-synthetic plus real EEG from 16 participants | 10 subjects across 3 setups / 40 adults, LOSO |
| Preprocessing | 100 Hz; 1–20 Hz; non-overlapping epochs | 1–20 Hz | Digital-filter and rule-based morphology | Previous digital-filter method plus automatic adaptive threshold | Low-pass, stable-point/peak features, clustering/template learning | Fp1/Fp2 reference construction; threshold mask; regression | Learned time-pattern representation / 21 features and ML |
| Threshold/calibration | Autoreject-derived channel peak-to-peak CV screen; pool selected epochs; median + `k × 1.4826 MAD` | Overall mean + 1.5 SD for initial candidates; morphology and robust amplitude-distribution filtering | Rule-based/filter response; explicitly estimates blink range | Individualized automatic threshold with real-time adaptation | Self-learns user/session blink profiles; usable in moving windows ≥30 s | Automatic robust cross-validated threshold option on frontal reference | Supervised learned detector / supervised features |
| Epoch/window role | 10–120 s sensitivity; 30 s primary; candidate epochs calibrate one per-session channel threshold | Continuous pool; ocular indices can be windowed after detection | Evaluates contaminated 1-s epochs and artifact ranges | Training length and real-time updating evaluated | Moving-window online use proposed; ≥30 s | Continuous blink reference; separate ERP epochs downstream | Short event segments / subject-held-out validation |
| Channel strategy | All channels feed Stage A; channel-wise events; oracle best channel for headline F1 | Tests candidates and automatically chooses best channel/IC | Single frontal/prefrontal | Single prefrontal | Single channel | Fp1/Fp2 reference | CNN setup-dependent / portable two-channel |
| Event refinement | Insufficiently specified in PDF | Duration/separation gates, landmark fitting, waveform quality, amplitude and pAVR criteria | Waveform/range rules | Waveform/range rules | Stable points and learned pattern correlation | Binary threshold mask (removal-oriented) | Learned episode detection / classification |
| Validation | Event IoU ≥0.1; session macro-F1; two corpora; per-session oracle channel | Large heterogeneous corpus, visual/video checks; not same event-F1 protocol | 24-person validation against conventional methods | Two comparator algorithms; online demonstration | Cross-headset/activity, annotated events | Semi-synthetic ground truth and real EEG | Individual/cross-subject detection / LOSO |
| Genuine overlap with current paper | — | Same 1–20 Hz and robust thresholding; best-channel concept; complete blink pipeline | Prior single-channel event/range detection and epoch-contamination evaluation | Prior adaptive individualized thresholding and real-time operation | Prior unsupervised session-specific event detection and 30-s moving-window concept | Recent automatic robust cross-validated thresholding of Fp1/Fp2 for blink regions | More recent event-level/generalization competitors omitted from baseline set |
| Distinguishing element of current paper | Candidate-epoch restriction before channel-wise robust thresholding, evaluated in two driving corpora | Does not use the same candidate-epoch calibration sequence | Does not use the same two-stage candidate-pool estimator | Online rather than epoch-conditioned pool | Learns morphology/pattern rather than the exact amplitude-pool sequence | Removal-focused and frontal averaged reference, not candidate-epoch-conditioned channel thresholds | Learned models and different validation aims |

Primary sources: [BLINKER](https://doi.org/10.3389/fnins.2017.00012); [single-prefrontal detector](https://doi.org/10.1016/j.cmpb.2015.10.011); [real-time adaptive detector](https://pubmed.ncbi.nlm.nih.gov/26888113/); [Blink 2019 paper](https://gnan.ece.gatech.edu/archive/agarwal-blink.pdf), DOI [10.1109/ALLERTON.2019.8919795](https://doi.org/10.1109/ALLERTON.2019.8919795); [ARMBR](https://pmc.ncbi.nlm.nih.gov/articles/PMC12539671/); [Rejer & Gago 2025](https://pubmed.ncbi.nlm.nih.gov/40328273/); [Zhong et al. 2026](https://pubmed.ncbi.nlm.nih.gov/41177306/); [autoreject](https://pmc.ncbi.nlm.nih.gov/articles/PMC7243972/).

### 3.3 State-of-the-art context

| Study | Year | Validation design | Reported result | Relevance and comparability warning |
|---|---:|---|---|---|
| Kleifges et al., BLINKER | 2017 | >2,000 datasets; automated candidate-channel selection; video checks on subsets | No directly comparable event-IoU macro-F1 | This is a **complete multi-stage pipeline**, whereas the manuscript tests only its threshold-crossing stage. |
| Agarwal & Sivakumar, *Blink* | 2019 | Four annotated datasets, cross-headset/activity | >98% accuracy, average precision 0.934 | Accuracy and event definition differ; still an important missing unsupervised single-channel baseline/prior-art citation. |
| Jiang et al., VME + morphology | 2023 | Semi-simulated and real EEG, 9 subjects | Accuracy 97.63%, sensitivity 92.64% in the publisher summary | Different signal decomposition, optimization, data, and metric; cannot rank against current F1. [DOI](https://doi.org/10.1109/JSEN.2023.3305118) |
| Rejer & Gago, CNN episodes | 2025 | 10 subjects, three setups; individual and cross-subject tests | Detection rates 96.91%, 97.18%, and 94.45% cross-subject | A contemporary event detector; learned rather than threshold-based; metric/matching details differ. |
| McCloy et al., ARMBR | 2025 | Semi-synthetic and real data; blink detection plus removal | Focuses on reconstruction/removal rather than comparable F1 | Particularly relevant because its automatic option uses robust cross-validated blink thresholding. |
| Zhong et al. | 2026 | 40 adults; portable two-channel device; LOSO | Mean blink-classification accuracy 95% | Cued movement classification, not continuous naturalistic event segmentation. |
| Current manuscript | 2026 draft | 46 internal segments + 58 public recordings; IoU ≥0.1; oracle best channel/session | Macro-F1 88.25% and 80.68% | Outcome-selected channel, uncertain participant independence, and incomplete baselines prevent a state-of-the-art claim. |

The paper does not literally use “state of the art,” but its abstract-level superiority wording may be read that way. It should explicitly say the comparisons are limited to **two threshold baselines under this implementation**, not the current field.

### 3.4 Claimed-contribution audit

| Claimed contribution | Existing literature | Truly new element that may remain | Degree of novelty | Defensible wording |
|---|---|---|---|---|
| Three-stage epoch-aware threshold pipeline (Intro, p. 2) | Autoreject already supplies cross-validated peak-to-peak trial/sensor thresholds; BLINKER supplies robust thresholding and event refinement; adaptive/session-specific blink methods predate this paper. | Using autoreject-style high-amplitude candidate epochs as the exclusive calibration pool for a per-channel robust blink threshold, then applying it to all epochs. | **Incremental methodological / engineering** | “We evaluate a candidate-epoch-conditioned composition of cross-validated epoch screening and robust channel-wise thresholding.” |
| “Among the first frameworks” (p. 2) | Exact ordering may be uncommon, but targeted search found substantial adjacent work and missing close studies. | Possibly the first explicit implementation of this exact composition in driving EEG; not established by the current search. | **Unproven first claim** | Delete “among the first.” If retained after systematic search: “To our knowledge, we have not identified a prior study evaluating this exact sequence…” |
| Systematic comparison with BLINKER and MNE | BLINKER and MNE are established, but manuscript removes major BLINKER stages and uses MNE defaults outside its typical EOG-event context. | Same-preprocessing threshold-stage comparison across two corpora. | **Validation novelty, compromised by fairness** | “We compare against the initial BLINKER threshold rule and MNE’s default peak detector under a common preprocessing protocol.” |
| Code release | Many prior algorithms release code/data (BLINKER, Blink, Eyeblink Master). The manuscript’s linked GitHub repository was empty on 1 October 2026. | Reproduction scripts for these particular experiments, once actually deposited. | **Not currently delivered** | Do not claim release until the repository contains a tagged/archived, runnable version. Then: “We provide scripts and an archived release that reproduce the reported analyses.” |
| Frontopolar electrodes preserve performance | Prior literature already establishes frontal/frontopolar dominance and single-channel blink detection. | Within-pipeline dual-corpus reduction analysis. | **Confirmatory/application validation** | “Within both evaluated corpora, Fp1/Fp2 retained oracle-event F1 under reduced input configurations.” |
| Stability across epoch durations | Window-length effects have been studied widely, but a systematic 10–120 s test for this exact detector is less common. | Sensitivity analysis of this pipeline, although restricted post hoc to Fp1/Fp2. | **Validation novelty** | “For Fp1/Fp2, mean F1 varied by at most [report range] across tested epoch durations.” |
| More reliable detection | Higher F1 is observed only under a permissive IoU rule and oracle channel selection; reliability was not measured. | None under the present design. | **Unsupported wording** | “Higher event-level F1 under the evaluated offline oracle-channel protocol.” |

### 3.5 Recommended novelty statement

> We introduce and evaluate a candidate-epoch-conditioned thresholding pipeline for offline blink-region detection in simulated-driving EEG. The pipeline combines cross-validated, channel-wise peak-to-peak screening with robust threshold calibration restricted to selected epochs. The individual components are established; the contribution is their explicit composition and its evaluation across two driving-EEG corpora, channel configurations, and epoch durations. Controlled ablations are required before attributing performance gains specifically to candidate-epoch conditioning.

## 4. Title, abstract, keywords, and manuscript argument

### 4.1 Title

Current: **“Epoch-Aware Threshold Estimation for Blink Detection in Naturalistic Driving EEG.”**

Problems:

1. “Naturalistic driving” is inaccurate or at least undefined because both datasets use simulated lane-keeping (pp. 4–5).
2. “Blink detection” is broader than the operational output, which is channel-wise threshold-crossing regions under an IoU ≥0.1 match.
3. “Epoch-aware” is acceptable, but “candidate-epoch-conditioned” is more precise: the method does not estimate a separate threshold per epoch; it estimates one channel threshold from pooled selected epochs.

Preferred title:

> **Candidate-Epoch–Conditioned Thresholding for Offline Blink-Region Detection in Simulated-Driving EEG**

Less technical alternative:

> **Epoch-Screened Threshold Calibration for Blink Detection in Simulated-Driving EEG**

### 4.2 Abstract consistency and claim strength

| Abstract statement (p. 1) | Assessment | Required change |
|---|---|---|
| Existing methods “typically estimate a single amplitude threshold” from mixed continuous segments | Too broad; several adaptive, windowed, unsupervised, and learned detectors exist. | Restrict to the two comparator threshold rules or cite a systematic basis. |
| Pooling “dilut[es]” amplitude statistics | Plausible for BLINKER’s mean/dispersion rule, not a universal mechanism and not the same failure mode as MNE’s range threshold. | Present as a method-specific hypothesis. |
| Two “naturalistic driving-EEG corpora” | Contradicted by Methods: both are simulated lane-keeping. | Use “simulated-driving EEG corpora.” |
| “full 32-channel montage” | Misleading because the montages differ; Cao’s 32 include two mastoids, and headline F1 is selected from the best channel/session. | State “dataset-specific 32-channel inputs, evaluated at a per-session oracle-selected channel.” Better: report fixed Fp1/Fp2 as headline. |
| “significantly outperforming both baselines” | Numerically true under the authors’ protocol, but baselines are incomplete/default and statistical methods are absent from Methods. | Say “had higher paired session-level F1 than the tested baseline implementations”; report `n`, effect size, CI and adjusted p. |
| “more reliable” | Reliability not measured. | Replace with “higher event-level F1 under this offline evaluation.” |

The Abstract must disclose: participant/session counts, the 58/62 public exclusion flow, per-session oracle channel selection, incomplete BLINKER configuration, IoU threshold, and uncertainty/effect size. It should not imply that two corpora constitute external generalization when both are used in development/evaluation and labels differ in quality.

### 4.3 Keywords

Current keywords are generally discoverable but should replace “naturalistic driving” with **simulated driving** and consider **event detection**, **adaptive thresholding**, and **ocular artifact**. “Epoch-aware detection” is a manuscript-specific phrase and may be less searchable than “epoch screening.”

### 4.4 Argument and flow

Current flow: Introduction → dense algorithm Methods → datasets/annotations/metrics → channel-subset analysis → epoch-duration analysis → strategy comparison → Discussion → Conclusion.

Recommended flow:

1. **Introduction:** distinguish blink-as-signal from blink-as-artifact, define exact threshold-calibration problem, and state a falsifiable hypothesis.
2. **Related Work:** compare continuous threshold rules, adaptive/windowed detectors, morphology/template methods, and learned event detectors; include a component table.
3. **Methods:** cohorts/ethics and analysis flow first; algorithm specification; comparators; prespecified ablations; statistical analysis; reproducibility.
4. **Results 1—Primary:** complete proposed method versus fair complete baselines and fixed-channel deployment results.
5. **Results 2—Mechanism:** candidate-epoch versus all-epoch factorial ablation and threshold/error analysis.
6. **Results 3—Secondary:** channel reduction and epoch-duration sensitivity.
7. **Discussion:** supported findings, alternatives, comparison with literature, practical meaning, limitations.

The present ordering makes a five-page channel-ranking analysis appear to be the central study while the nominal methodological contribution receives approximately one page and no causal ablation.

## 5. Section-by-section manuscript-quality review

| Section | What works | Main problem | Required revision |
|---|---|---|---|
| Introduction, pp. 1–2 | Establishes blink relevance and artifact-versus-signal perspective. | Overgeneralizes continuous thresholds; missing closest adaptive/unsupervised methods; internally inconsistent “dilution” mechanism; “among first” unsupported. | Rebuild around the exact candidate-calibration problem and current prior-art matrix. |
| Methods overview, pp. 2–4 | Three stages and Figure 1 are conceptually understandable. | “Epoching makes thresholds adaptive” is false/misleading; Stage A CV and Stage C extraction are not fully specified; `k` is not given in the active PDF text. | Supply algorithm/pseudocode, all parameters and edge cases; distinguish session-specific from epoch-specific adaptation. |
| Datasets, pp. 4–5 | Public dataset source and channel lists are given; annotation sources are unusually candid. | Counts conflict; internal participants/demographics absent; exclusions absent; montage/region definition ambiguous; no ethics. | Add cohort-flow and acquisition tables and declarations. |
| Ground truth, pp. 4–5 | Internal labels use synchronized video, EAR, and vertical EOG; raters are described as blinded. | Second rater did not annotate independently; Cao labels use the same EEG morphology the detector exploits; no agreement; no annotation uncertainty; timing shift chosen manually. | Add independent subset annotation, agreement and timing-tolerance analysis; discuss incorporation bias. |
| Evaluation, p. 5 | Event-level one-to-one matching and session macro-averaging are preferable to sample accuracy. | IoU ≥0.1 is permissive and sensitivity is absent; exact matching algorithm not defined; division-by-zero handling absent. | Add IoU sensitivity (0.1–0.5), onset/offset errors, count error, and matching implementation. |
| Statistical analysis | — | Missing as a Methods subsection in the PDF. | Restore it, including test families, exact n, effect sizes, CIs, missing pairs and preregistration status. |
| Results, pp. 5–10 | Extensive electrode-level reporting and dual-corpus replication. | Redundant figures; means without distributions; selective focus on best electrodes; oracle best channel in primary comparison; appendix contradiction. | Reorder, consolidate, add distributions/intervals, and clearly separate exploratory from confirmatory analyses. |
| Discussion, pp. 10–11 | Acknowledges annotation uncertainty, offline operation, and limited domains. | Treats hypothesized mechanisms as established; does not discuss unfair baselines/oracle selection/no ablation; overstates cross-hardware independence. | Add alternative explanations and validity threats; constrain inferences to the evaluation protocol. |
| Limitations, p. 11 | Notes two datasets, offline simulation, no duration stratification, and imperfect labels. | Omits the most conclusion-changing limitations (confounding, oracle channel, incomplete baselines, participant dependence, whole-session calibration, parameter sensitivity, label incorporation bias). | Replace with a threats-to-validity structure; see Section 10. |
| Conclusion, p. 11 | Does acknowledge lack of beyond-domain and deployment evidence. | “supports epoch screening as principal contribution” and “more reliable” exceed evidence; “spatially sparse” relies on oracle/selected electrodes. | State association, not isolated cause; define the exact offline scope. |
| Data/code availability | Footnote links to GitHub on p. 2; the linked repository was empty when checked on 1 October 2026. | The explicit code-release claim is presently unfulfilled; no commit/tag/DOI/license/environment or label/data access statement exists. | Deposit the actual code and environment, add a tagged archive/DOI and dedicated availability statement, or remove the release claim. |
| Ethics/COI/authorship | Funding disclosed on p. 1. | No ethics approval, consent, COI or author-contribution statements. | Add journal-compliant declarations before submission. |
| References | Includes BLINKER, MNE, autoreject, and several domain papers. | Important close methods from 2016, 2019, 2025 and 2026 are absent from the novelty argument. | Add and critically compare, not merely decorate the Introduction. |
| Supplementary information | Appendix provides per-electrode means/deltas. | No supplementary protocol, annotations, exclusion log, complete statistics, parameter sensitivity or reproducibility manifest. | Supply structured supplement and machine-readable results. |

## 6. Discussion and conclusion claim audit

| Claim | Location | Classification | Reason | Safer wording |
|---|---|---|---|---|
| Fp1/Fp2 concentration agrees with prior driving studies | Discussion, p. 10 | **Reasonably supported** | Descriptive dual-corpus rankings and literature align, though oracle/annotation effects remain. | Keep, but call it confirmatory and report uncertainty. |
| Frontopolar advantage does not rely on other channels | p. 10 | **Partially supported** | Single-channel reruns remove other-channel inputs, but pipeline and selection behavior change. | “The advantage persisted when the pipeline was rerun using the electrode alone.” |
| Occipital-only systems would “miss most” blink information | p. 10 | **Overstated** | Low F1 is shown for this algorithm/labels, not information-theoretic absence or all systems. | “This detector recovered substantially fewer reference events at occipital sites.” |
| Pipeline accommodates common epoch durations | p. 11 | **Moderately supported** | Only Fp1/Fp2, two corpora, whole-session offline calibration; small average changes. | “Mean F1 at Fp1/Fp2 was similar across 10–40 s under this offline protocol.” |
| BLINKER errors arise because blink-free epochs pull threshold down | p. 11 | **Speculative** | Actual thresholds not recorded; center, spread, multiplier and morphology differ. | “One possible explanation is…; the present design does not isolate it.” |
| MNE misses arise because a single large artifact raises threshold | p. 11 | **Speculative** | Plausible from its range rule but no session-level artifact/threshold analysis. | Same caution and direct threshold/error analysis. |
| Similar margins mean advantage is not recording-system dependent | p. 11 | **Overstated** | Dataset differs simultaneously in hardware, montage, labels, participants and protocol; two systems cannot establish invariance. | “The ranking replicated in a second corpus recorded with different hardware.” |
| Epoch screening is the principal cause/contribution | Conclusion, p. 11 | **Unsupported causal attribution** | No controlled screening ablation. | “The complete candidate-epoch-conditioned configuration had higher F1 than the tested baseline implementations.” |
| Spatially sparse approach without dense montage | p. 11 | **Weak-to-moderate** | Fp1/Fp2 single-channel reruns are promising, but electrode was identified/tested on the same data and no fixed prospective selection is shown. | “Results motivate prospective fixed-Fp1/Fp2 validation.” |
| Practical foundation | p. 11 | **Speculative** | Offline, whole-session and oracle channel selection; no timing/cost/online test. | “A candidate for further prospective and online evaluation.” |

## 7. Figure-by-figure and caption audit

### Figure 1 — Pipeline overview (p. 3)

- **Intended demonstration:** Five operations and the relationship among signal preparation, candidate-epoch screening, threshold calibration, and region extraction.
- **Does it demonstrate it?** Largely yes; this is the manuscript’s clearest figure.
- **Problems:** The graphic title says “Proposed Double-Thresholding Method” while the manuscript/title calls it epoch-aware; only three example channels are shown although the method is presented as 32-channel; “Fp1 threshold” is not numerically tied to `k`; the drawing may imply Stage B estimates a threshold from only three candidate epochs without showing failure/empty cases. Small labels will be difficult at final two-column size.
- **Caption change:** State explicitly that traces are schematic, that one session-wide threshold per channel is estimated from all selected epochs, and that selection does not establish that an excursion is ocular.
- **Visual/statistical improvement:** Add the exact Stage A and Stage B decision equations/parameters in small callouts; use consistent method name; increase text size.

### Figure 2 — Electrode map (p. 4)

- **Intended demonstration:** Dataset montage overlap and eight anatomical regions.
- **Does it demonstrate it?** Only partly.
- **Problems:** “32 electrodes used” is ambiguous/incorrect across two different 32-channel montages; Cao A1/A2 mastoids are not represented; midline and excluded electrodes are not clearly marked as unassigned; region boundaries appear authoritative although the cited rule and exact membership are not tabulated; blue/yellow/red may fail for some color-vision deficiencies.
- **Caption change:** Define whether the map shows the union, explicitly list unassigned/reference/mastoid sites, and give channel counts per corpus/region.
- **Visual/statistical improvement:** Use two panels (Internal, Cao2018) plus shape encoding; include A1/A2 at mastoids; provide a machine-readable mapping table.

### Figure 3 — Full-montage per-electrode F1 (p. 6)

- **Intended demonstration:** Spatial ranking when all dataset-specific 32 channels enter the pipeline.
- **Does it demonstrate it?** Descriptively, yes.
- **Problems:** Means only; no uncertainty, session distribution, or sample count in caption; labels are tiny; sorting differs by dataset and impedes direct correspondence; “four curated regions” omits channels outside those plotted and does not explain why.
- **Caption change:** Add `n=46` segments and `n=58` recordings, define macro/session mean and exclusions, and state that no inferential comparison is encoded.
- **Improvement:** Replace bars with dot/interval plots or paired distribution summaries; use consistent electrode ordering.

### Figure 4 — Regional-rerun per-electrode F1 (p. 7)

- **Intended demonstration:** Electrode performance after the complete pipeline is rerun using only its region.
- **Does it demonstrate it?** Descriptively, but it repeats Figure 3’s pattern.
- **Problems:** No uncertainty or `n`; readers may mistake electrode output F1 for region-level detector F1; very small text; no direct delta from full montage.
- **Caption change:** Clarify that Stage A’s input set changes and each bar is a channel output from a region-constrained rerun, not a collapsed region score.
- **Improvement:** Merge with Figure 5; plot paired delta and confidence interval instead of a second raw-mean bar chart.

### Figure 5 — Regional rerun versus full montage (p. 7)

- **Intended demonstration:** Paired mean differences and corrected significance.
- **Does it demonstrate it?** Partly.
- **Problems:** Opaque/translucent bars are hard to distinguish; significance stars replace effect sizes; no exact n, p, effect or interval; vertical separators and tiny labels create clutter; same-data selection/exploration is not flagged.
- **Caption change:** Add family size (24/18), actual pair counts, precise statistic/effect size, and explain whether electrode set was prespecified.
- **Improvement:** Forest plot of delta F1 with 95% CI and multiplicity-adjusted p; raw paired points in supplement.

### Figure 6 — Single-channel F1 (p. 8)

- **Intended demonstration:** Each electrode operating as a self-contained detector.
- **Does it demonstrate it?** Descriptively, yes.
- **Problems:** Redundant with Figure 7; no variability/sample size; “detection F1 of every electrode” may imply independent electrodes despite shared sessions; tiny values near zero are unreadable.
- **Caption change:** Add n, macro definition, and that the complete detector was recalibrated separately for each electrode.
- **Improvement:** Merge with Figure 7; rank plot with intervals and fixed cross-corpus electrode order.

### Figure 7 — Single-channel versus full montage (p. 9)

- **Intended demonstration:** Loss caused by single-channel input.
- **Does it demonstrate it?** Partly.
- **Problems:** Same bar/significance limitations as Figure 5; no exact statistics; large plotting area devoted to near-zero electrodes; corrected families differ across corpora without being prominent.
- **Caption change:** Add exact n and family sizes, rank-biserial effects, and the exploratory nature of per-electrode testing.
- **Improvement:** Delta forest plot; combine Figures 3–7 into one primary summary and detailed supplement.

### Figure 8 — Epoch duration (p. 9)

- **Intended demonstration:** Fp1/Fp2 performance stability from 10–120 s.
- **Does it demonstrate it?** Means are shown, but visual scale overstates changes.
- **Problems:** Y-axis begins at 70%; no error bars/raw paired values; stars show significance although differences are practically tiny; selecting only the two best electrodes from Experiment 1 is same-data outcome selection; caption calls them “consistently best-performing” but does not label analysis exploratory.
- **Caption change:** Disclose post-selection, n, test family, exact effect/range, and that bars are session means without uncertainty.
- **Improvement:** Full 0–100 panel plus a delta-from-30-s panel with bootstrap CI and paired session lines; report practical-equivalence bounds rather than infer stability from nonsignificance.

### Figure 9 — Precision–recall scatter (p. 10)

- **Intended demonstration:** Session heterogeneity and different operating tendencies of the three implementations.
- **Does it demonstrate it?** It shows dispersion, but the oracle-channel protocol undermines interpretation.
- **Problems:** Every point is chosen at the highest-F1 channel using ground truth; dense overplotting; large mean markers obscure points; “Proposed-approach” terminology differs from text; no paired lines/intervals; axes are percentages but F1 selection shapes the plotted P/R distribution.
- **Caption change:** Begin with “Oracle analysis”; state that reference labels selected the channel separately for every method/session; give n and note points are not prospective operating points.
- **Improvement:** Primary fixed-channel scatter; show paired per-session differences or marginal distributions; use transparency/faceting and confidence ellipses only if justified.

## 8. Table-by-table and caption audit

### Table I — Headline strategy F1 (p. 10)

- **Intended demonstration:** Proposed method has higher average F1 than two tested implementations.
- **Does it demonstrate it?** It reports the means, but not a scientifically complete comparison.
- **Problems:** Oracle channel selection; BLINKER incomplete; no n, dispersion, CI, exact p, effect size, precision or recall; asterisks encode only thresholded significance; “four comparisons” are not obvious from the 2×2 baseline contrasts.
- **Caption change:** Name BLINKER condition “initial threshold stage,” name MNE version/parameters, disclose oracle selection and n, give family definition.
- **Improvement:** Add mean/median, CI/IQR, fixed-channel metrics, delta, adjusted p and rank-biserial `r`; preferably one row per method and dataset with precision/recall/F1.

### Tables II–III — Regional rerun statistics (p. 14)

- **Intended demonstration:** Per-electrode regional-versus-full differences.
- **Does it demonstrate it?** Only means, deltas and binary significance.
- **Problems:** Captions are excessively long and all-caps; exact adjusted p-values promised in Results are absent; no effect sizes, intervals, or pair counts; “all sessions common” is not quantified; tiny significant differences lack practical context.
- **Caption change:** Shorten to one declarative sentence and move test details to a shared table note.
- **Improvement:** Add `n`, adjusted p, rank-biserial effect and CI; machine-readable supplementary CSV.

### Tables IV–V — Single-channel statistics (p. 15)

- **Intended demonstration:** Per-electrode single-channel-versus-full differences.
- **Does it demonstrate it?** Same partial support as Tables II–III.
- **Problems:** Same missing statistics; oversized captions; page 15 contains excessive whitespace caused by float placement; table headings wrap awkwardly; no equivalence test for Fp1/Fp2, so nonsignificance is incorrectly suggestive of retained/comparable performance.
- **Caption change:** State that failure to reject does not establish equivalence.
- **Improvement:** Add prespecified equivalence margins and paired CI if “retained most/comparable” is a claim; reformat as landscape supplement or split machine-readable tables.

### Recommended concise shared appendix caption pattern

> **Table II. Regional-input versus full-input per-electrode F1 in Internal (`n = …` paired sessions).** Values are session-mean F1; ΔF1 is regional minus full input. `p_adj` is the two-sided Wilcoxon signed-rank p-value adjusted across 24 electrodes; `r_rb` is matched-pairs rank-biserial correlation. Electrode regions and all exclusions were prespecified as described in Section … .

## 9. Terminology and definition consistency

| Current terms | Problem | Recommended controlled term |
|---|---|---|
| naturalistic driving / simulated lane-keeping | Ecological setting is inconsistent. | **simulated-driving lane-keeping task** throughout. |
| epoch-aware / adaptive / local statistical context | One threshold per channel/session is estimated from pooled selected epochs; it is not separately adapted per epoch. | **candidate-epoch-conditioned, session-specific threshold**. |
| blink activity / blink artifact / blink event / blink region | Physiological event, signal manifestation and predicted interval are conflated. | **reference blink event** (label), **ocular transient** (signal), **predicted blink region** (algorithm output). |
| full montage / all 32 channels | The two datasets’ 32-channel sets differ and Cao includes A1/A2 mastoids. | **dataset-specific 32-channel input**; list channels and channel types. |
| Internal / internal dataset | Capitalization treats a generic adjective as a proper name. | Give the corpus a stable descriptive name or use **internal corpus** consistently. |
| Cao2018 / Cao et al. 2019 | Year/name relationship is unexplained. | Define: “Cao2018 (dataset release name; publication year 2019)” if accurate. |
| session | For Internal it appears to mean one 30-min video segment; public participants have multiple sessions. | Distinguish **participant**, **recording**, **30-min segment**, and **analysis unit**. |
| macro-F1 | Macro is over sessions after an oracle channel choice; this is not macro class F1. | **mean session-level event F1** (and define selection). |
| reliable / robustness / stability | Used without reliability, perturbation, or equivalence analyses. | Use quantitative terms: **higher F1**, **range across durations**, **replicated ranking**. |
| baseline | Full published algorithms and extracted stages are mixed. | **complete comparator**, **threshold-stage ablation**, or **software default**, as applicable. |

Undefined/incompletely defined items include the exact `k` in the active PDF, “valid epoch,” blink-region extraction/merging rules, threshold polarity, zero-candidate behavior, corrected family structure, and the meaning of “complete recording session.”

## 10. Ethics, reporting guidance, and omitted limitations

### 10.1 Applicable guidance

- **COBIDAS-MEEG** is the most directly relevant reporting framework. It calls for sufficient acquisition, preprocessing, statistical, exclusion, and data-sharing details to understand and replicate M/EEG studies. See the [OHBM report](https://www.humanbrainmapping.org/files/2020/COBIDAS-MEEG_NatNeuro_revised.pdf), [acquisition guidance](https://cobidasmeeg.wordpress.com/2018/08/07/acquisition-reporting/), and [analysis guidance](https://cobidasmeeg.wordpress.com/2018/08/07/biophysical-and-statistical-analyses/).
- **STROBE** is useful for reporting the internally collected observational human dataset—participant selection, numbers at each stage, descriptive characteristics, missing data, and precision—though this is primarily an algorithm-validation paper, not a classical epidemiological cohort. See the [official STROBE checklist](https://www.strobe-statement.org/fileadmin/Strobe/uploads/checklists/STROBE_checklist_v4_combined.pdf).
- CLAIM, TRIPOD-AI, CONSORT, PRISMA, ARRIVE, and STARD are **not primary fits**: this is not medical imaging AI, a clinical prediction model, randomized trial, systematic review, animal experiment, or diagnostic-accuracy study against a clinical target. Do not claim compliance merely to add a checklist.

### 10.2 Missing declarations/reporting

| Item | PDF status | Action |
|---|---|---|
| Internal ethics committee and approval number | Absent | Add committee, institution, approval ID/date, and whether protocol covered synchronized face video and data sharing. |
| Informed consent | Absent | State written consent, including video/EEG and secondary use; explain anonymization. |
| Recruitment/eligibility/demographics | Absent | Report participant count, age/sex and relevant eligibility; clarify repeated recordings. |
| Public-data ethical provenance/license | Only dataset citation | State repository/version, license/terms, original ethics, download date and file list. |
| Data availability | Absent | Explain access to raw internal data, derived annotations, Cao annotations, and de-identification constraints. |
| Code availability | GitHub footnote points to a public but empty repository as of 1 October 2026 | Upload the complete version used for the paper, then add version/commit, environment lockfile, license, archived DOI, run commands and mapping to figures/tables. |
| Annotation availability | Absent | Release interval labels and adjudication/exclusion log where consent/license permits. |
| Conflicts of interest | Absent | Add explicit declaration. |
| Author contributions | Absent | Add CRediT roles. |
| Funding role | Grant acknowledged | State funder role in design, analysis, writing and submission. |
| Preregistration/protocol | Absent | State whether analyses and parameter choices were prespecified; label exploratory analyses. |

### 10.3 Limitations omitted from the current p. 11 paragraph

The Limitations section should explicitly cover, in descending importance:

1. No ablation isolates candidate-epoch screening from estimator/multiplier/extraction differences.
2. Headline results are oracle best-channel performance chosen with reference labels.
3. BLINKER is incomplete and MNE uses a default threshold; the comparison is not a full modern benchmark.
4. Internal participant count and repeated-session dependence are unknown; sessions/segments may not be independent.
5. Whole-session calibration uses future data and is not an online/causal detector.
6. The public labels were created from Fp1/Fp2 EEG morphology, creating potential incorporation bias when evaluating EEG detectors, especially at those channels.
7. The second rater reviewed the first rater’s labels, so independent agreement is unknown.
8. Four of 62 public sessions disappear from analysis without a PDF-level exclusion account.
9. IoU = 0.1 is permissive; conclusions may depend on tolerance and event merging.
10. `k`, Stage A threshold optimization, epoch duration, filter, minimum duration and channel union have insufficient sensitivity analysis.
11. The two datasets are both simulated lane-keeping and do not establish on-road, clinical, cross-task or cross-population generalization.
12. Hardware replication is confounded by montage, annotation modality, dataset, participant population and protocol.
13. No prospective fixed-channel selection, external untouched test corpus, online latency, computational cost, calibration drift, missing-channel, noise or movement robustness evaluation is shown.
14. Prolonged closures and partial blinks are pooled; drowsiness-relevant event-type performance is unknown.
15. No equivalence test supports claims that Fp1/Fp2 “retained” performance; nonsignificance is not equivalence.

## 11. Sentence-level scientific and clarity corrections

1. **Original (p. 1):** “As a result, blink information can be extracted from EEG recordings, either by analysing the ocular components embedded in the EEG signal [5, 8].”  
   **Problem:** “Either” introduces only one alternative; sentence is grammatically incomplete.  
   **Suggested:** “Blink information can therefore be extracted by analysing ocular components embedded in EEG recordings [5, 8].”

2. **Original (p. 2):** “When thresholds are estimated from the entire recording, they may be biased by the presence of clean epochs that contain few or no blinks, which may distort threshold estimates and suppress blink detection…”  
   **Problem:** For the manuscript’s own BLINKER account, clean epochs lower the threshold and increase false positives, not suppress detection; the direction depends on estimator.  
   **Suggested:** “The effect of pooling blink-rich and blink-poor intervals depends on the estimator: it may lower a location/dispersion threshold and increase false positives, whereas a range-based threshold may be raised by isolated excursions and increase false negatives.”

3. **Original (p. 2):** “This paper makes several contributions…” followed by “among the first frameworks.”  
   **Problem:** Novelty is asserted without a close prior-art comparison.  
   **Suggested:** “We evaluate an explicit composition of candidate-epoch screening and robust channel-wise threshold calibration; both constituent techniques have prior precedents.”

4. **Original (p. 2):** “a zero-phase band-pass filter … is applied which is removes…”  
   **Problem:** Grammar.  
   **Suggested:** “A zero-phase 1–20 Hz band-pass filter is applied to remove slow drift and attenuate high-frequency muscle and line noise.”

5. **Original (p. 2):** “Epoching is what makes the thresholds adaptive…”  
   **Problem:** The threshold remains one session-level value per channel; epoching alone does not make it adaptive.  
   **Suggested:** “Epoching enables candidate-epoch selection; Stage B then estimates one session-specific threshold per channel from the pooled selected epochs.”

6. **Original (p. 3):** “Instead, a channel-specific threshold … is calculated from each of the channel’s.”  
   **Problem:** Incomplete sentence.  
   **Suggested:** “Instead, a channel-specific threshold is estimated from that channel’s distribution of epoch peak-to-peak amplitudes.”

7. **Original (p. 3):** “The resulting set of candidate epochs is defined as The set of suspicious epochs is therefore can be represented as below;”  
   **Problem:** Duplicated, ungrammatical prose and terminology shift.  
   **Suggested:** “The candidate-epoch set is therefore” followed by Eq. (2).

8. **Original (p. 4):** “Let ξc be the channel-specific center … which can be express as below:”  
   **Problem:** Grammar and unnecessary lead-in.  
   **Suggested:** “The channel-specific centre is the median” followed by Eq. (4).

9. **Original (p. 4):** “Two EEG corpora … providing 104 complete recording sessions in total.”  
   **Problem:** The subsequent available counts total 108, while results use 104 after an unexplained four-recording loss.  
   **Suggested:** “The corpora provided 108 recordings; 104 were analysed after excluding four Cao2018 recordings for [prespecified reasons].”

10. **Original (p. 9):** “BLINKER was represented by its threshold-crossing stage but blink marphological-fitting step and automatic channel selection were not used.”  
    **Problem:** Grammar/typo and scientifically crucial comparator truncation is underemphasized.  
    **Suggested:** “We evaluated only BLINKER’s initial threshold-crossing rule; its morphological fitting and automatic channel-selection stages were omitted. This condition is therefore a BLINKER-stage ablation, not the complete BLINKER algorithm.”

11. **Original (pp. 9–10):** “This consideration favours no method in particular, since each is evaluated at its best-performing channel.”  
    **Problem:** It favors all methods via label leakage and does not establish fairness if channel-selection mechanisms differ.  
    **Suggested:** “This oracle analysis gives each method an optimistic upper bound because the reference labels select the best channel separately in every session; it does not represent prospective channel selection.”

12. **Original (p. 10):** “channel.Session-level F1…”  
    **Problem:** Missing space.  
    **Suggested:** “channel. Session-level F1…”

13. **Original (p. 11):** “Both failures are consistent with calibrating the threshold on the whole recording.”  
    **Problem:** “Consistent with” is acceptable, but subsequent sentences present the mechanisms as facts despite no threshold logs/ablation.  
    **Suggested:** “Both patterns are compatible with, but do not establish, a whole-recording calibration effect; the current comparison also changes estimator, multiplier, and post-processing.”

14. **Original (p. 11):** “Its advantage therefore does not appear to depend on a particular recording system…”  
    **Problem:** Two confounded datasets cannot isolate recording-system dependence.  
    **Suggested:** “The method ranking replicated in a second corpus acquired with different hardware, although hardware was confounded with montage, participants, protocol, and annotation modality.”

15. **Original (p. 11):** “supporting epoch screening as the principal methodological contribution…”  
    **Problem:** Unsupported causal attribution.  
    **Suggested:** “showing that the complete candidate-epoch-conditioned configuration had higher F1 than the two tested baseline implementations; an ablation is needed to isolate the contribution of epoch screening.”

## 12. Simulated journal reviewers

### Reviewer A — Domain expert

**Major concerns**

1. The title mislabels simulated lane-keeping as naturalistic driving.
2. Cao2018 ground truth is inferred from Fp1/Fp2 morphology, then the paper concludes Fp1/Fp2 are optimal. This is a serious incorporation-bias alternative.
3. The paper equates blink detection with fatigue-monitoring usefulness without evaluating blink duration classes, prolonged closure, blink-rate error, or downstream fatigue discrimination.
4. Internal cohort participant/demographic/ethical provenance is missing.

**Minor concerns**

- Distinguish blink physiology from ocular transient morphology and detector interval.
- Explain partial blink labeling and its drowsiness relevance.
- Clarify the region map, mastoids and excluded midline channels.

**Questions for authors**

- Were Cao labels assigned without knowledge of detector output and without preferentially trusting Fp1/Fp2?
- How many unique internal participants generated 46 segments?
- Are blinks, microsleeps and prolonged closures separated?

**Required experiments/analyses**

- Independent video/eye-tracker validation on a held-out corpus.
- Event-type and duration-stratified analysis; blink-count/rate error.
- Fixed frontopolar channel evaluation selected before seeing test labels.

**Required textual changes**

- Replace naturalistic/reliable/generalizable language; state offline simulated-driving scope.

### Reviewer B — Methods/statistics expert

**Major concerns**

1. No experiment isolates epoch screening; the conclusion is causally overidentified.
2. Per-session best-channel selection is a label-informed oracle.
3. BLINKER is incompletely implemented and cannot support a superiority claim over BLINKER.
4. Session independence is unknown; participants may contribute repeated segments.
5. Statistical methods are absent from Methods; appendix omits promised p-values/effects.

**Minor concerns**

- IoU 0.1 requires sensitivity analysis.
- Non-significance is interpreted as stability/retained performance without equivalence testing.
- Means and stars should be supplemented by distributions and uncertainty.

**Questions for authors**

- Was `k=3` fixed before inspecting labels, and why is BLINKER’s published 1.5 multiplier not factorially crossed?
- How were empty candidate sets, overlapping crossings, and session boundaries handled?
- Were the four excluded public recordings removed before or after viewing performance?

**Required experiments/analyses**

- Full factorial pool × estimator × multiplier ablation.
- Fixed-channel and nested-selection evaluation.
- Participant-clustered uncertainty and sensitivity to matching rules.

**Required textual changes**

- Rename oracle results, distinguish full methods from component ablations, and remove causal language.

### Reviewer C — Skeptical general reviewer

**Major concerns**

1. Novelty is not positioned against close unsupervised/adaptive methods from 2016–2026.
2. The main experiment is buried after redundant channel plots.
3. No dedicated availability, ethics, reproducibility or complete cohort-flow statements.
4. The Discussion explains rather than tests alternative mechanisms.

**Minor concerns**

- Figures 3–7 are repetitive and difficult to read.
- Figure 8’s truncated scale is visually misleading.
- Numerous grammatical errors remain in Methods.

**Questions for authors**

- What exact capability is novel beyond composing autoreject and robust amplitude thresholding?
- Why are contemporary *Blink*, adaptive real-time, CNN and ARMBR methods absent?
- Can every table and figure be regenerated from a tagged archive?

**Required experiments/analyses**

- At minimum, controlled ablation and complete/fair baseline reruns.
- Preferably, one untouched external/video-labeled evaluation.

**Required textual changes**

- Add Related Work; reorganize results; revise title/abstract/conclusion; consolidate visuals.

## 13. Difficult adversarial questions for the authors

1. What experiment uniquely identifies candidate-epoch screening—rather than median versus mean, MAD scaling, `k`, or post-processing—as the cause of the F1 gain?
2. What is the F1 of the proposed median/MAD/`k` rule when calibrated on **all** epochs?
3. What is the F1 of the BLINKER threshold formula when calibrated on the **same selected candidate epochs**?
4. Why was `k` chosen, when was it chosen, and was the choice made without viewing either corpus’s reference labels?
5. Why is an incomplete BLINKER threshold stage called BLINKER in the abstract/table rather than a BLINKER-stage ablation?
6. How does the complete published BLINKER pipeline perform under the same event-matching protocol?
7. Why is per-session best-channel selection not described as an oracle, and how would a deployed system choose that channel without labels?
8. What are results at prespecified Fp1 and Fp2, and after channel selection using only development subjects?
9. How many unique internal participants generated the 46 “sessions,” and how many segments/recordings came from each participant?
10. Why does the Methods text describe 62 + 46 = 108 available recordings while the total and analyses use 104?
11. What were the exact prespecified exclusion reasons for the four omitted Cao2018 recordings, and were their detector outputs examined before exclusion?
12. Could annotation from Fp1/Fp2 morphology make Fp1/Fp2 appear optimal by construction in Cao2018?
13. What independent agreement is obtained when two raters annotate the same recordings from scratch?
14. How sensitive are findings to IoU thresholds of 0.2, 0.3 and 0.5 and to onset/offset tolerances?
15. How are adjacent threshold crossings merged, and what minimum/maximum event durations are enforced?
16. What happens when no epoch passes Stage A or when candidate epochs are dominated by motion/electrode artifacts?
17. Are actual session thresholds and their differences across methods available, and do they support the proposed dilution mechanism?
18. Does a high-amplitude nonocular artifact trigger the Stage A union rule and contaminate Stage B thresholds across channels?
19. Because whole-session calibration accesses future samples, what evidence supports any practical/online implication?
20. Does “stable across epoch durations” mean statistically equivalent within a prespecified margin, or only that most null hypotheses were not rejected?
21. Why were only Fp1/Fp2 tested for duration sensitivity after they were selected on the same datasets?
22. Why does Figure 8 truncate its y-axis at 70% when the practical differences are mostly below one percentage point?
23. Are the same recordings used to select channels, choose parameters, construct figures, and claim generalization?
24. Which acquisition system, electrode material, original sampling rate, impedance procedure and participant demographics apply to the internal corpus?
25. What is the exact ethical approval and consent basis for synchronized identifiable face video?
26. Can the new manual interval labels—especially for Cao2018—be released with adjudication and exclusion metadata?
27. How do performance and count error differ for normal blinks, partial blinks, prolonged closures and nonblink ocular movements?
28. How much of the apparent cross-dataset robustness is attributable to the permissive 0.1 overlap rule?
29. Why should readers interpret two simulated lane-keeping corpora as naturalistic or generalizable to real driving?
30. What computational cost, latency, memory and calibration-window evidence supports the word “practical”?

## 14. Minimum revision set before the novelty/mechanism claims are defensible

### Essential

1. Candidate-versus-all-epoch factorial ablation under an identical threshold estimator, multiplier and event extractor.
2. Complete BLINKER comparison or explicit relabeling of the current condition as a component ablation.
3. Fixed/prespecified channel evaluation; retain oracle best-channel only as a secondary upper bound.
4. Participant/session/exclusion flow and participant-aware analysis.
5. Full algorithm specification and restored Statistical Analysis section.
6. Ethics/consent and data/code/annotation availability declarations.
7. Title/abstract/discussion/conclusion rewritten to offline simulated-driving scope and noncausal language.

### Strongly recommended

1. IoU/onset-offset/count sensitivity and independent annotation subset.
2. Threshold logging and artifact-stratified error analysis to test the proposed mechanism.
3. Add *Blink* 2019, real-time adaptive 2016, ARMBR 2025, Rejer 2025 and Zhong 2026 to Related Work; evaluate at least one stronger modern method if feasible.
4. Rebuild figures around distributions, confidence intervals and differences; consolidate Figures 3–7.
5. Prospective video/eye-tracker-labeled external validation.

### Optional

1. Online moving-window implementation and latency profiling.
2. Noise, missing-channel, movement, sampling-rate and device perturbation tests.
3. Downstream fatigue-estimation analysis using detector-derived blink metrics.

## 15. Source list used for this specialist audit

- Kleifges et al. (2017), BLINKER: https://doi.org/10.3389/fnins.2017.00012
- Jas et al. (2017), autoreject: https://doi.org/10.1016/j.neuroimage.2017.06.030 and https://pmc.ncbi.nlm.nih.gov/articles/PMC7243972/
- Chang et al. (2016), single-prefrontal detection: https://doi.org/10.1016/j.cmpb.2015.10.011
- Chang, Lim & Im (2016), unsupervised real-time adaptive detection: https://doi.org/10.1088/0967-3334/37/3/401
- Agarwal & Sivakumar (2019), *Blink*: https://doi.org/10.1109/ALLERTON.2019.8919795 and https://gnan.ece.gatech.edu/archive/agarwal-blink.pdf
- Shahbakhti et al. (2021), VME-DWT: https://doi.org/10.1109/TNSRE.2021.3054733
- Jiang et al. (2023), VME and morphological feature extraction: https://doi.org/10.1109/JSEN.2023.3305118
- McCloy et al. (2025), ARMBR: https://pmc.ncbi.nlm.nih.gov/articles/PMC12539671/
- Rejer & Gago (2025), CNN blink episodes: https://doi.org/10.1088/1741-2552/add49d
- Wang (2025), sliding-window higher-order cumulants: https://doi.org/10.7717/peerj-cs.3249
- Zhong et al. (2026), portable two-channel platform: https://doi.org/10.1016/j.jneumeth.2025.110616
- MNE `find_eog_events` official documentation: https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html
- Manuscript-linked code repository (empty when checked 1 October 2026): https://github.com/pyresearchs/double_thresholding_blink
- OHBM COBIDAS-MEEG report: https://www.humanbrainmapping.org/files/2020/COBIDAS-MEEG_NatNeuro_revised.pdf
- Official STROBE materials: https://www.strobe-statement.org/

---

**Specialist verdict:** The paper contains a potentially useful, interpretable candidate-epoch-conditioned implementation and a valuable dual-corpus validation effort. At present, however, the evidence supports only the performance of the **complete configuration under an offline oracle-channel protocol**. It does not establish that epoch screening caused the improvement, that the method is superior to complete BLINKER or contemporary detectors, that the detector is reliable, or that results generalize beyond two simulated-driving corpora.
