---
schema_version: '1.0'
claim_id: CL_b_intro_p001_003
paragraph_id: b_intro/p001
paper: tian2021fatigue
cite: tian2021fatigue
evidence_ids:
- EV_tian2021fatigue_001
sentence_id: s03
manuscript_text: Beyond these physiological functions, blink behaviour has been increasingly
  recognised as an important indicator in fatigue-driving research \citep{alyan2023blink,tian2021fatigue}.
evidence_class: full_text
locator:
  source_file: tian2021fatigue.pdf
  page: 1
  page_index: 0
  section: Abstract
  units: PDF points
  coordinate_origin: top_left
  coordinate_method: geometric_resolver
  bbox:
    x0: 185.083
    y0: 245.475
    x1: 467.869
    y1: 340.805
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

To accurately identify fatigued driving, establishing a monitoring system is one of the important guarantees of improving traffic safety and reducing traffic accidents. Among many research methods, electrooculogram signal (EOG) has unique advantages. This paper presents a systematic literature review of these technologies and summarizes a basic framework of fatigue driving monitoring system based on EOGs.

## Normalized evidence

To accurately identify fatigued driving, establishing a monitoring system is one of the important guarantees of improving traffic safety and reducing traffic accidents. Among many research methods, electrooculogram signal (EOG) has unique advantages. This paper presents a systematic literature review of these technologies and summarizes a basic framework of fatigue driving monitoring system based on EOGs.

## Evidence meaning

This review paper establishes that EOG (electrooculogram) signals, which capture eyelid-movement features, are an active research area for fatigue driving monitoring, and that this paper surveys that literature.

## Provenance notes

- The supporting text appears in the Abstract on PDF page 1.
- Extracted directly with PyMuPDF (`coordinate_method: geometric_resolver`), not GROBID. Evidence verified against PDF page 1.
- `support_type: background`: this is a review paper motivating the research area (EOG-based fatigue monitoring), not a direct empirical measurement of "blink behaviour as an indicator." EOG captures eyelid movement generally, of which blinks are one feature among several (saccades, fixations) per this paper's own feature taxonomy. Worth confirming during QC that this framing is close enough to the manuscript's specifically blink-focused claim.
- `support: partial` — the review frames EOG-based fatigue monitoring broadly; EOG captures multiple eye-movement features, of which blinks are one. Close but not a direct match to the manuscript's specifically blink-focused claim.
