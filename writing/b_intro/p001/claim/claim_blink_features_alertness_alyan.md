---
schema_version: '1.0'
claim_id: CL_b_intro_p001_005
paragraph_id: b_intro/p001
paper: alyan2023blink
cite: alyan2023blink
evidence_ids:
- EV_alyan2023blink_002
sentence_id: s04
manuscript_text: Variations in blink-related features, such as blink frequency, blink duration,
  eye-closure duration, and blink patterns, can reflect changes in alertness and cognitive
  state \citep{alyan2023blink,ren2019comparison}.
evidence_class: full_text
locator:
  source_file: alyan2023blink.pdf
  page: 1
  page_index: 0
  section: Abstract
  units: PDF points
  coordinate_origin: top_left
  coordinate_method: geometric_resolver
  bbox:
    x0: 267.161
    y0: 388.624
    x1: 554.199
    y1: 399.343
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

The study reveals that EEG measures related to natural eye blink behavior provide insights into the effect of cognitive load on different driving tasks, with implications for driver safety.

## Normalized evidence

The study reveals that EEG measures related to natural eye blink behavior provide insights into the effect of cognitive load on different driving tasks, with implications for driver safety.

## Evidence meaning

The paper's own conclusion: EEG measures time-locked to natural eye blinks provide insight into cognitive load during driving.

## Provenance notes

- The supporting text is the closing sentence of the Abstract, PDF page 1.
- `support_type: indirect`: the manuscript claims specifically that "blink frequency, blink duration, eye-closure duration, and blink patterns" (i.e. simple behavioural blink metrics) reflect alertness/cognitive state. What this paper actually measures is EEG activity *time-locked to* blink events (bERP/bERSP components) — a related but distinct measurement approach. It does support the broader claim that blink-related signals carry cognitive-load information, which is the closest genuine match available in this source.
- `support: partial` — the paper measures EEG components time-locked to blinks (bERP/bERSP), not the simple blink metrics (frequency, duration) the manuscript lists.
