---
schema_version: '1.0'
claim_id: CL_b_intro_p003_016
paragraph_id: b_intro/p003
paper: jiang2023eyeblink
cite: jiang2023eyeblink
evidence_ids:
- EV_jiang2023eyeblink_001
manuscript_text: Machine learning methods rely on trained models to classify blink events,
  while morphology-based methods identify blinks based on their characteristic waveform shape~\citep{rashida2023quantitative,jiang2023eyeblink}.
evidence_class: full_text
locator:
  source_file: jiang2023eyeblink.pdf
  page: 8
  page_index: 7
  section: A. Performance Evaluation
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 311.97
    y0: 385.53
    x1: 563.04
    y1: 394.17
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: methodological
  human_qc: pending
---

## Exact evidence (literal)

The mutual correlation between the generic template and the candidate eyeblink was calculated to detect the eyeblink waveform. Three morphological parameters, including rising slope, falling slope, and curvature of the eyeblink waveform, are calculated.

## Normalized evidence

Candidate eyeblinks are detected by correlating them with a generic template and calculating three waveform-shape features: rising slope, falling slope, and curvature.

## Evidence meaning

The method detects candidate eyeblinks using template similarity and morphological properties of the waveform (rising slope, falling slope, curvature). The stated slope and curvature features directly characterize waveform shape, supporting the manuscript claim that morphology-based methods identify blinks based on their characteristic waveform shape.

## Provenance notes

- Evidence extracted via Codex CLI from jiang2023eyeblink.pdf, page 21380, section IV. Results.
- The page number (21380) appears to be a column/article number rather than a physical PDF page; the evidence is from the Results section where the morphological feature extraction is described.
- Support_type is methodological because the evidence comes from the paper's method/results description.
