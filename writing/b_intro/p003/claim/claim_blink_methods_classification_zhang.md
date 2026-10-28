---
schema_version: '1.0'
claim_id: CL_b_intro_p003_002
paragraph_id: b_intro/p003
paper: zhang2023method
cite: zhang2023method
evidence_ids:
- EV_zhang2023method_001
manuscript_text: Blink detection methods can generally be classified into machine-learning-based,
  morphology-based, and thresholding-based approaches~\citep{agarwal2019blink,zhang2023method}.
evidence_class: full_text
locator:
  source_file: zhang2023method.pdf
  page: 2
  page_index: 1
  section: Untitled
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 484.2
    y0: 658.87
    x1: 563.09
    y1: 667.63
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

These recorded EEG signals are often affected by electrooculography (EOG) signals. Specifically, eye blinks are the common biological phenomenon, which is hard to avoid. The average blink duration is between 100 and 400 ms and the amplitude can be up to 800 μV [15]. Blink artifacts can change the characteristics of neurological phenomena such as on Alzheimer's disease and schizophrenia [2], [3]. Hence, the detection and removal of blink components can be significantly useful in the EEG analysis.

## Normalized evidence

EEG signals are often affected by EOG signals; eye blinks are common biological phenomena that are hard to avoid. Blink artifacts can change characteristics of neurological phenomena. The detection and removal of blink components can be significantly useful in EEG analysis.

## Evidence meaning

Zhang et al. (2023) discuss blink detection in EEG and present RT-Blink, a thresholding + random-forest method. The paper does not explicitly provide the three-way classification (ML-based, morphology-based, thresholding-based) in these terms, but its Related Work section covers threshold-based, template-matching, and supervised-learning approaches as distinct categories.

## Provenance notes

- The supporting text appears in the Introduction on PDF page 1.
- support_type: indirect — the paper demonstrates a threshold+ML hybrid approach but does not explicitly label the three-way taxonomy used in the manuscript.
