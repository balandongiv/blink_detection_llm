---
schema_version: '1.0'
claim_id: CL_b_intro_p005_006
paragraph_id: b_intro/p005
paper: ko2020eyeblink
cite: ko2020eyeblink
evidence_ids:
- EV_ko2020eyeblink_001
manuscript_text: As a result, naive application of thresholding in an epoch-structured context
  may risk under-detection of blinks, which undermines the reliability of fatigue assessments
  based on blink metrics~\citep{ko2020eyeblink,shahbakhti2023fusion}.
evidence_class: abstract
locator:
  source_file: ko2020eyeblink.pdf
  page: 3
  page_index: 2
  section: Untitled
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 48.96
    y0: 311.3
    x1: 300.01
    y1: 319.36
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

By combining the features associated with electrocortical activities and eyeblink recognition analysis, it becomes feasible to design an accurate system for the inattention state prediction using just a single EEG sensor. [...] The drowsiness prediction from a frontal single-channel setup can achieve a comparable performance with using an array of occipital EEG sensors. As a direct result of utilizing a dry sensor placed in the non-covered with hair head area, the proposed approach in this study is low-cost and user-friendly.

## Normalized evidence

Ko et al. demonstrate that combining EEG spectral features with eyeblink recognition significantly improves fatigue/inattention prediction from single-channel forehead EEG, showing that blink metrics are essential for reliable fatigue assessment.

## Evidence meaning

Directly supports the claim that under-detection of blinks undermines fatigue assessments. The paper shows blink recognition is a key component for accurate fatigue prediction — if blink detection is unreliable, the fatigue assessment built on it is undermined.

## Provenance notes

- Evidence from abstract, pages 1-2.
- support: strong — directly demonstrates the dependency of fatigue assessment on reliable blink detection.
