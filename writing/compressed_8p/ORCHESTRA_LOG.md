# Orchestra log: 8-page compression

Brief: `../../agent_handoff_plan.md`

## Source map

| File | Role | Notes |
|---|---|---|
| `writing/IEEE-TJ-color-latex-template/main.tex` | Untouched original root | Compiles to 16 pp: body ~11.5 pp, refs ~2.5 pp (49 entries), appendix 2 pp |
| `writing/{a_abstract,b_introduction.tex,b_intro,d_method,e_result,f_discussion,g_conclusion,h_appendix}` | Untouched original modular prose | |
| `writing/compressed_8p/original_flat.tex` | Flattened snapshot of the original (latexpand, comments blanked) | Read-only reference for all agents |
| `writing/compressed_8p/main.tex` | The ONE working copy (Writer only) | Builds against `../e_result/figures/`, `../figures/`, `../images/`, `../*.bib` |
| `writing/e_result/figures/*.pdf` | Result figures | Fig numbering in original PDF: 1 flowchart, 2 eeg_map, 3 full-montage per electrode, 4 regional per electrode, 5 regional stats, 6 single-channel boxplot, 7 single-channel stats, 8 epoch duration, 9 PR scatter |
| `writing/EXPECTED_JOURNAL.md` | Candidate venues (BSPC, CMPB; Elsevier) | No venue-specific template supplied with the brief |

## Assumptions

- A1. Venue not fixed by the brief. Use the manuscript's current IEEE `ieeecolor` journal layout (two-column) and count 8 pages including references.
- A2. Supplementary material assumed permitted. The per-electrode appendix tables (original Tables II to V) move to a supplement and do not count toward 8 pages.
- A3. Original Fig. 7 = `fig_exp1_single_channel_stats.pdf` (single-electrode vs full-montage, Wilcoxon/Bonferroni, two dataset panels).

## Decision log

(filled in as agents report)

### Reports received (Proposal, Curator, Audit), resolved 2026-10-27

- D1. Narrative: adopt brief's central narrative and the name Candidate-Epoch-Conditioned Thresholding (CECT). Title unchanged (author decision); "epoch-aware" used only with the CECT definition.
- D2. Result order: baseline comparison first (headline), then channel analysis (Fig. 7), then epoch duration.
- D3. Preprocessing order resolved from code (Audit): epoching -> per-epoch zero-phase 1-20 Hz band-pass at native rate -> per-epoch resampling to 100 Hz (src/common/epoch_input.py:69-81; src/utils/channel_ablation_utils.py:236). Overview, Fig. 1 caption and preprocessing paragraph rewritten to this order; the "implementation detail / limitation" note is dropped because it is no longer inconsistent. Fig. 1 artwork itself still shows the old order -> flagged.
- D4. Abstract and Table I carry the retrospective best-channel-per-session (oracle) qualifier.
- D5. Fp1/Fp2 claim worded per corpus: Cao2018 -> only electrodes without a significant reduction; Internal -> only electrodes with F1 above ~11% without a significant reduction (others non-significant are near floor). "No significant difference detected", never equivalence.
- D6. Drop "smallest reduction" (conclusion) and "third/fourth highest F3/F4" claims; fix "each epoch" adaptation wording; discussion epoch range 10-120 s with the small Internal declines.
- D7. Limitations add: pipelines also differ in the threshold location statistic and margin (no value stated), so no component is isolated. No new numbers added (Stage A candidate fraction, k value, E84) — flagged to author instead.
- D8. Figures kept: Fig. 1 flowchart (figure*), Table I, PR scatter, Fig. 7 single-electrode stats + epoch-duration (figure*). eeg_map, full-montage/regional/boxplot figures and appendix tables -> supplement.tex.
- D9. Fig. 7 legibility: layout-only regeneration (panels side by side, Fp1/Fp2 emphasised) into a NEW file; original figure untouched; data unchanged.

### Unresolved, for the author
- U1. Internal all_channel gate includes off-montage E84 and lacks Cz (31 real electrodes); "32 channels incl. Cz" is inaccurate; rerun pending (existing O2=E83 issue).
- U2. Baseline vs proposed differ in threshold multiplier and centre statistic; not stated numerically.
- U3. Annotation provenance (blinded raters vs PyBlinker-initialised Cao2018 labels) unverified.
- U4. Fp1/Fp2 chosen in Exp 1 on the same sessions used in Exp 2; sessions treated as independent in Wilcoxon tests.
- U5. Venue undecided (EXPECTED_JOURNAL lists Elsevier journals; layout is IEEE).

### QC round (2026-10-27)
- Fixed: Internal Fp1/Fp2 wording (reference runs named, 11% bound), Cao2018 maxima rounded to about 0.4/0.3 pp, two over-reaching discussion sentences, misplaced nystrm2024what citation, dead \IfFileExists fallbacks (duplicate labels), supplement author line, supplement references placement, "Stage A to Stage C" wording.
- Rebuilt: main.pdf 7 pp incl. references, supplement.pdf 5 pp, no undefined/multiply-defined refs.
- Open (author): U1-U5 above; Fig. 1 artwork shows old preprocessing order and "Double-Thresholding" banner (regenerate from images/flow.pptx); template LOGO placeholder in header.
