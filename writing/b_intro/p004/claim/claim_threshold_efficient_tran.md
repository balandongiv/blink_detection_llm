---
schema_version: '1.0'
claim_id: CL_b_intro_p004_018
paragraph_id: b_intro/p004
paper: tran2021detection
cite: tran2021detection
evidence_ids:
- EV_tran2021detection_002
manuscript_text: >-
  The simplicity of thresholding makes it computationally efficient and easy to
  implement, particularly in real-time fatigue-detection
  systems~\citep{tran2021detection,jefri2022eye}.
evidence_class: full_text
locator:
  source_file: tran2021detection.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 246.29
    y0: 303.21
    x1: 290.51
    y1: 312.17
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

The paper presents a simple, fast, and automated eye-blink detection algorithm that did not require user training before algorithm execution.

## Normalized evidence

The paper presents a simple, fast, and automated eye-blink detection algorithm that does not require user training before execution.

## Evidence meaning

The source characterizes the proposed blink-detection algorithm as simple, fast, and automated. This partially supports the claim about computational efficiency and ease of implementation but does not explicitly address real-time fatigue-detection applicability.

## Provenance notes

- Evidence matched via GROBID sentence extraction (tei_coordinates=True, segment_sentences=True) and Codex CLI.
- GROBID coordinates: page 2, Abstract section, bbox verified against TEI XML.
- Support rated as partial because the source establishes simplicity and speed but not the broader claim about fatigue-detection systems.
