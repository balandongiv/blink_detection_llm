---
schema_version: '1.0'
claim_id: CL_b_intro_p002_006
paragraph_id: b_intro/p002
paper: akuthota2023artifacts
cite: akuthota2023artifacts
evidence_ids:
- EV_akuthota2023artifacts_001
manuscript_text: blink-related components are often present in EEG signals because eyelid
  movements and eye movements generate strong electrical potentials~\citep{croft2000removal,akuthota2023artifacts}.
evidence_class: full_text
locator:
  source_file: akuthota2023artifacts.pdf
  page: 3
  page_index: 2
  section: 'ABSTRACT:'
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 486.68
    y0: 361.34
    x1: 547.26
    y1: 370.99
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

Artifacts in the EEG signal can be eliminated by filtering out the electrical activity produced by head and eye muscle contractions.

## Normalized evidence

Artifacts in EEG signals can be removed by filtering electrical activity produced by head and eye-muscle contractions.

## Evidence meaning

The source identifies electrical activity from eye-related muscle contractions as a source of EEG artifacts. This supports the manuscript claim that eye movements generate electrical potentials present in EEG, though it does not explicitly characterize these potentials as "strong" or specifically discuss eyelid movements.

## Provenance notes

- Evidence extracted via Codex CLI from akuthota2023artifacts.pdf, page 188, section 1.2. Signal Capturing Block.
- Support rated as partial because the source mentions eye muscle contractions generating electrical activity (artifacts) in EEG but does not explicitly describe the potentials as "strong" or distinguish eyelid movements.
