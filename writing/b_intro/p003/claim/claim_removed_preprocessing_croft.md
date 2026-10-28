---
schema_version: '1.0'
claim_id: CL_b_intro_p003_009
paragraph_id: b_intro/p003
paper: croft2000removal
cite: croft2000removal
evidence_ids:
- EV_croft2000removal_003
manuscript_text: In such cases, blink components are commonly removed during EEG preprocessing~\citep{croft2000removal,klein2013reliable}.
evidence_class: full_text
locator:
  source_file: croft2000removal.pdf
  page: 5
  page_index: 4
  section: EOG correction
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 315.75
    y0: 224.0
    x1: 545.68
    y1: 233.02
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

Rejection procedures omit trials with large eye-movements from analysis, and are typically used in conjunction with experimental control. Artifact trials are defined as trials with VEOG greater than a preset criterion and are removed from further analysis.

Instead of removing the EEG data affected by eye-movement from the analysis, correction procedures attempt to remove the effect of the eye-movement from the EEG.

## Normalized evidence

Typically used rejection procedures remove artifact-contaminated trials, while correction procedures remove the effect of eye movements from the EEG.

## Evidence meaning

The paper describes routine rejection and correction approaches for removing ocular effects from EEG data, supporting the manuscript claim that blink components are commonly removed during EEG preprocessing.

## Provenance notes

- Evidence extracted via Codex CLI from croft2000removal.pdf, page 8, sections EOG rejection and EOG correction.
- Support rated as partial because the source discusses ocular artifact removal generally (including all eye movements), not blink-specific component removal during a formally named preprocessing stage.
