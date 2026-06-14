
# Paragraph structure validator

Checks:

```text
Every paragraph has its own folder.
Every paragraph folder has paragraph.tex.
No paragraph.tex contains multiple paragraphs.
Every subsection with multiple paragraphs has p001, p002, etc.
No direct prose exists inside subsection main.tex.
```

# Evidence validator

Checks:

```text
Every paragraph has evidence.json.
Every claim has source study_id.
Every claim has exact_original_text.
Every paragraph has original_quotes.tex.
Every citation key exists in references.bib.
Every experiment has run.sh or equivalent entrypoint.
Every experiment stores outputs in a dedicated output folder.
Every experiment documents whether it is rerun-only or new analysis.
Every experiment has a LaTeX rerun-note paragraph.
Rerun-note paragraph is under the same subsection as the result.
Rerun-note paragraph uses \experimentnote{...}.
Preliminary result is not overwritten.
Rerun result is separately stored.
Diff report exists when preliminary result exists.
```

# Writing soundness validator

Checks:

```text
logical flow
overclaiming
unsupported causal claims
citation placement
paragraph purpose
transition quality
academic tone
result-discussion-conclusion alignment
```

# Analysis validator

Checks:

```text
Raja dataset was loaded.
Murat2018 dataset was loaded.
Every result table/figure is generated from a script.
No manual result table is accepted.
Every reported number appears in analysis outputs.
```

# Conclusion validator

Checks:

```text
No new claims.
Matches research objective.
Matches results.
Matches discussion.
Mentions limitations only if discussed earlier.
```
