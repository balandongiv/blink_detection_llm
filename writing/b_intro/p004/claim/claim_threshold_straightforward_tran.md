---
schema_version: '1.0'
claim_id: CL_b_intro_p004_001
paragraph_id: b_intro/p004
paper: tran2021detection
cite: tran2021detection
evidence_ids:
- EV_tran2021detection_001
manuscript_text: Thresholding is one of the most straightforward and widely used approaches
  for detecting blink activity from EEG signals ~\citep{tran2021detection,chang2016detection}.
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
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

The paper presents a simple, fast, and automated eye-blink detection algorithm that did not require user training before algorithm execution. The proposed method performed consistently and successfully detected spiking activities of eye blinks with a mean accuracy of over 96%.

## Normalized evidence

Tran et al. present a simple thresholding-based eye-blink detection algorithm for EEG signals that achieves >96% accuracy without user training.

## Evidence meaning

Directly supports the claim that thresholding is a straightforward and widely used approach for EEG blink detection. The paper title is "Detection of EEG-Based Eye-Blinks Using A Thresholding Algorithm", and the abstract emphasizes simplicity, speed, and automation.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: direct — paper title and abstract directly describe thresholding for blink detection.
- The emphasis on "simple, fast, and automated" directly supports "straightforward and widely used".
