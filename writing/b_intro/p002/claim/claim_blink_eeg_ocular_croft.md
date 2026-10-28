---
schema_version: '1.0'
claim_id: CL_b_intro_p002_001
paragraph_id: b_intro/p002
paper: croft2000removal
cite: croft2000removal
evidence_ids:
- EV_croft2000removal_001
manuscript_text: blink-related components are often present in EEG signals because eyelid
  movements and eye movements generate strong electrical potentials~\citep{croft2000removal,akuthota2023artifacts}.
evidence_class: full_text
locator:
  source_file: croft2000removal.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 455.99
    y0: 320.75
    x1: 546.83
    y1: 329.77
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

Eye movements cause changes to the electric fields around the eyes, and consequently over the scalp. As a result, EEG recordings are often significantly distorted, and their interpretation problematic. A number of methods have been proposed to overcome this problem, ranging from the rejection of data corresponding temporally to large eye movements, to the removal of the estimated effect of ocular activity from the EEG (EOG correction).

## Normalized evidence

Eye movements cause changes to the electric fields around the eyes, and consequently over the scalp. As a result, EEG recordings are often significantly distorted, and their interpretation problematic. A number of methods have been proposed to overcome this problem, ranging from rejection of temporally corresponding data to removal of estimated ocular activity from the EEG (EOG correction).

## Evidence meaning

Croft & Barry (2000) state that eye movements generate electrical field changes over the scalp that significantly distort EEG recordings. This directly supports the manuscript claim that eyelid and eye movements generate strong electrical potentials that create blink-related components in EEG signals.

## Provenance notes

- The supporting text appears in the Summary (Abstract) on PDF page 1.
- Croft (2000) is a foundational review on ocular artifact removal from EEG.
- The paper uses "eye movements" broadly, which includes blinks (eyelid movements); the manuscript narrows this to "blink-related components" specifically.
- `support_type: background` — the paper reviews artifact removal methods rather than studying blinks per se, but its opening statement directly establishes the physical mechanism (electrical potentials from eye/eyelid movements) that the manuscript cites.
