---
schema_version: "1.0"
claim_id: CL_b_intro_p005_005
paragraph_id: b_intro/p005
paper: guttmann2019new
cite: guttmann2019new
evidence_ids:
  - EV_guttmann2019new_001
manuscript_text: >-
  When thresholds are estimated from the entire recording, they may be biased by
  the presence of clean epochs that contain few or no blinks, which may distort
  threshold estimates and suppress blink detection in epochs where blinks are more
  prevalent~\citep{klein2013reliable,guttmann2019new}.
evidence_class: full_text
locator:
  source_file: guttmann2019new.pdf
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

In general, blink correction algorithms perform a correction uniformly across all blinks. However, due to the fact that blink amplitudes vary from blink to blink (intra-subject variability), and vary between subjects (inter-subject variability), the uniform approach often results in residual blink activity or a distortion in EEG data.

## Normalized evidence

Guttmann et al. identify that uniform blink correction across all blinks fails because blink amplitudes vary both within and between subjects, resulting in residual artifacts or EEG distortion.

## Evidence meaning

Directly supports the claim that thresholds estimated from entire recordings may be biased. The paper explicitly states that uniform (global) approaches produce residual artifacts or distortion due to intra- and inter-subject variability in blink amplitudes, motivating their adaptive algorithm.

## Provenance notes

- Evidence from abstract, page 1.
- support: strong — directly addresses the threshold bias problem described in the manuscript text.
