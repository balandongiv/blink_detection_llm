---
schema_version: '1.0'
claim_id: CL_b_intro_p003_015
paragraph_id: b_intro/p003
paper: rashida2023quantitative
cite: rashida2023quantitative
evidence_ids:
- EV_rashida2023quantitative_001
manuscript_text: Machine learning methods rely on trained models to classify blink events,
  while morphology-based methods identify blinks based on their characteristic waveform shape~\citep{rashida2023quantitative,jiang2023eyeblink}.
evidence_class: full_text
locator:
  source_file: rashida2023quantitative.pdf
  page: 3
  page_index: 2
  section: 1. Introduction
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 163.29
    y0: 542.84
    x1: 288.57
    y1: 550.5
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

In ML-based eye-blink detection techniques, relevant EEG features are selected and extracted from EEG recordings to train the ML models. Thus, the ML algorithms can decide whether an EEG segment is blink-contaminated or not.

## Normalized evidence

In ML-based eye-blink detection techniques, relevant EEG features are selected and extracted from EEG recordings to train the ML models. Thus, the ML algorithms can decide whether an EEG segment is blink-contaminated or not.

## Evidence meaning

The source directly describes ML-based eye-blink detection where features are extracted to train models that classify EEG segments as blink-contaminated or not, supporting the manuscript claim that machine learning methods rely on trained models to classify blink events.

## Provenance notes

- Evidence extracted via Codex CLI from rashida2023quantitative.pdf, page 2, section 1. Introduction.
- The source frames blink detection as classification of EEG segments, which aligns with the manuscript's description of trained models classifying blink events.
