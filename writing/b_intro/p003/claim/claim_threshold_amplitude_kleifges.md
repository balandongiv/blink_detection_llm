---
schema_version: '1.0'
claim_id: CL_b_intro_p003_004
paragraph_id: b_intro/p003
paper: kleifges2017blinker
cite: kleifges2017blinker
evidence_ids:
- EV_kleifges2017blinker_001
manuscript_text: Thresholding-based methods, in contrast, detect candidate blink events when
  the signal amplitude exceeds a certain threshold value, as blink activity typically produces
  large-amplitude deflections ~\citep{chang2016detection,kleifges2017blinker}.
evidence_class: full_text
locator:
  source_file: kleifges2017blinker.pdf
  page: 2
  page_index: 1
  section: INTRODUCTION
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 177.84
    y0: 588.04
    x1: 550.43
    y1: 598.56
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: methodological
  human_qc: pending
---

## Exact evidence (literal)

Contamination of electroencephalography (EEG) by eye and muscle activity is an ongoing challenge, and many techniques exist for the removal of these artifacts (Jung et al., 2000; Delorme et al., 2007; Nolan et al., 2010; Mognon et al., 2011; Winkler et al., 2011).

## Normalized evidence

Contamination of EEG by eye and muscle activity is an ongoing challenge, and many techniques exist for the removal of these artifacts.

## Evidence meaning

Kleifges et al. (2017) describe BLINKER, which extracts blinks from EEG using amplitude thresholds combined with other criteria. The Introduction acknowledges EEG contamination by eye activity. The BLINKER pipeline itself uses a range-based threshold to identify blink candidates, supporting the general concept of threshold-based blink detection. However, the paper does not contain the exact phrasing about "large-amplitude deflections" — it implements thresholding rather than describing it generically.

## Provenance notes

- The supporting text appears in the Introduction on PDF page 1.
- support_type: methodological — the paper implements a threshold-based approach (BLINKER uses amplitude range thresholds) rather than explicitly stating the general principle.
- The paper's main contribution is the BLINKER toolbox, not a description of thresholding as a method category.
