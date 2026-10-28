---
schema_version: '1.0'
claim_id: CL_b_intro_p005_002
paragraph_id: b_intro/p005
paper: tran2021detection
cite: tran2021detection
evidence_ids:
- EV_tran2021detection_001
manuscript_text: This epoch-structured setting introduces additional challenges for threshold-based
  blink detection~\citep{tran2021detection,jefri2022eye}.
evidence_class: full_text
locator:
  source_file: tran2021detection.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 246.29
    y0: 303.21
    x1: 290.51
    y1: 312.17
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

This paper presents a simple, fast and automated eye-blink detection algorithm using a simple thresholding algorithm which did not require user training before algorithm execution.

## Normalized evidence

Tran et al. present a threshold-based eye-blink detection algorithm that is simple and automated but does not account for epoch structure.

## Evidence meaning

Partially supports the claim about challenges of threshold-based detection in epoch-structured settings. The paper demonstrates a straightforward thresholding approach applied to continuous EEG, implicitly illustrating that such methods do not account for epoch-level variability.

## Provenance notes

- Evidence from abstract, page 1.
- support: partial — paper demonstrates threshold-based blink detection but does not explicitly discuss epoch-structured challenges.
