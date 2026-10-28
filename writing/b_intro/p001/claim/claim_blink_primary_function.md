---
schema_version: "1.0"
claim_id: CL_b_intro_p001_002
paragraph_id: b_intro/p001
paper: nystrm2024what
cite: nystrm2024what
evidence_ids:
  - EV_nystrm2024what_002

sentence_id: s02
manuscript_text: >-
  Its primary functions are to protect the ocular surface, maintain corneal
  moisture, and support visual comfort \citep{nystrm2024what}.

evidence_class: full_text

locator:
  source_file: nystrm2024what.pdf
  page: 2
  page_index: 1
  section: What is a blink and what types of blinks are there?
  units: PDF points
  coordinate_origin: unrecorded
  coordinate_method: hand_authored
  bbox:
    x0: 306.159
    y0: 382.449
    x1: 544.281
    y1: 516.914

state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

Humans are one of the many species that regularly open and close their eyelids. Blount (1927) provides four reasons why blinking is common in human and many non-human species. First, blinking is used to moisten the surface of the eyeball and to remove dirt from the eyes. Second, “to allow alter- ation to take place in the tension of the ocular muscles and thus to eliminate early fatigue” (p.120 Blount 1927). Third, to protect the eyes from injury due to external impact of the eyes, and finally, to protect the eyes against continuous expo- sure to light. In addition, (Cruz et al., 2011) write that blinks contribute to clarity of vision and to maintain the stability of tear film.

## Normalized evidence

Humans are one of the many species that regularly open and close their eyelids. Blount (1927) provides four reasons why blinking is common in human and many non-human species. First, blinking is used to moisten the surface of the eyeball and to remove dirt from the eyes. Second, “to allow alteration to take place in the tension of the ocular muscles and thus to eliminate early fatigue” (p.120 Blount 1927). Third, to protect the eyes from injury due to external impact of the eyes, and finally, to protect the eyes against continuous exposure to light. In addition, (Cruz et al., 2011) write that blinks contribute to clarity of vision and to maintain the stability of tear film.

## Evidence meaning

The source enumerates several biological functions of blinking: moistening and cleaning the ocular surface, reducing ocular-muscle fatigue, protecting the eyes from external injury and prolonged light exposure, supporting visual clarity, and maintaining tear-film stability.

## Provenance notes

- The supporting paragraph appears on PDF page 2 under "What is a blink and what types of blinks are there?".
- The literal field preserves the hyphenated line breaks "alter- ation" and "expo- sure" exactly as extracted. The normalized field joins them.
- The passage attributes the individual functions to Blount (1927) and Cruz et al. (2011); Nyström et al. (2024) summarizes those prior sources. Worth confirming during QC that citing nystrm2024what here is the intent rather than citation laundering (docs/14).
- `support_type: direct` is carried over from the original fixture. The manuscript claim compresses six listed functions into three, which arguably makes it `synthesis`. Left unchanged because relabelling is the researcher's scientific judgment, not the agent's.
- The bbox was typed by a human, not extracted. Regenerate after the coordinate spike.
