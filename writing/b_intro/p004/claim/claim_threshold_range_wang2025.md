---
schema_version: '1.0'
claim_id: CL_b_intro_p004_009
paragraph_id: b_intro/p004
paper: wang2025sliding
cite: wang2025sliding
evidence_ids:
- EV_wang2025sliding_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: wang2025sliding.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 374.34
    y0: 333.61
    x1: 558.21
    y1: 343.82
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

This study presents a sliding window higher-order cumulant (HOC) method for accurate blink artifact detection. The method operates in two steps. First, preliminary detection of blink artifacts is achieved by computing HOCs within the sliding windows of contaminated EEG. Second, the method identifies blink peaks within the detected intervals and further adjusts the detection results using the peaks.

## Normalized evidence

Wang et al. propose a two-step sliding window HOC method for single-channel EEG blink artifact detection: initial detection via higher-order cumulants, followed by peak-based refinement.

## Evidence meaning

Supports the "hybrid pipeline" claim: the method uses a two-step approach with initial detection (analogous to thresholding) followed by peak refinement. Demonstrates single-channel detection for blink artifacts.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: partial — uses statistical (HOC) rather than classical amplitude thresholding, but follows the two-step detection-refinement pattern described in the manuscript.
