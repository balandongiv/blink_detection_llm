---
schema_version: '1.0'
claim_id: CL_b_intro_p002_002
paragraph_id: b_intro/p002
paper: agarwal2019blink
cite: agarwal2019blink
evidence_ids:
- EV_agarwal2019blink_001
manuscript_text: blink information can be extracted from EEG recordings, either by analysing
  the ocular components embedded in the EEG signal ~\citep{agarwal2019blink,shahbakhti2023fusion}.
evidence_class: full_text
locator:
  source_file: agarwal2019blink.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 105.34
    y0: 203.23
    x1: 298.8
    y1: 211.29
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

Eye-blinks are known to substantially contaminate EEG signals, and thereby severely impact the decoding of EEG signals in various medical and scientific applications. In this work, we consider the problem of eye-blink detection that can then be employed to reliably remove eye-blinks from EEG signals. We propose a fully automated and unsupervised eye-blink detection algorithm, Blink that self-learns user-specific brainwave profiles for eye-blinks.

## Normalized evidence

Eye-blinks are known to substantially contaminate EEG signals, and thereby severely impact the decoding of EEG signals in various medical and scientific applications. The authors propose a fully automated and unsupervised eye-blink detection algorithm, Blink, that self-learns user-specific brainwave profiles for eye-blinks.

## Evidence meaning

Agarwal & Sivakumar (2019) describe extracting blink information from EEG by detecting ocular components — their Blink algorithm identifies eye-blink artifacts in EEG signals. This directly supports the manuscript claim that blink information can be extracted from EEG by analysing ocular components.

## Provenance notes

- The supporting text appears in the Abstract on PDF page 1.
- The paper focuses on blink detection (extracting blink timing) from single-channel EEG, which is one form of extracting blink information from EEG recordings.
