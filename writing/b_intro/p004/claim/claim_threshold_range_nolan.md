---
schema_version: '1.0'
claim_id: CL_b_intro_p004_004
paragraph_id: b_intro/p004
paper: nolan2010faster
cite: nolan2010faster
evidence_ids:
- EV_nolan2010faster_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: nolan2010faster.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 290.5
    y0: 319.99
    x1: 553.78
    y1: 326.76
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

We describe FASTER (Fully Automated Statistical Thresholding for EEG artifact Rejection). Parameters were estimated for various aspects of data (e.g., channel variance) in both the EEG time series and in the independent components of the EEG: outliers were detected and removed.

## Normalized evidence

Nolan et al. describe FASTER, a fully automated statistical thresholding system for EEG artifact rejection that detects and removes outliers.

## Evidence meaning

FASTER uses statistical thresholding as part of a pipeline for EEG artifact rejection, supporting the claim that thresholding is used as an initial step in hybrid pipelines. However, FASTER is primarily an artifact rejection tool (including but not limited to blinks), not specifically a blink detector.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: indirect — FASTER uses thresholding for general EEG artifact rejection, not specifically blink detection.
- The paper combines thresholding with ICA, fitting the 'hybrid pipeline' description.
