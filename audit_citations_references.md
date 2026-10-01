# Citation, Reference, Dataset, and Literature-Balance Audit

## Scope and audit method

This report audits the compiled manuscript `writing/IEEE-TJ-color-latex-template/main.pdf` (16 PDF pages; manuscript text on pp. 1--13 and appendix thereafter), its active LaTeX sources, `references_from_csv.bib`, `references_scopus_new.bib`, and the generated `main.bbl`. The active bibliography contains 49 cited works. Claims were checked against publisher pages, PubMed/PMC, Crossref metadata, official software documentation, and official dataset records where accessible. A citation is not counted as verified merely because its title appears relevant.

The most important source-level locations are given alongside PDF pages so that every finding can be reproduced. URLs below point to the accessed external evidence.

## Executive findings

1. **Major method-provenance error:** the manuscript says that Stage B "adopts" BLINKER's robust center-plus-dispersion threshold. BLINKER's initial candidate detector actually uses the whole-signal **mean + 1.5 ordinary standard deviations**. BLINKER uses `1.4826 x MAD` later to screen the distribution of already detected candidate blink amplitudes. The manuscript has combined ideas into a different estimator and should describe it as an adaptation/new construction, not BLINKER's threshold formula. See PDF p. 3--4; `d_method/step2_get_threshold_candidates.tex:4-5,32-48`; [BLINKER full text, preprocessing and potential blink detection](https://pmc.ncbi.nlm.nih.gov/articles/PMC5289990/#S3), especially the sections describing the initial threshold and robust amplitude-distribution criterion.
2. **Major unsupported causal/gap claim:** the Introduction states that blink-free epochs dilute whole-recording thresholds and suppress detection, citing Klein (2013) and Guttmann-Flury et al. (2019). Those sources concern blink detection/correction and variability; they do not directly demonstrate the manuscript's specific epoch-composition mechanism. The manuscript's own commented text acknowledges that thresholds and the isolated effect of epoch screening were not measured. This should be framed as a hypothesis and tested by ablation. See PDF p. 2; `b_intro/p005/paragraph.tex:1`; `e_result/exp3/par4.tex:1-3`.
3. **Critical dataset accounting contradiction:** Methods says 104 sessions total, then describes 62 Cao2018 + 46 Internal sessions (=108). Figures/results use 58 Cao2018 sessions, and a commented source line reveals that four public sessions were excluded for unresolved annotation issues. The exclusion is not reported in the compiled paper. See PDF p. 4 and figure captions on pp. 7--10; `d_method/material/dataset.tex:1,3,5`; `d_method/material/annotation.tex:9-10`. The official dataset really contains 62 sessions from 27 participants, so the discrepancy is in the manuscript's analysed subset, not the source dataset ([Scientific Data paper](https://doi.org/10.1038/s41597-019-0027-4); [official NEMAR record](https://www.nemar.org/dataset/nm000275)).
4. **Citation mismatch in the opening rationale:** Alyan et al. (2023) studies blink-related EEG responses to cognitive load in proactive/reactive driving, not fatigue progression or slower/prolonged blinks. It does not support the sentence "increasing fatigue levels are often associated with slower and more prolonged blinks." See PDF p. 1; `b_intro/p001/paragraph.tex:2`; [Alyan et al. full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10632495/).
5. **Bibliography quality is not submission-ready:** 30/49 rendered references lack a volume or page/article number. Two entries have incomplete author lists (Alyan 2023; Wang 2025), one book chapter is misrepresented as a 2023 journal-style item although publisher metadata gives 2024, and two conference papers are rendered without their conference venues/pages. The `.bib` files contain DOIs for most entries, but the generated bibliography suppresses all DOI fields.
6. **Dataset citation is incomplete:** the public corpus should cite the dataset DOI/version directly (raw data: [figshare v5, DOI 10.6084/m9.figshare.6427334.v5](https://doi.org/10.6084/m9.figshare.6427334.v5)), state the licence (CC BY 4.0), identify the exact downloaded version, and provide the analysed file list. The paper citation alone is insufficient for computational reproducibility.
7. **Internal corpus is not externally auditable:** no participant count, demographics, recruitment criteria, ethics approval, acquisition sampling rate, session-to-participant structure, or data/code access statement is supplied. Forty-six 30-minute video segments are called "sessions," but their number of independent drivers is unknown. This prevents evaluation of independence and generalisation.
8. **Literature balance is distorted by mixing detection and removal:** the long Introduction citation cluster combines blink detectors, artifact-rejection pipelines, and blink-correction/removal algorithms as if all were comparable detection approaches. It gives breadth without clearly distinguishing task, ground truth, validation unit, or output.
9. **The novelty statement is not adequately sourced:** "among the first frameworks" is not backed by a transparent search or closest-prior-art comparison. The active paper omits a literature comparison table even though one exists under an archived `obs` path. At minimum it should compare Autoreject-based epoch screening, BLINKER, MNE, Chang et al. (2016), RT-Blink, GMM detection, and recent short-segment/single-channel methods.
10. **MNE implementation claims need an implementation source:** Gramfort et al. (2013) is the general MNE-Python paper and does not document the current `find_eog_events` threshold. The quarter-range statement is supported by the [official MNE `find_eog_events` documentation](https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html), which should be cited with the package version and function/code commit used.
11. **The reproducibility claim is currently false:** PDF p. 2 says the source code, baseline implementations, and experiment scripts are released and that "every result" can be regenerated. The footnoted public [GitHub repository](https://github.com/pyresearchs/double_thresholding_blink) displayed **"This repository is empty"** when checked on 2026-10-01. Until code, environment lock files, data manifests, commands, and a release/tag are deposited, the paper cannot claim released code or result regeneration.

## Sentence-level citation audit

Verdicts use the requested categories: **Direct**, **Partial**, **Indirect/insufficient**, **Does not support**, **Contradicts**, **Citation unnecessary**, **Citation missing**, and **Unable to verify fully**.

| PDF / source evidence | Manuscript claim | Citation(s) | What the source actually supports | Verdict | Required action |
|---|---|---|---|---|---|
| p. 1; `b_intro/p001/paragraph.tex:1` | A blink is eyelid closure/reopening; blinking protects/moistens the eye and supports vision. | Nyström et al. 2024 [1] | Defines blinks via eyelid closing/opening and reviews moistening, protection, and visual/tear-film functions. [Publisher/PubMed record](https://pubmed.ncbi.nlm.nih.gov/38424292/) | **Direct** | Retain; add full metadata in bibliography. |
| p. 1; `p001:1` | Blink behaviour is an important fatigue-driving indicator. | Alyan 2023 [2]; Tian & Cao 2021 [3] | Tian & Cao review EOG/ocular features in fatigue detection. Alyan studies blink-related EEG and cognitive load, not fatigue detection. | **Partial** | Keep Tian; replace Alyan here with a primary fatigue/blink study (e.g., Ingre 2006 or Schleicher 2008). |
| p. 1; `p001:1` | Blink frequency, duration, eye closure, and patterns reflect alertness/cognitive state. | Alyan 2023 [2]; Ren 2019 [4] | Alyan supports blink-related EEG changes with task/cognitive load; Ren compares blink-rate measures across mental states. The combined list is broader than either source alone. | **Partial** | Split cognitive-load and vigilance/fatigue claims and cite condition-matched primary studies. |
| p. 1; `p001:2` | Increasing driving fatigue is associated with slower/prolonged blinks and impaired driving risk. | Alyan 2023 [2] | Alyan manipulated proactive/reactive driving difficulty and analysed blink-related ERPs/ERSPs; it did not test fatigue progression or prolonged blink kinematics. | **Does not support** | Replace with Ingre et al. 2006 ([DOI](https://doi.org/10.1111/j.1365-2869.2006.00504.x)), Schleicher et al. 2008 ([DOI](https://doi.org/10.1080/00140130701817062)), or another direct primary study. Separate impaired-driving risk if not directly measured. |
| p. 1; `p001:3` | Blink behaviour is a useful non-invasive fatigue marker. | Shahbakhti 2023 [5]; Tian 2021 [3] | Both concern blink/EOG features for driver fatigue; Shahbakhti combines Fp1 EEG and blink features. | **Direct**, with scope limits | Retain but avoid universal language; both concern controlled/simulated settings. |
| p. 1; `p002:1` | Camera, EEG, and EOG can capture blink activity; ocular potentials contaminate EEG. | Tian 2021 [3]; Shahbakhti 2023 [5]; Croft 2000 [6]; Akuthota 2023/2024 [7] | Tian and Shahbakhti support modalities; Croft directly explains ocular electrical fields over the scalp. Akuthota is a secondary book chapter. | **Direct/Partial** | Prefer Croft or another primary biophysical source; correct Akuthota metadata and publication type. |
| p. 1; `p002:3-4` | Blink information can be extracted from EEG and used for fatigue/drowsiness. | Agarwal 2019 [8]; Shahbakhti 2023 [5]; Ko 2020 [9]; Alyan 2023 [2] | Agarwal supports EEG blink extraction; Shahbakhti/Ko support fatigue use. Alyan supports cognitive load, not drowsiness. | **Partial** | Remove Alyan from the drowsiness clause or rewrite as broader driving-state monitoring. |
| p. 1; `p003:1-3` | Blink activity is either artifact or meaningful fatigue information; three detector classes exist. | Croft/Tian/Akuthota/Klein/Shahbakhti/Ko/Agarwal/RT-Blink/etc. | The cited works exemplify artifact removal and fatigue use. Agarwal and RT-Blink are two algorithms, not evidence for an exhaustive three-class taxonomy. | **Indirect/insufficient** for taxonomy; otherwise **Direct/Partial** | Cite a review/taxonomy or state "approaches relevant here include..." rather than "can generally be classified." |
| pp. 1--2; `p004:1` | Thresholding is widely used. | Tran 2021 [16]; Chang 2016 [14] | Both are threshold-related examples; two examples do not establish prevalence. | **Partial** | Replace "widely used" with "has been used" or add a review/survey. |
| p. 2; `p004:2` | Thresholding is computationally efficient/easy, particularly in real-time fatigue systems. | Tran 2021 [16]; Jefri 2022 [17] | These works use amplitude thresholding; they do not, by themselves, establish runtime or real-time fatigue deployment. | **Indirect/insufficient** | Report measured complexity/runtime or cite real-time Chang et al. 2016 [48]. |
| p. 2; `p004:3` | Existing approaches range from rule-based thresholds to hybrid refinement pipelines. | 13 references [8, 11, 13--16, 18--24] | The cluster mixes detection, artifact rejection (FASTER), correction/removal, and hybrid classifiers. It supports diversity but not a clean taxonomy. | **Partial; citation decoration risk** | Divide by task: event detection, artifact screening, and artifact removal. Use a comparison table rather than a 13-paper sentence-end cluster. |
| p. 2; `p004:5-6` | Blink amplitude varies across subjects/electrodes/devices/conditions; low/high thresholds trade false positives/negatives. | Guttmann 2019 [24]; Wang 2022 [20]; Tran 2021 [16]; Jefri 2022 [17] | Inter-/intra-subject variability and threshold trade-offs are supported, but the full list of device/electrode/signal-quality causes is broader than demonstrated. | **Partial** | Narrow wording or add direct multi-device/multi-channel evidence. |
| p. 2; `p004:8` | Adaptive/robust threshold selection is critical specifically in fatigue driving. | Ko 2020 [9]; Shahbakhti 2023 [5] | These are fatigue applications; neither uniquely establishes the need for the manuscript's threshold-selection mechanism. | **Indirect/insufficient** | Present as motivation/inference, not sourced fact. |
| p. 2; `p005:1` | Many fatigue-driving studies use epochs; epoch structure challenges threshold detectors. | Cao 2019 [25]; Tran 2021 [16]; Jefri 2022 [17] | Cao provides one sustained-attention driving corpus and event structure. Tran/Jefri use segmented analyses, but do not establish a general epoch-specific failure mechanism. | **Partial** | Cite multiple explicit epoch-based driving studies and distinguish analysis windows from task-event epochs. |
| p. 2; `p005:1` | Blink-free epochs dilute whole-recording threshold estimates and suppress detection in blink-rich epochs. | Klein 2013 [10]; Guttmann 2019 [24] | Neither source directly tests this asserted dilution mechanism in epoch-structured driving EEG. | **Does not directly support** | Mark as the paper's hypothesis; add threshold-distribution evidence and a candidate-screening on/off ablation. |
| p. 2; `p005:1` | Epoch-aware adaptation is required instead of a global threshold. | Guttmann 2019 [24]; Agarwal 2019 [8] | Both are adaptive/unsupervised methods, but neither validates the exact epoch-aware requirement claimed. | **Indirect/insufficient** | Reword as proposed approach and avoid implying prior evidence already establishes necessity. |
| p. 2; `p007:4` | "Among the first" to integrate the three stages. | None | No search method or closest-prior-art table is presented. | **Citation missing / unverified novelty** | Replace with a precise component-level contribution and add a documented search/comparison. |
| p. 2; `p007:5` | BLINKER and MNE are baseline methods. | BLINKER [15]; MNE paper [26] | BLINKER is direct. Gramfort 2013 establishes MNE-Python generally, not the `find_eog_events` defaults used. | **Partial** | Add official function documentation/version/commit and cite the exact implementation. |
| p. 2; `p007:6-7` | Source code, baselines, and all experiment scripts are released; every result can be regenerated. | Footnoted GitHub URL | The linked public repository reported "This repository is empty" on 2026-10-01. | **Contradicted by linked artifact** | Upload the complete code and reproducible environment, create a versioned archival release/DOI, and weaken/remove the claim until the artifact is public and tested. |
| pp. 2--3; `step1_select_bad_epoch.tex:3,24-26` | Stage A adopts Autoreject peak-to-peak threshold selection through cross-validation. | Jas et al. 2017 [27] | Autoreject explicitly uses cross-validation and a robust metric to estimate peak-to-peak rejection thresholds. [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC7243972/) | **Direct**, but adaptation needs detail | State exactly which Autoreject variant/API and deviations were used; add missing DOI `10.1016/j.neuroimage.2017.06.030`. |
| pp. 3--4; `step2_get_threshold_candidates.tex:4-5,32-48` | BLINKER uses a median/robust-dispersion/sensitivity threshold of the stated form. | BLINKER [15] | BLINKER initial candidates use mean + 1.5 SD over the overall signal. Its 1.4826xMAD statistic is used later for candidate-amplitude distribution filtering. | **Contradicts / misattributes method** | Describe Stage B as the authors' adaptation; cite BLINKER only for the ingredients it actually uses, and cite a robust-statistics source for MAD scaling. |
| p. 4; `dataset.tex:3` | Cao2018 has 62 sessions, 27 participants, ~90-min immersive lane-keeping, 32 electrophysiological channels. | Cao 2019 [25] | Directly supported by the paper and official record: 62 recordings, 27 healthy adults, 32 EEG channels (30 scalp + A1/A2), 500 Hz, ~82 h total. | **Direct** | Retain; add dataset DOI/version/licence and state why only 58 were analysed. |
| p. 4; `dataset.tex:5` | Internal EGI 128-channel data were reduced to a 32-channel montage "following" Hatlestad-Hall 2023. | Hatlestad-Hall 2023 [28] | Hatlestad-Hall subsampled a **BioSemi ABCD radial** 128-electrode montage to approximate standard 10-10/10-20 positions for source-connectivity analysis. It is not an EGI HydroCel mapping authority. [Publisher record/table](https://doi.org/10.1016/j.clinph.2023.03.002) | **Partially related but insufficient** | Provide the EGI sensor-number-to-label mapping/coordinates used and cite an EGI HydroCel-specific source. Cite Hatlestad only if its exact 32 labels motivated selection, not as proof of EGI correspondence. |
| p. 4; `dataset.tex:7` | Eight left/right anatomical regions are assigned "as per" Butler & Trainor 2012. | Butler & Trainor 2012 [29] | This is an auditory pitch ERP/source-estimation experiment, not a general electrode-atlas or montage standard. It may use regional groupings, but is weak authority for the present montage partition. | **Indirect/insufficient** | Define the grouping operationally in a table and cite a standard 10-10 coordinate/region source if a normative anatomical claim is intended. |
| p. 5; `annotation.tex:6` | EAR from facial landmarks tracks eyelid opening/closure. | Soukupova & Cech 2016 [30] | Directly supports EAR-based real-time blink detection from facial landmarks. | **Direct** | Add proceedings pages/URL; report landmark detector/version and handling of failed frames. |
| p. 5; `annotation.tex:9` | Cao2018 distributes task events but no video/EOG/blink labels. | Cao 2019 [25] | Dataset documentation supplies lane-departure/response events and EEG; no blink annotations/video/separate EOG are part of the public release. | **Direct** | Retain; distinguish A1/A2 references from EOG. |
| p. 5; `annotation.tex:9` | Blinks can appear as transient high-amplitude EEG deflections. | Iwasaki 2005 [31]; Croft 2000 [6]; BLINKER [15] | Directly supported, although ocular events other than blinks can resemble these transients. | **Direct with specificity caveat** | Add explicit morphology criteria and a false-positive adjudication rule, especially because public labels use EEG alone. |
| p. 5; `eval_metric.tex:5-12` | IoU and one-to-one event matching are appropriate; threshold = 0.1. | Startsev & Zemblys 2023 [32] | The review supports event-level matching and maximum-IoU methods, demonstrates thresholds such as 0.3/0.5, and warns implementation choices materially alter scores. It does not justify 0.1. [Publisher full text](https://doi.org/10.3758/s13428-021-01763-7) | **Direct** for IoU; **unsupported** for 0.1 | Justify 0.1 a priori and report sensitivity at stricter thresholds (e.g., 0.3 and 0.5). Specify match ordering. |
| p. 10; `e_result/exp2/par1.tex:1` | Driving studies use windows from seconds to minutes. | Ahn/Chai/Lan/Dai/Chen [33--37] | Ahn explicitly uses 10-s trials; Chai uses 20-s segments. The corpus of citations supports varied windows, but some cited studies are not EEG blink detectors and Dai concerns nuclear-control-room operators. | **Partial** | Separate driving-EEG examples from non-driving/non-EEG examples; give each actual window in a short table. |
| p. 10; `e_result/exp2/par2.tex:1` | The tested durations 10--120 s are supported by those five citations. | [33--37] | The references motivate a range but do not necessarily justify every value in the seven-level grid or 30 s as reference. | **Indirect/insufficient** | State that the grid is an experimental design choice; cite exact precedent per duration only where true. |
| p. 10; `e_result/exp3/par1.tex:1-2` | BLINKER and MNE use pooled continuous thresholds; BLINKER uses mean + robust dispersion and MNE quarter-range. | BLINKER [15]; Gramfort 2013 [26] | Continuous pooling is fair; BLINKER's initial dispersion is ordinary SD, not robust. MNE's current docs give `(max-min)/4`, but Gramfort 2013 is not the function-level evidence. | **Contradicts** for BLINKER dispersion; **citation mismatch** for MNE detail | Correct BLINKER mechanism and cite official MNE docs/source with software version. |
| p. 10; `e_result/exp3/par4.tex:1` and p. 11; `d3_main_implication:4` | Observed precision/recall patterns confirm threshold-dilution/range mechanisms. | BLINKER/MNE citations plus manuscript results | The patterns are compatible with those mechanisms but do not isolate them; thresholds were not recorded and center, dispersion, multiplier, signal pool, and post-processing differ. | **Overinterpretation; citation cannot establish causality** | Say "consistent with" only and add factorial ablations/recorded threshold distributions. |
| p. 10--11; `d1_frontopolar/par1.tex:1-3` | Fp1/Fp2 results agree with prior frontopolar fatigue/blink studies; occipital alpha is a fatigue marker. | Ko 2020; Shahbakhti 2022/2023; Simon 2011; Lin 2014; Li 2015 | The cited studies directly support frontopolar blink use and occipital/alpha vigilance systems. | **Direct** | Retain; clarify that detector performance and fatigue-classification utility are different endpoints. |
| p. 11; `d2_epoch_stability:2-4` | Prior blink detectors generally use one epoch duration; no systematic duration study exists. | Chang 2016; Wang 2025; Shahbakhti 2021 | These examples use fixed/short segments, but three papers cannot substantiate a field-wide negative claim, especially through 2026. | **Indirect/insufficient / novelty unverified** | Document search terms/databases/date and temper to "we did not identify..." |
| p. 11; `d2_epoch_stability:7` | Blink artifacts last about 100--500 ms. | Chang 2016 [14] | Chang explicitly states a gradual rise/fall generally within 100--500 ms. [Publisher page](https://doi.org/10.1016/j.cmpb.2015.10.011) | **Direct** | Retain. |
| p. 11; `d3_main_implication:2-4` | False detections inflate blink-rate indices; warning systems need per-driver reliability; blink rate varies with sleepiness and drivers. | Tian 2021; Ingre 2006; Schleicher 2008 | Inflation is a logical consequence, Tian supplies use of blink metrics; Ingre directly studies individual differences but not engineering requirements; Schleicher directly links blink/saccade features and fatigue. | **Partial to Direct** | Mark warning-system statement as an engineering argument rather than a finding of Ingre. |
| p. 11; `d5_limitations:2` | Blink definitions/boundaries vary with representation and criteria. | Nyström 2024 [1] | Directly supported; the source emphasizes inconsistent blink definitions and signal-dependent operationalisation. | **Direct** | Retain. |
| p. 11; `d6_future:1` | Guttmann 2025 includes motor imagery/execution, SSVEP, and P300 with EEG, eye tracking, and high-speed video; real-time adaptive blink thresholds exist. | Guttmann 2025 [47]; Chang 2016 [48] | Both claims are supported by their respective sources. | **Direct** | Retain; add full article number and DOI metadata. |
| p. 11; `d6_future:3` | A frontopolar channel may carry theta/beta activity as well as blinks. | Ko 2020; Shahbakhti 2022; Aoki 2023 | Broadly supported in single/prefrontal EEG drowsiness studies, though channel and feature definitions differ. | **Partial/Direct** | Keep cautious "may" wording and avoid implying one channel replaces occipital alpha without direct validation. |

## Bibliography existence and metadata audit

### High-priority metadata defects

| Ref. | Problem in manuscript/BibTeX | Verified metadata | Action |
|---|---|---|---|
| [2] `alyan2023blink` | Rendered with one author, "E. Alyan." | Six authors: E. Alyan, S. Arnau, J. Reiser, R. Getzmann, M. Karthaus, E. Wascher; *Scientific Reports* 13(1), article 19396 (2023), DOI [10.1038/s41598-023-46738-0](https://doi.org/10.1038/s41598-023-46738-0). | Replace author list and add volume/issue/article number. |
| [7] `akuthota2023artifacts` | Stored/rendered as 2023 journal-like item. | Book chapter, pp. 195--214, published 2024 in *Computational Intelligence and Deep Learning Methods for Neuro-rehabilitation Applications*, DOI [10.1016/B978-0-443-13772-3.00004-2](https://doi.org/10.1016/B978-0-443-13772-3.00004-2). | Change type to `@incollection`, year to 2024, and add book editors/publisher/pages/ISBN if available. |
| [8] `agarwal2019blink` | `@article`; no venue/pages in rendered list. | Conference paper, *2019 57th Annual Allerton Conference on Communication, Control, and Computing*, pp. 1113--1121, DOI [10.1109/ALLERTON.2019.8919795](https://doi.org/10.1109/ALLERTON.2019.8919795). | Use `@inproceedings`; add booktitle and pages. |
| [17] `jefri2022eye` | `@article`; no venue/pages. | *IET Conference Proceedings* 2022(10), pp. 77--83; 8th International Conference on Mechatronics Engineering, DOI [10.1049/icp.2022.2269](https://doi.org/10.1049/icp.2022.2269). | Use conference/proceedings metadata and pages. |
| [21] `wang2025sliding` | Rendered with one author, "G. Wang." | Six authors: Guojing Wang, Hongyun Liu, Shijing Wu, Xiaohua Yu, Buqing Wang, Weidong Wang; *PeerJ Computer Science* 11:e3249 (2025), DOI [10.7717/peerj-cs.3249](https://doi.org/10.7717/peerj-cs.3249). | Replace author list; add volume/article number. |
| [27] `jas2017autoreject` | DOI absent from `.bib` and rendered item. | *NeuroImage* 159, 417--429 (2017), DOI [10.1016/j.neuroimage.2017.06.030](https://doi.org/10.1016/j.neuroimage.2017.06.030), PMID 28645840. | Add DOI and issue/date if desired. |
| [29] `black2012` | BibTeX volume is the literal string `Volume 3 - 2012`, rendered as `vol. Volume 3 - 2012`. Key is misleading (`black2012`) although authors are Butler & Trainor. | Butler & Trainor, *Frontiers in Psychology* 3, article 180 (2012), DOI [10.3389/fpsyg.2012.00180](https://doi.org/10.3389/fpsyg.2012.00180). | Set `volume={3}`, `pages/article-number={180}`; rename key when convenient. |
| [30] `soukupova2016realtime` | Proceedings location/editor are present, but no page range or stable paper URL in rendered list. | T. Soukupova and J. Cech, "Real-Time Eye Blink Detection using Facial Landmarks," *21st Computer Vision Winter Workshop* (2016). No Crossref DOI located. | Add verified pages and official repository URL; do not invent a DOI. |
| All | Generated IEEE bibliography omits DOI fields even when present in `.bib`. | DOI metadata resolves for 47 cited works with DOI fields; Soukupova has no DOI located. | Configure the IEEE bibliography output to include DOI where journal policy permits, or provide complete volume/pages/article numbers at minimum. |

### Completeness summary

- **49** active cited bibliography entries were inspected.
- **30/49 rendered entries** lack either a volume or a page/article number: [1--17], [19--25], [29--30], [36], [38], [44], and [47].
- **Two incomplete author lists:** [2] Alyan et al. and [21] Wang et al.
- **One wrong publication year/type:** [7] Akuthota et al. is a 2024 book chapter, not a 2023 journal article.
- **Two conference works typed as articles with no venue:** [8] Agarwal & Sivakumar; [17] Jefri et al.
- **No duplicate active references** were found in `main.bbl`.
- **No active in-text citation is absent from `main.bbl`, and every `main.bbl` item is cited.**
- No retraction or expression of concern was found in the publisher/PubMed/Crossref checks performed for the 49 active items. This is a negative search result, not a guarantee; it should be refreshed immediately before submission.

### Verified all-reference ledger

The following compact ledger records existence and canonical DOI. "Metadata match" means title and principal bibliographic identity matched; it does **not** mean the rendered entry is complete.

| Keys / refs | Verification result |
|---|---|
| `nystrm2024what` [1] | Exists; metadata match; DOI [10.3758/s13428-023-02333-9](https://doi.org/10.3758/s13428-023-02333-9); 56(4):3280--3299; PMID 38424292. |
| `alyan2023blink` [2] | Exists; DOI [10.1038/s41598-023-46738-0](https://doi.org/10.1038/s41598-023-46738-0); **author list incomplete in BibTeX**. |
| `tian2021fatigue` [3] | Exists; DOI [10.1186/s13640-021-00575-1](https://doi.org/10.1186/s13640-021-00575-1); *J Image Video Proc.* 2021:33. |
| `ren2019comparison` [4] | Exists; DOI [10.1109/TNSRE.2019.2906371](https://doi.org/10.1109/TNSRE.2019.2906371); 27(5):867--875. |
| `shahbakhti2023fusion` [5] | Exists; DOI [10.1109/TNSRE.2023.3267114](https://doi.org/10.1109/TNSRE.2023.3267114); 31:2037--2046; PMID 37058390. |
| `croft2000removal` [6] | Exists; DOI [10.1016/S0987-7053(00)00055-1](https://doi.org/10.1016/S0987-7053(00)00055-1); 30(1):5--19. |
| `akuthota2023artifacts` [7] | Exists; DOI resolves; **wrong year/type** as above. |
| `agarwal2019blink` [8] | Exists; DOI resolves; **conference venue/pages missing** as above. |
| `ko2020eyeblink` [9] | Exists; DOI [10.1088/1741-2552/ab909f](https://doi.org/10.1088/1741-2552/ab909f); 17(3):036015. |
| `klein2013reliable` [10] | Exists; DOI [10.1007/s10548-013-0281-2](https://doi.org/10.1007/s10548-013-0281-2); 26(4):558--568. |
| `zhang2023method` [11] | Exists; DOI [10.1109/JSEN.2022.3232176](https://doi.org/10.1109/JSEN.2022.3232176); 23(3):2794--2802. |
| `rashida2023quantitative` [12] | Exists; DOI [10.1016/j.neuri.2022.100115](https://doi.org/10.1016/j.neuri.2022.100115); 3(1):100115. |
| `jiang2023eyeblink` [13] | Exists; DOI [10.1109/JSEN.2023.3305118](https://doi.org/10.1109/JSEN.2023.3305118); 23(18):21374--21384. |
| `chang2016detection` [14] | Exists; DOI [10.1016/j.cmpb.2015.10.011](https://doi.org/10.1016/j.cmpb.2015.10.011); 124:19--30. |
| `kleifges2017blinker` [15] | Exists; DOI [10.3389/fnins.2017.00012](https://doi.org/10.3389/fnins.2017.00012); 11:12; PMCID PMC5289990. |
| `tran2021detection` [16] | Exists; DOI [10.24018/ejeng.2021.6.4.2438](https://doi.org/10.24018/ejeng.2021.6.4.2438); 6(4):6--12. |
| `jefri2022eye` [17] | Exists; DOI resolves; **proceedings metadata missing** as above. |
| `nolan2010faster` [18] | Exists; DOI [10.1016/j.jneumeth.2010.07.015](https://doi.org/10.1016/j.jneumeth.2010.07.015); 192(1):152--162. |
| `ghosh2023automatic` [19] | Exists; DOI [10.1109/JSEN.2023.3237383](https://doi.org/10.1109/JSEN.2023.3237383); 23(5):5422--5436. |
| `wang2022multidimensional` [20] | Exists; DOI [10.1109/TNSRE.2022.3164126](https://doi.org/10.1109/TNSRE.2022.3164126); 30:905--914. |
| `wang2025sliding` [21] | Exists; DOI resolves; **five coauthors omitted** as above. |
| `cao2021unsupervised` [22] | Exists; DOI [10.1109/JBHI.2021.3057891](https://doi.org/10.1109/JBHI.2021.3057891); 25(8):2895--2905. |
| `valderrama2018automatic` [23] | Exists; DOI [10.1088/1741-2552/aa8d95](https://doi.org/10.1088/1741-2552/aa8d95); 15(1):016008. |
| `guttmann2019new` [24] | Exists; DOI [10.1016/j.compbiomed.2019.103442](https://doi.org/10.1016/j.compbiomed.2019.103442); 114:103442. |
| `cao2019multichannel` [25] | Exists; DOI [10.1038/s41597-019-0027-4](https://doi.org/10.1038/s41597-019-0027-4); *Scientific Data* 6:19. |
| `GramfortEtAl2013a` [26] | Exists; DOI [10.3389/fnins.2013.00267](https://doi.org/10.3389/fnins.2013.00267); 7:267. |
| `jas2017autoreject` [27] | Exists; **DOI missing in BibTeX**; canonical DOI [10.1016/j.neuroimage.2017.06.030](https://doi.org/10.1016/j.neuroimage.2017.06.030). |
| `Hatlestad_2023_reliable` [28] | Exists; DOI [10.1016/j.clinph.2023.03.002](https://doi.org/10.1016/j.clinph.2023.03.002); 150:1--16. |
| `black2012` [29] | Exists; DOI resolves; **malformed volume and uninformative key** as above. |
| `soukupova2016realtime` [30] | Exists as workshop paper; no DOI located; rendered metadata incomplete. |
| `iwasaki2005effects` [31] | Exists; DOI [10.1016/j.clinph.2004.11.001](https://doi.org/10.1016/j.clinph.2004.11.001); 116(4):878--885. |
| `Startsev2023` [32] | Exists; DOI [10.3758/s13428-021-01763-7](https://doi.org/10.3758/s13428-021-01763-7); 55(4):1653--1714. |
| `ahn2016exploring` [33] | Exists; DOI [10.3389/fnhum.2016.00219](https://doi.org/10.3389/fnhum.2016.00219); 10:219; PMID 27242483. |
| `chai2017improving` [34] | Exists; DOI [10.3389/fnins.2017.00103](https://doi.org/10.3389/fnins.2017.00103); 11:103; PMID 28326009. |
| `lan2024driving` [35] | Exists; DOI [10.1016/j.bspc.2024.106031](https://doi.org/10.1016/j.bspc.2024.106031); 92:106031. |
| `dai2023detection` [36] | Exists; DOI [10.3390/app13042718](https://doi.org/10.3390/app13042718); 13(4):2718. |
| `chen2022fatigue` [37] | Exists; DOI [10.3390/s22134717](https://doi.org/10.3390/s22134717); 22(13):4717. |
| `shahbakhti2022simultaneous` [38] | Exists; DOI [10.1109/JBHI.2021.3096984](https://doi.org/10.1109/JBHI.2021.3096984); 26(3):1001--1012. |
| `simon2011eeg` [39] | Exists; DOI [10.1016/j.clinph.2010.10.044](https://doi.org/10.1016/j.clinph.2010.10.044); 122(6):1168--1178. |
| `lin2014wireless` [40] | Exists; DOI [10.1109/TBCAS.2014.2316224](https://doi.org/10.1109/TBCAS.2014.2316224); 8(2):165--176. |
| `li2015context` [41] | Exists; DOI [10.3390/s150820873](https://doi.org/10.3390/s150820873); 15(8):20873--20893. |
| `rashid2021random` [42] | Exists; DOI [10.18280/ts.380501](https://doi.org/10.18280/ts.380501); 38(5):1259--1270. |
| `lee2023lstm` [43] | Exists; DOI [10.1016/j.eswa.2022.119032](https://doi.org/10.1016/j.eswa.2022.119032); 213:119032. |
| `shahbakhti2021vme` [44] | Exists; DOI [10.1109/TNSRE.2021.3054733](https://doi.org/10.1109/TNSRE.2021.3054733); 29:408--417; PMID 33497337. |
| `ingre2006subjective` [45] | Exists; DOI [10.1111/j.1365-2869.2006.00504.x](https://doi.org/10.1111/j.1365-2869.2006.00504.x); 15(1):47--53. |
| `schleicher2008blinks` [46] | Exists; DOI [10.1080/00140130701817062](https://doi.org/10.1080/00140130701817062); 51(7):982--1010. |
| `guttmann2025dataset` [47] | Exists; DOI [10.1038/s41597-025-04861-9](https://doi.org/10.1038/s41597-025-04861-9); *Scientific Data* 12(1), article number should be added. |
| `chang2016unsupervised` [48] | Exists; DOI [10.1088/0967-3334/37/3/401](https://doi.org/10.1088/0967-3334/37/3/401); 37(3):401--417. |
| `aoki2023drowsiness` [49] | Exists; DOI [10.24507/ijicic.19.01.229](https://doi.org/10.24507/ijicic.19.01.229) resolves to the publisher PDF; 19(1):229--238. Crossref did not return a record, so verify directly with the journal at final proof stage. |

## Dataset audit

### Public Cao sustained-attention driving corpus

| Item | Manuscript | External record | Audit verdict / action |
|---|---|---|---|
| Identity | Called "Cao2018" and cited to a 2019 paper. | Cao et al. 2019, *Scientific Data* 6:19; raw figshare dataset v5. | Use an unambiguous name such as "Cao et al. sustained-attention dataset" or "NCTU-LK" and explain the `Cao2018` label. |
| Participants/sessions | 27 participants, 62 sessions. | Confirmed. Participants were healthy adults aged 22--28; 62 recordings; ~82 total hours. | Add demographics and subject-session nesting. |
| Analysed sessions | Headline total implies 58 public sessions; methods describes all 62. | Official dataset has 62; manuscript source says four were excluded but the sentence is commented out. | **Critical:** report all four exclusions, session IDs, reasons, and whether rules were set before observing model performance. |
| Acquisition | 32 electrophysiological channels; ~90-min task. | 30 scalp EEG + A1/A2 mastoid references, 500 Hz; sessions vary roughly 41--118 min although nominal task is 90 min. | Report 500 Hz and actual retained durations. Clarify that A1/A2 are references, not scalp EEG or EOG channels. |
| Events/labels | No blink labels/video/EOG; manual EEG-only annotation. | Official records contain lane-departure/response events, not blink labels. | Correctly stated, but EEG-only ground truth is not independent of the EEG algorithms being evaluated. Report annotation uncertainty and sensitivity to label rules. |
| Dataset version/licence | Not reported. | Raw data v5, DOI [10.6084/m9.figshare.6427334.v5](https://doi.org/10.6084/m9.figshare.6427334.v5), CC BY 4.0; BIDS conversion also exists at [NEMAR](https://www.nemar.org/dataset/nm000275). | Add exact DOI/version/licence/download date and analysed file manifest. |

### Internal corpus

The internal data cannot be independently verified from the manuscript or a public registration. The following omissions must be corrected before the corpus can support generalisation claims:

- number of unique participants underlying 46 video segments;
- sessions/segments per participant and whether inferential analyses account for repeated participants;
- age, sex/gender, eligibility, sleep/fatigue protocol, time of day, and simulated-driving duration;
- ethics committee, approval identifier, informed-consent statement, and data governance;
- EEG sampling rate, amplifier model/settings, impedance procedure, EOG derivation/electrode positions, and exact EGI sensor-number-to-10-20 mapping;
- inclusion/exclusion flow from acquired to 46 analysed segments;
- total annotated blink count per participant/session and distribution of partial versus complete blinks;
- whether the 0--7-frame synchronisation shift was chosen while viewing EEG transients, who chose it, and whether raters were blinded at that step;
- data/code availability and, if raw data cannot be shared, a justified controlled-access route plus derived annotation files.

The sentence that the two corpora provide "different hardware setups" is supported descriptively, but two simulated lane-keeping corpora do not establish cross-task, cross-population, clinical, or real-driving generalisation.

## Literature balance and missing references

### Closest/methodologically necessary literature missing or underused

| Missing or underused source | Why it matters | Recommended use |
|---|---|---|
| Official MNE `find_eog_events` documentation/source | It is the primary evidence for the default `(max(eog)-min(eog))/4` threshold; the general 2013 MNE paper does not document that function default. | Cite the exact versioned docs/source and report MNE version, function arguments, channel choice, and any wrapper code. [Current official documentation](https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html). |
| Jas et al. 2017 DOI metadata | Stage A directly adapts Autoreject, making it central prior art. | Add DOI [10.1016/j.neuroimage.2017.06.030](https://doi.org/10.1016/j.neuroimage.2017.06.030) and clearly enumerate deviations from the original algorithm. |
| Robust statistics source for MAD normalisation | BLINKER is not the original source for the normal-consistency factor, and the proposed formula is not BLINKER's candidate threshold. | Cite a primary robust-statistics source (e.g., Rousseeuw & Croux 1993, already present in the broader `.bib`) and explain why median + `k x 1.4826 MAD` is appropriate for a blink-enriched, non-normal signal pool. |
| Farago et al. 2022, "Blink and saccade detection from forehead EEG" | Directly relevant single-/forehead-EEG ocular-event detection and workload context; currently present in the large `.bib` but absent from the manuscript. | Include in closest-prior-art comparison; DOI [10.1109/I2MTC48687.2022.9806494](https://doi.org/10.1109/I2MTC48687.2022.9806494). |
| Explicit dataset citation for Cao raw data | The data descriptor is not a substitute for a versioned data citation. | Cite figshare raw v5 DOI [10.6084/m9.figshare.6427334.v5](https://doi.org/10.6084/m9.figshare.6427334.v5). |
| Source/standard for 10-10 anatomical grouping and EGI HydroCel mapping | Butler & Trainor is task-specific; Hatlestad-Hall uses BioSemi ABCD geometry. | Supply a mapping table and cite the actual coordinate/montage authority used. |
| Recent/closest method comparison through 2026 | The negative novelty claims were not supported by a documented current search. | Search IEEE Xplore, PubMed, Scopus/Web of Science, Crossref, and Google Scholar for `EEG AND (blink OR ocular) AND (detect* OR threshold*) AND (epoch OR window OR adaptive)` through the submission date, and report screening criteria. Include peer-reviewed 2025 work and clearly label preprints. |

### Balance problems

1. The Introduction heavily cites papers about **artifact removal/correction** (FASTER, Ghosh, Valderrama, Guttmann-Flury) as evidence about **event detection**. Those tasks have different outputs and validation targets. A method can remove blink energy without accurately estimating onset/offset, so they should not be merged into one detector family.
2. The manuscript cites many supporting examples but little contradictory evidence about the instability of blink features, ambiguity between blinks and other ocular movements, or signal-dependent annotation. Nyström 2024 and Startsev 2023 provide this caution and should be integrated into the main argument, not only limitations.
3. The novelty/gap text does not compare the exact combination of components: per-channel Autoreject thresholding, union selection of high-amplitude epochs, median/MAD sample threshold, and channel-wise application. Without that component matrix, "among the first" is not auditable.
4. Comparisons across published F1/accuracy values would be inappropriate unless matching rules, IoU thresholds, datasets, channels, and independent units are aligned. The paper correctly avoids a raw state-of-the-art number claim, but it should still provide a qualitative closest-method table.
5. Tian & Cao 2021 is a review and is repeatedly used for broad fatigue claims. For central physiological claims (blink duration/frequency with sleepiness), cite the primary driving studies already in the bibliography (Ingre 2006; Schleicher 2008) rather than relying on a secondary chain.

## Required corrections, prioritised

### Essential before submission

1. Correct the 104/108/58 session accounting and disclose the four excluded Cao sessions with IDs and reasons.
2. Correct the BLINKER method description and all causal interpretation that depends on "robust dispersion" or proven threshold dilution.
3. Replace the Alyan citation for fatigue-associated prolonged blinks with condition-matched primary evidence.
4. Add an exact, versioned public-dataset citation and internal-corpus participant/ethics/session structure.
5. Repair the incomplete author lists and the Akuthota year/type error; convert Agarwal and Jefri to conference entries; add the Autoreject DOI.
6. Justify the IoU = 0.1 match criterion with sensitivity analyses and specify the one-to-one matching order.
7. Populate and archive the footnoted code repository, or remove the statements that code is released and every result can be regenerated.

### Strongly recommended

1. Rebuild every active bibliography entry from DOI/publisher metadata; 30/49 are incomplete in the rendered PDF.
2. Replace the unsourced "among the first" statement with a precise novelty statement supported by a closest-prior-art table and documented search date.
3. Cite exact software documentation/version for MNE and code/version for BLINKER and Autoreject.
4. Separate literature on event detection, artifact detection/rejection, and artifact removal.
5. Provide an EGI-specific channel mapping and a transparent electrode-to-region table.
6. Add a claim-to-source supplement so that long multi-claim paragraphs do not end in decorative citation clusters.

## Suggested defensible replacements for the most problematic sentences

1. **Current (p. 1):** "In the context of driving fatigue, increasing fatigue levels are often associated with slower and more prolonged blinks ... [Alyan]."

   **Suggested:** "In simulated-driving studies, increasing subjective sleepiness has been associated with longer blink durations and substantial between-driver variability [Ingre 2006; Schleicher 2008]."

2. **Current (p. 2):** "When thresholds are estimated from the entire recording, they may be biased by the presence of clean epochs ... [Klein; Guttmann-Flury]."

   **Suggested:** "We hypothesised that estimating one threshold from a recording that mixes blink-rich and blink-free epochs could change the operating point of a threshold detector. The cited prior methods motivate adaptive thresholding but do not directly test this epoch-composition mechanism."

3. **Current (pp. 3--4):** "The estimation adopts the approach by [BLINKER], in which each threshold combines ... robust dispersion ..."

   **Suggested:** "Stage B uses a median-plus-scaled-MAD threshold. BLINKER motivated the use of amplitude thresholds and the scaled MAD in blink-candidate screening, but the present center, dispersion, signal pool, and multiplier form a distinct estimator."

4. **Current (p. 10):** "BLINKER combines the mean of the pooled signal with a robust dispersion term ..."

   **Suggested:** "BLINKER's initial potential-blink threshold is the pooled-signal mean plus 1.5 ordinary standard deviations; its robust MAD statistic is used later when filtering candidate blink amplitudes."

5. **Current (p. 2):** "To our knowledge, this is among the first frameworks ..."

   **Suggested:** "The contribution evaluated here is the specific combination of cross-validated epoch screening, a union rule across channels, and per-channel median/MAD thresholds estimated only from screened epochs. We do not claim that its individual components are new."

## Source links used most heavily

- Nyström et al. 2024: [PubMed/PMC](https://pubmed.ncbi.nlm.nih.gov/38424292/)
- Alyan et al. 2023: [Scientific Reports](https://doi.org/10.1038/s41598-023-46738-0)
- Croft & Barry 2000: [Elsevier](https://doi.org/10.1016/S0987-7053(00)00055-1)
- BLINKER: [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC5289990/)
- Autoreject: [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC7243972/)
- Cao et al. dataset paper: [Scientific Data](https://doi.org/10.1038/s41597-019-0027-4)
- Cao raw dataset: [figshare v5](https://doi.org/10.6084/m9.figshare.6427334.v5)
- Cao dataset official BIDS/NEMAR record: [NEMAR nm000275](https://www.nemar.org/dataset/nm000275)
- Hatlestad-Hall et al. 2023: [Clinical Neurophysiology](https://doi.org/10.1016/j.clinph.2023.03.002)
- Startsev & Zemblys 2023: [Behavior Research Methods](https://doi.org/10.3758/s13428-021-01763-7)
- MNE `find_eog_events`: [official documentation](https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html)
- Footnoted code repository (empty at audit time): [pyresearchs/double_thresholding_blink](https://github.com/pyresearchs/double_thresholding_blink)
- Tian & Cao 2021: [SpringerOpen](https://doi.org/10.1186/s13640-021-00575-1)
