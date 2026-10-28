---
schema_version: '1.0'
claim_id: CL_b_intro_p005_008
paragraph_id: b_intro/p005
paper: agarwal2019blink
cite: agarwal2019blink
evidence_ids:
- EV_agarwal2019blink_001
manuscript_text: Addressing this challenge requires developing blink detection methods that
  explicitly account for the epoch structure and can adapt threshold estimation to the specific
  characteristics of each epoch or subset of epochs, rather than relying on a global threshold
  derived from the entire recording~\citep{guttmann2019new,agarwal2019blink}.
evidence_class: abstract
locator:
  source_file: agarwal2019blink.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 86.0
    y0: 253.04
    x1: 298.8
    y1: 261.1
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

We propose a fully automated and unsupervised eye-blink detection algorithm, Blink that self-learns user-specific brainwave profiles for eye-blinks. Hence, Blink does away with any user training or manual inspection requirements. Blink functions on a single channel EEG, and is capable of estimating the start and end timestamps of eye-blinks in a precise manner.

## Normalized evidence

Agarwal and Sivakumar propose Blink, a fully automated unsupervised algorithm that self-learns user-specific blink profiles from single-channel EEG without requiring manual threshold setting or training.

## Evidence meaning

Partially supports the claim about developing adaptive blink detection methods. Blink adapts to each user's brainwave profile rather than relying on a global threshold, which aligns with the manuscript's call for methods that adapt to specific characteristics. However, the paper does not explicitly discuss epoch-structured recordings.

## Provenance notes

- Evidence from abstract, page 1.
- support: partial — Blink is adaptive (self-learns user-specific profiles) but does not specifically address epoch structure or per-epoch threshold estimation.
