---
schema_version: '1.0'
claim_id: CL_b_intro_p004_013
paragraph_id: b_intro/p004
paper: valderrama2018automatic
cite: valderrama2018automatic
evidence_ids:
- EV_valderrama2018automatic_001
manuscript_text: Existing approaches range from single- or few-channel detectors that apply
  amplitude thresholds with rule-based decision logic to hybrid pipelines that combine thresholding
  as an initial detection step with additional candidate-refinement mechanisms ~\citep{nolan2010faster,
  chang2016detection,jiang2023eyeblink, ghosh2023automatic,tran2021detection,zhang2023method,wang2022multidimensional,wang2025sliding,kleifges2017blinker,cao2021unsupervised,agarwal2019blink,valderrama2018automatic,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: valderrama2018automatic.pdf
  page: 3
  page_index: 2
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 158.68
    y0: 477.65
    x1: 516.74
    y1: 486.39
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

This paper describes and evaluates the Iterative Template Matching and Suppression (ITMS), a new method proposed for detecting and suppressing the artifact associated with the blink activity from a single channel EEG. The approach of ITMS consists of (a) an iterative process in which blink-events are detected and the blink-artifact waveform of the analyzed subject is estimated, (b) generation of a signal modeling the blink-artifact, and (c) suppression of this signal from the raw EEG.

## Normalized evidence

Valderrama et al. propose ITMS, a single-channel iterative template matching method for blink-artifact detection and suppression from EEG. The method iteratively detects blink events, estimates the artifact waveform template, and suppresses it.

## Evidence meaning

Supports the range of approaches claim: ITMS is a single-channel blink detection and suppression method that uses template matching rather than simple thresholding, demonstrating the spectrum from thresholding to more sophisticated approaches.

## Provenance notes

- Evidence from abstract, page 2 of accepted manuscript PDF.
- support_type: partial — uses template matching rather than thresholding, but demonstrates the range of single-channel blink detection approaches cited in the manuscript.
