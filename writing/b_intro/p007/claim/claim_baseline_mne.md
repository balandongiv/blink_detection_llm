---
schema_version: "1.0"
claim_id: CL_b_intro_p007_002
paragraph_id: b_intro/p007
paper: gramfortetal2013a
cite: gramfortetal2013a
evidence_ids:
  - EV_gramfortetal2013a_001
manuscript_text: >-
  Second, we systematically compare the proposed pipeline against baseline
  methods, including BLINKER ~\citep{kleifges2017blinker} and
  MNE~\citep{gramfortetal2013a}.
evidence_class: full_text
locator:
  source_file: gramfortetal2013a.pdf
  page: 1
  page_index: 0
  section: Abstract
  coordinate_method: none
state:
  source_resolution: resolved
  extraction: ok
  location: page_only
  support: strong
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

MNE-Python is an open-source software package that addresses this challenge by providing state-of-the-art algorithms implemented in Python that cover multiple methods of data preprocessing, source localization, statistical analysis, and estimation of functional connectivity between distributed brain regions.

## Normalized evidence

Gramfort et al. describe MNE-Python, an open-source software package for MEG and EEG data analysis providing preprocessing, source localization, and statistical analysis algorithms.

## Evidence meaning

Cited as a baseline method for comparison. MNE-Python is a widely used EEG/MEG analysis package; the manuscript uses it as a benchmark alongside BLINKER. The paper itself is about the MNE-Python software suite, not specifically about blink detection.

## Provenance notes

- Evidence from abstract, page 1.
- support: strong — MNE-Python is a widely used, open-source EEG analysis package, appropriate as a baseline tool.
- MNE-Python provides general EEG/MEG preprocessing including artifact detection capabilities.
