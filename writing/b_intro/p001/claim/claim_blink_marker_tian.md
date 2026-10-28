---
schema_version: '1.0'
claim_id: CL_b_intro_p001_008
paragraph_id: b_intro/p001
paper: tian2021fatigue
cite: tian2021fatigue
evidence_ids:
- EV_tian2021fatigue_002
sentence_id: s06
manuscript_text: Therefore, blink behaviour provides a useful and non-invasive marker for
  monitoring driver fatigue \citep{shahbakhti2023fusion,tian2021fatigue}.
evidence_class: full_text
locator:
  source_file: tian2021fatigue.pdf
  page: 3
  page_index: 2
  section: 1 Introduction
  units: PDF points
  coordinate_origin: top_left
  coordinate_method: geometric_resolver
  bbox:
    x0: 137.63
    y0: 155.779
    x1: 477.599
    y1: 169.93
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

The limitations of fatigue driving monitoring methods in the current transportation field are discussed and analyzed to simplify the current research on non-invasive fatigue monitoring.

## Normalized evidence

The limitations of fatigue driving monitoring methods in the current transportation field are discussed and analyzed to simplify the current research on non-invasive fatigue monitoring.

## Evidence meaning

The review paper frames its own contribution as advancing non-invasive fatigue-monitoring research, situating EOG/blink-based approaches within that goal.

## Provenance notes

- The supporting text is on PDF page 3, in the numbered list of this review's contributions.
- Contains the manuscript's own phrase "non-invasive" verbatim, which is why this half of the joint citation (`shahbakhti2023fusion,tian2021fatigue`) was chosen to carry the non-invasive framing — see `CL_b_intro_p001_007`'s notes for why shahbakhti2023fusion does not use that word at all.
- `support_type: background`: this states the review's research framing, not an empirical result about blink behaviour specifically being non-invasive.
- `support: partial` — the review's framing ("non-invasive fatigue monitoring") matches the manuscript's phrasing, but this is a research-agenda statement, not empirical evidence about blink behaviour specifically.
