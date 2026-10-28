---
schema_version: '1.0'
claim_id: CL_b_intro_p001_006
paragraph_id: b_intro/p001
paper: alyan2023blink
cite: alyan2023blink
evidence_ids:
- EV_alyan2023blink_003
sentence_id: s05
manuscript_text: >-
  In the context of driving fatigue, increasing fatigue levels are often
  associated with slower and more prolonged blinks, which may reflect reduced
  vigilance and an elevated risk of impaired driving
  performance~\citep{alyan2023blink}.
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
  support: unsupported
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

The study reveals that EEG measures related to natural eye blink behavior provide insights into the effect of cognitive load on different driving tasks, with implications for driver safety.

## Normalized evidence

The study reveals that EEG measures related to natural eye blink behavior provide insights into the effect of cognitive load on different driving tasks, with implications for driver safety.

## Evidence meaning

The paper's closing Abstract sentence, reused here as the closest available candidate — see provenance notes for why it does not actually support this specific manuscript sentence.

## Provenance notes

- Deliberately marked `support: unsupported`, not left for a human to discover cold: this manuscript sentence claims that fatigue causes "slower or prolonged blinks" indicating "reduced vigilance." A full-text search of this PDF found **zero** occurrences of "prolonged", "slower", "vigilan*", or any discussion of blink-duration changes with fatigue. The paper studies EEG amplitude/latency components time-locked to blinks under varying task load, not blink-duration/speed itself.
- The attached evidence is the closest topically-related passage this source offers (same excerpt as `CL_b_intro_p001_005`), included so the claim has a resolved source and a real, inspectable text rather than nothing — not because it actually supports the sentence. This is exactly the kind of citation the manual-QC workflow (`docs/16`) exists to catch: recommend `needs_better_evidence` or `rejected` during review, not `approved`.
- Per `AGENTS.md` §1.8, no stronger match was fabricated to make this look better-supported than it is.
- Manuscript text updated (2026-10-05) to match current paragraph.tex wording. Semantic claim unchanged; support assessment still holds.
