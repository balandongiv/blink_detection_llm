---
schema_version: '1.0'
claim_id: CL_b_intro_p003_006
paragraph_id: b_intro/p003
paper: tian2021fatigue
cite: tian2021fatigue
evidence_ids:
- EV_tian2021fatigue_002
manuscript_text: It is important to distinguish between two major perspectives on blink activity
  in the existing literature~\citep{croft2000removal,tian2021fatigue}.
evidence_class: full_text
locator:
  source_file: tian2021fatigue.pdf
  page: 6
  page_index: 5
  section: 3.1 Baseline drift of EOG
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 163.85
    y0: 259.14
    x1: 477.61
    y1: 270.82
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

EOGs are useful for estimating eye gaze but it can add artifacts to EEG [38, 39]. Many researchers tried to remove EOG components from other signals [40, 41].

## Normalized evidence

EOG activity can provide useful eye-gaze information while also appearing as an artifact in EEG that researchers attempt to remove.

## Evidence meaning

This passage contrasts the informational value of ocular activity with its treatment as contamination in EEG. It supports the manuscript's claim about two perspectives, though the distinction concerns EOG activity generally rather than blink activity specifically.

## Provenance notes

- Evidence extracted via Codex CLI from tian2021fatigue.pdf, page 5, section 3.1 Baseline drift of EOG.
- Support rated as partial because the paper discusses the dual nature of EOG signals (useful vs artifact) rather than blink activity specifically.
