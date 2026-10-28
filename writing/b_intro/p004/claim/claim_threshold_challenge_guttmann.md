---
schema_version: '1.0'
claim_id: CL_b_intro_p004_014
paragraph_id: b_intro/p004
paper: guttmann2019new
cite: guttmann2019new
evidence_ids:
- EV_guttmann2019new_001
manuscript_text: Despite these developments, selecting an appropriate threshold remains challenging
  because blink amplitude varies across participants, electrode locations, recording devices,
  signal quality, and experimental conditions ~\citep{guttmann2019new,wang2022multidimensional}.
evidence_class: full_text
locator:
  source_file: guttmann2019new.pdf
  page: 2
  page_index: 1
  section: Abstract
  coordinate_method: grobid_coords
  coordinate_origin: top_left
  units: PDF points
  bbox:
    x0: 316.86
    y0: 358.93
    x1: 557.64
    y1: 366.89
state:
  source_resolution: resolved
  extraction: ok
  location: page_and_bbox
  support: strong
  support_type: direct
  human_qc: pending
---

## Exact evidence (literal)

The main goal of this paper is to present a new algorithm for blink correction (ABC) that is adaptive to inter- and intra-subject variability. Comparison between ABC and the commonly-used Independent Component Analysis (ICA) for blinks removal shows a net amelioration with ABC. With the same pipeline using uncorrected data as a reference, ABC improves classification by 5.38% in average, whereas ICA deteriorates by −2.67%.

## Normalized evidence

Guttmann-Flury et al. present a blink correction algorithm (ABC) that is explicitly adaptive to inter- and intra-subject variability, outperforming ICA for blink removal.

## Evidence meaning

Directly supports the claim that blink amplitude varies across participants (inter-subject) and within participants (intra-subject), and that threshold selection must be adaptive to account for this variability.

## Provenance notes

- Evidence from abstract, page 1.
- support_type: direct — the paper's central contribution is addressing inter- and intra-subject variability in blink correction, directly supporting the amplitude variability claim.
