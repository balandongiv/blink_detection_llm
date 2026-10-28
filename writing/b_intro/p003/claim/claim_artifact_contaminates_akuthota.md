---
schema_version: '1.0'
claim_id: CL_b_intro_p003_008
paragraph_id: b_intro/p003
paper: akuthota2023artifacts
cite: akuthota2023artifacts
evidence_ids:
- EV_akuthota2023artifacts_002
manuscript_text: In many EEG studies, blink-related activity is treated as an artifact because
  it contaminates neural signals and may interfere with the interpretation of brain activity~\citep{croft2000removal,akuthota2023artifacts}.
evidence_class: full_text
locator:
  source_file: akuthota2023artifacts.pdf
  page: 4
  page_index: 3
  section: 2. LITERATURE REVIEW
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 505.81
    y0: 156.74
    x1: 547.31
    y1: 166.39
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

The above table contain different artifacts removal techniques EOG, ECG, EMG, Physical movement artifacts(motion artifacts) etc but mainly focused on ocular or Eye Blink (EB) artifacts because the EB artifacts are main cause of error or distortion in EEG signal pre-processing.

## Normalized evidence

The table covers removal techniques for EOG, ECG, EMG, and physical-movement artifacts, focusing mainly on ocular or eye-blink artifacts because they are a major cause of error or distortion during EEG preprocessing.

## Evidence meaning

The paper explicitly classifies eye-blink activity as an artifact and states that it causes error or distortion in EEG processing, directly supporting the manuscript claim that blink-related activity is treated as an artifact that contaminates neural signals.

## Provenance notes

- Evidence extracted via Codex CLI from akuthota2023artifacts.pdf, page 189, section 2. Literature Review.
- The paper uses "EB artifacts" (Eye Blink artifacts) as its standard terminology, confirming the artifact classification.
