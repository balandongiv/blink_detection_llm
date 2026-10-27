# Multi-Agent Handoff: Compress the Blink-Detection Paper to 8 Pages

## Mission

Compress the supplied journal paper to **8 pages total**, including references, while giving the contribution a clear, high-tempo narrative. The manuscript should make the novelty easy to understand without overstating what the experiments establish.

The **Orchestra Agent** owns the task. The user will refer all source files to that agent. It must inventory and read every supplied file before delegating or making claims. Treat the original manuscript and any supplied supplements as evidence; this brief is the workflow and scope guide.

## Required outcome

Deliver an 8-page manuscript draft and a short change summary. Preserve the scientific meaning, methods, results, citations, figure/table attribution, and limitations. Do not silently alter data or invent analyses.

The central narrative should be:

> In epoch-structured driving EEG, calibrating a threshold from the whole recording can mix blink-rich and blink-poor segments. The proposed pipeline screens candidate epochs, estimates robust channel-specific thresholds from those epochs, and applies the thresholds across the recording. The complete configuration outperformed the selected threshold baselines on two simulated-driving corpora; a matched ablation is still needed to attribute that gain specifically to candidate-epoch screening.

## Agent roles

### 1. Orchestra Agent — accountable lead

- Inventory all files the user supplies; identify the current manuscript, supplements, figure files, and any journal formatting requirements.
- Read the manuscript and this handoff brief. Keep a source map with file names, versions, and what each supports.
- Assign bounded tasks to the agents below, resolve disagreements, and maintain one decision log.
- Own the final outline, page budget, integration, and author-facing change summary.
- Ensure the Writer Agent edits one working copy and that all agents review the same version.
- Do not delegate final scientific judgment or final acceptance of the 8-page limit.

### 2. Audit Agent — scientific accuracy and claim audit

Independently check the manuscript’s claims against its methods, results, tables, figures, and supplied source files. Return a concise audit with:

- Claims that are supported, unsupported, or need qualification.
- Numerical values and comparison conditions that must remain exact.
- Important methodological caveats, including evaluation protocol and baseline scope.
- Any internal inconsistencies or missing information that could make compression misleading.

Do not rewrite the paper. Flag uncertainty rather than filling gaps.

### 3. Proposal Agent — narrative, novelty, and Fig. 7

Propose the strongest defensible story and a compression strategy. Return:

- A one-sentence main contribution and a short introduction logic.
- One or two sentences for the main message of each experiment.
- A recommendation for Fig. 7: its role in the story, what to emphasize, and whether to retain, simplify, or move details to supplementary material.
- Accurate, concise terminology for the method.

Keep recommendations tied to evidence in the supplied files.

### 4. Writer Agent — 8-page manuscript

Prepare the compressed draft from the Orchestra Agent’s approved outline and the Audit Agent’s constraints.

- Target **8 pages including references**, subject to the supplied journal template.
- Preserve the important methods needed to reproduce the study, the central results, and limitations.
- Use 1–2 sentences to state the message of each experiment before giving only the necessary supporting details.
- Remove repetition, long electrode-by-electrode descriptions, and procedural detail that does not change interpretation; move detail to a supplement only if the venue permits it.
- Retain citations for claims and methods. Do not invent citations or results.
- Make no unapproved changes to analysis, data, or authorship.

### 5. QC Agent — independent final review

Review the Writer Agent’s integrated draft without editing it first. Return a defect list, then verify fixes in the final version.

Check:

- Exact page count under the required template, including references.
- Figures, tables, captions, citations, equations, and cross-references render and point to the right content.
- Numerical results and statistical statements match the source.
- Methods are internally consistent, especially the order of preprocessing and epoching.
- The abstract, introduction, results, and conclusion tell the same story.
- Claims remain within the evidence; limitations and evaluation qualifications remain visible.
- No duplicated, orphaned, unreadable, or clipped content.

### 6. Evidence and Figure Curator — recommended additional agent

Create a compact evidence map linking each proposed central claim to the exact source section, table, figure, or supplement. Inspect Fig. 7 and other candidate figures for legibility at the target page size. Recommend the smallest set of figures/tables that carries the story, and identify detail that can be removed or moved to supplementary material. Do not change figure data or redraw a figure in a way that changes its meaning.

## Claude model and thinking budget

Do not assign the most expensive Claude model or extended/high thinking to every role. Use the closest available Claude model tier in the user’s account; model names and availability may change.

| Role | Default model tier | Thinking setting | Escalate when |
|---|---|---|---|
| Orchestra Agent | Sonnet-class | Medium | Use Opus-class/high thinking only to resolve a material scientific disagreement or make the final high-stakes claim-scope decision. |
| Audit Agent | Sonnet-class | High for the first scientific audit | Use Opus-class/high thinking only if the paper contains a consequential ambiguity that cannot be resolved from the supplied sources. |
| Proposal Agent | Haiku- or Sonnet-class | Low to medium | Escalate only if the novelty story conflicts with the audit or source evidence. |
| Writer Agent | Sonnet-class | Medium | Use high thinking for dense technical passages or if compression risks changing scientific meaning; do not use Opus by default. |
| QC Agent | Haiku- or Sonnet-class | Low to medium for the checklist pass | Escalate only for disputed statistics, methodology, or interpretation. |
| Evidence and Figure Curator | Haiku-class | Low | Escalate only if figure interpretation or source attribution is ambiguous. |

### Cost controls

- Reserve the highest-cost model and high/extended thinking for the Audit Agent’s key claim check or a specific unresolved issue, not for every agent turn.
- The Orchestra Agent should first synthesize the structured reports at medium thinking. Escalate only on a material conflict or unsupported claim.
- Give agents only the files and excerpts needed for their assigned task. The Orchestra Agent remains responsible for receiving and inventorying all files; the Audit Agent gets the full manuscript and relevant supplements, while other roles can use focused sections, figures, captions, and result tables.
- Ask each agent for concise, structured output: the requested deliverables, evidence location, and unresolved questions. Avoid repeated full-paper summaries.
- Do not use high thinking for routine copy-editing, formatting, evidence extraction, or page-count checks.
- If an agent is uncertain, have it identify the exact passage/table/figure and ask for a targeted review instead of rerunning the whole task at a higher tier.

## Workflow and ownership

1. **Orchestra:** Inventory all files and determine the target journal/template and whether supplements are allowed. If the venue is not specified in the supplied files, use the manuscript’s current IEEE-style layout and record that assumption.
2. **Parallel review:** Give the Audit Agent the full source set; give the Proposal Agent the manuscript and any relevant supplements; give the Evidence and Figure Curator the figures, captions, and results. Each returns recommendations to the Orchestra Agent.
3. **Orchestra:** Resolve findings, approve the narrative and figure plan, and issue the Writer Agent a bounded brief.
4. **Write:** Writer Agent produces one integrated 8-page draft. Keep an untouched original.
5. **Independent QC:** QC Agent checks that same draft. Writer fixes only logged defects; QC rechecks page count and critical items.
6. **Handoff:** Orchestra provides the final draft, a concise change summary, the page count/template used, and any unresolved scientific or formatting questions.

Avoid parallel edits to the same manuscript. The Orchestra Agent is the only agent that merges content and approves the final version.

## Narrative and compression guidance

### Introduction logic

1. **Application:** Blink activity is useful information in fatigue-driving EEG, not only an artifact to remove.
2. **Pain point:** Amplitude thresholds vary across people, channels, hardware, and recording conditions. Whole-recording calibration can combine blink-rich and blink-poor segments and shift the operating point.
3. **Gap and question:** Test a candidate-epoch-conditioned, robust, channel-specific threshold pipeline against selected continuous-signal baselines, and examine its behavior across channel configurations and epoch durations.
4. **Contribution:** Present this as an evaluation of the complete pipeline. Do not claim that candidate-epoch screening alone caused the improvement without a matched ablation.

### Experiment messages to preserve

- **Channel/montage analysis:** Detection is strongest at frontal/frontopolar sites. Fp1 and Fp2 perform well as single-channel detectors and do not show a statistically significant reduction from full-montage scores in either corpus; this motivates reduced-channel evaluation but does not establish equivalence.
- **Epoch-duration analysis:** Fp1/Fp2 performance is broadly stable from 10 to 120 seconds, with small, corpus-specific differences. Describe this as offline robustness to common segmentation choices.
- **Baseline comparison:** The complete proposed configuration has the highest reported session-mean F1 on both corpora (88.25% Internal; 80.68% Cao2018) among the tested methods. State the comparison limits and evaluation protocol alongside these values.

### Method name and scope

A possible concise name is **Candidate-Epoch-Conditioned Thresholding (CECT)**. Define it precisely:

1. Multichannel peak-to-peak screening selects candidate epochs.
2. Samples from the candidate epochs yield a robust threshold per channel.
3. Each channel threshold is applied across all valid epochs to extract blink regions.

Use “epoch-aware” only with this definition. The method estimates session/channel thresholds from a selected pool; do not imply a separate threshold for every epoch or online adaptation.

## Fig. 7 recommendation

Use Fig. 7 to support the practical channel-selection insight: Fp1 and Fp2 are the only electrodes without a statistically significant drop from full-montage performance in both corpora, while most other electrodes show reductions. Keep both dataset panels, emphasize Fp1/Fp2, and simplify the detail for legibility if needed. State “no significant difference detected,” not “equivalent”; equivalence was not tested. Summarize lower-priority electrode-by-electrode results in text or supplementary material if permitted.

## Page budget starting point

Adjust to the supplied venue template, but keep the total at 8 pages including references.

| Content | Page-equivalent target |
|---|---:|
| Abstract and introduction | 0.9 |
| Method, datasets, evaluation protocol | 2.2 |
| Results: baseline comparison, Fig. 7, epoch robustness | 2.0 |
| Discussion and limitations | 0.9 |
| Conclusion | 0.2 |
| References | 1.8 |
| **Total** | **8.0** |

Prioritize one pipeline figure, one compact baseline comparison table, and Fig. 7. Consider moving detailed per-electrode statistics and extended tables to supplementary material if the target venue allows it.

## Non-negotiable accuracy checks

- Keep the headline F1 values qualified as **retrospective best-channel-per-session** if that remains the reported evaluation condition; do not present them as a fixed-channel deployment result.
- The BLINKER comparison uses a BLINKER-derived threshold stage, not the complete published BLINKER pipeline.
- A higher score for the complete pipeline does not isolate the causal contribution of candidate-epoch screening. Preserve the need for a matched ablation.
- “No significant difference” in Fig. 7 is not proof of equivalence.
- The study covers two simulated-driving datasets and offline evaluation; do not claim validated real-time or real-world driving performance.
- Resolve the preprocessing-order inconsistency between the pipeline overview and implementation note using the actual method/source files. Do not choose an order by guesswork.
- Do not compare absolute scores across datasets as if their annotation modalities and conditions were identical.
- Preserve uncertainty and limitations that materially affect interpretation, even under the page limit.

