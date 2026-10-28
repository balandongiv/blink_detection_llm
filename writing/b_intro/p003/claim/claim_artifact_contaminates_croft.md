---
schema_version: '1.0'
claim_id: CL_b_intro_p003_007
paragraph_id: b_intro/p003
paper: croft2000removal
cite: croft2000removal
evidence_ids:
- EV_croft2000removal_002
manuscript_text: >-
  In many EEG studies, blink-related activity is treated as an artifact because
  it contaminates neural signals and may interfere with the interpretation of
  brain activity~\citep{croft2000removal,akuthota2023artifacts}.
evidence_class: full_text
locator:
  source_file: croft2000removal.pdf
  page: 6
  page_index: 5
  section: General introduction
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

Eye-movements are a major source of contamination of the electroencephalogram (EEG). This is because eye-movements cause a change in the electric fields that surround the eyes, and these distort the electric fields over the scalp. Since the EEG is a record of the electrical activity over the scalp, the EEG is distorted. For example, in figure 1 the effect of a large vertical eye-movement on the EEG can be seen. In measuring the EEG, we are typically interested in the underlying neural potentials (bold line), but our recording is of the combination of neural and eye-movement potentials (thin line).

It is thought that the eyelid acts as a sliding potential source, and that this type of ocular activity (blinking) affects the EEG differently than the eye-movements described above [20]. It has been argued that the source of such blinking artifacts is anterior to the source of other types of eye-movement artifact [5].

## Normalized evidence

Eye movements contaminate and distort EEG recordings by combining ocular potentials with the neural potentials of interest; the paper identifies blinking as ocular activity that affects the EEG and explicitly calls it an artifact.

## Evidence meaning

The source explains that ocular potentials contaminate the neural EEG signal and explicitly classifies blink-related activity as an artifact, directly supporting the manuscript claim about blinks being treated as artifacts that contaminate neural signals and interfere with brain activity interpretation.

## Provenance notes

- Evidence extracted via Codex CLI from croft2000removal.pdf, page 6, sections General introduction and Eyelid movement.
- The passage combines two sections to show both the contamination mechanism and the explicit characterization of blinking as an artifact.
