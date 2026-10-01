# Methods, Statistics, Validation, and Reproducibility Audit

## Scope and evidence base

This specialist audit covers adversarial causal attribution, ablation and sensitivity, experimental units, data leakage, statistics, performance metrics, baseline fairness, preprocessing, parameter selection, reproducibility/code, robustness, generalization, external validation, and equation/algorithm traceability. The primary manuscript is the 15-page PDF `writing/IEEE-TJ-color-latex-template/main.pdf` (built 2026-10-01). Code and archived result CSVs were inspected in the same repository and, where the manuscript depends on adjacent packages, in the locally available `pyblinker` and `blink_evaluation` source trees.

External methodological checks used authoritative sources: the [MNE `find_eog_events` documentation](https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html), [MNE resampling guidance](https://mne.tools/stable/help/faq.html), [SciPy Wilcoxon documentation](https://scipy.github.io/devdocs/reference/generated/scipy.stats.wilcoxon.html), the [AutoReject project description](https://github.com/autoreject/autoreject), and the [manuscript's cited GitHub repository](https://github.com/pyresearchs/double_thresholding_blink).

## Bottom-line assessment

The archived results do show large within-session numerical differences between the proposed configuration and the two implemented comparator configurations. Independent recalculation reproduces the headline means and the reported significance direction. However, the evidence does **not** isolate epoch screening as the cause. The proposed condition changes the calibration pool, location estimator, multiplier, and threshold-learning machinery at once; moreover, `k=3.0` was selected using an ablation on the same experiment suite, while the BLINKER threshold-crossing baseline uses `k=1.5`. The main causal statement in the Conclusion (PDF p. 11), that the comparison supports epoch screening as the principal contribution, is therefore not demonstrated.

Two additional issues require rerunning, rather than merely rewriting, the Internal analyses. First, archived runs used a nominal 32-channel montage that omitted unavailable Cz/E129 and included an erroneous off-montage E84; the Stage-A union rule means E84 could change candidate epochs and thus every channel's threshold. Second, the code epochs first, then filters and resamples each epoch independently, whereas the PDF says continuous data are downsampled, filtered, and only then epoched. This creates repeated epoch-edge operations and means the implemented experiment is not the stated method.

The strongest defensible result in the current evidence is narrower: **under a lenient IoU=0.1 event criterion, oracle per-session channel selection, full-session offline calibration, and the archived preprocessing/configuration, the proposed configuration had higher macro-F1 than the two particular threshold-crossing comparator configurations.** It is not yet evidence that epoch screening uniquely caused the gain, that the complete BLINKER method was surpassed, or that the detector is reliable on unseen subjects, future time, new devices, or real driving.

## Consolidated methods issue table

| ID | Severity | PDF evidence | Code/data evidence | Problem and consequence | Required action |
|---|---|---|---|---|---|
| MS-01 | **CRITICAL** | Abstract p. 1; Results pp. 9-10; Discussion/Conclusion p. 11 attribute the improvement to epoch-aware screening. | Proposed: `std_threshold: 3.0` (`experiment_script/setup/exp2_strategy_comparison.yaml:2`), median center, flagged-epoch pool. BLINKER: default `std_threshold=1.50` and mean center (`pyblinker/blinker/default_setting.py:84`; `strategies/kleifges.py`). | Multiple components change simultaneously. The 11.3-24.4 point margins cannot be causally attributed to epoch screening. The larger multiplier alone plausibly raises precision and reduces BLINKER's false-positive load. | Run the matched factorial ablation in the confound table below. Until then replace causal language with configuration-level language. |
| MS-02 | **CRITICAL** | PDF pp. 4, 6-10 repeatedly says all 32 Internal channels/montage. | `brain_region_raja.yaml:60-71` states Cz/E129 is unavailable, the true montage is 31 channels, and pre-fix runs include erroneous E84. Published CSVs contain E83 and E84 but no E129; `n_channels_used=32`. `paper_data.py` explicitly says only a rerun removes E84's Stage-A influence. | The analyzed montage is not the declared montage. Because Stage A uses a union across channels, an off-montage signal can change candidate epochs and thresholds for all reported channels. Exact Internal results are not trustworthy until rerun. | Correct the channel map, rerun all Internal experiments from raw data, regenerate every figure/table/claim, and archive a channel manifest per session. |
| MS-03 | **CRITICAL** | PDF p. 2 and Fig. 1 p. 3: continuous recording is downsampled to 100 Hz, filtered 1-20 Hz, then segmented. | `src/exp/exp2_channel_group_sweep.py:70-77` epochs first; `src/common/epoch_input.py:69-78` filters and resamples each epoch independently. | The implementation is not the reported pipeline. Per-epoch filtering/resampling introduces an edge operation at every epoch and can make performance depend on epoch length for signal-processing reasons rather than the proposed statistical mechanism. MNE warns that epoch-level resampling introduces edge artifacts at every epoch. | Implement and rerun the stated continuous filter/resample-then-epoch pipeline, or accurately report the implemented order and quantify edge sensitivity. Prefer continuous preprocessing. |
| MS-04 | **CRITICAL** | Introduction p. 2 says source code and scripts allow every result to be regenerated (footnote 1). | The [cited repository is currently empty](https://github.com/pyresearchs/double_thresholding_blink). `requirements.txt` uses unpinned Git dependencies. The active base environment cannot import the required `pyblinker.double_thresholding`/`strategies` modules; a separate local Conda environment can. Internal data and both corpora's derived annotations are not in this repository. | The reproducibility claim is false at audit time. A third party cannot regenerate the study. | Publish a versioned release/DOI containing code, exact lockfile, commit SHAs, annotations (subject to consent/license), manifests, and one-command workflows. State what data cannot be shared and provide a deterministic synthetic/smoke test. |
| MS-05 | **MAJOR** | PDF p. 10: “the channel with the highest F1 was then retained” and claims this favors no method. Table I and Fig. 9 use that value. | `experiment_script/paper_data.py:17,142-143` explicitly calls this a “best-channel-per-session oracle”; channel is selected by ground-truth F1 separately for every method/session. | This is direct test-label use at evaluation time. It inflates reported scores and is not a deployable rule. Equal access does not eliminate optimism or method-dependent search benefits. Headline values are oracle upper bounds. | Make a prespecified fixed channel (e.g., Fp1), training-only channel selection, or nested subject-wise selection the primary analysis. Label oracle results explicitly as upper bounds. |
| MS-06 | **MAJOR** | PDF never reports how `k` was selected and only defines `k>0` (p. 4). | `src/exp/exp6_std_threshold_sweep.py:3` states: “This is the ablation that decided std_threshold=3.0 for the rest of the suite.” No held-out selection cohort is documented. | Hyperparameter selection appears to have used the same corpora and labels later used for testing. This is supervised test-set tuning even though the detector itself is unsupervised. | Separate development and locked test subjects/datasets, or use nested subject-wise validation. Report the full sweep and selection rule, including all tried values. |
| MS-07 | **MAJOR** | PDF pp. 4-5: 104 total sessions, but Cao2018 is said to contain 62 and Internal 46 (which sum to 108). | Archived results contain 58 Cao2018 + 46 Internal = 104. Dataset discovery retains only `status == Complete`; four Cao sessions are `Issue` (`S49/080602m`, `S44/070209m`, `S42/061229n`, `S22/090922m`). The manuscript's exclusion sentence is commented out. | Four exclusions and reasons are omitted. Since completion/issue status follows manual annotation, exclusion may be outcome- or quality-related and can bias results. | Add a participant/session flow diagram, prespecified eligibility criteria, exact exclusions and reasons, and sensitivity analysis including resolvable sessions where possible. |
| MS-08 | **MAJOR** | Statistical tests are paired by session (pp. 7-10, 14-15); public data are 62 sessions from 27 participants (p. 4). Internal participant count is omitted. | Archived identifiers show 46 Internal sessions from 17 participants (mostly three segments/person) and 58 Cao sessions from 27 participants (1-5 sessions/person). | Sessions from the same person are not independent. SciPy's Wilcoxon documentation assumes paired differences are independent and identically distributed. Treating sessions as independent understates uncertainty/pseudoreplicates subjects. | Use participant-level aggregation, cluster bootstrap/permutation, or a mixed-effects model. Report both subject- and session-level estimates. |
| MS-09 | **MAJOR** | PDF p. 5 accepts IoU >= 0.1; the paper calls the output blink “regions.” | `blink_evaluation/channel_scoring.py:95` defaults to 0.1. Matching maximizes summed IoU with Hungarian assignment, then discards pairs below threshold (`matching.py:100+`). | IoU=0.1 is lenient for boundary localization, and method-specific event durations can interact with the metric. A detector may receive full event credit despite poor onset/offset agreement. The assignment maximizes sum IoU, not necessarily TP cardinality above threshold. | Report sensitivity at IoU 0.1/0.25/0.5/0.75, onset/offset error, duration error, event-count bias, and FP/hour. Use maximum-cardinality threshold-qualified matching or verify equivalence. |
| MS-10 | **MAJOR** | PDF p. 9 calls the comparator “BLINKER”; p. 11 interprets BLINKER's failure. | The manuscript admits only BLINKER's threshold-crossing stage is used; morphology fitting and automatic channel selection are removed. Proposed Stage C uses essentially the same crossing scan. | This is not a comparison with the complete established BLINKER system. Labeling it BLINKER overstates baseline scope and may unfairly penalize it. | Rename to “BLINKER-style threshold-crossing baseline” and separately benchmark the complete validated BLINKER pipeline/configuration. |
| MS-11 | **MAJOR** | PDF p. 9 says all three receive the same preprocessed epochs. | Prepared data are already 1-20 Hz filtered; the MNE wrapper then calls `find_eog_events` with `l_freq=1`, `h_freq=20`, filtering again. MNE also emits fixed +/-0.10 s intervals, unlike threshold-crossing boundaries. | Comparator inputs/event construction are not functionally identical. Double filtering and fixed windows can affect peaks, boundaries, and IoU. | Compare once-filtered signals; document each comparator's unavoidable native processing. Add tuned and native MNE variants, and boundary-matched peak-to-region rules. |
| MS-12 | **MAJOR** | Stage A p. 2 is described as finding epochs “likely to contain blink activity”; Cao labels p. 5 are visually defined from Fp1/Fp2 high-amplitude morphology. | AutoReject is designed to learn PTP thresholds for identifying bad trials/sensors, not blink specificity. Union across 32 channels flags any high-amplitude transient. | Candidate epochs may be selected by muscle, motion, electrode pops, or other artifacts; the claimed mechanism (“blink-heavy pool”) is assumed, not measured. Cao ground truth shares the same EEG amplitude cue, risking criterion circularity. | Report Stage-A precision/recall for “contains >=1 blink,” artifact composition, thresholds, flagged fraction, and results with video/EOG-independent ground truth. |
| MS-13 | **MAJOR** | PDF p. 3 says cross-validation selects each `tau*`, but the optimization equation/number of folds/candidate handling is absent. PDF p. 4 leaves `k` unspecified; Stage C lacks crossing/minimum-duration rules. | A detailed `cross_validation_eq.tex` exists but is not included. Code uses AutoReject Bayesian optimization, seed 42, `augment=False`, fallback to all epochs if none flagged, positive-only crossing, and >50 ms duration, none fully reported. | The algorithm cannot be reproduced from the paper and the displayed equations do not define `b_i`. Important behavior is hidden in dependencies. | Add complete pseudocode/equations and all defaults, including K/folds, optimizer, seed, fallback, polarity, equality rules, minimum duration, and boundary handling. |
| MS-14 | **MAJOR** | Conclusion p. 11 says median configuration and supports epoch screening. | Archived median-vs-mean fixed-channel ablation is nonsignificant at Fp1/Fp2 on both corpora; oracle med-vs-mean is also nonsignificant (Internal p=0.268; Cao p=0.405). | Median choice is not independently established, and it does not establish screening. The paper suppresses a relevant null ablation while making component-level claims. | Restore and transparently report the ablation; focus the primary factorial analysis on screened vs all-epoch calibration at matched `k` and center. |
| MS-15 | **MAJOR** | Epoch-duration analysis pp. 8-10 selects Fp1/Fp2 because they were best in Experiment 1, then tests those electrodes against 30 s on the same sessions. | Same archived sessions drive selection and inference. | Post-selection inference/winner's curse favors the 30-s reference used to identify the channels, especially on Internal where 30 s is the maximum. | Prespecify channels from external literature/training subjects, or nest channel selection inside subject-held-out validation. |
| MS-16 | **MODERATE** | PDF reports only means and adjusted `p<0.05` in the primary table and asterisks in figures/tables. | Exact p-values, confidence intervals, rank-biserial effects, and paired-difference distributions are omitted. Text says Appendix tables give exact adjusted p-values, but Tables II-V contain only a “Sig.” asterisk column. | Readers cannot judge uncertainty, practical magnitude, or assumption sensitivity. Non-significance is sometimes rhetorically treated as retained/comparable performance without an equivalence margin. | Report n, estimate, paired delta, 95% cluster CI, exact raw/adjusted p, effect size, and a prespecified noninferiority/equivalence analysis if comparability is claimed. |
| MS-17 | **MODERATE** | PDF claims stability/robustness across epoch durations and hardware (pp. 10-11). | Only epoch length is varied. No seeds, noise, missing-channel, threshold, filter, sampling-rate, or artifact perturbation results are shown; both corpora are simulated lane keeping and parameters/annotation team are shared. | “Robust,” “reliable,” hardware-independent, and generalized interpretations exceed the tested perturbations. | Restrict language to the observed setting and add the robustness tests listed below. |
| MS-18 | **MODERATE** | No computational-cost section; Introduction motivates computational efficiency/real time. | Full-session calibration, 32-channel AutoReject Bayesian optimization, and oracle channel evaluation are offline. | No evidence supports real-time suitability or complexity advantage. | Report wall time, memory, hardware, asymptotic cost, latency, and a causal/streaming implementation. |

## What actually caused the improvement? Confound analysis

| Component | BLINKER-style baseline | Proposed primary | Controlled? | Confounding risk |
|---|---|---|---|---|
| Calibration pool | All concatenated valid epochs | Only AutoReject-flagged epochs (fallback all if <1) | **No** | This is the claimed innovation, but not isolated. |
| Center | Arithmetic mean | Median | **No** | Changes threshold location and sensitivity to peaks. Archived med-vs-mean difference is small/nonsignificant, but it still must be controlled. |
| Dispersion | 1.4826 x MAD | 1.4826 x MAD | Yes | Shared implementation. |
| Multiplier `k` | 1.5 | 3.0 | **No** | Major precision-recall confound; the doubled multiplier plausibly reduces false positives. |
| Stage-A machinery | None | AutoReject per-channel PTP thresholds + union | **No** | Adds optimizer, randomness, and multichannel artifact sensitivity. |
| Channel use for calibration | Each channel separately | Candidate epochs are determined by union over the whole montage; threshold then per channel | **No** | Cross-channel information benefits proposed method even when scoring one channel. |
| Event scan | Positive threshold crossing, >50 ms | Same scan | Largely yes | Shared core, but manuscript does not disclose positive polarity/minimum duration. |
| Channel chosen for reporting | Ground-truth best per session/method | Ground-truth best per session/method | Symmetric access, **not valid deployment** | Oracle inflation may differ by method and masks poor fixed-channel sessions. |
| Preprocessing | Once in shared prepared epochs | Same | Yes vs BLINKER | Both inherit per-epoch edge mismatch. |
| BLINKER morphology/quality stages | Removed | Not applicable | No | Comparator is only one stage of BLINKER. |
| Hyperparameter selection | Default inherited from BLINKER | `k=3.0` selected by same-suite ablation | **No** | Proposed receives data-informed tuning; baseline does not receive comparable tuning. |

### Minimum factorial experiment needed to isolate epoch screening

At minimum, run all cells below on prespecified fixed channels and subject-held-out folds, with identical preprocessing, scan, event rules, and channel-selection policy:

1. All-epoch pool + mean + `k=1.5` (current BLINKER-style threshold baseline).
2. Screened pool + mean + `k=1.5`.
3. All-epoch pool + median + `k=1.5`.
4. Screened pool + median + `k=1.5`.
5. Repeat cells 1-4 at `k=3.0`.

A screened-vs-all contrast averaged within each matched center/multiplier combination estimates the screening contribution. Center x screening and multiplier x screening interactions should be reported. If resources are constrained, the irreducible comparison is **all-epoch median/MAD at k=3 vs screened-epoch median/MAD at k=3**; without it, the principal causal claim must be removed.

## Parameter and threshold audit

| Parameter/decision | Implemented value | Reported in PDF? | How selected? | Training/test separation? | Audit verdict |
|---|---:|---|---|---|---|
| Nominal sampling rate | 100 Hz | Yes, pp. 2-3 | Convenience/common grid | Not applicable | Raw acquisition rates and resampling implementation missing. |
| Band-pass | 1-20 Hz | Yes | Not justified quantitatively | Same corpora | Filter type/order/transition/padding omitted. |
| Preprocessing order | Epoch -> per-epoch filter -> per-epoch resample | **No; contradicted** | Code architecture | Same corpora | Must reconcile/rerun. |
| Reference epoch | 30 s, nonoverlapping | Yes | Literature/practice; also primary condition | Same data | Reasonable but not independently chosen. |
| Epoch-duration sweep | 10,20,30,40,50,60,120 s | Yes | Literature range | Same sessions/channels selected at 30 s | Post-selection bias; no <10 s or overlap test. |
| Stage-A optimizer | AutoReject `bayesian_optimization` | No | Package default/code default | Full evaluated session | Report algorithm and folds. |
| Stage-A random seed | 42 | No | Unexplained | Full evaluated session | Repeat across seeds. |
| Stage-A augmentation | False | No | Code choice | Full evaluated session | Report and justify. |
| Candidate rule | Any channel PTP > its learned threshold | Partly | Proposed design | Full evaluated session | High false-candidate/artifact risk. |
| Minimum flagged epochs | 1; otherwise fall back to all epochs | No | Unexplained | Full evaluated session | Report fallback frequency and sensitivity. |
| Stage-B center | Median | Yes | Robustness rationale | Same test corpora | Archived advantage vs mean nonsignificant. |
| MAD scaling | 1.4826 | Yes | Normal-consistency/BLINKER | Not tuned | Fine, but “SD compatible” is only under distributional assumptions. |
| Proposed `k` | 3.0 | **No** | Same-suite ablation (`exp6_std_threshold_sweep.py`) | **No held-out test documented** | Test-set tuning; full sweep must be disclosed/nested. |
| BLINKER `k` | 1.5 | No | Baseline default | No comparable tuning | Unfair causal comparison. |
| Minimum event duration | Strictly >50 ms | No | Dependency default | Not tuned/reported | Sensitivity needed; equality at 50 ms is rejected. |
| Crossing polarity | Positive only (`value > threshold`) | No | Dependency behavior | Not tested | Polarity/reference dependence; test inversion/absolute amplitude. |
| Inter-event separation | Baseline/proposed crossing wrapper uses no separation filter | No | Code choice | Not tested | May split/merge differently from full BLINKER. |
| Event matching IoU | 0.1 | Yes | Cited event review but no task-specific validation | Same data | Too lenient as sole criterion. |
| Assignment | Max summed IoU, then threshold | No | Library implementation | Not tested | Verify maximum-cardinality behavior. |
| MNE internal band-pass | 1-20 Hz on already 1-20-Hz prepared signal | Partly | Code setting | Same | Double-filtered comparator. |
| MNE threshold | `(max-min)/4` | Yes | MNE default | Full session | Official MNE documentation confirms; tune/sweep fairly. |
| MNE event half-window | 0.10 s | No | Config default | Unexplained | Directly affects IoU and event duration. |
| Channel selection | Per-method/session argmax F1 | Disclosed but not called oracle | Test labels | **No** | Invalid primary deployment metric. |
| Multiplicity | Bonferroni within local families | Partly | Analysis choice | N/A | Family definitions and exact p absent; selection multiplicity omitted. |

## Experimental unit, leakage, and validation audit

### True units

- Event counts are repeated observations nested within sessions.
- Sessions are nested within people. Archived IDs yield **17 Internal participants for 46 sessions** and **27 Cao participants for 58 analyzed sessions**.
- The independent biological unit for population inference is the participant, not the blink, epoch, electrode, or session.
- The paper correctly computes event metrics within session and macro-averages sessions, avoiding blink-count pseudoreplication at the metric stage, but the inferential tests then incorrectly treat repeated sessions from one participant as independent differences.

### Leakage and optimism pathways

1. **Direct ground-truth leakage:** best channel is chosen by test-session F1 separately for every method. This is explicitly an oracle in the code.
2. **Hyperparameter leakage:** the repository says a same-suite standard-threshold ablation selected `k=3.0`; no held-out development set is documented.
3. **Post-selection inference:** Fp1/Fp2 are selected as winners at the 30-s condition on the same sessions used for epoch-duration hypothesis tests.
4. **Full-session transduction:** Stage A/B examine the entire evaluated session, including future data, before detecting any event. This is not label leakage, but it is offline/transductive calibration and cannot support prospective/online claims.
5. **No subject-held-out external test:** there is no learned supervised model, but channel/parameter/design choices were informed by these corpora. The public corpus is a second benchmark, not clean external validation unless it was locked before all choices.

Recommended primary evaluation: freeze all parameters using development participants; use a fixed deployable channel or training-fold channel choice; evaluate once on held-out participants (preferably a third independently annotated corpus); compute cluster/participant uncertainty; and keep the current per-session oracle only as a labeled upper bound.

## Independent statistical recalculation

Using `publication_results/exp3_raja/exp2_strategy_comparison_raja_results.csv` and `publication_results/exp3_cao/exp2_strategy_comparison_cao2018_results.csv`, the headline oracle means reproduce. Two-sided SciPy Wilcoxon tests also reproduce significance. Rank-biserial correlations below use signed ranks of nonzero paired differences. “Subject sensitivity p” first averages sessions within subject and is only a simple sensitivity check, not a substitute for a full clustered model.

| Dataset | Comparison | Proposed mean F1 | Baseline mean F1 | Mean delta | Raw p | Bonferroni x4 p | Rank-biserial r | Subject-aggregated sensitivity p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Internal (46 sessions, 17 subjects) | Proposed-Med vs BLINKER-style | 0.882509 | 0.765428 | +0.117081 | 2.26e-5 | 9.05e-5 | 0.6818 | 0.0129 |
| Internal | Proposed-Med vs MNE | 0.882509 | 0.666429 | +0.216080 | 5.95e-4 | 0.00238 | 0.5652 | 0.00385 |
| Cao2018 (58 sessions, 27 subjects) | Proposed-Med vs BLINKER-style | 0.806753 | 0.694013 | +0.112740 | 4.50e-9 | 1.80e-8 | 0.8854 | 5.53e-6 |
| Cao2018 | Proposed-Med vs MNE | 0.806753 | 0.562736 | +0.244017 | 2.18e-7 | 8.71e-7 | 0.7826 | 1.84e-4 |

Thus, clustering does not appear likely to erase the direction of the configuration-level difference, but it does not repair the causal confounding, oracle evaluation, test-set tuning, montage error, or metric leniency.

The archived Proposed-Med vs Proposed-Mean oracle comparison is nonsignificant: Internal 0.88251 vs 0.87421 (p=0.268), Cao2018 0.80675 vs 0.80303 (p=0.405). The archived fixed-Fp1/Fp2 analysis likewise reports no significant median-vs-mean contrast. This weakens claims that the median estimator itself is demonstrated to improve performance.

### Statistical reporting defects

- No confidence intervals for F1, precision, recall, deltas, or subject heterogeneity.
- No exact p-values in the main table; Appendix prose promises exact adjusted p-values but Tables II-V provide only asterisks.
- No rank-biserial effects despite a dormant methods fragment saying they would be reported.
- No assessment of the Wilcoxon symmetry assumption for paired differences.
- No subject-cluster analysis.
- No noninferiority/equivalence test for claims that Fp1/Fp2 “retain” full-montage performance. Failure to reject a difference is not evidence of equivalence.
- Numerous per-electrode families are separated by corpus/configuration; this is defensible only if prespecified, but the post-selection of highlighted electrodes is not incorporated into multiplicity control.
- F1 differences as small as 0.4 points become significant in the epoch-duration experiment, while uncertainty and practical margins are not shown.

## Metric audit

Macro session averaging is a reasonable headline choice because it prevents long/high-blink-count recordings from dominating. Precision, recall, and F1 are also appropriate event-detection summaries. They are insufficient for a blink-region method, however, because:

- IoU=0.1 provides very weak boundary evidence.
- F1 does not show false alarms per unit time, blink-count bias, calibration, onset/offset error, or duration error.
- Oracle channel selection maximizes the same F1 later reported, creating selection bias.
- MNE events are fixed 200-ms windows, whereas threshold-crossing durations vary; IoU can therefore favor a method's interval geometry.
- Cao labels derived from EEG amplitude share the detector's core cue.
- Macro-F1 alone can hide catastrophic per-driver failures; Fig. 9 reveals dispersion but provides no robust lower-tail metric.

Add median and interquartile session F1, 5th percentile/worst-decile performance, FP/minute, blink-count bias, recall by blink duration/amplitude, onset and offset absolute errors, duration error, and IoU-threshold curves. Report both fixed-channel and oracle results.

## Preprocessing and algorithm traceability

### Material code-to-paper discrepancies

| Topic | PDF | Implementation/archive | Consequence |
|---|---|---|---|
| Preprocessing order | Continuous downsample -> filter -> epoch (pp. 2-3) | Epoch -> filter each epoch -> resample each epoch | Different signals and repeated boundary artifacts. |
| Stage C scope | Search “within each valid epoch” (p. 4) | Concatenate all valid epochs and scan crossings across boundaries (`double_thresholding/core.py:107-113`) | Events may span artificial joins; not the specified per-epoch reset. |
| Internal montage | 32 named electrodes including Cz and P5 (p. 4) | No Cz/E129; includes P8 and erroneous E84; Fig. 7 even labels E83 | Results and anatomical interpretation do not match declared inputs. |
| Session counts | 104 total; public corpus “contains 62” (p. 4) | 58 public +46 internal analyzed | Four exclusions hidden. |
| Stage-A equation | `tau*` selected by CV; `b_i` then appears (p. 3) | Actual AutoReject optimization details only in dependency; unused `cross_validation_eq.tex` exists | Published algorithm incomplete. |
| Threshold multiplier | Defines `k>0` only (p. 4) | Proposed k=3, BLINKER k=1.5 | Critical hidden confound. |
| Event rules | Merely “comparing samples” (p. 4) | Positive-only crossings, strict >50 ms, no minimum-separation filter | Polarity/duration behavior hidden. |
| MNE preprocessing | “same epochs, filtered 1-20 Hz” (p. 9) | Wrapper filters 1-20 Hz again inside `find_eog_events` | Comparator double filtered. |
| Code release | Code allows every result to be regenerated (p. 2) | Linked GitHub repository empty | Claim is currently false. |
| Appendix p-values | Results text says exact adjusted p-values are in Tables II-V | Tables show only “Sig.” asterisks | Traceability contradiction. |

Other missing preprocessing details: original sampling rates, exact reference/re-reference operations, units/scaling, FIR design/order/transition bandwidth, padding, treatment of incomplete final epochs, bad-segment annotations, flat/noisy channels, clipping/saturation, polarity conventions, and whether video-shift adjustment was performed before viewing all labels. The code uses a legacy Hamming-FIR path with DC padding and delay compensation, not enough information is in the PDF to reproduce it.

## Baseline fairness

The comparison is not yet a fair test of the scientific proposition “screening vs pooling.”

- BLINKER is reduced to a bare threshold-crossing stage but named as the established full method.
- BLINKER uses k=1.5 while proposed uses k=3.0 selected on these corpora.
- Proposed uses a whole-montage union to calibrate each channel; BLINKER calibrates each channel independently.
- MNE is double filtered and assigned a fixed 200-ms window; neither the window nor threshold is tuned.
- The proposed method appears extensively explored (center, k, epoch length, channel subsets), while comparable baseline tuning/sensitivity is absent.
- No simple all-epoch median/MAD k=3 baseline is shown, even though it is the exact control needed.
- No modern morphology/GMM/learning baseline from the cited literature is implemented.

Baseline comparisons should use identical data manifests, preprocessing, fixed channels, matching, and a symmetric tuning budget nested within development data. Native complete-method results can be shown separately from mechanism-matched ablations.

## Missing experiment table

| Missing analysis/experiment | Why needed | Could change conclusion? | Priority |
|---|---|---|---|
| Matched all-epoch vs screened pool at identical center and k | Isolates the claimed contribution | **Yes, directly** | **Essential before publication** |
| 2 (pool) x 2 (center) x 2+ (k) factorial ablation | Quantifies interactions/confounds | **Yes** | **Essential before publication** |
| Full Internal rerun with correct 31-channel manifest or defensible replacement for Cz | Removes E84/Cz contamination | **Yes** | **Essential before publication** |
| Continuous preprocessing rerun matching the PDF | Removes per-epoch edge confound | **Yes** | **Essential before publication** |
| Fixed deployable channel and nested/held-out channel choice | Removes oracle label leakage | **Yes for headline magnitude** | **Essential before publication** |
| Subject-clustered/mixed-effects analysis | Corrects true unit and uncertainty | Possibly for marginal findings | **Essential before publication** |
| Locked development/test separation for k and all hyperparameters | Removes test-set tuning | **Yes** | **Essential before publication** |
| IoU and boundary sensitivity (0.1-0.75, onset/offset/duration errors) | Validates region localization | **Yes** | **Essential before publication** |
| Transparent four-session exclusion analysis | Rules out selection bias | Possibly | **Essential before publication** |
| Full BLINKER and fairly tuned/native MNE comparisons | Supports baseline superiority | **Yes** | **Essential before publication** |
| Stage-A blink-purity/sensitivity and artifact composition | Tests assumed mechanism | **Yes for mechanistic claim** | **Essential before publication** |
| Random-seed repeat (e.g., >=20 seeds) | AutoReject optimization is stochastic | Possibly | Strongly recommended |
| k, minimum-duration, MNE-window, filter, and sampling-rate sweeps | Tests arbitrary constants | Possibly | Strongly recommended |
| Negative-polarity/signal-inversion test | Detects reference/polarity dependence | Possibly | Strongly recommended |
| Robustness to motion, electrode pops, clipping, noise, missing channels | Tests naturalistic reliability | Yes for robustness claim | Strongly recommended |
| Recall by normal blink vs prolonged closure and amplitude quartile | Fatigue relevance and subgroup behavior | Possibly | Strongly recommended |
| Third corpus with independent video/eye-tracker labels | Genuine external validation | Yes for generalization | Strongly recommended |
| Online/causal moving calibration | Supports deployment/real-time claims | Yes for deployment | Strongly recommended |
| Compute time, memory, and latency benchmark | Supports efficiency/practicality | No for accuracy, yes for deployment | Useful additional evidence |
| Candidate-pool fraction and fallback frequency per session | Explains when method degenerates to baseline | Possibly | Useful additional evidence |

## Robustness, generalization, and practical significance

The two-corpus repetition is useful but weaker than it appears. Both datasets use simulated lane keeping, both are processed and annotated by the same study team, both use full-session offline calibration, and both inform method development. Different hardware does not establish hardware independence when dataset, montage, annotation certainty, and participant composition all change together. The similar 11-point gap to the BLINKER-style baseline is encouraging configuration-level replication, but it is not a controlled cross-device experiment.

Practical significance of an 11-point F1 margin could be substantial, but the operational consequence is not quantified. The paper should translate errors into false blinks/minute and blink-rate bias because fatigue monitoring acts on derived blink rates/durations, not F1 itself. It must also show lower-tail per-driver reliability. A mean of 88% can coexist with unacceptable sessions, and the paper itself notes MNE's low-recall failures without applying the same worst-case standard to the proposed method.

No complexity evidence is presented. AutoReject Bayesian optimization across a full montage and full session may be materially more expensive than a one-pass threshold. The method is offline and noncausal because the threshold uses future epochs. “Straightforward,” “practical,” or real-time-adjacent language should be qualified until latency and a moving-window implementation are tested.

## Recommended defensible revision of the core claim

Current conclusion (PDF p. 11) effectively claims that the comparison supports epoch screening as the principal contribution. A defensible interim wording is:

> Under offline full-session calibration, an IoU threshold of 0.1, and oracle per-session channel selection, the evaluated screened-epoch median/MAD configuration achieved higher macro-F1 than the implemented BLINKER-style threshold-crossing and MNE peak-detection configurations on two simulated-driving corpora. Because calibration pool, threshold center, multiplier, and comparator implementations differed, the present comparison does not isolate the contribution of epoch screening; matched ablations and subject-held-out validation are required.

After the essential experiments, a stronger mechanism-level claim would be justified only if screened vs all-epoch calibration remains beneficial at matched center/k, fixed deployable channels, corrected preprocessing, participant-level inference, and stricter boundary criteria.

## High-priority questions for the authors

1. Why was k=3.0 used for the proposed method while the BLINKER-style baseline used k=1.5?
2. Was k=3.0 selected after inspecting F1 on either corpus, and where is the complete sweep?
3. What result is obtained for all-epoch median/MAD at k=3.0 versus screened-epoch median/MAD at k=3.0?
4. Why is a best-channel-per-session oracle, chosen using reference labels, the headline operating point?
5. What are the fixed-Fp1 and fixed-Fp2 strategy-comparison scores for every comparator?
6. Why are 58 of 62 Cao sessions analyzed, and what specific issues led to the four exclusions?
7. How many Internal participants produced the 46 sessions, and why are repeated sessions treated as independent Wilcoxon observations?
8. How do conclusions change under participant-level aggregation or cluster bootstrap?
9. Why does the manuscript describe 32 Internal electrodes including Cz when archived results have no Cz and include E84?
10. Has every Internal result been rerun after correcting E84 to E83, given that Stage A uses all channels?
11. Why does code epoch before filtering/resampling while the method and Fig. 1 state the reverse order?
12. How much of the epoch-duration effect is caused by repeated filter/resampling edge operations?
13. What fraction of Stage-A candidate epochs actually contains a manually annotated blink?
14. How often does the fallback to all epochs occur, and what is performance in those sessions?
15. How sensitive are results to IoU thresholds of 0.25, 0.5, and 0.75?
16. What are onset, offset, and duration errors, not only event F1?
17. Why is the complete BLINKER pipeline not tested while the truncated stage is labeled BLINKER?
18. Why is MNE filtered again internally and assigned an undocumented +/-100 ms window?
19. Does the method work after signal inversion or with negative blink polarity?
20. What are results across multiple AutoReject seeds?
21. How were original sample rates, references, bad channels, clipping, and incomplete epochs handled?
22. Can the authors provide a public, immutable code release when the manuscript's linked repository is empty?
23. Can the derived annotations be released, particularly the Cao annotations not supplied with the public data?
24. Why were nonsignificant median-vs-mean ablations archived while the Conclusion describes a median-based configuration as supporting screening?
25. What evidence supports hardware independence when corpus, montage, annotation modality, and participant population all change simultaneously?

