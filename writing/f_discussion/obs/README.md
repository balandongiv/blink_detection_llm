# writing/f_discussion/obs/

LaTeX source moved out of the active `writing/f_discussion/` tree because it is not
`\input` (or is only referenced behind a commented-out `\input`) anywhere in the live
`access.tex` -> `discussion.tex` chain. Nothing was deleted; every `.tex` file moved via
`git mv`, so its history and original path are one `git log --follow` away.

- `d3_estimator/paragraph.tex` -- discusses the Stage-B median/MAD vs. mean
  threshold-estimator comparison. Its results subsection lives at
  `e_result/obs/exp3/sec.tex`, itself archived because `result.tex` never `\input`s it.
  Re-enable both together.
- `d5_channel_instability/paragraph.tex` -- draws its selection-frequency and
  cross-condition-agreement numbers from the "Stability of the Channel Choice"
  subsubsection, which is commented out of `e_result/exp1/sec.tex`. Re-enable both
  together.
- `d4_why_dilution/paragraph.tex` -- the Experiment 3 precision-recall / threshold-dilution
  interpretation. Merged into `d3_main_implication/paragraph.tex` so that Experiment 3 is
  discussed in one paragraph; restoring it would duplicate that content.
- `d11_literature/paragraph.tex` -- positions the detector against prior work
  (`tab:literature_comparison`); never `\input` anywhere, live or commented, since the
  Literature Review section itself is commented out of `access.tex`.
- `p10_selection_frequency/paragraph.tex` -- best-electrode selection-frequency numbers;
  never `\input` anywhere, live or commented.
- `p1.tex` -- an earlier whole-discussion draft, superseded by the current per-topic
  `d*_*/paragraph.tex` files; never `\input` anywhere.

## Restoring something from here

1. `git mv` the file(s) back to their original path under `f_discussion/` (see
   `git log --follow <path>` for the original location).
2. Uncomment (or add) the corresponding `\input` line in `discussion.tex`.
3. Recompile.
