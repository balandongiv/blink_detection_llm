---
schema_version: '1.0'
claim_id: CL_b_intro_p004_017
paragraph_id: b_intro/p004
paper: guttmann2019new
cite: guttmann2019new
evidence_ids:
- EV_guttmann2019new_003
manuscript_text: >-
  Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that
  combine thresholding as an initial detection step with additional
  candidate-refinement mechanisms
  ~\citep{nolan2010faster, chang2016detection,jiang2023eyeblink,
  ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: guttmann2019new.pdf
  page: 3
  page_index: 2
  section: 1. Introduction
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 217.47
    y0: 264.68
    x1: 288.7
    y1: 273.53
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

Using the maximum amplitude on the frontopolar channel (FP1) as a parameter, ABC aims to correct blinks while staying in the temporal domain.

## Normalized evidence

Using the maximum amplitude on the frontopolar channel (FP1) as a parameter, the ABC method aims to correct blinks while remaining in the temporal domain.

## Evidence meaning

The source describes a single-channel blink correction approach using amplitude on FP1 with a temporal-domain method. This partially supports the claim about single-channel detectors applying amplitude thresholds but does not establish the full range of approaches or hybrid candidate-refinement pipelines.

## Provenance notes

- Evidence matched via GROBID sentence extraction (tei_coordinates=True, segment_sentences=True) and Codex CLI.
- GROBID coordinates: page 3, section 1. Introduction, bbox verified against TEI XML.
- Support rated as partial because the source describes one specific approach, not the full range claimed.
