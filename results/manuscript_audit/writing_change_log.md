# Writing change log (per-electrode results paragraphs)

Source of truth: results/manuscript_audit/{regional,single_electrode}_{internal,cao2018}_per_electrode.csv.
Numbers corrected: none. Every existing number was checked against the CSVs and kept.

## writing/e_result/exp1/p05_regional/p2.tex (regional rerun, Internal)

1. OLD: "..., 11 of the 24 electrodes remained significantly different after correction, and every significant difference was a reduction in the regional rerun."
   NEW: "..., 11 of the 24 electrodes remained significantly different after correction. All 24 electrodes had a lower session-mean $F_1$ in the regional rerun than in the full-montage run, so every significant difference was a reduction. The 13 non-significant electrodes also decreased, but their reductions did not reach significance."
   Reason: split long sentence. State direction for all 24 electrodes, including the 13 non-significant ones (all delta_f1_pp < 0 in CSV).
2. OLD: "Despite a visible drop in their session means, neither of the two highest-performing electrodes, Fp2 and Fp1, differed significantly from the full-montage run (adjusted $p > 0.05$ for both)."
   NEW: "Fp2 and Fp1 had the two highest regional-rerun scores, but neither differed significantly from the full-montage run (adjusted $p = 1.000$ for both)."
   Reason: exact adjusted p form (CSV p_adj = 1.0 for both). Shorter sentence.
3. OLD: "In contrast, AF4 and AF3, the third- and fourth-highest-performing electrodes, were significantly lower in the regional rerun, as were F3 and F4."
   NEW: "In contrast, AF4 and AF3, the third- and fourth-highest-performing electrodes, were significantly lower in the regional rerun. F3 and F4 were also significantly lower."
   Reason: split sentence.
4. OLD: "In the central region, C3 and FC6 showed significant reductions whereas C4 did not, and the pronounced C3--C4 asymmetry in absolute $F_1$ persisted."
   NEW: "In the central region, C3 and FC6 showed significant reductions, whereas FC5, FC1, FC2 and C4 did not."
   Reason: account for all six central electrodes. Dropped the descriptive asymmetry clause that was attached to the significance sentence.
5. OLD: "Five posterior electrodes, CP2, CP5, CP6, PO3, and PO4, also reached significance despite their very low absolute $F_1$, whereas none of the remaining posterior electrodes did."
   NEW: "In the parietal region, CP2, CP5 and CP6 showed significant reductions, whereas CP1 did not. In the occipital region, as defined in Figure~\ref{fig:eeg_map}, PO3 and PO4 showed significant reductions. The other six occipital electrodes, E83, O1, P3, P8, P7 and P4, did not."
   Reason: "posterior" forbidden. Parietal and occipital in separate sentences. Removed the "despite ... low absolute F1" link. All non-significant electrodes named (4+2+3+2 = 11 significant).
6. ADDED: "Table~\ref{tab:app_regional_internal} in Appendix~\ref{app:per_electrode_stats} lists the session-mean $F_1$, $\Delta F_1$ and adjusted $p$-value for every electrode."
   Reason: point to appendix table.

## writing/e_result/exp1/p05_regional/p3.tex (regional rerun, Cao2018)

1. OLD: "Sixteen of the 18 electrodes remained significantly different after correction, and again every significant difference was a reduction."
   NEW: "Sixteen of the 18 electrodes remained significantly different after correction. All 18 electrodes had a lower session-mean $F_1$ in the regional rerun than in the full-montage run, including the non-significant Fp1 and Fp2. Every significant difference was therefore a reduction."
   Reason: state direction of non-significant electrodes. Split sentence.
2. OLD: "As on Internal, only the frontopolar pair Fp1 and Fp2 did not reach significance (adjusted $p > 0.05$ for both), whereas F3 and F4, the third- and fourth-highest-performing electrodes, did."
   NEW: "As on Internal, only Fp1 and Fp2 did not reach significance (adjusted $p = 1.000$ for both). F3 and F4, the third- and fourth-highest-performing electrodes, did reach significance."
   Reason: removed "frontopolar pair". Exact adjusted p. Split sentence.
3. OLD: "Unlike on Internal, every central, parietal, and occipital electrode reached significance, including both C3 and C4."
   NEW: "Unlike on Internal, all six central electrodes reached significance, including both C3 and C4. Both parietal electrodes, CP3 and CP4, also reached significance. All six occipital electrodes, as defined in Figure~\ref{fig:eeg_map}, reached significance as well."
   Reason: parietal and occipital in separate sentences. Counts add up (2 frontal + 6 + 2 + 6 = 16).
4. ADDED: pointer to Table~\ref{tab:app_regional_cao2018}.

## writing/e_result/exp1/p07_single_channel/p2.tex (single-electrode run, Internal)

1. OLD: "Every electrode scored lower in the single-electrode run, with $\Delta F_1$ ranging from $-7.02$ to $-0.15$ percentage points."
   NEW: "Every electrode scored lower in the single-electrode run than in the full-montage run. Values of $\Delta F_1$ ranged from $-7.02$ percentage points for C3 to $-0.15$ percentage points for CP2. The ten non-significant electrodes therefore also decreased, but their reductions did not reach significance."
   Reason: name the extremes. State direction of the 10 non-significant electrodes. Numbers unchanged.
2. OLD: "Although Fp1 and Fp2 retained the two highest single-electrode scores, neither differed ..."
   NEW: "Fp1 and Fp2 retained the two highest single-electrode scores, but neither differed ..."
   Reason: minor restructuring. Content and p unchanged.
3. OLD: "In contrast, AF4 and AF3 were significantly lower in the single-electrode run than in the full-montage run."
   NEW: "In contrast, the other four frontal electrodes, AF4, AF3, F4 and F3, were all significantly lower in the single-electrode run."
   Reason: F3 and F4 were significant but missing.
4. OLD: "Beyond the frontal region, both C3 and C4 showed a significant configuration effect despite the large C3--C4 asymmetry noted above."
   NEW: "In the central region, C3, FC5 and C4 showed significant reductions, whereas FC6, FC2 and FC1 did not."
   Reason: FC5 was missing. Removed the "despite asymmetry" link.
5. ADDED: "In the parietal region, only CP1 showed a significant reduction. CP2, CP5 and CP6 did not."
   Reason: parietal region was not mentioned. CP1 significant.
6. OLD: "Most occipital electrodes also differed significantly, with the exception of O1 and P4, even though all of them had very low absolute $F_1$."
   NEW: "In the occipital region, as defined in Figure~\ref{fig:eeg_map}, PO3, PO4, E83, P3, P8 and P7 showed significant reductions, whereas O1 and P4 did not."
   Reason: name all significant electrodes (4+3+1+6 = 14). Removed the "even though ... low absolute F1" link. P4 region follows the pipeline definition.
7. ADDED: pointer to Table~\ref{tab:app_single_internal}.

## writing/e_result/exp1/p07_single_channel/p3.tex (single-electrode run, Cao2018)

1. OLD: "..., 16 of the 18 electrodes remained significantly different after correction, and all differences were again reductions."
   NEW: "..., 16 of the 18 electrodes remained significantly different after correction. All 18 electrodes scored lower in the single-electrode run than in the full-montage run, including the non-significant Fp1 and Fp2. Every difference was therefore again a reduction."
   Reason: make explicit that non-significant Fp1 and Fp2 also decreased. Split sentence.
2. OLD: "As on Internal, only the frontopolar pair Fp1 and Fp2 did not reach significance ..."
   NEW: "As on Internal, only Fp1 and Fp2 did not reach significance ..."
   Reason: removed "frontopolar pair".
3. OLD: "F3 and F4, which had the third- and fourth-highest single-electrode scores, showed the two largest reductions (...)."
   NEW: "F3 and F4 had the third- and fourth-highest single-electrode scores. They also showed the two largest reductions (...)."
   Reason: split sentence. Numbers (-10.21, -8.96) unchanged and verified (next largest FT8 -6.63).
4. OLD: "Every central, parietal, and occipital electrode differed significantly, including both C3 and C4."
   NEW: "All six central electrodes differed significantly, including both C3 and C4. Both parietal electrodes, CP3 and CP4, also differed significantly. All six occipital electrodes, as defined in Figure~\ref{fig:eeg_map}, differed significantly as well."
   Reason: parietal and occipital in separate sentences. Counts add up to 16.
5. ADDED: pointer to Table~\ref{tab:app_single_cao2018}.

## writing/e_result/exp1/p07_single_channel/paragraph_electrode_level_stats.tex

1. OLD: "... tested within each dataset" (no full stop)
   NEW: "... tested within each dataset."
   Reason: missing full stop.
2. OLD: "The Figure~\ref{fig:exp1_single_channel_stats} shows, ..., together with the adjusted-significance marker."
   NEW: "Figure~\ref{fig:exp1_single_channel_stats} shows, ..., with an asterisk marking electrodes that remained significant after correction."
   Reason: grammar. The figure shows asterisks only, and the wording now matches the regional intro.

## Manager review edits
- p05_regional/p2.tex: merged the two direction sentences into "Every significant difference was a reduction. The 13 non-significant electrodes also had a lower session-mean F1 in the regional rerun than in the full-montage run, so no electrode increased." Reason: removed redundancy. No numbers changed.
- p07_single_channel/p2.tex: dropped the redundant clause "but their reductions did not reach significance". No numbers changed.
- h_appendix/appendix_per_electrode_stats.tex: Internal table notes changed from "FC and FT sites" to "FC sites" (Internal has no FT electrodes).

---

## Round 2 (consistency sweep, p-value form, near-threshold notes)

No numbers were changed in round 2. All counts were re-checked against the four CSVs after editing (see "Count check" at the end).

### A. Adjusted p-value form (item 2)
Non-significant results now read "adjusted $p > 0.05$". Significant results now read "adjusted $p < 0.05$". Exact adjusted p-values appear only in the appendix tables.

| File | Old | New |
|---|---|---|
| p05_regional/p2.tex | "...remained significantly different after correction." | "...remained significantly different after correction (adjusted $p < 0.05$)." |
| p05_regional/p2.tex | "(adjusted $p = 1.000$ for both)" | "(adjusted $p > 0.05$ for both)" |
| p05_regional/p3.tex | same two changes as p2.tex | same |
| p07_single_channel/p2.tex | same two changes | same |
| p07_single_channel/p3.tex | same two changes | same |
| p05_regional/possible_discussion.tex | "showed no detectable paired difference after correction in either corpus" | "(adjusted $p > 0.05$)" and "(adjusted $p < 0.05$)" added. See section C. |
| p08_montage_contribution/paragraph.tex | exact p for Fp1/Fp2 ($p=1.000$, $p=0.991$) and for AF4/AF3/F3/F4 ($p=0.001$ ... $p<0.001$) | "(adjusted $p > 0.05$ for both)" and "(adjusted $p < 0.05$ for all four / for both)". The old exact values came from a different correction family and did not match the CSVs. The significance classification is the same in both. |

### B. Near-threshold notes (item 3)
There is one sentence per section and no qualitative labels. The appendix tables show the exact adjusted p for each case: regional Internal CP2 0.041, CP5 0.049, FC5 0.058; single-electrode Internal FC5 0.041; single-electrode Cao2018 P4 0.046.
- p05_regional/p2.tex (regional section): added "Three electrodes, CP2, CP5 and FC5, lay close to the corrected threshold (Table~\ref{tab:app_regional_internal})."
- p07_single_channel/p3.tex (single-electrode section): added "Two electrodes, FC5 on Internal and P4 on Cao2018, lay close to the corrected threshold (Tables~\ref{tab:app_single_internal} and~\ref{tab:app_single_cao2018})."
- Classification is unchanged. CP2, CP5, FC5 (single-electrode) and P4 are significant. FC5 (regional) is not.

### C. Terminology and style sweep (item 1)

**p04_per_electrode/paragraph_per_electrode.tex**
- "detection quality was concentrated at the frontopolar pair rather than distributed across the frontal region." -> "detection quality was highest at Fp1 and Fp2 rather than uniform across the frontal region." Reason: removes "frontopolar", which is not a declared region.
- "The posterior electrodes performed markedly worse than the frontal and central sites, and the parietal and occipital groups differed between datasets." -> "The parietal and occipital electrodes performed markedly worse than the frontal and central electrodes. Their performance also differed between datasets." Reason: "posterior" removed and the sentence split.
- "P3 and P4, the most anterior electrodes assigned to this region, reached 12.80% and 12.67%. The regional mean F1 on Cao2018 was therefore driven by P3 and P4 rather than by electrodes over the occipital cortex." -> "P3 and P4 reached 12.80% and 12.67%. Within the Cao2018 occipital region, P3 and P4 therefore scored highest and O1 and O2 scored lowest." Reason: "anterior" removed, and "driven by" / "occipital cortex" removed as an anatomical overclaim.
- Caption "scored inside the full 32-channel Proposed-approach montage run" -> "scored in the full-montage run". Also "regional-subset" -> "regional" in a commented-out caption line.

**p05_regional/paragraph_per_electrode.tex**
- "remained concentrated at the frontopolar and neighbouring anterior frontal electrodes rather than distributed uniformly across the frontal region." -> "was highest at Fp1, Fp2 and the neighbouring frontal electrodes rather than uniform across the frontal region."
- "within the frontal subset's own rerun" -> "within the frontal regional rerun". Also "the entire frontal subset" -> "the entire frontal region".
- "Although every one of these frontal electrodes scored lower in its own subset rerun ... so restricting Stage~A/B screening to the frontal subset alone did not reorder the strongest frontal electrodes." -> split into three sentences using "regional rerun" and "Stage~A and Stage~B". The ranking claim was checked against the CSVs and holds on both datasets.
- "within their own subset rerun" -> "in the central regional rerun". Also "persisted in the central subset's self-contained rerun" -> "persisted in the central regional rerun". The long sentence was split.
- "Wheras on Cao2018, ..." -> "On Cao2018, ..." Reason: typo fixed and the sentence split.
- "much lower in their own subset reruns" -> "scored much lower in their regional reruns". The parietal and occipital best-electrode clause was split into two sentences.
- "Overall, the self-contained subset reruns preserved the same anterior-to-posterior spatial pattern ... frontopolar and anterior frontal sites and much lower performance at the central, parietal and occipital electrodes." -> "Overall, the regional reruns preserved the pattern observed in the full-montage run. $F_1$ was highest at Fp1, Fp2 and the neighbouring frontal electrodes, and lower at most central, parietal and occipital electrodes." Reason: forbidden terms removed. "Most" was added because C3 on Internal (58.59%) exceeds F3 and F4. A strict frontal-to-occipital decline does not hold on Internal (occipital mean > parietal mean).
- Caption "Per-electrode detection F1 within each region's own channel-subset rerun ... self-contained subset run." -> "Per-electrode detection $F_1$ in the regional rerun of each electrode's own region, coloured by region. Each bar is one electrode's session-mean $F_1$ when only the electrodes of its region were supplied to the pipeline."

**p05_regional/possible_discussion.tex** (included via sec.tex)
- "Fp1 and Fp2, the highest-performing electrode in each dataset, showed no detectable paired difference after correction in either corpus, while most other electrodes changed significantly, generally by a few percentage points. Significant differences were also more widespread on Cao2018 than on Internal, where roughly half of the non-frontal electrodes did not reach significance ..." -> "Fp1 and Fp2, the two highest-performing electrodes in each dataset, showed no significant paired difference after correction in either dataset (adjusted $p > 0.05$). By contrast, 11 of the other 22 electrodes on Internal and all 16 on Cao2018 were significantly lower in the regional rerun (adjusted $p < 0.05$). Significant differences were therefore more widespread on Cao2018 than on Internal. On Internal, 11 of the 18 non-frontal electrodes did not reach significance despite showing the same direction of change."
  - **Corrected wording (not a number change).** "Roughly half" of the non-frontal Internal electrodes was inaccurate; the true figure is 11 of 18. "Most other electrodes" was imprecise on Internal, where it is 11 of 22. "Generally by a few percentage points" was removed because several significant reductions are below 0.5 percentage points.
- "posterior electrodes" -> "parietal and occipital electrodes" in a commented-out line.

**p07_single_channel/paragraph_per_electrode.tex**
- Internal opening sentence split into four. "the earlier restricted analysis" -> "the regional analysis".
- "The weakest was C4 with an F1 of 1.51%, with every parietal and occipital electrode below 3.2%." -> split into two sentences.
- Cao2018 paragraph rewritten into short sentences.
  - "the same as Internal's canonical frontal set" was removed because it was inaccurate. Internal's top four are Fp1, Fp2, AF4 and AF3.
  - "followed by the remaining central electrodes FC4, FT8 and FT7" -> "FC4, FT8 and FT7 followed at ...". C3 and C4 also remain, so "remaining" was wrong.
  - "the entire second tier ... weaker central pair" -> "The six central electrodes therefore occupied the next six places in the ranking ... The weakest central electrodes were C3 and C4". Checked against the CSV (ranks 5–10).
  - "the same anterior-to-posterior decline reported for the full-montage and regional-subset analyses" -> "the same decline from the frontal to the occipital region reported for the full-montage run and the regional analysis". The decline is monotonic on Cao2018 in all three configurations.

**sec.tex (figure captions)**
- fig:exp1_single_channel_stats: "comparison of Proposed-approach $F_1$ when each electrode ... operated as a complete self-contained detector (narrow, opaque bar) against the same electrode scored inside the full 32-channel montage" -> "comparison of $F_1$ for each electrode ... in the single-electrode run (narrow, opaque bar) and in the full-montage run (wide, translucent bar)". The stray full stop that followed a comment line was fixed. The comma splice "marks adjusted $p<0.05$, electrodes without ..." was split into two sentences.
- fig:f1_by_epoch: "of Proposed-approach across epoch durations" -> "of the pipeline across epoch durations". Also "reported separately: Internal (top row) ..." -> "reported separately for Internal (top row) ..." to remove the colon.

**p08_montage_contribution/paragraph.tex** (not \input anywhere; edited because it is under exp1)
- "The subset analyses above" -> "The regional analysis above". Also "full 32-channel Proposed-approach run" -> "full-montage run". p-values changed as in section A.

### Count check after round 2
All counts match the CSVs.
- Regional, Internal: 11 significant named (AF4, AF3, F3, F4, C3, FC6, CP2, CP5, CP6, PO3, PO4). 13 non-significant named. All 24 decreased.
- Regional, Cao2018: 16 significant (F3, F4 + 6 central + CP3, CP4 + 6 occipital). Fp1 and Fp2 non-significant. All 18 decreased.
- Single-electrode, Internal: 14 significant named (AF4, AF3, F4, F3, C3, FC5, C4, CP1, PO3, PO4, E83, P3, P8, P7). 10 non-significant named. ΔF1 ranges from −7.02 to −0.15 percentage points. All 24 decreased.
- Single-electrode, Cao2018: 16 significant. Fp1 and Fp2 non-significant. All 18 decreased. F3 (−10.21) and F4 (−8.96) are the two largest reductions.
- possible_discussion.tex: 11 of 22 (Internal, excluding Fp1 and Fp2), 16 of 16 (Cao2018), and 11 of 18 non-frontal Internal electrodes non-significant.
- p08: the significance classes for Fp1, Fp2, AF4, AF3, F3 and F4 match the single-electrode CSVs, as do all six ΔF1 values.

---

## Round 3 (flow revision)

Scope: this round only restructures the prose. Every number and claim is unchanged. A decimal-by-decimal comparison against the committed versions shows no F1 or ΔF1 value added, removed or altered. The only numeric differences are the round-2 "0.05" thresholds and the exact p-values removed from p08.

Principles applied:
- Each paragraph leads with the overall pattern (all electrodes decreased) and then gives the number of significant reductions.
- The separate sentences "every significant difference was a reduction" and "the non-significant electrodes also decreased" are gone. The direction is now stated once.
- "Remained significantly different" and "remained significant" are dropped everywhere.
- Parallel results across datasets are linked with "likewise", "as on Internal", "unlike on Internal" and "in contrast". "Therefore" is kept only where it marks a real inference.
- Closely related facts are joined, for example the per-region significant/non-significant pairs and the near-threshold note with the table pointer.

### p05_regional/p2.tex (regional, Internal)
Old (round 2) opening: "11 of the 24 electrodes remained significantly different after correction (adjusted $p < 0.05$). Every significant difference was a reduction. The 13 non-significant electrodes also had a lower session-mean $F_1$ ... so no electrode increased."
New: "On Internal (...A), all 24 electrodes had a lower session-mean $F_1$ in the regional rerun than in the full-montage run, and the reduction was significant after correction for 11 of them (adjusted $p < 0.05$)."
Other changes:
- "AF4 and AF3 ... were significantly lower in the regional rerun. F3 and F4 were also significantly lower." -> "..., as were F3 and F4."
- Central, parietal and occipital sentences recast as "the reduction was significant for X but not for Y". The occipital sentence now reads "only PO3 and PO4 were significantly lower, and E83, O1, P3, P8, P7 and P4 were not".
- The near-threshold sentence now leads into the table pointer: "Table~... gives their exact adjusted $p$-values, together with the session-mean $F_1$ and $\Delta F_1$ of every electrode."

### p05_regional/p3.tex (regional, Cao2018)
New text:
- "all 18 electrodes likewise scored lower in the regional rerun than in the full-montage run, but significant reductions were far more widespread than on Internal."
- "Sixteen of the 18 reductions were significant after correction (adjusted $p < 0.05$). As on Internal, only Fp1 and Fp2 did not reach significance (adjusted $p > 0.05$ for both), whereas F3 and F4, the third- and fourth-highest-performing electrodes, did."
- "Unlike on Internal, the reduction was significant at all six central electrodes, including both C3 and C4, and at both parietal electrodes, CP3 and CP4. It was also significant at all six occipital electrodes, as defined in Figure~\ref{fig:eeg_map}."

Removed: "Every significant difference was therefore a reduction." It was redundant.

### p07_single_channel/p2.tex (single-electrode, Internal)
The opening follows the target style supplied: "every electrode scored lower in the single-electrode run than in the full-montage run, with $\Delta F_1$ ranging from $-7.02$ percentage points at C3 to $-0.15$ percentage points at CP2. These reductions were significant after correction for 14 of the 24 electrodes (adjusted $p < 0.05$)."

Other changes:
- Removed "The ten non-significant electrodes therefore also decreased." It was redundant.
- "In contrast, the other four frontal electrodes ... were all significantly lower." The words "in the single-electrode run" were dropped because the context already makes it clear.
- The per-region sentences were recast in the same pattern as p05/p2. The parietal sentence now reads "only CP1 was significantly lower, whereas CP2, CP5 and CP6 were not". The occipital sentence now reads "the reduction was significant for PO3, PO4, E83, P3, P8 and P7, leaving O1 and P4 as the only exceptions".

### p07_single_channel/p3.tex (single-electrode, Cao2018)
Opening: "all 18 electrodes likewise scored lower in the single-electrode run than in the full-montage run, and 16 of these reductions were significant after correction (adjusted $p < 0.05$). As on Internal, only Fp1 and Fp2 did not reach significance (adjusted $p > 0.05$ for both)."

Other changes:
- Removed "Every difference was therefore again a reduction." It was redundant.
- The central and parietal results are now one sentence: "The reduction was also significant at all six central electrodes, including both C3 and C4, and at both parietal electrodes, CP3 and CP4." The occipital result is a separate sentence: "All six occipital electrodes ... were likewise significantly lower."
- The near-threshold sentence now leads into a combined pointer to both single-electrode tables.

### p04_per_electrode/paragraph_per_electrode.tex
- "...than the frontal and central electrodes. Their performance also differed between datasets." -> joined with "and".
- Cao2018 occipital: "O1 and O2 were near floor ... T5 and T6 were intermediate ... P3 and P4 reached 12.80% and 12.67%. Within the Cao2018 occipital region, P3 and P4 therefore scored highest and O1 and O2 scored lowest." -> "P3 and P4 scored highest at 12.80\% and 12.67\%, T5 and T6 were intermediate at 9.26\% and 8.30\%, and O1 and O2 were near floor at 3.10\% and 3.33\%." The same facts are ordered from highest to lowest instead of being stated twice.
- "The Cao2018 occipital group" -> "The Cao2018 occipital region".

### p05_regional/paragraph_per_electrode.tex
- Internal frontal: the two sentences were joined, and "then fell sharply at F3 and F4" became part of the first sentence.
- Cao2018 frontal: "the same four strongest electrodes, Fp1, Fp2, F3 and F4, made up the entire frontal region" -> "the frontal region consists of Fp1, Fp2, F3 and F4 only". The word "same" was imprecise because Internal's four strongest are Fp2, Fp1, AF4 and AF3.
- "Every one of these frontal electrodes scored lower ... However, the ranking ... was unchanged ... Restricting Stage~A and Stage~B ... therefore did not reorder ..." -> "Every one of these frontal electrodes scored lower in the regional rerun than in the full-montage run (Section~...), but restricting Stage~A and Stage~B to the frontal electrodes left their ranking by $F_1$ unchanged in both datasets." The last two sentences said the same thing, so they were merged.
- Central: "The central regional rerun again showed a dataset-specific asymmetry. On Internal, C3 reached ... while C4 reached only ..., so the pronounced C3--C4 asymmetry seen in the full-montage run persisted. On Cao2018, in contrast, C3 and C4 remained close together ..., so the asymmetry again stayed specific to Internal." The two "therefore" sentences were folded in.
- Parietal and occipital: "The best parietal electrode reached only $1.92\%$ on Internal (CP1) and $15.63\%$ on Cao2018 (CP4). The best occipital electrode reached $3.35\%$ on Internal (PO3) and $10.04\%$ on Cao2018 (P3)." Each region keeps its own sentence.
- Closing: the two sentences were joined with "with".

### p05_regional/possible_discussion.tex
- "... in either dataset (adjusted $p > 0.05$). By contrast, 11 of the other 22 ..." -> joined with "whereas".
- "Significant differences were therefore more widespread on Cao2018 than on Internal. On Internal, 11 of the 18 ..." -> "... than on Internal, where 11 of the 18 non-frontal electrodes did not reach significance despite showing the same direction of change."

### p07_single_channel/paragraph_per_electrode.tex
- Internal: the four opening sentences were merged into two: "... topped Internal's ranking at 83.73\%, ... respectively (Figure~...). These are the same four frontal electrodes identified by the regional analysis, and in the same order except that Fp1 now leads Fp2 by 0.36 percentage points rather than trailing it."
- "C3 followed next in the ranking" -> "C3 came next". Also "which trailed further behind at" -> "at", which removes a redundancy.
- "Performance then fell sharply across the remaining 17 electrodes. ... The weakest was C4 ... Every parietal and occipital electrode ..." -> "Performance then fell sharply across the remaining 17 electrodes, with every parietal and occipital electrode below $3.2\%$ and C4 the weakest overall at $1.51\%$." The CSV confirms C4 is the lowest of all 24.
- Cao2018: the ranking and the "matching the full-montage ranking" statement were rejoined. "The six central electrodes therefore occupied the next six places" -> "Performance then dropped to $38.44\%$ at FC3, the first of the six central electrodes that occupied the next six places." The "therefore" there was not an inference, so it was removed.
- "where the weakest electrode, O1, reached" -> "where O1 was the weakest electrode overall at". The CSV confirms this.
- "reported for the full-montage run and the regional analysis" -> "seen in the full-montage run and the regional analysis". The earlier sections describe the per-region values but do not explicitly state a monotonic decline.

### p07_single_channel/paragraph_electrode_level_stats.tex
- "tested with a two-tailed Wilcoxon signed-rank test, paired by session, with $p$ Bonferroni-corrected ..." -> "tested with a two-tailed Wilcoxon signed-rank test paired by session, and $p$-values were Bonferroni-corrected ...". This removes a comma chain.
- "electrodes that remained significant after correction" -> "electrodes that were significant after correction".

### p05_regional/paragraph_electrode_level_stats.tex
- "electrodes that remained significant after correction" -> "electrodes that were significant after correction". This is the same rule-5 fix. It is the only change to this file in rounds 2 and 3.

### p08_montage_contribution/paragraph.tex (not \input anywhere)
- "on either corpus" -> "on either dataset". The adjusted-p form was moved into that sentence.
- The four "In Internal / In Cao2018" sentences were combined into two, each giving the ΔF1 values for one electrode group across both datasets.
- "At every weaker frontal-adjacent electrode, by contrast, the gain was significant" -> "By contrast, the gain was significant at every weaker frontal-adjacent electrode (adjusted $p < 0.05$)".
- Claims are unchanged. This paragraph still contains interpretive statements, such as "already capture nearly all of the detectable blink signal" and "consistent with the full montage recovering blink epochs". Round 3 was restricted to flow, so these were not revised.
