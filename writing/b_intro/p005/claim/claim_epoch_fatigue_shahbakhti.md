---
schema_version: '1.0'
claim_id: CL_b_intro_p005_007
paragraph_id: b_intro/p005
paper: shahbakhti2023fusion
cite: shahbakhti2023fusion
evidence_ids:
- EV_shahbakhti2023fusion_001
manuscript_text: As a result, naive application of thresholding in an epoch-structured context
  may risk under-detection of blinks, which undermines the reliability of fatigue assessments
  based on blink metrics~\citep{ko2020eyeblink,shahbakhti2023fusion}.
evidence_class: abstract
locator:
  source_file: shahbakhti2023fusion.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 48.96
    y0: 471.11
    x1: 300.02
    y1: 479.53
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

The moving standard deviation algorithm identifies eye blink intervals (EBIs) to extract blink-related features. [...] The comparison between the obtained results from both databases by the AdaBoost classifier in terms of sensitivity (90.2% vs. 87.4%), specificity (87.7% vs. 85.5%), and accuracy (88.4% vs. 86.8%) indicates the reliability of the proposed method for the fatigue detection.

## Normalized evidence

Shahbakhti et al. fuse EEG spectral features with eye blink interval (EBI) analysis for driver fatigue detection, achieving 88-90% accuracy across two databases.

## Evidence meaning

Directly supports the claim that blink metrics are central to fatigue assessments. The paper demonstrates that blink-related features are a key input to fatigue classification — if blink detection is unreliable (under-detection), the fatigue assessment pipeline is compromised.

## Provenance notes

- Evidence from abstract, page 1.
- support: strong — blink interval extraction is a core component of their fatigue detection pipeline.
