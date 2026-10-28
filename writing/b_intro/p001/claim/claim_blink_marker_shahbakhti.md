---
schema_version: '1.0'
claim_id: CL_b_intro_p001_007
paragraph_id: b_intro/p001
paper: shahbakhti2023fusion
cite: shahbakhti2023fusion
evidence_ids:
- EV_shahbakhti2023fusion_001
sentence_id: s06
manuscript_text: Therefore, blink behaviour provides a useful and non-invasive marker for
  monitoring driver fatigue \citep{shahbakhti2023fusion,tian2021fatigue}.
evidence_class: full_text
locator:
  source_file: shahbakhti2023fusion.pdf
  page: 4
  page_index: 3
  section: II. Methods
  units: PDF points
  coordinate_origin: top_left
  coordinate_method: geometric_resolver
  bbox:
    x0: 153.576
    y0: 252.657
    x1: 409.019
    y1: 751.767
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

given the fact that the concentration level decreases in the fatigue state, blink-related measures can be of discriminative power in the classification between alertness and fatigue states. In particular, it was demonstrated that while the eye blink rate increases in the fatigue state, its amplitude decreases [23].

## Normalized evidence

given the fact that the concentration level decreases in the fatigue state, blink-related measures can be of discriminative power in the classification between alertness and fatigue states. In particular, it was demonstrated that while the eye blink rate increases in the fatigue state, its amplitude decreases.

## Evidence meaning

Edited meaning: blink rate/amplitude discriminate fatigue from alert states.

## Provenance notes

- The supporting sentence is on PDF page 4, but PyMuPDF's raw reading order interleaves a figure caption ("Fig. 3. An example for extraction of the blink-related features...") in the middle of it, because the figure sits between the two halves of the sentence in the page layout. That caption was excised when building this excerpt so the sentence reads correctly; a layout-aware pipeline (e.g. GROBID) would not have interleaved it in the first place. Flagged here rather than silently smoothed over.
- The excerpt starts mid-sentence at "given the fact..."; the full sentence begins "Consequently, given the fact...".
- `support_type: direct`: unlike the alyan2023blink claims in this paragraph, this is a genuinely close match — the source explicitly states blink rate and amplitude change with fatigue state, directly supporting "blink behaviour provides a useful ... marker for monitoring driver fatigue." It does not, however, use the word "non-invasive" anywhere in the paper (checked exhaustively) — the method still requires a scalp EEG electrode, which is arguably not "non-invasive" in the plain-language sense. See `CL_b_intro_p001_008` for the half of this joint citation that actually supports the non-invasive framing.
- `support: strong` — the source explicitly states blink rate and amplitude discriminate fatigue from alert states, directly supporting the manuscript's "useful marker for monitoring driver fatigue" claim.
