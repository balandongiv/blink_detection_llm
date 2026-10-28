---
schema_version: '1.0'
claim_id: CL_b_intro_p004_006
paragraph_id: b_intro/p004
paper: ghosh2023automatic
cite: ghosh2023automatic
evidence_ids:
- EV_ghosh2023automatic_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: ghosh2023automatic.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 162.9
    y0: 333.92
    x1: 309.45
    y1: 342.34
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

We propose a robust method that can automatically detect and remove eyeblink and muscular artifacts from EEG using a k-nearest neighbor (kNN) classifier and a long short-term memory (LSTM) network. Our method adopts a sliding window of 0.5 s to detect and remove the artifacts from EEG. Features, such as the variance, peak-to-peak amplitude, and average rectified value, are calculated for each EEG segment to identify corrupted segments using the kNN classifier.

## Normalized evidence

Ghosh et al. propose a hybrid kNN + LSTM pipeline for automatic eyeblink and muscular artifact detection and removal from EEG, using amplitude-based features (peak-to-peak amplitude, variance) within a sliding window.

## Evidence meaning

Supports the "hybrid pipelines" claim: the method uses amplitude-based features (related to thresholding concepts) as initial detection, followed by LSTM-based correction. Demonstrates the range of approaches from simple thresholding to ML-augmented pipelines.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: partial — uses amplitude features (conceptually related to thresholding) in a ML pipeline, but is primarily a classifier-based approach rather than a traditional thresholding method.
