---
schema_version: '1.0'
claim_id: CL_b_intro_p003_010
paragraph_id: b_intro/p003
paper: klein2013reliable
cite: klein2013reliable
evidence_ids:
- EV_klein2013reliable_001
manuscript_text: In such cases, blink components are commonly removed during EEG preprocessing~\citep{croft2000removal,klein2013reliable}.
evidence_class: full_text
locator:
  source_file: klein2013reliable.pdf
  page: 2
  page_index: 1
  section: Introduction
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 51.02
    y0: 545.31
    x1: 289.12
    y1: 554.07
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

Blinks as well as other eye movements have been known for decades as sources of serious perturbations in EEG-measurements (Hillyard and Galambos 1970; Berg 1986; Kenemans et al. 1991), and just as long, researchers have attempted to develop methods that detect and correct or reject such artefacts automatically (Girton and Kamiya 1973; Gasser et al. 1986; Anderer et al. 1999; Croft and Barry 2000; Schlögl et al. 2007).

## Normalized evidence

Blinks and other eye movements have long been recognized as serious EEG perturbations, and researchers have correspondingly developed methods to detect, correct, or reject these artifacts automatically.

## Evidence meaning

The source establishes that blink-related artifacts are routinely detected and corrected or rejected in EEG processing, supporting the manuscript claim about common removal of blink components during preprocessing.

## Provenance notes

- Evidence extracted via Codex CLI from klein2013reliable.pdf, page 558, section Introduction.
- Support rated as partial because the source discusses automatic detection and correction/rejection of blink artifacts generally, rather than specifying that independent components are removed during a named preprocessing stage.
