---
schema_version: "1.0"
claim_id: CL_b_intro_p004_016
paragraph_id: b_intro/p004
paper: shahbakhti2023fusion
cite: shahbakhti2023fusion
evidence_ids:
  - EV_shahbakhti2023fusion_001
manuscript_text: >-
  Therefore, adaptive and robust threshold selection remains a critical
  consideration for reliable blink detection, particularly in fatigue-driving
  applications~\citep{ko2020eyeblink,shahbakhti2023fusion}.
evidence_class: abstract
locator:
  source_file: shahbakhti2023fusion.pdf
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

We present a new driver fatigue detection method based on simultaneous EEG and eye blinks analysis using an Fp1 EEG channel. First, the moving standard deviation algorithm identifies eye blink intervals (EBIs) to extract blink-related features. The employment of a single prefrontal EEG channel should be prioritized as it provides users with more comfort. Considering the existence of commercial single prefrontal channel EEG headbands, the proposed method can be used to detect the driver fatigue in real-world scenarios.

## Normalized evidence

Shahbakhti et al. present a single-channel EEG method for driver fatigue detection that fuses EEG features with eye blink analysis, using a standard deviation-based algorithm to identify blink intervals for fatigue classification.

## Evidence meaning

Directly supports the claim that robust blink detection is critical for fatigue-driving applications. The paper demonstrates a real-world-applicable single-channel method for fatigue detection via blink analysis.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: direct — demonstrates blink detection for fatigue-driving applications using single prefrontal EEG.
- See also existing claims in p001.
