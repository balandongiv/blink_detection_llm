---
schema_version: '1.0'
claim_id: CL_b_intro_p004_005
paragraph_id: b_intro/p004
paper: jiang2023eyeblink
cite: jiang2023eyeblink
evidence_ids:
- EV_jiang2023eyeblink_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: jiang2023eyeblink.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 105.93
    y0: 216.66
    x1: 309.45
    y1: 225.08
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

We propose a single-channel automatic eyeblink detection algorithm based on joint optimization of variational mode extraction (VME) algorithm and morphological feature extraction (MFE). First, we use the k-means clustering algorithm and discrete Fourier transform (DFT) to automatically extract the center frequency of eyeblink signal. Simultaneously, we use singular spectrum analysis (SSA) to filter the EEG data. Then, eyeblink detection is performed based on VME and adaptive threshold extracted by MFE.

## Normalized evidence

Jiang et al. propose a single-channel eyeblink detection algorithm that combines VME with morphological feature extraction and adaptive thresholding — a hybrid pipeline using thresholding as an initial step with additional refinement.

## Evidence meaning

Directly supports the claim about hybrid pipelines combining thresholding with candidate-refinement mechanisms. The algorithm uses adaptive thresholding (via MFE) as part of a multi-stage detection pipeline.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: direct — demonstrates hybrid pipeline combining thresholding with VME/MFE refinement.
- See also existing claims in p003 for this paper.
