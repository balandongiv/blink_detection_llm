---
schema_version: '1.0'
claim_id: CL_b_intro_p004_010
paragraph_id: b_intro/p004
paper: kleifges2017blinker
cite: kleifges2017blinker
evidence_ids:
- EV_kleifges2017blinker_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: kleifges2017blinker.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 512.11
    y0: 322.09
    x1: 550.37
    y1: 331.49
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

We have implemented an automated pipeline (BLINKER) for extracting ocular indices such as blink rate, blink duration, and blink velocity-amplitude ratios from EEG channels, EOG channels, and/or independent components (ICs). The toolbox, which is easy to use and can be applied to collections of data without user intervention, can automatically discover which channels or ICs capture blinks.

## Normalized evidence

Kleifges et al. describe BLINKER, an automated pipeline for extracting ocular indices (blink rate, duration, velocity-amplitude ratios) from EEG/EOG channels and ICs. The pipeline automates blink detection across channels without user intervention.

## Evidence meaning

BLINKER exemplifies a hybrid pipeline: it uses amplitude-based detection to extract blinks, then computes multiple ocular indices. Directly supports the claim about the range of approaches from amplitude thresholds to hybrid pipelines.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: direct — BLINKER is an automated blink extraction pipeline that uses amplitude-based detection.
- See also existing claims in p003.
