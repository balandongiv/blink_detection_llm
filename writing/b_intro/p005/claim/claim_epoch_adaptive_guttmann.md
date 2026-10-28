---
schema_version: '1.0'
claim_id: CL_b_intro_p005_009
paragraph_id: b_intro/p005
paper: guttmann2019new
cite: guttmann2019new
evidence_ids:
- EV_guttmann2019new_002
manuscript_text: >-
  Addressing this challenge requires developing blink detection methods that
  explicitly account for the epoch structure and can adapt threshold estimation
  to the specific characteristics of each epoch or subset of epochs, rather
  than relying on a global threshold derived from the entire
  recording~\citep{guttmann2019new,agarwal2019blink}.
evidence_class: full_text
locator:
  source_file: guttmann2019new.pdf
  page: 5
  page_index: 4
  section: 3.1. Problem statement
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 102.39
    y0: 193.08
    x1: 288.66
    y1: 201.93
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

Once the blinks have been identified, a preliminary analysis will highlight the huge intra-and inter-subject variability of their characteristic parameter.

## Normalized evidence

Once blinks have been identified, a preliminary analysis highlights the large intra- and inter-subject variability of their characteristic parameters.

## Evidence meaning

The source identifies the need to account for variability in blink characteristics across and within subjects, which motivates adaptive threshold estimation. It does not specifically discuss epoch-aware threshold estimation or contrast it with a recording-wide global threshold.

## Provenance notes

- Evidence matched via GROBID sentence extraction (tei_coordinates=True, segment_sentences=True) and Codex CLI.
- GROBID coordinates: page 5, section 3.1. Problem statement, bbox verified against TEI XML.
- Support rated as partial because the source establishes the variability problem but does not explicitly propose epoch-level adaptation.
