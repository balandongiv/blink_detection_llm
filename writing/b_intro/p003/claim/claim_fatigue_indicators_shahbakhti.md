---
schema_version: '1.0'
claim_id: CL_b_intro_p003_014
paragraph_id: b_intro/p003
paper: shahbakhti2023fusion
cite: shahbakhti2023fusion
evidence_ids:
- EV_shahbakhti2023fusion_004
manuscript_text: From this perspective, blink events are identified, extracted, and analysed
  as potential indicators of driver fatigue~\citep{ko2020eyeblink,shahbakhti2023fusion}.
evidence_class: full_text
locator:
  source_file: shahbakhti2023fusion.pdf
  page: 4
  page_index: 3
  section: C. The Proposed Method
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 84.21
    y0: 671.14
    x1: 300.02
    y1: 679.78
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: methodological
  human_qc: pending
---

## Exact evidence (literal)

Secondly, EBIs are identified using the MSD algorithm and three blink-related measures are dervied. Thirdly, the identified EBIs are filtered from the EEG signal based on the DWT algorithm, and then linear and nonlinear features are extracted from the filtered EEG sub-bands. Finally, a subset of prominent features are selected and fed to different classifiers to discriminate between the fatigue from alert driving states.

## Normalized evidence

Secondly, eye-blink intervals (EBIs) are identified using the MSD algorithm and three blink-related measures are derived. Thirdly, the identified EBIs are filtered from the EEG signal using the DWT algorithm, after which linear and nonlinear features are extracted from the filtered EEG sub-bands. Finally, prominent features are selected and supplied to classifiers to discriminate between fatigue and alert driving states.

## Evidence meaning

The method identifies eye-blink intervals, derives blink measures, extracts further features, and uses selected features to distinguish fatigued from alert driving states. This directly supports the manuscript claim about blink events being identified, extracted, and analysed as potential indicators of driver fatigue.

## Provenance notes

- Evidence extracted via Codex CLI from shahbakhti2023fusion.pdf, page 3, section II.C. The Proposed Method.
- Support_type is methodological because the evidence comes from the paper's method description showing how blink events are processed for fatigue classification.
- Note: the original PDF contains the typo "dervied" for "derived" in the literal evidence.
