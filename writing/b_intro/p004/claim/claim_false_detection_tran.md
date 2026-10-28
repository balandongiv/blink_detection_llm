---
schema_version: '1.0'
claim_id: CL_b_intro_p004_020
paragraph_id: b_intro/p004
paper: tran2021detection
cite: tran2021detection
evidence_ids:
- EV_tran2021detection_004
manuscript_text: >-
  A threshold that is too low may produce false detections due to noise or other
  artifacts, whereas a threshold that is too high may miss genuine blink
  events~\citep{tran2021detection,jefri2022eye}.
evidence_class: full_text
locator:
  source_file: tran2021detection.pdf
  page: 4
  page_index: 3
  section: C. Eye Blink Detection
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 131.56
    y0: 657.98
    x1: 290.18
    y1: 666.94
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

These thresholds are usually a fixed constant per dataset or individual data.

## Normalized evidence

Thresholds are usually a fixed constant per dataset or individual data.

## Evidence meaning

The source confirms that detection depends on dataset- or individual-specific threshold values, implying sensitivity to threshold choice. However, it does not explicitly state the false-positive and false-negative consequences of setting thresholds too low or too high.

## Provenance notes

- Evidence matched via GROBID sentence extraction (tei_coordinates=True, segment_sentences=True) and Codex CLI.
- GROBID coordinates: page 4, section C. Eye Blink Detection, bbox verified against TEI XML.
- Support rated as partial because the source mentions fixed thresholds but does not directly describe the specific failure modes (false positives from low threshold, missed events from high threshold) the manuscript claims.
