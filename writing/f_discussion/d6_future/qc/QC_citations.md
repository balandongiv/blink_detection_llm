# QC sheet for `f_discussion/d6_future/paragraph.tex`

Prepared 2026-09-30, after d6 was rewritten to follow the limitations that remain in `d5_limitations/paragraph.tex`. Please tick each box after checking the source yourself.

## Where the paragraph appears

| Item | Value |
|---|---|
| Source file | `writing/f_discussion/d6_future/paragraph.tex`, one paragraph of about 205 words, excluding citations |
| Compiled PDF | `writing/elsarticle/bspc_manuscript.pdf`, PDF pages 30–31, line numbers about 625–644 |
| Build status | `latexmk` exit 0. All citations in this paragraph resolve. |
| Reference numbers in the PDF | Nyström [1], Tian [3], Shahbakhti 2023 [5], Ko [9], Shahbakhti 2022 [36], Guttmann-Flury 2025 [45], Chang [46], Aoki [47] |
| Local reference PDFs | `writing/f_discussion/d6_future/qc/pdfs/` (untracked in git). Tian and Chang are covered in the d3 QC folder and sheet. |

## How d6 maps to d5

| d5 limitation (current text) | d6 response |
|---|---|
| "The benchmark was restricted to two driving datasets, so generalisation to other experimental paradigms or clinical populations was not tested." | Validate on independent driving datasets and recording systems, then on task-block or trial paradigms (Guttmann-Flury 2025). Clinical populations are **not** addressed in d6. |
| "All analyses were also performed offline on recorded data, so performance under real driving conditions … was not assessed." | Online evaluation under real driving conditions, with the threshold re-estimated over a moving window (Chang 2016). |
| "Performance was not reported separately by blink duration, so detection of prolonged eye closures … remains unestablished." | Report normal blinks and prolonged closures separately. This sentence is unchanged from the earlier d6. |
| "…the evaluation depends on the available reference annotations and their definitions of blink onset and offset…" | Reference annotations from simultaneous eye-tracking or high-speed video (Nyström 2024, Guttmann-Flury 2025). This item is **new**. |
| (not from d5) | Frontopolar spectral markers. This sentence is unchanged from the earlier d6 and follows from d1. |

---

## Part A: New or re-used citations in the rewritten sentences

### A1. `guttmann2025dataset` [45], FULL TEXT
- **Claims:**
  1. "…then on paradigms organised into task blocks or trials, such as the motor-imagery, motor-execution, steady-state visually evoked potential and P300 sessions of a recent multimodal dataset~\citep{guttmann2025dataset}."
  2. "Reference annotations derived from simultaneous eye-tracking or high-speed video~\citep{nystrm2024what,guttmann2025dataset} would reduce the dependence of the evaluation on how blink onset and offset are marked in the EEG."
- **Reference:** Guttmann-Flury, E., Sheng, X., Zhu, X. (2025). Dataset combining EEG, eye-tracking, and high-speed video for ocular activity analysis across BCI paradigms. *Scientific Data*, 12, 587. doi:10.1038/s41597-025-04861-9. PMC11978869. Open access.
- **PDF:** `qc/pdfs/guttmann2025dataset.pdf` (18 pp., published version)
- **Exact wording:**
  - p. 1: "We introduce a large dataset capturing electroencephalogram (EEG) signals, eye-tracking, high-speed camera recordings, as well as subjects’ mental states and characteristics, to provide a multifactor analysis of eye-related movements."
  - p. 1: "Four paradigms - motor imagery, motor execution, steady-state visually evoked potentials, and P300 spellers - are selected due to their capacity to evoke various sensory-motor responses and potential influence on ocular activity."
  - p. 3: "This dataset provides a visually observable reference for eye movements, specifically blinks, through video recordings."
  - p. 14: "The relative positions of these key facial landmarks are then analyzed to detect blinks and to accurately determine their onset and offset."
  - p. 15: "This cross-modal example also validates the overall data quality by enabling comparative analysis between EEG and high-speed video recordings during blinks."
- **To check:** that the four paradigms are trial-based. The abstract gives trial counts ("2520 trials for each of the first three paradigms, and 5670 for P300").
- [ ] Checked

### A2. `nystrm2024what` [1], FULL TEXT
- **Claim:** "Reference annotations derived from simultaneous eye-tracking or high-speed video~\citep{nystrm2024what,guttmann2025dataset}…"
- **Reference:** Nyström, M., Andersson, R., Niehorster, D. C., Hessels, R. S., Hooge, I. T. C. (2024). What is a blink? Classifying and characterizing blinks in eye openness signals. *Behavior Research Methods*, 56(4), 3280–3299. doi:10.3758/s13428-023-02333-9. PMC11133197. Open access.
- **PDF:** `qc/pdfs/nystrm2024what.pdf` (20 pp., published version, so PDF p1 = journal p. 3280)
- **Exact wording (journal p. 3280):**
  - "Traditionally, eyelid position has been estimated directly or indirectly with attachment devices such as electrooculography (EOG) or magnetic search coils (MSC), but it is increasingly being estimated from video recordings of participants’ faces."
  - "However, blinks and their parameters can be estimated only indirectly from this signal, since it does not explicitly contain information about the eyelid position." ("This signal" is the eye tracker's pupil-size signal.)
  - "Blink durations were about 60 ms longer in EO blinks compared to PS blinks."
- **Note:** Nyström shows that blink onset and offset, and therefore duration, depend on the signal used. That supports the idea that a reference taken from a direct eyelid signal would change the annotations. d5 already cites Nyström for the same point.
- [ ] Checked

### A3. `chang2016unsupervised` [46], ABSTRACT (paywalled)
- **Claim:** "Online use would require the threshold to be re-estimated over a moving window of recent epochs rather than calibrated on the whole session, and real-time threshold adaptation has already been achieved for unsupervised blink detection~\citep{chang2016unsupervised}."
- **Exact wording (abstract, *Physiol Meas* 37(3), p. 401):** "…(2) proposing a novel algorithm structure to detect blink artifacts in a real-time environment without any a priori knowledge, and (3) demonstrating that the length of training data can be minimized through the use of a real-time adaption procedure."
- **Note:** The "moving window" is our suggestion. Chang shows only that real-time adaptation is feasible. The full record is in the d3 QC sheet history.
- [ ] Checked

### A4. Citations unchanged from the earlier d6
The following were already in d6 before this rewrite, with the same wording, so they are not re-verified here:
- `tian2021fatigue` and `shahbakhti2023fusion` (prolonged closures)
- `ko2020eyeblink`, `shahbakhti2022simultaneous` and `aoki2023drowsiness` (frontopolar spectral markers)

---

## Part B: Claims based on the Methods

| Sentence in d6 | Source | Exact wording |
|---|---|---|
| "rather than calibrated on the whole session" | `d_method/m_pipeline_overview.tex:7` | "(4) Stage B pools the samples from these candidate epochs to estimate a robust sample-level threshold independently for each channel. (5) Stage C applies each channel's threshold to the corresponding channel across all valid epochs…" |

- [ ] Part B checked
