---
schema_version: '1.0'
claim_id: CL_b_intro_p007_001
paragraph_id: b_intro/p007
paper: kleifges2017blinker
cite: kleifges2017blinker
evidence_ids:
- EV_kleifges2017blinker_001
manuscript_text: Second, we systematically compare the proposed pipeline against baseline
  methods, including BLINKER ~\citep{kleifges2017blinker} and MNE~\citep{gramfortetal2013a}.
evidence_class: full_text
locator:
  source_file: kleifges2017blinker.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 512.11
    y0: 322.09
    x1: 550.37
    y1: 331.49
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: background
  human_qc: pending
---

## Exact evidence (literal)

We have implemented an automated pipeline (BLINKER) for extracting ocular indices such as blink rate, blink duration, and blink velocity-amplitude ratios from EEG channels, EOG channels, and/or independent components (ICs). [...] The toolbox, which is easy to use and can be applied to collections of data without user intervention, can automatically discover which channels or ICs capture blinks.

## Normalized evidence

Kleifges et al. describe BLINKER, an automated MATLAB pipeline for extracting ocular indices (blink rate, duration, velocity-amplitude ratios) from EEG/EOG channels or independent components.

## Evidence meaning

Directly supports the use of BLINKER as a baseline method for comparison. The paper establishes BLINKER as a well-documented, publicly available automated blink extraction tool, making it a natural benchmark for evaluating new blink detection pipelines.

## Provenance notes

- Evidence from abstract, page 1.
- support: strong — BLINKER is an established, publicly available automated pipeline, appropriate as a baseline.
- Toolbox available at https://github.com/VisLab/EEG-Blinks.
