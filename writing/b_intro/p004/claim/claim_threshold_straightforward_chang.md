---
schema_version: '1.0'
claim_id: CL_b_intro_p004_002
paragraph_id: b_intro/p004
paper: chang2016detection
cite: chang2016detection
evidence_ids:
- EV_chang2016detection_001
manuscript_text: Thresholding is one of the most straightforward and widely used approaches
  for detecting blink activity from EEG signals ~\citep{tran2021detection,chang2016detection}.
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

In this paper, a novel method to detect eye blink artifacts from a single-channel frontal EEG signal was proposed by combining digital filters with a rule-based decision system. The easiest way to detect eye blink artifacts is simply using a predetermined amplitude threshold. This method classifies an EEG epoch as being artifact contaminated if a portion of the EEG or electrooculogram (EOG) signals in this epoch exceeds an amplitude (or power) threshold.

## Normalized evidence

Chang et al. propose a method to detect eye blink artifacts from single-channel frontal EEG using digital filters and rule-based decisions. They describe amplitude thresholding as "the easiest way to detect eye blink artifacts."

## Evidence meaning

Directly supports the claim that thresholding is straightforward and widely used. The paper both describes the simplicity of thresholding and builds upon it with a rule-based extension.

## Provenance notes

- Evidence from abstract and Introduction section, page 1.
- support_type: direct — explicitly describes amplitude thresholding as the simplest detection method.
- See also CL_b_intro_p003_003 for additional evidence from this paper.
