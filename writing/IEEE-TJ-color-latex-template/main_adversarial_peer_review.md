# Adversarial Scientific and Reproducibility Audit

**Manuscript:** *Epoch-Aware Threshold Estimation for Blink Detection in Naturalistic Driving EEG*  
**Primary artifact:** `main.pdf` (15 pages; build inspected 1 October 2026)  
**Audit date and literature cutoff:** 1 October 2026  
**Audit mode:** Lead-agent consolidation of three independent specialist tracks: (i) claims, citations, bibliography, and datasets; (ii) methods, statistics, code, leakage, and reproducibility; and (iii) novelty, manuscript structure, figures, tables, ethics, and simulated peer review.

This is a pre-submission scientific audit, not a publication recommendation. The PDF was treated as the authoritative manuscript, with LaTeX sources, archived result tables, and repository code used to test traceability and reproducibility. External claims were checked primarily against original articles, publisher/PubMed/PMC records, official dataset records, and official software documentation.

---

## PART A — EXECUTIVE SCIENTIFIC ASSESSMENT

### What the paper claims

The paper proposes a three-stage, offline blink-region detector for simulated-driving EEG: cross-validated peak-to-peak thresholds identify candidate high-amplitude epochs; samples from those epochs calibrate a channel-wise median-plus-scaled-MAD threshold; and threshold crossings are converted to blink regions. It reports higher session-macro F1 than implemented BLINKER-style and MNE configurations on an Internal corpus and the Cao sustained-attention corpus, identifies Fp1/Fp2 as strong channels, and reports limited changes over 10–120 s epoch durations.

### What is genuinely supported

The archived strategy-comparison tables reproduce the reported numerical direction. Under the archived pipeline, IoU = 0.1, full-session calibration, and reference-label-selected best channel in every session, the complete proposed configuration has higher mean F1 than the two implemented comparator configurations:

| Corpus | Analyzed sessions | Proposed | BLINKER-style | MNE | Proposed minus BLINKER-style | Proposed minus MNE |
|---|---:|---:|---:|---:|---:|---:|
| Internal | 46 | 0.8825 | 0.7654 | 0.6664 | +0.1171 | +0.2161 |
| Cao2018 | 58 | 0.8068 | 0.6940 | 0.5627 | +0.1127 | +0.2440 |

Independent recalculation reproduces the session-level Wilcoxon significance direction. A simple subject-aggregated sensitivity analysis also remains significant for these four headline comparisons. This supports a **configuration-level performance difference**; it does not identify its cause or establish deployable performance.

### What remains uncertain

The central mechanism is not identified. Relative to the BLINKER-style comparator, the proposed condition changes the calibration pool, centre estimator, multiplier (`k=3.0` versus `1.5`), multichannel AutoReject gate, and tuning history. The experiment therefore cannot establish that epoch screening caused the gain. In addition, the headline F1 is an oracle upper bound: the best channel is selected separately for every method and test session using reference labels. Four public sessions are silently excluded, repeated sessions are treated as independent, the public labels are inferred from the same EEG morphology being detected, and the Internal analyses contain a montage error that can propagate through the all-channel Stage-A union.

### Strongest contribution

The strongest potentially publishable contribution is an interpretable **candidate-epoch-conditioned threshold-calibration configuration**, together with empirical channel and epoch-duration characterization across two simulated-driving corpora. This is best described as incremental methodological/engineering novelty plus validation novelty.

### Greatest threat to validity

The greatest threat is the combination of unisolated causal factors and label-informed oracle evaluation. The reported advantage cannot presently be assigned to epoch screening, and the primary scores do not represent a channel-selection rule usable on unseen data.

### Greatest threat to novelty

The method composes established elements from AutoReject, BLINKER-like thresholding, robust statistics, and prior adaptive or individualized blink detectors. The exact composition may be distinctive, but the manuscript does not yet show that this composition—rather than its multiplier or other accompanying choices—produces the advantage.

### Most important missing experiment

Run a participant-held-out, fixed-channel factorial comparison with identical preprocessing and event extraction:

`calibration pool {all epochs, screened epochs} × centre {mean, median} × k {1.5, 3.0}`.

The irreducible minimum is all-epoch median/MAD at `k=3` versus screened-epoch median/MAD at `k=3`. Without that matched contrast, the causal claim about epoch screening should be removed.

---

## PART B — TOP 10 MOST IMPORTANT PROBLEMS

### 1. The claimed cause of improvement is confounded — **CRITICAL**

**Evidence:** The PDF attributes the improvement to epoch screening. The archived implementation uses screened epochs, a median centre, `k=3.0`, and a multichannel AutoReject union; the BLINKER-style condition uses all epochs, a mean centre, `k=1.5`, and no gate. The manuscript’s own inactive text acknowledges that both centre and multiplier differ and that thresholds were not recorded.

**Consequence:** The main mechanistic conclusion is not identified. A doubled multiplier alone could raise precision and reduce false positives.

**Correction:** Run the factorial ablation above, log thresholds and candidate-pool composition, and use configuration-level wording until the screened-versus-all contrast is isolated.

### 2. Headline F1 is a test-label-selected channel oracle — **CRITICAL**

**Evidence:** The Results state that the channel with the highest F1 is retained. `experiment_script/paper_data.py` explicitly labels this a best-channel-per-session oracle and applies an F1 argmax after comparison with reference labels.

**Consequence:** The score cannot be achieved prospectively without labels and omits channel-selection error. Giving each method the same oracle does not remove optimism.

**Correction:** Make fixed Fp1/Fp2, a prespecified channel, or training-fold/nested subject-wise channel selection primary. Retain the current analysis only as an explicitly named oracle upper bound.

### 3. The Internal montage is wrong and can contaminate every Internal result — **CRITICAL**

**Evidence:** The paper describes 32 channels including Cz and P5. The archived configuration states that E129/Cz was unavailable, uses P8, and admits that pre-fix runs included off-montage E84 because of an O2 mapping error. Published CSVs contain E83 and E84 but no E129. Stage A takes the union of flags over all channels.

**Consequence:** E84 can change which epochs enter Stage B for every channel, so dropping E84 only from output tables does not repair the analysis.

**Correction:** Freeze a valid montage manifest, rerun every Internal experiment from raw data, and regenerate all Internal figures, tables, and claims.

### 4. Implemented preprocessing contradicts the manuscript — **CRITICAL**

**Evidence:** The PDF and Fig. 1 say continuous downsampling/filtering precedes epoching. Code creates epochs first, then filters and resamples each epoch independently.

**Consequence:** Repeated epoch-edge operations can create duration-dependent artifacts. This directly confounds the epoch-length experiment and makes the paper non-reproducible from its description.

**Correction:** Rerun with continuous preprocessing before epoching, or accurately report the implemented order and demonstrate that edge handling does not drive results.

### 5. The BLINKER comparator is incomplete and mischaracterized — **CRITICAL**

**Evidence:** The manuscript omits BLINKER’s morphology fitting and automatic channel selection but labels the threshold-crossing fragment “BLINKER.” It also says BLINKER uses a robust centre-plus-dispersion initial threshold. The original method’s initial detector uses whole-signal mean + 1.5 ordinary SD; scaled MAD appears later in candidate-amplitude filtering ([BLINKER full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC5289990/)).

**Consequence:** The paper neither compares against full BLINKER nor accurately attributes its own Stage-B formula. The superiority claim and method provenance are misleading.

**Correction:** Rename the condition “BLINKER-style initial-threshold ablation,” implement full BLINKER separately, and describe the proposed median/MAD rule as an adaptation/new construction.

### 6. Hyperparameter selection used the evaluated suite — **MAJOR**

**Evidence:** `src/exp/exp6_std_threshold_sweep.py` states that its ablation selected `std_threshold=3.0` “for the rest of the suite.” The PDF defines only `k>0` and does not disclose the selected value or a held-out selection set.

**Consequence:** This is supervised tuning on evaluation corpora unless nested or separated by locked subjects. Reported performance is optimistic and the comparison gives the proposal more tuning than the baseline.

**Correction:** Disclose the full sweep and selection rule; freeze parameters on development participants and evaluate once on locked subjects or use nested subject-wise validation.

### 7. Dataset flow and experimental units are misreported — **MAJOR**

**Evidence:** Methods says 104 total sessions but describes 62 Cao + 46 Internal = 108. Results contain 58 Cao sessions. A commented source line identifies four unresolved Cao annotations as excluded. Archived IDs show 46 Internal sessions from 17 participants and 58 Cao sessions from 27 participants.

**Consequence:** Exclusions and selection bias cannot be assessed, and treating sessions as independent pseudoreplicates people. Subject-level uncertainty is understated.

**Correction:** Add a participant/session flow table with all exclusions and timing; use participant aggregation, cluster bootstrap/permutation, or mixed-effects analysis.

### 8. Ground truth is not sufficiently independent — **MAJOR**

**Evidence:** Cao labels were created from EEG high-amplitude morphology with Fp1/Fp2 displayed by default, then amplitude-based EEG detectors are evaluated and Fp1/Fp2 are declared optimal. The second rater reviewed the first rater’s annotations rather than independently annotating the full sample. Internal boundaries also used EEG/EOG to refine video labels.

**Consequence:** Incorporation bias can inflate apparent accuracy and frontopolar superiority; independent inter-rater reliability is unknown.

**Correction:** Independently annotate a held-out video/eye-tracker subset, blind raters to method outputs, report independent agreement, and analyze sensitivity to annotation modality.

### 9. Event validation is lenient and incomplete — **MAJOR**

**Evidence:** A one-to-one event match is accepted at IoU ≥ 0.1. The cited review supports event matching but not this threshold; it illustrates stricter values and warns that matcher details affect scores ([Startsev & Zemblys](https://doi.org/10.3758/s13428-021-01763-7)). MNE emits fixed ±100 ms windows while threshold crossings have variable boundaries.

**Consequence:** A detector can receive full event credit despite poor onset/offset or duration localization, and method-specific interval geometry can affect F1.

**Correction:** Report IoU curves at 0.1/0.25/0.5/0.75, onset/offset/duration error, count bias, and false positives per minute; harmonize or explicitly analyze event construction.

### 10. The reproducibility and human-subject reporting claims fail — **MAJOR**

**Evidence:** The linked [GitHub repository](https://github.com/pyresearchs/double_thresholding_blink) was empty on 1 October 2026. A fresh import fails because required historical `pyblinker` modules are absent; dependencies are unpinned. The PDF lacks Internal participant count/demographics, ethics approval, consent, data availability, and a usable code release.

**Consequence:** An independent group cannot regenerate the study or assess ethical and population validity.

**Correction:** Publish an immutable tagged/DOI archive with exact environment, dependency commits, manifests, annotations where permitted, and one-command workflows; add complete ethics and availability statements.

---

## PART C — CRITICAL AND MAJOR ISSUES

### Consolidated master issue table

| ID | Severity | Section | Manuscript statement/issue | Reviewer concern | Evidence | Consequence | Recommended correction |
|---|---|---|---|---|---|---|---|
| A01 | CRITICAL | Abstract; Results; Conclusion | Improvement is attributed to epoch screening | Pool, centre, multiplier, gate, and tuning all change | PDF pp. 1, 9–11; archived configs/code | Causal mechanism unidentified | Matched factorial ablation; configuration-level wording |
| A02 | CRITICAL | Results; Table I; Fig. 9 | Best channel retained per session/method | Test labels choose the operating channel | PDF pp. 9–10; `paper_data.py` oracle | Optimistic, non-deployable headline F1 | Fixed/nested channel primary; oracle secondary |
| A03 | CRITICAL | Dataset; Figs. 2–7 | Internal uses stated 32-channel montage | Actual archive has no Cz, includes erroneous E84 | montage YAML and CSVs | All-channel Stage-A contamination | Correct manifest and rerun all Internal analyses |
| A04 | CRITICAL | Preprocessing; Fig. 1 | Filter/resample continuous data before epoching | Code epochs before per-epoch filter/resample | experiment and epoch-input code | Edge artifacts confound duration results | Rerun continuous preprocessing; document filter design |
| A05 | CRITICAL | Baselines; Discussion | Comparator is “BLINKER” | Only threshold stage used; method formula misattributed | PDF p. 9; original BLINKER paper | Baseline unfairness and provenance error | Full BLINKER plus clearly named stage ablation |
| A06 | MAJOR | Threshold method | `k` is a generic sensitivity multiplier | Proposed uses undisclosed k=3 chosen by same-suite sweep | `exp6_std_threshold_sweep.py` | Test-set tuning/optimism | Nested or locked development/test selection |
| A07 | MAJOR | Dataset | Two corpora provide 104 sessions | Described counts sum to 108; only 58/62 Cao analyzed | PDF p. 4; result CSVs; commented exclusion text | Hidden exclusions and selection risk | Full flow diagram and sensitivity analysis |
| A08 | MAJOR | Statistics | Sessions are paired independent observations | 17 Internal and 27 Cao people contribute repeated sessions | archived IDs | Pseudoreplication and narrow uncertainty | Participant-clustered inference |
| A09 | MAJOR | Ground truth | Two experts produce reference intervals | Second reviewer not independent; Cao is EEG-only | annotation section | Unknown reliability and incorporation bias | Independent blinded subset and agreement |
| A10 | MAJOR | Evaluation | IoU ≥ 0.1 defines a match | Threshold is unvalidated and permissive | PDF p. 5; Startsev review | Weak boundary evidence | IoU/boundary/count sensitivity |
| A11 | MAJOR | Baselines | All methods receive same preprocessed epochs | MNE filters 1–20 Hz again and uses fixed windows | wrapper and MNE docs | Functionally unequal comparator inputs | Once-filtered native/tuned variants |
| A12 | MAJOR | Stage A | Flagged epochs are likely blink-containing | AutoReject detects high PTP artifacts, not blink specificity | [AutoReject paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7243972/) | Unverified candidate-pool mechanism | Measure blink enrichment and artifact composition |
| A13 | MAJOR | Algorithm | Displayed equations define reproducible method | `b_i`, CV objective, k, polarity, fallback and >50 ms rule missing | PDF pp. 3–4; dormant equation source; code | Method cannot be reimplemented | Complete equations/pseudocode and parameter table |
| A14 | MAJOR | Statistics | Wilcoxon/Bonferroni establishes superiority/stability | No CI/effect in paper; family definitions fragmented; null ≠ equivalence | Tables I–V | Practical magnitude and uncertainty unclear | Cluster CIs, exact p, effects, equivalence margins |
| A15 | MAJOR | Selective reporting | Median/MAD supports robust improvement | Archived median-vs-mean ablation is nonsignificant | Internal p=.268; Cao p=.405 oracle; fixed-channel nulls | Component claim overstated | Restore negative ablation and interpret transparently |
| A16 | MAJOR | Code availability | Every result can be regenerated from released code | Linked repository is empty; imports fail; dependencies unpinned | live GitHub and fresh import | Reproducibility claim false | Versioned archive, lockfile, manifests, smoke test |
| A17 | MAJOR | Ethics/reporting | Human/video corpus used | No ethics board, approval ID, consent, demographics, recruitment | PDF end matter | Ethical and external-validity assessment impossible | Add complete human-subject declaration |
| A18 | MAJOR | Novelty | “Among the first” epoch-aware framework | Close adaptive/unsupervised methods absent | Chang 2016, Agarwal 2019, ARMBR 2025, Rejer 2025 | Novelty overstated | Component matrix and cautious novelty statement |
| A19 | MAJOR | Title/generalization | “Naturalistic driving EEG”; “reliable”; hardware-independent | Both datasets are simulated; no reliability or controlled device study | title, abstract, discussion | Scope overclaimed | Use simulated-driving and protocol-limited wording |
| A20 | MAJOR | Bibliography | References support claims and are complete | Several central citations mismatch; 30/49 incomplete | citation audit and publisher metadata | Scientific rationale and provenance weakened | Correct claims and rebuild bibliography metadata |
| A21 | MAJOR | Figures/tables | Visuals support stability and superiority | Means/stars dominate; Fig. 8 truncated; n/CI/exact p absent | Figs. 3–9; Tables I–V | Magnitude and heterogeneity obscured | Distributions, paired deltas, CIs, n, exact statistics |
| A22 | MAJOR | Generalization | Two datasets show recording-system independence | Hardware is confounded with protocol, montage, people, labels | corpus descriptions | No isolated cross-device evidence | Restrict claim or controlled cross-device/external test |

### Claim → evidence matrix

| Major claim | Evidence provided | Evidence sufficient? | Alternative explanation | Additional evidence required |
|---|---|---|---|---|
| Epoch screening improves detection | Proposed configuration beats two comparators | **No** | k, centre, full-montage gate, tuning, event rules | Matched pool-only contrast/factorial ablation |
| Proposed method is better than BLINKER | Higher F1 than a threshold-crossing implementation | **No** | Complete BLINKER stages were removed | Full BLINKER under same data/evaluation plus mechanism-matched ablation |
| Proposed method is better than MNE | Higher oracle F1 than one MNE configuration | **Partial** | MNE is double filtered, untuned, and given fixed windows | Fair native/tuned MNE variants and fixed-channel evaluation |
| Fp1/Fp2 are preferred channels | Highest means across analysed data | **Partial** | Same channels guided Cao labels; post-selection and montage errors | Independent-label corpus and held-out channel selection |
| Fp1/Fp2 retain full-montage performance | Small/nonsignificant mean differences | **No** for equivalence | Low power or wide heterogeneity | Prespecified equivalence margin and participant-cluster CI |
| Performance is stable over epoch duration | Mostly small mean changes/non-significant tests | **Partial** | Per-epoch filter edges; winner selection at 30 s | Correct preprocessing, equivalence analysis, held-out channels |
| Method is robust/reliable | Replication of ranking on two corpora | **No** | Same analysis team, oracle, lenient matching, simulated tasks | Reliability/agreement, seeds, noise/missing-channel tests, lower-tail results |
| Advantage is hardware-independent | Similar ranking on two acquisition systems | **No** | Hardware changes jointly with cohort, task details, labels, montage | Controlled cross-device recording or explicit limitation |
| Method is practical | Simple thresholding narrative | **No** | Full-session multichannel AutoReject optimization may be costly/offline | Runtime, memory, latency, streaming calibration |
| Ground truth is expert quality | Two-reviewer adjudication | **Partial** | Sequential review creates dependence; EEG-derived labels share cue | Independent blinded annotations and agreement |
| Code makes every result reproducible | GitHub footnote | **No; contradicted** | Repository is empty and historical dependencies unavailable | Immutable complete release and independent reproduction |
| The novelty is the three-stage pipeline | Components described and related papers cited | **Partial** | Integration may be incremental and close work is omitted | Current prior-art matrix and isolated benefit |

### What actually caused the improvement?

| Claimed improvement | Claimed cause | Other variables changed | Confounding risk | Required experiment |
|---|---|---|---|---|
| Proposed > BLINKER-style, both corpora | Candidate-epoch screening | Pool, mean→median, k 1.5→3, multichannel gate, tuning budget, removal of full BLINKER stages | **Very high** | 2 pool × 2 centre × ≥2 k factorial; full BLINKER separately |
| Proposed > MNE | Epoch-aware robust thresholding | MNE threshold rule, second filter, fixed 200-ms windows, channel oracle, tuning budget | **Very high** | Harmonized preprocessing/event geometry; native and fairly tuned MNE |
| Median configuration > mean configuration | Robust median centre | Oracle selection and same-suite exploration | **Moderate**, and archived effect is nonsignificant | Restore fixed-channel/nested comparison with CI |
| Fp1/Fp2 ≈ full montage | Frontopolar sufficiency | Winner selection on same data, Cao incorporation bias, Internal montage error | **High** | Held-out fixed-channel noninferiority after rerun |
| Stable across epoch lengths | Duration tolerance | Per-epoch filtering/resampling edge behavior and 30-s-based channel selection | **High** | Continuous preprocessing plus nested/prespecified channels |
| Replicates across hardware | Hardware robustness | Dataset, population, montage, annotation modality and protocol all change | **High** | Same subjects/task annotated independently on two devices |

### Statistical recalculation and interpretation

| Corpus | Comparison | Raw Wilcoxon p (session) | Bonferroni ×4 p | Rank-biserial r | Subject-aggregated sensitivity p |
|---|---|---:|---:|---:|---:|
| Internal | Proposed vs BLINKER-style | 2.26×10⁻⁵ | 9.05×10⁻⁵ | 0.682 | 0.0129 |
| Internal | Proposed vs MNE | 5.95×10⁻⁴ | 0.00238 | 0.565 | 0.00385 |
| Cao2018 | Proposed vs BLINKER-style | 4.50×10⁻⁹ | 1.80×10⁻⁸ | 0.885 | 5.53×10⁻⁶ |
| Cao2018 | Proposed vs MNE | 2.18×10⁻⁷ | 8.71×10⁻⁷ | 0.783 | 1.84×10⁻⁴ |

These calculations confirm a large configuration-level difference and show that simple subject aggregation does not erase its direction. They do **not** repair oracle selection, test-set tuning, causal confounding, montage contamination, preprocessing mismatch, ground-truth circularity, or lenient matching. A participant-clustered model/interval remains required.

### Parameter and threshold audit

| Parameter | Value in implementation | How selected? | Tuned on training data? | Evidence/justification |
|---|---:|---|---|---|
| Output sampling | 100 Hz | Design choice | N/A | Reported; raw rates and resampling details incomplete |
| Band-pass | 1–20 Hz | Prior practice | No isolated validation | Filter type/order/transitions/padding omitted |
| Primary epoch | 30 s, non-overlap | Literature/design | Same corpora | Needs prespecification and corrected preprocessing |
| Duration sweep | 10,20,30,40,50,60,120 s | Design grid | Same sessions | Post-selection at Fp1/Fp2 |
| Stage-A optimization | AutoReject Bayesian optimization | Package/code default | Full evaluated session | Folds/objective/version absent from PDF |
| Stage-A seed | 42 | Unexplained | No | Repeat across seeds |
| Candidate rule | Any-channel PTP exceeds learned threshold | Proposed design | Full session | Blink specificity unvalidated |
| No-candidate fallback | Use all epochs | Unexplained | No | Frequency and impact unreported |
| Stage-B centre | Median | Robustness rationale | Explored on same corpora | Archived advantage versus mean is null |
| MAD scale | 1.4826 | Normal-consistency factor | No | Not itself a BLINKER initial threshold |
| Proposed `k` | 3.0 | Same-suite sweep | **No held-out set documented** | Critical hidden tuning |
| BLINKER-style `k` | 1.5 | Published/default rule | Not symmetrically tuned | Direct confound |
| Event polarity | Positive only | Dependency behavior | Not tested | Reference/polarity sensitivity missing |
| Minimum event duration | Strictly >50 ms | Dependency default | Not reported | Sweep required |
| Inter-event separation | None in crossing wrapper | Code choice | Not tested | Split/merge sensitivity missing |
| Event match | IoU ≥0.1 | Chosen; citation does not justify value | Same evaluation | Report stricter thresholds |
| MNE threshold | `(max−min)/4` | Function default | Not tuned | Cite/version [official documentation](https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html) |
| MNE half-window | 0.10 s | Config default | Not justified | Directly affects IoU |
| Reported channel | Per-session/method argmax F1 | Test labels | **No** | Oracle only |

### Explicit contradiction check

| Comparison | Discrepancy |
|---|---|
| Abstract ↔ Results | Abstract presents headline performance without saying it is per-session label-selected oracle performance and omits session/participant counts and four exclusions. |
| Abstract ↔ Conclusion | Both imply reliability and causal benefit, while no reliability analysis or causal ablation is reported. |
| Methods ↔ Results | Methods describes 62 Cao sessions; results use 58. Methods describes 104 total despite 62+46=108. |
| Methods ↔ code | PDF says continuous resample/filter then epoch; code epochs then filters/resamples. |
| Methods ↔ code | PDF leaves `k` unspecified; code uses proposed k=3 and baseline k=1.5. |
| Methods ↔ code | PDF implies within-epoch Stage C; code concatenates valid epochs and scans across joins. |
| Methods ↔ archived montage | PDF lists Cz/P5; archive lacks Cz, uses P8 and includes erroneous E84. |
| Results ↔ Tables | Text says Appendix Tables II–V provide exact adjusted p-values; tables show only stars. |
| Results ↔ Figures | Figures use 58 public sessions while dataset description gives 62 without exclusions. |
| Discussion ↔ Results | Discussion assigns errors to threshold dilution/single excursions, but thresholds were not logged and mechanisms were not ablated. |
| Conclusion ↔ Evidence | “Epoch screening [is] the principal contribution” is stronger than the configuration-level comparison permits. |
| Code-availability claim ↔ artifact | PDF says every result can be regenerated; linked repository was empty at audit time. |
| Main manuscript ↔ archived analyses | Relevant nonsignificant median-versus-mean ablations and explicit oracle-cost discussion exist in archived sources but are absent from the PDF. |
| Main manuscript ↔ supplementary information | No complete supplementary protocol, manifests, labels, or environment is provided; appendix lacks promised exact statistics. |

---

## PART D — MINOR AND MODERATE ISSUES

- Define whether “blink,” “blink event,” “blink region,” “candidate epoch,” “bad epoch,” and “artifact epoch” are distinct. “Bad epoch” suggests data rejection, whereas the method intentionally uses those epochs for calibration.
- Use “simulated-driving” consistently. Do not alternate with “naturalistic,” “real-world,” or “driving” without qualification.
- Clarify that one threshold is estimated per channel/session; epoching makes the calibration pool conditional, not temporally adaptive.
- Report A1/A2 as mastoid references rather than generic scalp/electrophysiological detector channels.
- Standardize Fp1/Fp2 capitalization and hyphenation of “per-session,” “channel-wise,” “event-level,” and “cross-validated.”
- Define all acronyms once: PTP, MAD, IoU, EOG, EAR, MNE, F1.
- Replace significance stars with exact adjusted p-values and effect sizes; state whether ± values are SD, SE, or CI.
- Reduce excessive decimal precision. Two or three decimals for F1 is sufficient when uncertainty is reported.
- Separate event detection literature from artifact removal/correction literature.
- Move the primary strategy comparison before the long channel-mapping sequence; make channel and duration analyses secondary.
- Consolidate repetitive electrode plots and add accessible colors/markers that remain interpretable in grayscale.
- Correct grammatical defects listed in Part K before resubmission.

### Terminology consistency table

| Current terms | Problem | Recommended term |
|---|---|---|
| Naturalistic driving / driving / simulated task | Ecological setting is blurred | “Simulated lane-keeping driving task” |
| Bad/suspicious/candidate epoch | Suggests rejection and changes meaning | “Candidate high-PTP epoch” |
| BLINKER | Only one stage is implemented | “BLINKER-style initial-threshold baseline” |
| Adaptive threshold | One full-session threshold per channel | “Session-specific, candidate-conditioned threshold” |
| Reliable/robust | No formal reliability or broad perturbation tests | “Higher F1 under the evaluated protocol” |
| Session/segment/recording | Internal 30-min segments may share participants | Define recording, segment, session, and participant separately |

---

## PART E — REFERENCE VERIFICATION REPORT

### Audit summary

- **49/49 active bibliography entries** were checked for existence and core metadata.
- **40 high-value cited-claim units** were audited sentence by sentence.
- Of these, **8 were directly supported without a material qualification**, **4 were direct with a scope/implementation caveat**, **13 were partial or mixed**, **12 were indirect, unsupported, missing, or overinterpreted**, and **3 were contradicted or materially misattributed**.
- No duplicate active references, in-text citations missing from the bibliography, or uncited bibliography entries were found.
- No retraction or expression of concern was found in the checked publisher/PubMed/Crossref records; this negative search should be refreshed immediately before submission.
- **30/49 rendered references** lack a volume or page/article number.
- Alyan 2023 and Wang 2025 have incomplete author lists; Akuthota is a 2024 book chapter but is represented as a 2023 journal-like item; Agarwal and Jefri are conference works without complete venue/pages; the AutoReject DOI is missing.

### Questionable-citation table

| Manuscript statement | Citation | What source actually reports | Verdict | Recommended action |
|---|---|---|---|---|
| Increasing fatigue causes slower/prolonged blinks | Alyan et al. 2023 | Blink-related EEG responses to cognitive load in proactive/reactive driving, not fatigue progression or prolonged-blink kinematics | Does not support | Replace with direct fatigue studies such as [Ingre 2006](https://doi.org/10.1111/j.1365-2869.2006.00504.x) and [Schleicher 2008](https://doi.org/10.1080/00140130701817062) |
| Blink-free epochs dilute thresholds and suppress detection | Klein 2013; Guttmann-Flury 2019 | Detection/correction and variability, not the proposed epoch-composition mechanism | Indirect/insufficient | State as hypothesis and test pool-only ablation |
| Stage B adopts BLINKER median + scaled-MAD threshold | BLINKER | Initial candidates use mean + 1.5 SD; scaled MAD is used later on candidate amplitudes | Contradicts/misattributed | Describe proposed rule as a distinct adaptation and cite robust statistics |
| MNE uses quarter-range default | Gramfort 2013 | General MNE paper; function default is documented in current MNE API docs | Citation mismatch | Cite exact MNE version and [function documentation](https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html) |
| IoU one-to-one matching justifies 0.1 | Startsev & Zemblys | Supports event matching but not 0.1; shows stricter examples and warns implementation affects results | Partial | Justify a priori and provide threshold sensitivity |
| 32-channel EGI mapping follows Hatlestad-Hall | Hatlestad-Hall 2023 | BioSemi ABCD subsampling, not an EGI HydroCel mapping authority | Partially related | Supply actual EGI mapping/coordinates and an appropriate source |
| Eight anatomical regions follow Butler & Trainor | Butler & Trainor 2012 | Task-specific auditory study, not a general electrode-atlas standard | Indirect | Define memberships operationally and cite a standard coordinate source |
| Thresholding is real-time/efficient | Tran 2021; Jefri 2022 | Use thresholding but do not establish the present runtime or deployment | Insufficient | Measure runtime/latency or narrow wording |
| Code and scripts are released; every result is reproducible | GitHub footnote | Repository displayed “This repository is empty” on audit date | Contradicted | Populate/archive exact release or remove claim |

### Bibliographic actions

1. Rebuild all entries from DOI/publisher metadata rather than patching visible omissions.
2. Cite the Cao raw data directly: [figshare v5, DOI 10.6084/m9.figshare.6427334.v5](https://doi.org/10.6084/m9.figshare.6427334.v5), including version, licence (CC BY 4.0), download date, and analysed file manifest; also identify the [official NEMAR record](https://www.nemar.org/dataset/nm000275).
3. Add AutoReject DOI [10.1016/j.neuroimage.2017.06.030](https://doi.org/10.1016/j.neuroimage.2017.06.030).
4. Separate primary event-detection evidence from artifact-removal papers.
5. Add exact versioned software citations for MNE, AutoReject, BLINKER implementation, and matching package.

---

## PART F — NOVELTY ASSESSMENT

### Novelty matrix

Raw published performance must not be compared as a league table because datasets, annotations, matching, and validation units differ.

| Feature | Current manuscript | BLINKER 2017 | Chang et al. adaptive 2016 | *Blink* 2019 | ARMBR 2025 | Rejer & Gago 2025 |
|---|---|---|---|---|---|---|
| Task | Offline blink-region detection in simulated driving | Multi-stage blink extraction | Online individualized frontal detection | Unsupervised single-channel event detection | Blink detection/removal | Learned event detection |
| Calibration | AutoReject-screened epoch pool; median/MAD | Whole-signal initial mean+1.5 SD, then morphology/robust candidate filters | Individual adaptive threshold | Self-learned user/session pattern | Robust cross-validated threshold option | CNN/learned representation |
| Epoch/window role | Candidate epochs calibrate one session threshold | Continuous detection | Online adaptation | Moving windows ≥30 s proposed | Removal pipeline | Event segments |
| Channels | Channel-wise; multichannel union; oracle report | Automatic candidate-channel selection | Single prefrontal | Single channel | Frontal reference | Setup-dependent |
| Validation | Two corpora; IoU .1; oracle channel | Large heterogeneous corpus/video subsets | 24 people/online comparison | Four datasets/headsets/activities | Semi-synthetic + real | Individual/cross-subject |
| Distinctive element | Exact candidate-epoch-conditioned per-channel calibration sequence | Full morphology pipeline | Earlier individualized online adaptation | Earlier unsupervised session learning | Cross-validated robust blink thresholding | Modern learned competitor |

Primary sources: [BLINKER](https://doi.org/10.3389/fnins.2017.00012), [Chang adaptive detector](https://pubmed.ncbi.nlm.nih.gov/26888113/), [Blink](https://doi.org/10.1109/ALLERTON.2019.8919795), [ARMBR](https://pmc.ncbi.nlm.nih.gov/articles/PMC12539671/), and [Rejer & Gago](https://doi.org/10.1088/1741-2552/add49d).

### Claimed-contribution audit

| Claimed contribution | Existing literature | Truly new element | Degree of novelty | Recommended wording |
|---|---|---|---|---|
| Epoch-aware threshold pipeline | AutoReject supplies CV PTP screening; BLINKER and robust statistics supply threshold ingredients; adaptive detectors predate this work | Using the union of high-PTP candidate epochs as the exclusive calibration pool for a channel threshold, then applying it across the session | Incremental methodological/engineering | “We evaluate a candidate-epoch-conditioned composition…” |
| Robust median/MAD threshold | Long-established robust estimator; BLINKER uses MAD later in its pipeline | Its placement after the proposed candidate-pool gate | Low/incremental | Do not imply the estimator itself is new |
| Two-corpus validation | Prior methods use other multi-corpus validations | Same configuration on two simulated-driving corpora | Validation novelty | “We evaluate on two simulated-driving corpora…” |
| Channel analysis | Frontopolar blink dominance is well known | Within-protocol mapping under this detector | Application/validation | Present as confirmation, not discovery |
| Epoch-duration analysis | Window-length studies exist | Sensitivity of this configuration over 10–120 s | Validation novelty | Avoid “robust” without equivalence/edge controls |
| Released reproducible implementation | Standard expectation | Potential engineering contribution | Not presently realized | Claim only after immutable complete release |

### Recommended revised novelty statement

> We evaluate an interpretable composition in which cross-validated peak-to-peak screening identifies candidate high-amplitude epochs, those epochs define a channel-wise median/MAD calibration pool, and the resulting session-specific thresholds are applied to simulated-driving EEG. The individual components are established; the contribution is their candidate-epoch-conditioned integration and its evaluation across two corpora. A matched ablation is required to quantify the independent contribution of epoch screening.

Do not use “first” or “among the first” unless a documented, reproducible search supports the exact claim.

---

## PART G — METHODS AND VALIDITY AUDIT

### Experimental design

The true population unit is the participant. Blinks are nested in epochs, epochs in segments/sessions, and sessions in people. Event metrics are reasonably macro-averaged within sessions, but inference then treats repeated sessions as independent. Report 17 Internal participants/46 sessions and 27 Cao participants/58 analysed sessions, with sessions per participant and participant-clustered uncertainty.

The Internal corpus also needs recruitment, eligibility, demographics, sleep/fatigue protocol, time of day, acquisition duration, amplifier/settings, raw sampling rate, reference, impedance, and a participant/session flow. The public corpus should state 30 scalp channels plus A1/A2, 500 Hz, exact retained durations, version, licence, and four excluded session IDs/reasons.

### Leakage and optimism

1. **Direct label leakage:** test F1 selects the best channel in each session.
2. **Hyperparameter leakage:** the same-suite sweep selected `k=3`.
3. **Post-selection inference:** Fp1/Fp2 were selected at 30 s on the data used for duration tests.
4. **Full-session transduction:** future samples calibrate the threshold; this is offline, not causal/online.
5. **No untouched external test:** both corpora informed design and tuning.

### Baseline fairness

- Full BLINKER is not evaluated.
- Proposed and BLINKER-style multipliers differ and receive unequal tuning.
- Proposed calibration uses all-channel information; the baseline is channel-local.
- MNE is filtered twice and converted to fixed windows.
- Event geometry differs among methods under an IoU metric.
- Modern competitive methods are discussed insufficiently and not benchmarked.

Use identical manifests, continuous preprocessing, fixed channels, matching, and symmetric development-only tuning for mechanism comparisons. Report native complete pipelines separately.

### Equations and algorithm

The paper must define the per-epoch statistic `b_i`, cross-validation objective, number of folds, optimizer, random seed, channel-union rule, `k`, empty-candidate fallback, threshold polarity, equality rule, minimum event duration, event merging/separation, epoch-boundary behavior, and zero-MAD case. The inactive `cross_validation_eq.tex` material should be reconciled with the implementation and restored in a concise algorithm or pseudocode.

### Performance metrics

Session-macro precision, recall, and F1 are appropriate but incomplete. Add median/IQR and lower-tail session F1, participant-cluster CIs, false positives/minute, blink-count bias, recall by blink duration/amplitude, onset and offset error, duration error, and IoU-threshold curves. Report fixed-channel results as primary and oracle results as a secondary ceiling.

### Generalization, robustness, and practical significance

The present evidence establishes only within-corpus, offline, full-session, simulated-driving performance under one annotation/evaluation team. It does not establish cross-task, real-driving, online, cross-device, or clinical generalization. An 11-point F1 difference could be practically important, but operational impact should be expressed as false blinks/minute and error in downstream blink rate/duration. Runtime, memory, calibration delay, seeds, motion/electrode artifacts, noise, clipping, reduced sampling, and missing channels remain untested.

### Methods reporting standard

No single clinical-prediction guideline maps perfectly to this unsupervised signal-processing validation. Use the [COBIDAS-MEEG recommendations](https://www.humanbrainmapping.org/files/2020/COBIDAS-MEEG_NatNeuro_revised.pdf) for acquisition/preprocessing/reproducibility, the event-detection reporting principles in Startsev & Zemblys, and relevant items from STARD/CLAIM-style diagnostic-AI reporting as transparency checklists without claiming formal compliance. IEEE’s human-subject policy requires the ethics/consent statements currently missing ([IEEE policy](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/)).

---

## PART H — ADVERSARIAL QUESTIONS FOR AUTHORS

1. What matched experiment shows that candidate-epoch screening, rather than `k=3`, caused the gain?
2. What is the all-epoch median/MAD result at `k=3` on the same fixed channel and splits?
3. What is the screened-pool mean/MAD result at `k=1.5`?
4. When and on which labels was `k=3` selected, and what values were tried?
5. Why is the best channel chosen with each test session’s reference F1, and how would deployment choose it without labels?
6. What are all comparator results at prespecified Fp1 and Fp2?
7. Why is a threshold-crossing fragment called BLINKER when morphology and automatic channel selection are removed?
8. How does the complete published BLINKER pipeline perform under the same protocol?
9. Why is MNE filtered a second time and assigned an undocumented ±100 ms interval?
10. How many unique Internal participants produced the 46 segments, and how many segments did each contribute?
11. Why are repeated sessions treated as independent Wilcoxon units?
12. Why does the paper report 104 total when the described corpora contain 108 available recordings?
13. Which four Cao recordings were excluded, why, and were their outputs examined before exclusion?
14. How can Cao EEG-derived labels independently validate an amplitude-based EEG detector, especially at Fp1/Fp2?
15. What independent inter-rater agreement is obtained when both raters annotate from scratch?
16. Why does the PDF list Cz/P5 when archived runs lack Cz, use P8, and include erroneous E84?
17. Have all Internal analyses been rerun after the E84/O2 mapping correction?
18. Why does the implementation epoch before filtering/resampling while Fig. 1 states the reverse?
19. How much of the duration result is explained by repeated per-epoch filter edges?
20. What fraction of Stage-A candidates actually contain a reference blink, and what other artifacts trigger the union?
21. How often does the no-candidate fallback occur, and how does performance change in those sessions?
22. How sensitive are results to IoU 0.25, 0.5, and 0.75?
23. What are onset, offset, duration, count, and false-alarm-rate errors?
24. Does maximum-summed-IoU assignment produce the same matches as maximum-cardinality threshold-qualified assignment?
25. Does the method work under signal inversion or negative blink polarity?
26. What happens across multiple AutoReject seeds and candidate-threshold optimizers?
27. Why were nonsignificant median-versus-mean ablations omitted from the active paper?
28. What evidence warrants “reliable,” “robust,” “naturalistic,” or hardware-independent wording?
29. What runtime, memory, and calibration latency support practical or real-time implications?
30. Can a third party reproduce every table from a tagged release when the linked repository is empty?

---

## PART I — REQUIRED ADDITIONAL EXPERIMENTS

### Missing-experiment table

| Missing analysis/experiment | Why needed | Could it change the conclusion? | Priority |
|---|---|---|---|
| Matched screened-versus-all pool at same centre/k | Isolates central contribution | Yes, directly | **Essential before publication** |
| 2×2×k factorial ablation | Quantifies centre/multiplier interactions | Yes | **Essential before publication** |
| Correct-montage Internal rerun | Removes E84/Cz contamination | Yes | **Essential before publication** |
| Continuous filter/resample-before-epoch rerun | Removes edge/order confound | Yes | **Essential before publication** |
| Fixed or nested channel evaluation | Removes oracle leakage | Yes for headline magnitude | **Essential before publication** |
| Locked/nested parameter selection | Removes test-set tuning | Yes | **Essential before publication** |
| Participant-clustered inference | Corrects experimental unit | Possibly for marginal claims | **Essential before publication** |
| Full exclusion/accounting analysis | Rules out selection bias | Possibly | **Essential before publication** |
| Full BLINKER and fair MNE comparison | Supports baseline claims | Yes | **Essential before publication** |
| IoU/boundary/count sensitivity | Validates event localization | Yes | **Essential before publication** |
| Stage-A blink-enrichment analysis | Tests proposed mechanism | Yes for mechanism | **Essential before publication** |
| Independent annotation subset | Tests incorporation bias/reliability | Yes | **Essential before publication** |
| ≥20 random-seed repeats | Measures optimization instability | Possibly | Strongly recommended |
| k/min-duration/filter/window/sampling sweeps | Tests arbitrary constants | Possibly | Strongly recommended |
| Noise, movement, clipping and missing-channel tests | Supports robustness | Yes for robustness claims | Strongly recommended |
| Recall by blink type/duration/amplitude | Establishes fatigue relevance | Possibly | Strongly recommended |
| Third untouched video/eye-tracker corpus | Genuine external validation | Yes for generalization | Strongly recommended |
| Streaming/moving calibration | Supports online use | Yes for deployment | Strongly recommended |
| Runtime, memory and latency benchmark | Supports practicality | No for accuracy | Useful additional evidence |
| Downstream blink-rate/fatigue impact | Establishes operational relevance | Possibly | Optional |

### Essential

Complete all rows marked Essential before retaining claims of epoch-screening causality, superiority over BLINKER, deployable performance, or reproducibility.

### Strongly recommended

Add seed and parameter robustness, artifact perturbations, duration/type stratification, an untouched independently labeled corpus, and a causal streaming version.

### Optional

Evaluate whether detector errors materially change downstream fatigue estimates and compare computational/energy cost on embedded hardware.

---

## PART J — MANUSCRIPT REVISION MAP

| Section | Current problem | What should change | New analysis required? |
|---|---|---|---|
| Title | “Naturalistic” overstates simulated tasks | Use “simulated-driving”; avoid reliability/robustness terms | No |
| Abstract | Omits participants, exclusions, oracle, uncertainty; causal/strong claims | State analysed recordings/participants, offline oracle protocol, deltas with CIs, and limitations | Yes for corrected numbers/CIs |
| Keywords | Should reflect task/method precisely | Add blink event detection, simulated driving, robust thresholding; remove inflated terms | No |
| Introduction | Unsupported dilution mechanism and novelty; mixed detection/removal literature | Separate hypothesis from evidence; add current related-work matrix | No, except claims depend on ablation |
| Related work | No focused active section | Compare BLINKER, MNE, Chang, Blink, GMM/RT-Blink, ARMBR, and recent learned detectors | No |
| Materials and Methods | Algorithm and preprocessing incomplete/contradicted | Report exact continuous pipeline, equations, parameters, versions, event rules | Yes; implementation must be reconciled |
| Dataset description | 104/108 conflict; participants/exclusions/ethics missing | Add flow table, nested units, demographics, acquisition, version/licence | Yes for manifest |
| Ground truth | Sequential review and EEG-derived labels underreported | Add blinding, independent agreement, modality-specific limitations | Yes |
| Statistical analysis | Essentially absent from Methods | Prespecify units, models, families, CIs/effects, equivalence and sensitivity | Yes |
| Results ordering | Main method comparison is buried | Lead with fixed-channel factorial/main comparison; oracle second | Yes |
| Results statistics | Means/stars only | Add distributions, n, participant CIs, exact p/effects and lower-tail results | Yes |
| Figures | Repetitive, no uncertainty; Fig. 8 truncated | Consolidate and use paired/difference plots with CIs | Yes |
| Tables | n/CI/effect/exact p absent | Expand Table I and Appendix tables | Yes |
| Discussion | Post-hoc mechanisms presented confidently | Discuss alternative explanations and unresolved confounds | Depends on new analyses |
| Limitations | Omits central validity threats | Add oracle, confounding, tuning, clustering, label bias, montage, offline scope | No |
| Conclusion | Attributes gain to screening; uses “reliable” | Restrict to complete-configuration result unless ablation confirms cause | Yes for stronger claim |
| Data availability | Absent | State Internal access, public DOI/version, label availability | No |
| Code availability | False current release claim | Supply tag/DOI/lockfile/manifests or remove claim | No analysis; artifact required |
| Ethics | Absent | Add committee, approval ID, consent/video governance | No |
| References | Metadata incomplete and several mismatches | Rebuild from authoritative records and correct claim-source links | No |
| Supplementary information | Promised exact stats absent; no full protocol | Add exact tables, manifests, thresholds, exclusions, ablations, environment | Yes |

---

## PART K — SENTENCE-LEVEL EDITING REPORT

1. **Original:** “As a result, blink information can be extracted from EEG recordings, either by analysing the ocular components embedded in the EEG signal [5, 8].”  
   **Problem:** “Either” introduces no second alternative.  
   **Suggested:** “Blink information can therefore be extracted by analysing ocular components embedded in EEG recordings [5, 8].”

2. **Original:** “When thresholds are estimated from the entire recording, they may be biased by the presence of clean epochs that contain few or no blinks, which may distort threshold estimates and suppress blink detection…”  
   **Problem:** The direction depends on the estimator; for the implemented BLINKER-style rule a lower threshold can increase false positives rather than suppress detections. The cited sources do not test this mechanism.  
   **Suggested:** “We hypothesised that mixing blink-rich and blink-poor intervals changes a detector’s operating point; the direction and magnitude depend on the threshold estimator and require direct ablation.”

3. **Original:** “To our knowledge, this is among the first frameworks…”  
   **Problem:** Unverified priority claim.  
   **Suggested:** “We evaluate a specific composition of candidate-epoch screening and robust channel-wise threshold calibration.”

4. **Original:** “a zero-phase band-pass filter … is applied which is removes…”  
   **Problem:** Grammar and missing filter specification.  
   **Suggested:** “A zero-phase 1–20 Hz band-pass filter is applied; the filter design, order, transition bands, and padding are reported below.”

5. **Original:** “Epoching is what makes the thresholds adaptive…”  
   **Problem:** The algorithm estimates one threshold per channel/session; it is not temporally adaptive.  
   **Suggested:** “Epoching enables candidate-pool selection; Stage B then estimates one session-specific threshold per channel.”

6. **Original:** “Instead, a channel-specific threshold … is calculated from each of the channel’s.”  
   **Problem:** Incomplete possessive phrase.  
   **Suggested:** “A channel-specific threshold is estimated from that channel’s samples in the selected candidate epochs.”

7. **Original:** “The resulting set of candidate epochs is defined as The set of suspicious epochs is therefore can be represented as below;”  
   **Problem:** Duplicated and ungrammatical.  
   **Suggested:** “The candidate-epoch set is therefore” followed by the equation.

8. **Original:** “Let ξc be the channel-specific center … which can be express as below:”  
   **Problem:** Grammar.  
   **Suggested:** “The channel-specific centre is the median” followed by the equation.

9. **Original:** “Two EEG corpora … providing 104 complete recording sessions in total.”  
   **Problem:** Available counts total 108; four Cao sessions are unreported exclusions.  
   **Suggested:** “The corpora provided 108 recordings; 104 were analysed after excluding four Cao recordings for the prespecified reasons listed in Table X.”

10. **Original:** “BLINKER was represented by its threshold-crossing stage but blink marphological-fitting step and automatic channel selection were not used.”  
    **Problem:** Typo, grammar, and insufficiently explicit truncation.  
    **Suggested:** “We evaluated only BLINKER’s initial threshold-crossing stage; morphology fitting and automatic channel selection were omitted. This is therefore a BLINKER-stage ablation, not the complete BLINKER algorithm.”

11. **Original:** “This consideration favours no method in particular, since each is evaluated at its best-performing channel.”  
    **Problem:** Outcome selection is optimistic for all methods and not deployable.  
    **Suggested:** “This reference-label-selected oracle provides an optimistic upper bound for each method and does not represent prospective channel selection.”

12. **Original:** “channel.Session-level F1…”  
    **Problem:** Missing space.  
    **Suggested:** “channel. Session-level F1…”

13. **Original:** “Both failures are consistent with calibrating the threshold on the whole recording.”  
    **Problem:** Mechanistic narrative is not isolated experimentally.  
    **Suggested:** “These patterns are compatible with, but do not establish, a whole-recording calibration effect; estimator, multiplier, and post-processing also differ.”

14. **Original:** “Its advantage therefore does not appear to depend on a particular recording system…”  
    **Problem:** Hardware is confounded with corpus, people, montage, task details, and annotation.  
    **Suggested:** “The configuration ranking repeated in a second corpus acquired with different hardware, although hardware effects cannot be separated from other corpus differences.”

15. **Original:** “supporting epoch screening as the principal methodological contribution…”  
    **Problem:** Unsupported causal attribution.  
    **Suggested:** “showing that the complete screened-epoch configuration outperformed the two implemented comparator configurations; matched ablations are needed to isolate screening.”

---

## PART L — FIGURE AND TABLE REPORT

| Item | Intended demonstration | Does it demonstrate it? | Problems/missing information | Recommended caption/visual change |
|---|---|---|---|---|
| Fig. 1 | Three-stage pipeline | Conceptually, not reproducibly | No axes/units; schematic status unclear; preprocessing order conflicts with code; Stage C rules absent | State it is schematic; show continuous preprocessing order, pool construction, threshold equation, fallback, polarity and event rules |
| Fig. 2 | 32-electrode montage and regions | No | Corpora have different montages; A1/A2 not scalp sites; Internal Cz absent; P5/P8/E83/E84 inconsistencies | Use separate corpus panels and explicit channel-to-region table; mark mastoids/unassigned sites |
| Fig. 3 | Internal regional performance | Partially | Means only; no n, uncertainty, raw sessions, or fixed versus oracle clarity | Show participant-aware distributions/CI and state n/selection rule in caption |
| Fig. 4 | Cao regional performance | Partially | Same problems; Cao labels may favor Fp1/Fp2 | Add modality-bias caveat and paired participant distributions |
| Fig. 5 | Internal electrode comparison/significance | Weakly | Overlapping bars/stars obscure values; no exact p/effect/CI | Replace with paired delta/forest plot; caption gives family, n, adjusted p and effect |
| Fig. 6 | Cao electrode comparison | Partially | Means without uncertainty and dense labeling | Use ranked dot/interval plot and identify references/mastoids |
| Fig. 7 | Internal electrode subset result | Weakly | Montage/error ambiguity; overlapping visual elements; E83/E84 issue | Regenerate after corrected rerun; show manifest and participant CIs |
| Fig. 8 | Epoch-duration stability | Misleading in current form | Y-axis starts at 70%, magnifying ≤1.28-point changes; no paired deltas/CI; edge confound | Use 0–100 scale or clearly marked zoom plus difference-from-30-s panel and equivalence band |
| Fig. 9 | Precision–recall/session behavior | Partially | Overplotting; no n/density/CI; means in P–R space are not paired method differences; oracle status underemphasized | Add paired F1-difference distribution or density; label oracle explicitly; report lower tail |
| Table I | Primary strategy comparison | Numerically, but incompletely | Oracle headline; no n, dispersion, exact p, effect, CI, fixed channels | Make fixed/nested channel primary; add n, mean/median, CI, paired delta, adjusted p, effect |
| Table II | Internal duration comparison (Fp1) | Incompletely | Exact adjusted p promised but only stars shown; no n/effect/CI | Add exact raw/adjusted p, cluster CI, effect and equivalence result |
| Table III | Internal duration comparison (Fp2) | Incompletely | Same | Same |
| Table IV | Cao duration comparison (Fp1) | Incompletely | Same; repeated subjects ignored | Same with participant clustering |
| Table V | Cao duration comparison (Fp2) | Incompletely | Same | Same with participant clustering |

Every caption should specify corpus, analysed recordings and participants, selection rule, metric/matching threshold, summary statistic/error representation, statistical test, correction family, and abbreviation definitions. Captions must not call oracle scores operational performance.

---

## PART M — FINAL CLAIM AUDIT

| Claim | Supported? | Evidence | Confidence | Required correction |
|---|---|---|---|---|
| The complete proposed configuration exceeds the two implemented comparators under the archived protocol | Yes, configuration-level | Reproduced means and paired direction on both corpora | Strong | State exact offline/oracle/IoU conditions |
| Epoch screening caused the improvement | No | No matched screened-versus-all contrast | Unsupported | Run factorial ablation or remove causal claim |
| The method outperforms BLINKER | No | Only initial threshold stage was tested | Unsupported | Test full BLINKER; relabel current baseline |
| The method outperforms MNE generally | Only within one configuration | One double-filtered, fixed-window default MNE setup | Weak | Fair native/tuned comparison and narrow wording |
| Median is superior to mean | No | Archived comparisons are nonsignificant | Weak | Restore null result; avoid component superiority |
| Fp1/Fp2 are strong channels in these analyses | Broadly yes | High mean fixed-channel performance | Moderate | Confirm after montage rerun and independent labels |
| Fp1/Fp2 are equivalent to full montage | Not established | Nonsignificance/small means, no equivalence test | Weak | Noninferiority/equivalence with clustered CI |
| Performance is insensitive to epoch duration | Partially | Small average changes under current implementation | Weak | Correct preprocessing and use equivalence analysis |
| Results generalize across recording hardware | No isolated evidence | Same ranking on two confounded corpora | Weak | Restrict claim or controlled cross-device study |
| The method is reliable | No formal reliability evidence | Event F1 only; dependent raters | Unsupported | Remove term or add repeatability/agreement studies |
| The method is robust | Very limited | One duration sweep and two corpora | Weak | Perturbation, seed, threshold and lower-tail tests |
| The method is practical/real-time capable | Not shown | No runtime/latency; full-session optimization | Unsupported | Benchmark and implement causal streaming version |
| Cao2018 contributes 62 analysed sessions | No | Only 58 result sessions; four excluded | Unsupported | Correct cohort flow |
| The Internal analysis uses the stated 32-channel montage | No | Archive lacks Cz and includes E84 error | Unsupported | Correct and rerun |
| The published equations reproduce the implementation | No | Missing CV/event rules and preprocessing mismatch | Unsupported | Full algorithm and verified implementation |
| Ground truth is independent and reliable | Not adequately | Sequential review; Cao EEG-derived labels | Weak | Independent blinded validation/agreement |
| Code is released and every result reproducible | No | Linked repository empty; dependency failure | Unsupported | Immutable complete release before claiming |
| The exact three-stage composition is a useful incremental contribution | Plausible | Distinct integration and two-corpus evaluation | Moderate | Position as incremental and demonstrate isolated value |

---

## Section-by-section completeness review

1. **Title:** Replace “Naturalistic” with “Simulated-Driving”; avoid “robust/reliable/real-time.” Suggested: *Candidate-Epoch-Conditioned Threshold Calibration for Blink Detection in Simulated-Driving EEG: A Two-Corpus Evaluation*.
2. **Abstract:** Add participant/session counts, exclusions, fixed versus oracle policy, matching criterion, uncertainty, and noncausal conclusion.
3. **Keywords:** Use precise event-detection and simulated-driving terms.
4. **Introduction:** Separate established evidence from the new dilution hypothesis; narrow novelty.
5. **Related work:** Add focused component-level comparison and contemporary competitors.
6. **Materials and Methods:** Reconcile code/order, define the complete algorithm, and disclose all parameters.
7. **Data/dataset:** Correct flow, nesting, demographics, acquisition, licences, and mapping.
8. **Statistical analysis:** Restore a complete prespecified subsection with participant-aware inference.
9. **Results:** Lead with corrected factorial/fixed-channel results; report uncertainty and lower tails.
10. **Figures:** Regenerate after reruns; show distributions and honest scales.
11. **Tables:** Add n, CI, exact p, effects, and deployable operating points.
12. **Discussion:** Address alternatives rather than asserting mechanisms.
13. **Limitations:** Add oracle, confounding, tuning, clustering, ground-truth bias, montage, and offline scope.
14. **Conclusion:** Restrict to configuration-level evidence unless new ablation supports causality.
15. **Data availability:** Add public version/DOI and Internal/annotation access conditions.
16. **Code availability:** Provide tagged archive/DOI, environment and run map.
17. **Ethics:** Add committee, approval, consent, face-video governance, and privacy.
18. **References:** Correct metadata and claim-to-source mismatches.
19. **Supplementary information:** Add cohort manifest, full parameter sweep, thresholds, exact statistics, exclusions, and reproducibility protocol.

---

## Simulated independent reviewer summaries

### Reviewer A — Domain expert

**Major concerns:** simulated versus naturalistic scope; EEG-derived public labels; blink-event relevance to fatigue; missing Internal participant/ethics data.  
**Required work:** independently video/eye-tracker-labeled subset, event-type/duration analysis, fixed frontopolar evaluation, and transparent cohort reporting.

### Reviewer B — Methods/statistics expert

**Major concerns:** no causal ablation; oracle channel selection; incomplete BLINKER; repeated-session pseudoreplication; missing statistical protocol and uncertainty.  
**Required work:** factorial ablation, fixed/nested selection, participant-clustered analysis, corrected preprocessing/montage, and metric sensitivity.

### Reviewer C — Skeptical general reviewer

**Major concerns:** incremental novelty is overstated; main experiment is buried; availability/ethics are incomplete; discussion mechanisms are post hoc.  
**Required work:** focused prior-art comparison, corrected primary experiments, complete reproducibility package, restrained title/abstract/conclusion, and consolidated visuals.

---

## Final defensible interim conclusion

The current evidence supports a narrow statement: under offline full-session calibration, IoU = 0.1, the archived preprocessing/configuration, and per-session reference-label-selected oracle channels, the screened-epoch median/MAD configuration achieved higher macro-F1 than the implemented BLINKER-style threshold-crossing and MNE configurations on two simulated-driving corpora. The evidence does not yet show that epoch screening uniquely caused the improvement, that complete BLINKER was surpassed, that performance is deployable or reliable, or that it generalizes beyond these protocols. The minimum path to a scientifically defensible paper is a corrected Internal/preprocessing rerun, participant-aware fixed-channel evaluation, matched causal ablation, fair baselines, independent-label sensitivity, and a complete immutable reproducibility package.

