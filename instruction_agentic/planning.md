Use a DAG, not a linear script.

```text
Bootstrap
   ↓
CSV → SQLite DB ───────────────┐
PDF/Text extraction ───────────┤
BibTeX generation ─────────────┤
                               ↓
                     Retrieval + Evidence Index
                               ↓
                    Paragraph Structure Agent
                               ↓
        ┌───────────────┬───────────────┬───────────────┐
        ↓               ↓               ↓
 Introduction       Results         Discussion
 Writing Agent      Analysis        Writing Agent
        ↓               ↓               ↓
        └───────────────┴───────┬───────┘
                                ↓
                         Conclusion Agent
                                ↓
                   Validation + Soundness Agent
                                ↓
                         LaTeX Build Agent
```

Parallelizable tasks:

```text
PDF extraction per PDF
CSV normalization per file
study retrieval per section
paragraph writing per paragraph
paragraph validation per paragraph
analysis scripts after DB creation
BibTeX generation after metadata ingestion
```

Non-parallel or limited-parallel tasks:

```text
final conclusion rewrite
global flow validation
final LaTeX compilation
final reference consistency check
```