---
schema_version: '1.0'
claim_id: CL_b_intro_p001_001
paragraph_id: b_intro/p001
paper: nystrm2024what
cite: nystrm2024what
evidence_ids:
- EV_nystrm2024what_001
sentence_id: s01
manuscript_text: Blinking is a physiological process that involves the closure and reopening
  of the eyelids \citep{nystrm2024what}.
evidence_class: full_text
locator:
  source_file: nystrm2024what.pdf
  page: 1
  page_index: 0
  section: Introduction
  units: PDF points
  coordinate_origin: unrecorded
  coordinate_method: hand_authored
  bbox:
    x0: 306.159
    y0: 463.413
    x1: 544.253
    y1: 510.725
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

Blinks involve the closing and re-opening of the eyelids and have been the subject of investigations in a large variety ofﬁelds due to their relation with human behavior, function, and cognition (e.g., Stern et al., 1984; Eckstein et al., 2017).

## Normalized evidence

Blinks involve the closing and re-opening of the eyelids and have been the subject of investigations in a large variety of fields due to their relation with human behavior, function, and cognition (e.g., Stern et al., 1984; Eckstein et al., 2017).

## Evidence meaning

The source directly defines a blink in terms of eyelid closing and re-opening, and states that blinks are studied across many fields because of their relationships with human behavior, function, and cognition.

## Provenance notes

- The supporting sentence appears in the Introduction on PDF page 1.
- The literal field preserves the typographic ligature U+FB01 in "ofﬁelds", where extraction also lost the space after "of". The normalized field restores both.
- The bbox was typed by a human, not extracted, hence `coordinate_method: hand_authored` and `coordinate_origin: unrecorded`. It must be regenerated once the GROBID coordinate spike establishes the origin convention. Do not treat these numbers as ground truth for a coordinate test.
- Evidence verified against PDF page 1 of nystrm2024what.pdf. The literal text matches the source.
