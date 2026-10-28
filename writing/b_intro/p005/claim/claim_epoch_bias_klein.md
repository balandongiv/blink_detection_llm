---
schema_version: '1.0'
claim_id: CL_b_intro_p005_004
paragraph_id: b_intro/p005
paper: klein2013reliable
cite: klein2013reliable
evidence_ids:
- EV_klein2013reliable_001
manuscript_text: When thresholds are estimated from the entire recording, they may be biased
  by the presence of clean epochs that contain few or no blinks, which may distort threshold
  estimates and suppress blink detection in epochs where blinks are more prevalent~\citep{klein2013reliable,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: klein2013reliable.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 254.95
    y0: 321.15
    x1: 289.12
    y1: 329.91
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

We propose an objective and quantitative method for the automatic detection of eyeblink artefacts from raw data using extreme value statistics, with a p-value acting as a threshold parameter.

## Normalized evidence

Klein and Skrandies propose a statistical method for automatic eyeblink artifact detection using extreme value statistics with a p-value threshold.

## Evidence meaning

Supports the claim about threshold estimation challenges — Klein et al. propose an adaptive statistical threshold (p-value) rather than a fixed amplitude threshold, implicitly acknowledging that fixed thresholds can be unreliable. Their method addresses the problem of threshold estimation from variable data.

## Provenance notes

- Evidence from abstract, page 1.
- support: strong — the paper directly addresses threshold estimation for blink detection using statistical methods, implicitly acknowledging that fixed thresholds estimated from entire recordings can be biased.
