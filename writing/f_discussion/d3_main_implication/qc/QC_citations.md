# QC sheet for `f_discussion/d3_main_implication/paragraph.tex`

Prepared 2026-09-29 and updated 2026-09-30. On 2026-09-30 you removed the disadvantages paragraph (the one about online calibration, amplitude-only screening and the full montage). The claims that paragraph carried, and their Åkerstedt 2010 and Casson 2019 citations, are no longer in d3. Online threshold adaptation (Chang 2016) is now cited in d6 instead; see `f_discussion/d6_future/qc/QC_citations.md`. Please tick each box after checking the source yourself.

## Where the paragraph appears

| Item | Value |
|---|---|
| Source file | `writing/f_discussion/d3_main_implication/paragraph.tex`, one paragraph of about 275 words, excluding citations |
| Compiled PDF | `writing/elsarticle/bspc_manuscript.pdf`, PDF pages 29–30, line numbers about 590–614 |
| Build status | `latexmk` exit 0. All citations in this paragraph resolve. |
| Reference numbers in the PDF | Tian [3], Kleifges [15], Gramfort [26], Ingre [43], Schleicher [44] |
| BibTeX entries no longer cited anywhere | `akerstedt2010reaction` and `casson2019wearable` are still in `references_scopus_new.bib` but uncited. BibTeX skips uncited entries, so they do not appear in the reference list. |
| Local reference PDFs | `writing/f_discussion/d3_main_implication/qc/pdfs/` (untracked in git) |

**Verification levels used below**
- **FULL TEXT:** the quote was found word for word in a local PDF, and the page is given.
- **ABSTRACT:** the full text is paywalled. The quote comes from the published abstract, which is printed on the article's first page.

---

## Part A: Citation evidence

### A1. `tian2021fatigue` [3], FULL TEXT
- **Claim:** "In a drowsiness-monitoring application, such false detections could artificially inflate blink-rate indices used to assess fatigue~\citep{tian2021fatigue}."
- **Reference:** Tian, Y., Cao, J. (2021). Fatigue driving detection based on electrooculography: a review. *EURASIP Journal on Image and Video Processing*, 2021:33. doi:10.1186/s13640-021-00575-1
- **PDF:** `qc/pdfs/tian2021fatigue.pdf`
- **Exact wording:**
  - Page 7 of 17 (§4.2): "Eye movement characteristics, such as saccades, fixations, and blinks detected by EOG signals, have already been used for fatigue driving monitoring [52]."
  - Page 8 of 17, Table 1 "Commonly eye movement features from EOGs", Blink row: "…maximum/mean/sum of blink rate/blink number"
- **Note:** Tian supports only the claim that blink-rate features are used for fatigue monitoring. "False detections inflate the index" is our own reasoning.
- [ ] Checked

### A2. `kleifges2017blinker` [15], FULL TEXT
- **Claims:** the tool name "BLINKER~\citep{kleifges2017blinker}", plus the uncited sentence "This limitation also helps explain why the complete BLINKER pipeline incorporates an additional blink-detection step rather than relying on thresholding alone."
- **PDF:** `qc/pdfs/kleifges2017blinker.pdf`
- **Exact wording:**
  - p. 3: "Regardless of the input signal type, BLINKER uses the same method for initial blink detection and preliminary calculation of blink start and end times." … "These intervals form the potential blinks."
  - p. 4: "Having identified the potential blinks, BLINKER then applies a fitting process to find specified landmarks for each blink and saves information about each candidate blink in a structure."
  - p. 4: "The quality (R2) of the correlation of these lines (denoted by leftR2 and rightR2, respectively) with the actual blink trajectory is a measure of the closeness of the potential blink to a stereotypical blink."
  - p. 8: "EEG channels in general have a smaller ratio of “good” blinks to potential blinks than the vertical upper EOG channel."
- **Note:** Kleifges does not say the fitting step was added *because* thresholding over-detects, so "helps explain why" is our interpretation.
- [ ] Checked

### A3. `GramfortEtAl2013a` [26], FULL TEXT (tool name only)
- **PDF:** `qc/pdfs/GramfortEtAl2013a.pdf`, p. 2: "In this paper, we describe the MNE-Python package in detail, starting from the standard analysis pipeline to more advanced usage."
- [ ] Checked

### A4. `ingre2006subjective` [43], FULL TEXT
- **Claim:** "This is arguably the more serious failure for a warning system, which must be reliable for each driver rather than on average~\citep{ingre2006subjective}."
- **Reference:** Ingre, M., Åkerstedt, T., Peters, B., Anund, A., Kecklund, G. (2006). *Journal of Sleep Research*, 15(1), 47–53. doi:10.1111/j.1365-2869.2006.00504.x
- **PDF:** `qc/pdfs/ingre2006subjective.pdf`. This is the published version, so PDF p1 = journal p. 47. It is a third-party copy hosted at fatiguemanagersnetwork.org.
- **Exact wording (Summary, journal p. 47):** "The results have implications for any application that needs prediction at the subject level (e.g. driver fatigue warning systems) as well as for research design and the interpretation of group average data."
- [ ] Checked

### A5. `schleicher2008blinks` [44], ABSTRACT (Taylor & Francis paywall)
- **Claim:** "…the degree of dilution depends on how often the driver blinks, and blink frequency changes with sleepiness and differs considerably between drivers~\citep{schleicher2008blinks}."
- **Reference:** Schleicher, R., Galley, N., Briest, S., Galley, L. (2008). Blinks and saccades as indicators of fatigue in sleepiness warnings: looking tired? *Ergonomics*, 51(7), 982–1010. doi:10.1080/00140130701817062. PubMed 18568959.
- **Exact wording (abstract, journal p. 982):**
  - "Regarding oculomotoric parameters, blink duration, delay of lid reopening, blink interval and standardised lid closure speed were identified as the best indicators of subjective as well as objective sleepiness."
  - "Substantial inter-individual differences in all of these variables were illustrated."
- **To check in the full text:** "blink interval" is the inverse of blink frequency. Confirm the direction of its change with sleepiness, and that the inter-individual differences apply to blink interval specifically.
- [ ] Checked

---

## Part B: Claims based on Experiment 3 and the Methods (checked word for word against the `.tex` files)

| # | Sentence in d3 | Source in manuscript | Exact wording in source |
|---|---|---|---|
| B1 | "BLINKER … retained most blinks but at the expense of lower precision" | `e_result/exp3/par4.tex:1` | "BLINKER favoured recall over precision, with a mean recall of 95.18\% and a mean precision of 67.94\%." and "the same bias was stronger, with a mean recall of 97.15\% against a mean precision of 56.96\%." |
| B2 | "the complete BLINKER pipeline incorporates an additional blink-detection step" | `e_result/exp3/par2.tex:1` | "…its blink-fitting step and automatic channel selection were not used." See also A2. |
| B3 | "MNE … instead missed most blinks in several sessions on each dataset" | `e_result/exp3/par4.tex:1` | "Its operating points were instead widely dispersed, and recall fell below 30\% in several sessions on each dataset." |
| B4 | "Both failures are consistent with calibrating the threshold on the whole recording…" | `e_result/exp3/par1.tex:1`, `par4.tex:1` | par1: "blink-free epochs dilute these amplitude statistics and pull the threshold down" and "a single large excursion anywhere in the recording raises the threshold for every epoch". par4: "Neither mechanism was isolated, however." |
| B5 | "estimating its threshold only from epochs flagged as containing prominent amplitude excursions" | `d_method/m_pipeline_overview.tex:7` | "Stage A applies an epoch-level, multichannel peak-to-peak screening with a union rule to identify candidate epochs containing prominent amplitude excursions." and "Stage B pools the samples from these candidate epochs…" |
| B6 | "The proposed approach outperformed BLINKER by a similar $F_1$ margin on Internal and Cao2018" | `e_result/exp3/par3.tex:1`, Table `tab:f1_significance` | "so the margin between them stayed close to 11 percentage points on both datasets". Table: Internal 88.25 vs 76.54, Cao2018 80.68 vs 69.40. |
| B7 | "recorded with different hardware and montages … both datasets were collected during simulated lane-keeping tasks" | `d_method/material/dataset.tex:3,7` | "The corpora differed in their acquisition montages and data provenance, allowing the proposed method to be evaluated under different hardware setups." and "EEG was acquired with a 128-channel EGI HydroCel system". |

- [ ] Part B checked

---

## Part C: Open items

1. **Schleicher 2008** was checked from the abstract only.
2. **Our interpretation, not directly cited:**
   - "false detections could artificially inflate blink-rate indices" (A1)
   - "the more serious failure for a warning system" (A4)
   - "helps explain why the complete BLINKER pipeline…" (A2)
   - "A threshold calibrated in this way would therefore depend partly on the state it is meant to monitor" (follows from A5 plus B4)
3. **Already present before these changes, and not introduced by them:** `e_result/exp2/par1.tex` contains two `\citep{...}` placeholders, which compile as undefined citations on page 21.
