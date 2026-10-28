---
schema_version: '1.0'
claim_id: CL_b_intro_p003_003
paragraph_id: b_intro/p003
paper: chang2016detection
cite: chang2016detection
evidence_ids:
- EV_chang2016detection_001
manuscript_text: Thresholding-based methods, in contrast, detect candidate blink events when
  the signal amplitude exceeds a certain threshold value, as blink activity typically produces
  large-amplitude deflections ~\citep{chang2016detection,kleifges2017blinker}.
evidence_class: full_text
locator:
  source_file: chang2016detection.pdf
  page: 2
  page_index: 1
  section: Introduction
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 471.52
    y0: 590.14
    x1: 548.11
    y1: 597.72
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

The easiest way to detect eye blink artifacts is simply using a predetermined amplitude threshold [7]. This method classifies an EEG epoch as being artifact contaminated if a portion of the EEG or electrooculogram (EOG) signals in this epoch exceeds an amplitude (or power) threshold.

## Normalized evidence

The easiest way to detect eye blink artifacts is using a predetermined amplitude threshold. This method classifies an EEG epoch as artifact-contaminated if a portion of the EEG or EOG signals exceeds an amplitude or power threshold.

## Evidence meaning

Chang et al. (2016) directly describe thresholding-based blink detection: detecting artifacts when signal amplitude exceeds a threshold value. This matches the manuscript's claim almost verbatim.

## Provenance notes

- The supporting text appears in the Introduction on PDF page 1 (bottom right column).
- The paper also proposes a more sophisticated method beyond simple thresholding, but the cited claim refers to the general description of thresholding methods.
