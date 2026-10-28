---
schema_version: '1.0'
claim_id: CL_b_intro_p004_021
paragraph_id: b_intro/p004
paper: chang2016detection
cite: chang2016detection
evidence_ids:
- EV_chang2016detection_002
manuscript_text: >-
  Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that
  combine thresholding as an initial detection step with additional
  candidate-refinement mechanisms
  ~\citep{nolan2010faster, chang2016detection,jiang2023eyeblink,
  ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: chang2016detection.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 491.91
    y0: 332.61
    x1: 548.11
    y1: 339.72
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

In this paper, a novel method to detect eye blink artifacts from a single-channel frontal EEG signal was proposed by combining digital filters with a rule-based decision system, and its performance was validated using an EEG dataset recorded from 24 healthy participants.

## Normalized evidence

A novel method to detect eye blink artifacts from a single-channel frontal EEG signal was proposed, combining digital filters with a rule-based decision system, validated on 24 healthy participants.

## Evidence meaning

The source describes a single-channel blink detector combining filtering with rule-based decision logic. This partially supports the claim about single-channel detectors applying amplitude thresholds with rule-based logic but does not establish the full range of approaches or hybrid pipelines.

## Provenance notes

- Evidence matched via GROBID sentence extraction (tei_coordinates=True, segment_sentences=True) and Codex CLI.
- GROBID coordinates: page 2, Abstract section, bbox verified against TEI XML.
- Support rated as partial because the source describes one specific approach, not the full range claimed.
