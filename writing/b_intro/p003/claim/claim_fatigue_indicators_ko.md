---
schema_version: '1.0'
claim_id: CL_b_intro_p003_013
paragraph_id: b_intro/p003
paper: ko2020eyeblink
cite: ko2020eyeblink
evidence_ids:
- EV_ko2020eyeblink_001
manuscript_text: From this perspective, blink events are identified, extracted, and analysed
  as potential indicators of driver fatigue~\citep{ko2020eyeblink,shahbakhti2023fusion}.
evidence_class: full_text
locator:
  source_file: ko2020eyeblink.pdf
  page: 4
  page_index: 3
  section: I. INTRODUCTION
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 171.31
    y0: 506.27
    x1: 300.03
    y1: 514.91
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

This study proposes a combined approach for extracting multiple physiological features from a single-channel EEG recording to develop an efficient and straightforward drowsiness-detection system. The vulnerability of the forehead EEG to blink-induced artifacts becomes a vital advantage here because it enables the detection of eyeblink events with subsequent evaluation of their parameters.

## Normalized evidence

This study proposes a combined approach for extracting multiple physiological features from a single-channel EEG recording to develop an efficient and straightforward drowsiness-detection system. The vulnerability of forehead EEG to blink-induced artifacts enables the detection of eyeblink events and subsequent evaluation of their parameters.

## Evidence meaning

The study explicitly detects eyeblink events, evaluates their parameters, and uses extracted physiological features in a driver-drowsiness detection system. This directly supports the manuscript claim about identifying, extracting, and analysing blink events as indicators of driver fatigue.

## Provenance notes

- Evidence extracted via Codex CLI from ko2020eyeblink.pdf, page 2, section I. INTRODUCTION.
- The source reframes blink artifacts as an advantage for drowsiness detection, which aligns with the manuscript's "meaningful information" perspective.
