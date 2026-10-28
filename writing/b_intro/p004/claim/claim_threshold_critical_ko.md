---
schema_version: '1.0'
claim_id: CL_b_intro_p004_015
paragraph_id: b_intro/p004
paper: ko2020eyeblink
cite: ko2020eyeblink
evidence_ids:
- EV_ko2020eyeblink_001
manuscript_text: Therefore, adaptive and robust threshold selection remains a critical consideration
  for reliable blink detection, particularly in fatigue-driving applications~\citep{ko2020eyeblink,shahbakhti2023fusion}.
evidence_class: abstract
locator:
  source_file: ko2020eyeblink.pdf
  page: 3
  page_index: 2
  section: Untitled
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 269.04
    y0: 241.56
    x1: 300.01
    y1: 249.62
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

In this article, we demonstrate that by combining the features associated with electrocortical activities and eyeblink recognition analysis, it becomes feasible to design an accurate system for the inattention state prediction using just a single EEG sensor. The recorded signals become greatly contaminated with eyeblink and movement artifacts, which makes it a challenge to acquire the data of suitable for analysis quality, particularly in few channel systems where a lack of spatial information limits the applicability of sophisticated signal cleaning algorithms.

## Normalized evidence

Ko et al. demonstrate that combining EEG features with eyeblink recognition enables fatigue/inattention prediction from a single forehead EEG sensor. They highlight the challenge of eyeblink contamination in few-channel systems.

## Evidence meaning

Directly supports the claim that adaptive threshold selection is critical for fatigue-driving applications: the paper demonstrates eyeblink recognition for drowsiness prediction and highlights the challenge of blink artifacts in single-channel EEG.

## Provenance notes

- Evidence from abstract, page 2 of accepted manuscript PDF.
- support_type: direct — demonstrates the importance of eyeblink detection for fatigue/driving applications.
- See also existing claims in p002.
