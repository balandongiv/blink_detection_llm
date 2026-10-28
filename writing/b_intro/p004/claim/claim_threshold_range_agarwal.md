---
schema_version: '1.0'
claim_id: CL_b_intro_p004_012
paragraph_id: b_intro/p004
paper: agarwal2019blink
cite: agarwal2019blink
evidence_ids:
- EV_agarwal2019blink_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: agarwal2019blink.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 86.0
    y0: 253.04
    x1: 298.8
    y1: 261.1
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

We propose a fully automated and unsupervised eye-blink detection algorithm, Blink, that self-learns user-specific brainwave profiles for eye-blinks. Hence, Blink does away with any user training or manual inspection requirements. Blink functions on a single channel EEG, and is capable of estimating the start and end timestamps of eye-blinks in a precise manner. The Blink algorithm performs consistently with an accuracy of over 98% for all the tasks with an average precision of 0.934.

## Normalized evidence

Agarwal and Sivakumar propose BLINK, a fully automated unsupervised single-channel eye-blink detection algorithm that self-learns brainwave profiles, eliminating manual threshold/template selection requirements and achieving >98% accuracy.

## Evidence meaning

Directly supports the claim about the range of approaches: BLINK is an automated single-channel detector that addresses limitations of manual thresholding (the paper explicitly lists "partly manual inspection for thresholds or template selection" as a limitation of existing methods).

## Provenance notes

- Evidence from abstract and Introduction, page 1.
- support_type: direct — BLINK exemplifies the evolution from manual thresholding to automated approaches.
- See also existing claims in p002 and p003.
