## 1. Core principle

The **Agent Manager should only think, plan, route, inspect, and decide**.

It must **not directly write paper text, code, LaTeX, database rows, or analysis outputs**. Instead, it creates task specifications and sends them to one of the allowed execution paths:

1. **ChatGPT UI/API-connected runner**
   Before using this runner, read:

   ```text
   C:\Users\balan\IdeaProjects\academic_paper_maker\README_CHATGPT_MCP.md
   ```

2. **Terminal Codex runner**
   Use the installed/logged-in Codex CLI runner on this computer.

   Model selection and effort level must follow:

   ```text
   instruction_agentic/model_selection.md
   ```

The manager must record which runner and model policy were used for every task.

---

## 2. Local instruction files are authoritative

Some instructions have been moved into local files. Agents must refer to these files whenever required instead of relying on duplicated prompt text.

Required local instruction files:

```text
C:\Users\balan\IdeaProjects\academic_paper_maker\README_CHATGPT_MCP.md
C:\Users\balan\IdeaProjects\academic_paper_maker\README_GROBID_MCP.md
instruction_agentic/model_selection.md
instruction_agentic/prompt/pdf_reader_prompt.md
writing/latex_writing_rule.md
```

Rules:

```text
1. If a local instruction file exists for a task, the agent must read it before starting that task.
2. The local file is the source of truth for that procedure.
3. Do not duplicate long local instructions in generated prompts unless needed for audit.
4. Record which local instruction files were consulted in the task manifest.
5. If a required local instruction file is missing, mark the task as blocked and report the missing path.
```

---

## 3. Dataset rule

This project uses:

```text
Raja dataset
Murat2018 dataset
```

Do **not** use Hakim or Hakim2029 as a dataset name.

All previous references to Hakim or Hakim2029 must be replaced with:

```text
Murat2018
```

The SQLite table name must be:

```text
murat2018_dataset
```

---

## 4. Proposed multi-agent architecture

| Agent                         | Main responsibility                                                      | Writes files? | Can run in parallel? |
| ----------------------------- | ------------------------------------------------------------------------ | ------------: | -------------------: |
| **Agent Manager**             | Thinks, plans, assigns tasks, checks status, chooses runner/model        |            No |         Controls all |
| **Data Ingestion Agent**      | Converts CSV to SQLite DB; ingests Raja and Murat2018 datasets           |           Yes |                  Yes |
| **PDF/Text Extraction Agent** | Extracts exact abstract/PDF text, page numbers, quotes, and provenance   |           Yes |                  Yes |
| **Study Retrieval Agent**     | Finds relevant studies for introduction and section claims using SQL/FTS |           Yes |                  Yes |
| **Paragraph Structure Agent** | Generates paragraph-level writing plans for each section/subsection      |           Yes |               Partly |
| **Academic Writing Agent**    | Writes LaTeX paragraph files using only cited evidence                   |           Yes |                  Yes |
| **Results Analysis Agent**    | Analyzes Raja and Murat2018 datasets; adds new analysis                  |           Yes |                  Yes |
| **Critical Analysis Agent**   | Interprets results, compares datasets, identifies limits/contradictions  |           Yes |                  Yes |
| **Discussion Agent**          | Writes discussion paragraphs tied to evidence and results                |           Yes |                  Yes |
| **Conclusion Agent**          | Inspects existing conclusion and rewrites it to match paper findings     |           Yes |           No/limited |
| **BibTeX/APA Agent**          | Generates dedicated `.bib` file from DB/CSV metadata                     |           Yes |                  Yes |
| **Validation Agent**          | Checks citations, evidence traceability, LaTeX compile, paragraph rules  |           Yes |                  Yes |
| **Soundness/Flow Agent**      | Checks argument flow, coherence, academic tone, and overclaiming         |           Yes |                  Yes |
| **Resume/State Agent**        | Tracks task state, hashes, retries, and internet-offline continuation    |           Yes |               Always |

Additional experiment agents:

| Agent                                 | Purpose                                                                         |
| ------------------------------------- | ------------------------------------------------------------------------------- |
| **Preliminary Result Registry Agent** | Records old/preliminary outputs before rerunning anything                       |
| **Experiment Rerun Agent**            | Reruns existing code for Raja and Murat2018                                     |
| **Result Diff Agent**                 | Compares rerun results against preliminary results                              |
| **New Analysis Idea Agent**           | Reads supplied PDFs and proposes possible extra analyses                        |
| **Analysis Feasibility Agent**        | Checks whether proposed analysis can be done using Raja/Murat2018 variables     |
| **New Analysis Coding Agent**         | Creates new analysis code only for feasible ideas                               |
| **Experiment Documentation Agent**    | Creates dedicated LaTeX paragraph explaining how to rerun each experiment       |
| **Draft Note Visibility Agent**       | Ensures experiment notes appear only in draft mode and are hidden in final mode |

---

## 5. Rebuilt pipeline

### Phase 0 — Bootstrap

Use the existing project structure. Create missing folders only when required.

```text
project/
  config/
    pipeline.yaml
    models.yaml
    sections.yaml

  data/
    raw/
      csv/
      pdf/
    extracted/
      grobid_mcp/
        tei_xml/
        json/
        text/
        logs/
    db/
      paper_sources.sqlite
    cache/
      model_calls/
      pdf_text/
      sql_exports/

  agents/
    manager/
    ingestion/
    retrieval/
    writing/
    validation/
    analysis/

  writing/
    main.tex
    references.bib
    sections/
    figures/
    tables/

  analysis/
    scripts/
    notebooks/
    outputs/
    new_analysis/

  evidence/
    quotes/
    claims/
    provenance/

  runs/
    tasks.sqlite
    logs/
    manifests/

  tutorial/
    tutorial/40_exp1_epoch_duration.py
    tutorial/41_exp1_exp2_strategy_comparison.py
    tutorial/42_exp4_boundary_tolerance.py
    tutorial/45_exp6_morphological_detailed.py
    tutorial/45_exp7_nmin_sensitivity.py
    tutorial/46_dbo_scan_scale_tuning.py
```

---

## 6. Phase 1 — Convert CSV to SQLite source of truth

The pipeline must **never write from CSV directly** after ingestion.

CSV files remain the raw source, but the working source of truth is:

```text
data/db/paper_sources.sqlite
```

CSV location:

```text
G:\My Drive\iterate_literature_review\complete_file_available_in_zotero.csv
```

Minimum tables:

```sql
studies(
  study_id TEXT PRIMARY KEY,
  title TEXT,
  authors TEXT,
  year INTEGER,
  journal TEXT,
  doi TEXT,
  abstract TEXT,
  source_csv TEXT,
  dataset_name TEXT
);

pdf_text(
  text_id TEXT PRIMARY KEY,
  study_id TEXT,
  page INTEGER,
  section_hint TEXT,
  original_text TEXT,
  extraction_method TEXT,
  source_pdf TEXT
);

references_meta(
  ref_id TEXT PRIMARY KEY,
  study_id TEXT,
  bibtex_key TEXT,
  apa7_text TEXT,
  bibtex_entry TEXT
);

raja_dataset(
  row_id TEXT PRIMARY KEY,
  study_id TEXT,
  variable_name TEXT,
  value TEXT,
  normalized_value TEXT
);

murat2018_dataset(
  row_id TEXT PRIMARY KEY,
  study_id TEXT,
  variable_name TEXT,
  value TEXT,
  normalized_value TEXT
);

claims(
  claim_id TEXT PRIMARY KEY,
  paragraph_id TEXT,
  claim_text TEXT,
  evidence_text_id TEXT,
  study_id TEXT,
  confidence_score REAL
);

paragraphs(
  paragraph_id TEXT PRIMARY KEY,
  section TEXT,
  subsection TEXT,
  paragraph_order INTEGER,
  tex_path TEXT,
  status TEXT,
  word_count INTEGER
);

tasks(
  task_id TEXT PRIMARY KEY,
  agent_name TEXT,
  input_hash TEXT,
  output_hash TEXT,
  status TEXT,
  requires_internet INTEGER,
  runner TEXT,
  model_hint TEXT,
  created_at TEXT,
  updated_at TEXT
);
```

Add SQLite FTS:

```sql
CREATE VIRTUAL TABLE study_fts USING fts5(
  study_id,
  title,
  abstract,
  content='studies',
  content_rowid='rowid'
);

CREATE VIRTUAL TABLE pdf_text_fts USING fts5(
  text_id,
  study_id,
  original_text,
  content='pdf_text',
  content_rowid='rowid'
);
```

---

## 7. PDF/Text Extraction Agent

### Role

```text
PDF/Text Extraction Agent
```

### Responsibility

Extract structured text, abstracts, sections, references, and exact original source text from PDFs using the GROBID MCP workflow.

Before extracting any PDF, the agent must read:

```text
C:\Users\balan\IdeaProjects\academic_paper_maker\README_GROBID_MCP.md
```

The task prompt and manifest example are located at:

```text
instruction_agentic/prompt/pdf_reader_prompt.md
```

### Hard rules

```text
1. Use MCP/GROBID as the primary PDF extraction method.
2. Do not use ad-hoc PDF parsing unless MCP/GROBID fails.
3. If fallback extraction is used, log the failure and record the fallback in extraction_method.
4. Store raw GROBID/MCP output before transforming it into SQLite.
5. Preserve exact original text.
6. Preserve provenance:
   - PDF filename
   - page number if available
   - section heading if available
   - paragraph/order index if available
   - extraction method
   - extraction timestamp
7. Insert extracted text into SQLite, not directly into writing files.
8. Every writing paragraph must cite extracted evidence from the DB or CSV metadata.
```

### Required extraction tables

```sql
CREATE TABLE IF NOT EXISTS pdf_extractions (
  extraction_id TEXT PRIMARY KEY,
  study_id TEXT,
  pdf_path TEXT NOT NULL,
  extraction_method TEXT NOT NULL,
  mcp_tool_name TEXT,
  grobid_output_path TEXT,
  status TEXT NOT NULL,
  error_message TEXT,
  extracted_at TEXT
);
```

```sql
CREATE TABLE IF NOT EXISTS pdf_text_chunks (
  chunk_id TEXT PRIMARY KEY,
  extraction_id TEXT NOT NULL,
  study_id TEXT,
  pdf_path TEXT NOT NULL,
  page_start INTEGER,
  page_end INTEGER,
  section_heading TEXT,
  chunk_order INTEGER,
  chunk_type TEXT,
  original_text TEXT NOT NULL,
  FOREIGN KEY (extraction_id) REFERENCES pdf_extractions(extraction_id)
);
```

Updated PDF extraction pipeline:

```text
PDF/Text Extraction Agent:
  1. Read README_GROBID_MCP.md.
  2. Read instruction_agentic/prompt/pdf_reader_prompt.md.
  3. Use MCP/GROBID as primary extraction method.
  4. Store raw GROBID/MCP output.
  5. Convert structured extraction to SQLite.
  6. Preserve exact original text for paragraph-level evidence.
  7. Allow fallback only after logged MCP/GROBID failure.
```

---

## 8. LaTeX paragraph rule

Every paragraph must live in its own `.tex` file.

A subsection with multiple paragraphs must contain multiple paragraph subfolders.

The full structure is defined in:

```text
writing/latex_writing_rule.md
```

This rule enables easy auditing:

```text
one paragraph
one folder
one evidence trail
```

---

## 9. Evidence and exact original text rule

Every idea used in writing must have an evidence record.

Example `evidence.json`:

```json
{
  "paragraph_id": "intro_01_background_p001",
  "claims": [
    {
      "claim": "The reviewed studies indicate a persistent limitation in prior evaluation methods.",
      "source_type": "abstract",
      "study_id": "raja_014",
      "exact_original_text": "Exact sentence copied from abstract or PDF here.",
      "source_location": {
        "csv_column": "abstract",
        "pdf_page": null
      },
      "bibtex_key": "Raja2024Evaluation"
    }
  ]
}
```

Example `original_quotes.tex`:

```latex
% Exact original text used to support this paragraph.
% Source: Raja2024Evaluation, abstract

\begin{quote}
Exact original text from the abstract or PDF goes here.
\end{quote}
```

The Validation Agent must fail any paragraph that lacks:

```text
paragraph.tex
original_quotes.tex
evidence.json
claims.json
at least one citation
claim-to-source mapping
```

---

## 10. Writing agents by section

### 10.1 Introduction Study Retrieval Agent

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

### 10.2 Paragraph Structure Agent

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

### 10.3 Academic Writing Agent

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

---

## 11. Results Analysis Agent

The Results Analysis Agent must explicitly use:

```text
Raja dataset
Murat2018 dataset
```

Minimum required analyses:

```text
1. Descriptive comparison of Raja vs Murat2018
2. Cross-dataset consistency check
3. Missingness / data-quality analysis
4. Robustness or sensitivity analysis
5. Subgroup or stratified analysis if variables permit
6. Contradiction analysis: where Raja and Murat2018 disagree
```

Outputs:

```text
analysis/scripts/
  01_load_data.py
  02_descriptive_analysis.py
  03_cross_dataset_comparison.py
  04_robustness_analysis.py
  05_extra_analysis.py

analysis/outputs/
  tables/
  figures/
  analysis_summary.md
  result_claims.json
```

The Results Analysis Agent must not directly write the Results section until scripts have produced reproducible outputs.

---

## 12. Critical Analysis Agent

Purpose:

```text
Interpret results critically.
Identify what is supported, what is weak, what contradicts prior studies, and what is uncertain.
```

Outputs:

```text
evidence/result_interpretation/critical_points.json
paper/sections/03_results/paragraph_plan.json
```

---

## 13. Discussion Agent

The Discussion Agent must synthesize:

```text
findings from Raja dataset
findings from Murat2018 dataset
prior studies
limitations
implications
possible explanations
```

It must avoid generic discussion.

Every paragraph should answer:

```text
What did we find?
Why does it matter?
How does it compare to prior studies?
What is the limitation?
What is the implication?
```

---

## 14. Conclusion Agent

The Conclusion Agent must first inspect:

```text
existing conclusion
introduction research gap
results claims
discussion claims
limitations
```

Then rewrite the conclusion so it is tightly connected to the full paper.

Validation rule:

```text
Every conclusion sentence must be traceable to either:
1. a result,
2. a discussion claim,
3. a stated limitation,
4. the original research objective.
```

No new claims may appear in the conclusion.

---

## 15. Extra Analysis Idea Miner Agent

The new analysis must not be created randomly.

The Extra Analysis Idea Miner Agent must:

```text
Read provided PDFs.
Extract analysis ideas.
Map each idea to available variables in Raja and Murat2018.
Reject ideas that cannot be implemented.
Rank ideas by novelty, feasibility, and relevance.
Generate scripts only for feasible analyses.
```

Output example:

```json
{
  "candidate_analysis": [
    {
      "idea": "Cross-dataset robustness check",
      "inspired_by": "study_019",
      "exact_original_text": "Exact PDF text that motivated this idea.",
      "required_variables": ["x", "y", "group"],
      "available_in_raja": true,
      "available_in_murat2018": true,
      "feasibility": "high",
      "recommended": true,
      "script_path": "analysis/scripts/05_cross_dataset_robustness.py"
    }
  ]
}
```

Recommended extra analyses:

```text
1. Cross-dataset replication: test whether the same pattern appears in Raja and Murat2018.
2. Heterogeneity analysis: check whether findings differ by subgroup.
3. Sensitivity analysis: test whether findings change under different filtering rules.
4. Missing-data analysis: report whether missingness could affect interpretation.
5. Contradiction matrix: identify where literature claims and dataset results disagree.
6. Evidence-strength scoring: classify claims as strong, moderate, weak, or speculative.
```

Decision chain:

```text
PDF reading agent extracts idea
↓
exact PDF text is stored
↓
idea is mapped to Raja/Murat2018 variables
↓
feasibility is checked using SQLite schema
↓
manager approves task internally
↓
new analysis code is created
↓
new analysis is run
↓
new result paragraph is written
↓
new rerun-note paragraph is written
```

Each new analysis must have:

```text
analysis/new_analysis/experiment_id/
  idea_source.json
  feasibility_report.md
  run.sh
  analysis.py
  outputs/
  manifest.json
```

Example `idea_source.json`:

```json
{
  "new_analysis_id": "new_001_cross_dataset_robustness",
  "idea": "Compare whether the main pattern is stable across Raja and Murat2018.",
  "inspired_by_pdf": "paper_07.pdf",
  "exact_original_text": "Exact sentence or paragraph from the PDF that inspired the analysis.",
  "required_variables": ["outcome", "group", "method"],
  "available_in_raja": true,
  "available_in_murat2018": true,
  "decision": "implement"
}
```

---

## 16. Parallel execution design

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

---

## 17. Resume when internet turns off

Use a local task database:

```text
runs/tasks.sqlite
```

Each task status must be one of:

```text
pending
running
completed
failed
blocked_offline
needs_review
```

Every task must include:

```text
input_hash
output_hash
runner
model_hint
requires_internet
created files
log path
local instruction files consulted
```

If internet turns off:

```text
1. Continue deterministic local tasks:
   - CSV to SQLite
   - SQL queries
   - local validation
   - LaTeX checks
   - existing cached model output review
   - analysis scripts
   - figure/table generation

2. Queue model-dependent tasks:
   - writing
   - deep reasoning validation
   - discussion synthesis
   - conclusion rewrite

3. Resume automatically when internet returns:
   - only rerun incomplete or stale tasks
   - skip tasks with matching input_hash/output_hash
```

Do not depend on memory of previous agent conversations.

Save every prompt, response, and output:

```text
data/cache/model_calls/
  task_intro_gap_p001/
    prompt.md
    response.md
    parsed_output.json
    model.txt
    timestamp.txt
```

---

## 18. Runner design

The manager chooses between two runners.

### Runner A — ChatGPT API/UI-connected runner

Use for:

```text
academic writing
flow checking
claim validation
discussion synthesis
conclusion rewriting
```

Before use, read:

```text
C:\Users\balan\IdeaProjects\academic_paper_maker\README_CHATGPT_MCP.md
```

### Runner B — Terminal Codex runner

Use for:

```text
code generation
script fixes
deterministic validation
pipeline orchestration
analysis scripts
LaTeX build/debug tasks
```

Model effort must follow:

```text
instruction_agentic/model_selection.md
```

---

## 19. Dedicated APA 7 bibliography

Create:

```text
paper/references.bib
```

Generate it from:

```text
references_meta.bibtex_entry
```

The BibTeX/APA Agent must:

```text
1. Extract title, author, year, journal, DOI from CSV/DB.
2. Normalize missing fields.
3. Create stable citation keys.
4. Remove duplicate references.
5. Save all entries to paper/references.bib.
6. Check every \cite{} key exists.
7. Check every .bib key is used or marked as unused.
```

Recommended LaTeX setup:

```latex
\usepackage[style=apa,backend=biber]{biblatex}
\addbibresource{references.bib}
```

Then at the end:

```latex
\printbibliography
```

---

## 20. Validators

Create deterministic validators first. Do not rely only on LLM judgment.

### Paragraph structure validator

Checks:

```text
Every paragraph has its own folder.
Every paragraph folder has paragraph.tex.
No paragraph.tex contains multiple paragraphs.
Every subsection with multiple paragraphs has p001, p002, etc.
No direct prose exists inside subsection main.tex.
```

### Evidence validator

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

### Writing soundness validator

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

### Analysis validator

Checks:

```text
Raja dataset was loaded.
Murat2018 dataset was loaded.
Every result table/figure is generated from a script.
No manual result table is accepted.
Every reported number appears in analysis outputs.
```

### Conclusion validator

Checks:

```text
No new claims.
Matches research objective.
Matches results.
Matches discussion.
Mentions limitations only if discussed earlier.
```

---

## 21. Suggested coding structure

```text
agents/
  manager/
    manager.py
    task_graph.py
    model_policy.py
    runners.py

  ingestion/
    csv_to_sqlite.py
    pdf_extract.py
    build_fts.py

  retrieval/
    retrieve_studies.py
    retrieve_quotes.py

  writing/
    paragraph_planner.py
    write_paragraph.py
    write_discussion.py
    write_conclusion.py

  analysis/
    analyse_raja.py
    analyse_murat2018.py
    compare_datasets.py
    extra_analysis.py

  validation/
    validate_paragraph_tree.py
    validate_evidence.py
    validate_bib.py
    validate_latex.py
    validate_flow.py

  utils/
    hashing.py
    paths.py
    logging.py
    sql.py
```

Use one command entry point:

```bash
python -m agents.manager.manager run --config config/pipeline.yaml
```

Useful subcommands:

```bash
python -m agents.manager.manager status
python -m agents.manager.manager resume
python -m agents.manager.manager rerun --task TASK_ID
python -m agents.manager.manager validate
python -m agents.manager.manager compile
```

---

## 22. Final recommended agent order

Use this order:

```text
1. Manager creates task graph.
2. Ingestion Agent converts CSV to SQLite.
3. PDF/Text Extraction Agent extracts abstracts/PDF text using GROBID MCP.
4. BibTeX Agent creates references.bib.
5. Retrieval Agent extracts relevant studies.
6. Extra Analysis Idea Miner reads supplied PDFs and proposes analyses.
7. Results Analysis Agent analyzes Raja + Murat2018.
8. Paragraph Structure Agent creates paragraph-level plans.
9. Academic Writing Agent writes introduction/results paragraphs.
10. Critical Analysis Agent strengthens interpretation.
11. Discussion Agent writes discussion.
12. Conclusion Agent rewrites conclusion based on whole paper.
13. Validation Agent checks structure, evidence, citations, and LaTeX.
14. Soundness/Flow Agent checks argument quality.
15. Manager reruns failed tasks only.
16. Build Agent compiles final LaTeX.
```
