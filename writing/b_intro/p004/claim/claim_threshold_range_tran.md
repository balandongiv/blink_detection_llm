---
schema_version: '1.0'
claim_id: CL_b_intro_p004_019
paragraph_id: b_intro/p004
paper: tran2021detection
cite: tran2021detection
evidence_ids:
- EV_tran2021detection_003
manuscript_text: >-
  Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that
  combine thresholding as an initial detection step with additional
  candidate-refinement mechanisms
  ~\citep{nolan2010faster, chang2016detection,jiang2023eyeblink,
  ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: tran2021detection.pdf
  page: 4
  page_index: 3
  section: C. Eye Blink Detection
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 94.94
    y0: 633.74
    x1: 290.34
    y1: 642.7
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

In addition, the method requires the computation of peak or valley thresholds, distances between the blink peaks and valleys.

## Normalized evidence

The method requires computing peak or valley thresholds and distances between blink peaks and valleys.

## Evidence meaning

The source describes a threshold-based detection method using peak/valley measurements with temporal criteria. This supports the claim about amplitude thresholds with rule-based decision logic but does not establish the full range of approaches or hybrid pipelines.

## Provenance notes

- Evidence matched via GROBID sentence extraction (tei_coordinates=True, segment_sentences=True) and Codex CLI.
- GROBID coordinates: page 4, section C. Eye Blink Detection, bbox verified against TEI XML.
- Support rated as partial because the source describes one specific threshold method, not the full range claimed.
