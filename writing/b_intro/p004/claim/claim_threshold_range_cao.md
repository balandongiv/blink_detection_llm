---
schema_version: "1.0"
claim_id: CL_b_intro_p004_011
paragraph_id: b_intro/p004
paper: cao2021unsupervised
cite: cao2021unsupervised
evidence_ids:
  - EV_cao2021unsupervised_001
manuscript_text: >-
  Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that
  combine thresholding as an initial detection step with additional
  candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink,
  ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: cao2021unsupervised.pdf
  page: 1
  page_index: 0
  section: Abstract
  coordinate_method: none
state:
  source_resolution: resolved
  extraction: ok
  location: page_only
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

To achieve an accurate and efficient eye blink detection, a novel unsupervised learning algorithm based on a hybrid thresholding followed by a Gaussian mixture model (GMM) is presented in this paper. The EEG signal is priliminarily screened by a cascaded thresholding method.

## Normalized evidence

Cao et al. propose an unsupervised blink detection algorithm combining cascaded thresholding with a Gaussian mixture model.

## Evidence meaning

Directly supports the 'hybrid pipeline' claim — Cao et al. explicitly use thresholding as an initial screening step followed by GMM-based classification, which is exactly the pattern described in the manuscript.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: direct — the paper explicitly uses "cascaded thresholding" as the initial screening step followed by GMM-based classification, exactly matching the manuscript's "hybrid pipeline" description.
