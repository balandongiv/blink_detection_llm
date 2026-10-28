---
schema_version: "1.0"
claim_id: CL_b_intro_p004_008
paragraph_id: b_intro/p004
paper: wang2022multidimensional
cite: wang2022multidimensional
evidence_ids:
  - EV_wang2022multidimensional_001
manuscript_text: >-
  Despite these developments, selecting an appropriate threshold remains
  challenging because blink amplitude varies across participants, electrode
  locations, recording devices, signal quality, and experimental conditions
  ~\citep{guttmann2019new,wang2022multidimensional}.
evidence_class: full_text
locator:
  source_file: wang2022multidimensional.pdf
  page: 1
  page_index: 0
  section: Abstract
  coordinate_method: none
state:
  source_resolution: resolved
  extraction: ok
  location: page_only
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

Eye blink artifact detection in scalp electroencephalogram (EEG) of epilepsy patients is challenging due to its similar waveforms to epileptiform discharges.

## Normalized evidence

Wang et al. note that eye blink detection in EEG is challenging due to waveform similarity with epileptiform discharges.

## Evidence meaning

Indirectly supports the claim that blink amplitude varies and threshold selection is challenging. The paper focuses on epileptiform discharge interference rather than cross-participant variability, but the core challenge of amplitude-based detection difficulty is shared.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: indirect — paper's focus is epileptiform discharge interference, not general cross-participant amplitude variability.
- The paper proposes multi-dimensional feature optimization to address detection challenges.
