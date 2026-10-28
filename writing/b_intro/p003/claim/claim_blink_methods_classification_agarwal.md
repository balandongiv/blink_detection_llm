---
schema_version: '1.0'
claim_id: CL_b_intro_p003_001
paragraph_id: b_intro/p003
paper: agarwal2019blink
cite: agarwal2019blink
evidence_ids:
- EV_agarwal2019blink_002
manuscript_text: Blink detection methods can generally be classified into machine-learning-based,
  morphology-based, and thresholding-based approaches~\citep{agarwal2019blink,zhang2023method}.
evidence_class: full_text
locator:
  source_file: agarwal2019blink.pdf
  page: 3
  page_index: 2
  section: II. RELATED WORK
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 63.96
    y0: 311.99
    x1: 298.8
    y1: 320.63
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: partial
  support_type: indirect
  human_qc: pending
---

## Exact evidence (literal)

Several related works lie at the intersection of EEG and eye-blinks, which can be broadly classified into two categories: (i) removing eye-blink artifacts from the EEG signal, and (ii) detecting the time instants of eye-blinks in EEG.

## Normalized evidence

Several related works at the intersection of EEG and eye-blinks can be broadly classified into two categories: (i) removing eye-blink artifacts from the EEG signal, and (ii) detecting the time instants of eye-blinks in EEG.

## Evidence meaning

Agarwal & Sivakumar (2019) classify blink-related methods into removal vs. detection categories. The manuscript's three-way classification (ML-based, morphology-based, thresholding-based) is a finer decomposition of detection methods. The paper discusses threshold-based, template-matching, and supervised-learning approaches in its Related Work, but does not explicitly state the three-category taxonomy used in the manuscript. Flag for QC: the manuscript's taxonomy may be a synthesis across multiple sources rather than directly from this paper.

## Provenance notes

- The supporting text appears in Section II (Related Work) on PDF page 2.
- support_type: indirect — the paper classifies approaches differently (removal vs. detection, then sub-methods) rather than using the exact three-category taxonomy.
