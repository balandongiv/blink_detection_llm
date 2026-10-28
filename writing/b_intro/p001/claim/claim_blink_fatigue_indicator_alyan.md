---
schema_version: '1.0'
claim_id: CL_b_intro_p001_004
paragraph_id: b_intro/p001
paper: alyan2023blink
cite: alyan2023blink
evidence_ids:
- EV_alyan2023blink_001
sentence_id: s03
manuscript_text: Beyond these physiological functions, blink behaviour has been increasingly
  recognised as an important indicator in fatigue-driving research \citep{alyan2023blink,tian2021fatigue}.
evidence_class: full_text
locator:
  source_file: alyan2023blink.pdf
  page: 1
  page_index: 0
  section: Introduction
  units: PDF points
  coordinate_origin: top_left
  coordinate_method: geometric_resolver
  bbox:
    x0: 167.902
    y0: 620.413
    x1: 321.274
    y1: 632.554
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

In recent studies, eye blinks have emerged as a promising tool for detecting cognitive load in real-life situ- ations involving sustained and uninterrupted task ­performance11–14.

## Normalized evidence

In recent studies, eye blinks have emerged as a promising tool for detecting cognitive load in real-life situ- ations involving sustained and uninterrupted task performance.

## Evidence meaning

The paper frames eye blinks as a tool for detecting cognitive load in real-life, sustained-task settings, of which driving (this paper's own study design) is one example.

## Provenance notes

- The supporting text appears in the Introduction on PDF page 1.
- Preserves two genuine PDF-extraction artifacts, faithfully, per `AGENTS.md` §1.8/`docs/07`: a hyphenated line break ("situ- ations") and a soft-hyphen character glued directly to a reference-number-carrying word ("\xadperformance11–14", where \xad is U+00AD SOFT HYPHEN). The normalized field removes both. Do not repair the literal field.
- `support_type: indirect`, not `direct`: this paper studies **cognitive load** during driving via blink-locked EEG. The word "fatigue" does not occur anywhere in the paper's own body text (checked exhaustively) — it appears only in the titles of other papers in the reference list. The manuscript's framing ("indicator in fatigue-driving research") is close to but not identical to what this source actually studies. Flag for QC: possible citation-fit mismatch (cognitive load ≠ fatigue).
- `support: partial` — the paper studies cognitive load, not fatigue specifically. The word "fatigue" does not appear in the paper's body text.
