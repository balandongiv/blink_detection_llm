
# 1. Introduction Study Retrieval Agent

Purpose:

```text
Extract relevant studies for the introduction.
Use SQL and FTS over abstracts and PDF text.
Prioritize studies from Raja dataset and Murat2018 dataset.
```

Outputs:

```text
evidence/introduction/relevant_studies.json
paper/sections/01_introduction/source_map.md
```

The agent must return:

```text
study_id
title
authors/year
relevance reason
exact abstract/PDF quote
recommended paragraph use
bibtex key
```

---

# 2. Paragraph Structure Agent

This agent does not write final prose. It writes paragraph plans.

Example output:

```json
{
  "section": "Introduction",
  "subsection": "Research gap",
  "paragraphs": [
    {
      "paragraph_id": "intro_gap_p001",
      "purpose": "Explain limitation in prior studies.",
      "required_sources": ["raja_014", "murat2018_022"],
      "must_include": [
        "problem context",
        "specific limitation",
        "why current study is needed"
      ],
      "avoid": [
        "overclaiming",
        "unsupported novelty claims"
      ]
    }
  ]
}
```

---

# 3. Academic Writing Agent

Writes only one paragraph at a time.

Input:

```text
paragraph plan
evidence bundle
required citation keys
target section
style guide
```

Output:

```text
paragraph.tex
```

Constraints:

```text
No evidence → fail.
No citation → fail.
No exact source quote → fail.
```