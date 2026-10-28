---
schema_version: '1.0'
claim_id: CL_b_intro_p004_007
paragraph_id: b_intro/p004
paper: zhang2023method
cite: zhang2023method
evidence_ids:
- EV_zhang2023method_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: zhang2023method.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 73.55
    y0: 248.74
    x1: 309.66
    y1: 257.03
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

We propose a short windowed and random forest based method toward the Real-Time Blink detection (RT-Blink), which balances the processing granularity and computation complexity. RT-Blink uses a potential blink (PB) boundary detecting algorithm and a pretrained random forest (RF) model with a set of features, including sample entropy (SampEn), standard deviation (SD), range of amplitude (RA), and rate of grade (RG), which enables fully automated identification of the duration of blinks from a single-channel EEG signal.

## Normalized evidence

Zhang et al. propose RT-Blink, a single-channel real-time blink detection method combining a boundary detection algorithm (initial thresholding step) with a random forest classifier (refinement mechanism).

## Evidence meaning

Directly supports the "hybrid pipeline" claim: RT-Blink uses boundary detection (thresholding-like initial step) followed by random forest classification (candidate refinement), exactly matching the described pattern.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: direct — exemplifies hybrid pipeline combining initial detection with ML refinement.
- See also existing claims in p003.
