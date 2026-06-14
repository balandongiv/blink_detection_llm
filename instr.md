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
    40_exp1_epoch_duration.py
    41_exp1_exp2_strategy_comparison.py
    42_exp4_boundary_tolerance.py
    45_exp6_morphological_detailed.py
    45_exp7_nmin_sensitivity.py
    46_dbo_scan_scale_tuning.py
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

### Hard rules and Output

The hard rule and required extraction tables as describe in `instruction_agentic/rule/GROBID.md` must be followed strictly.

---

## 8. LaTeX paragraph rule

Every paragraph must live in its own `.tex` file.

A subsection with multiple paragraphs must contain multiple paragraph subfolders.

The full structure is defined in `instruction_agentic/rule/latex_writing_rule.md`



This rule enables easy auditing:

```text
one paragraph
one folder
one evidence trail
```

---

## 9. Evidence and exact original text rule

Every idea used in writing must have an evidence record.
as explain in `instruction_agentic/rule/evidence_original_text.md`


---

## 10. Writing agents by section

The writing agents must follow the rules in `instruction_agentic/rule/writing_agents_by_section.md`.

---

## 11. Results Analysis Agent

The Results Analysis Agent must analyze both Raja and Murat2018 datasets. The rules for this agent are in `instruction_agentic/rule/results_analysis_agent.md`.
---

## 12. Critical Analysis Agent

The Critical Analysis Agent must interpret the results, compare the two datasets, and identify limitations and contradictions. It must write a structured interpretation that can be used by the Discussion Agent. The rules for this agent are in `instruction_agentic/rule/critical_analysis_agent.md`.
---

## 13. Discussion Agent

The rule for discussion agent is in `instruction_agentic/rule/discussion_agent.md`.

---

## 14. Conclusion Agent

The rule for conclusion agent is in `instruction_agentic/rule/conclusion_agent.md`
---

## 15. Extra Analysis Idea Miner Agent

The rule for the extra analysis idea miner agent is in `instruction_agentic/rule/extra_analysis_idea_miner.md`.
---

## 16. Parallel execution design
The manager should refer to `instruction_agentic/rule/parallel_execution.md` for the design of which tasks can run in parallel and which must run sequentially. The manager must enforce these rules when scheduling tasks and assigning runners.


---

## 17. Resume when internet turns off

The manager must track which tasks require internet and which runner/model they used. If the internet connection is lost, the manager should pause all tasks that require internet and allow tasks that do not require internet to continue running. Once the internet connection is restored, the manager should automatically resume paused tasks. The rules for this behavior are in `instruction_agentic/rule/resume_rule.md`.


---

## 18. Runner design
The manager should choose between two runners based on the task type. The rules for runner selection and task assignment are in `instruction_agentic/rule/runner_design.md`. The manager must ensure that tasks are sent to the appropriate runner and that the model effort level follows the guidelines in `instruction_agentic/model_selection.md`.

---

## 19. Dedicated APA 7 bibliography
This is an acedemic paper, and the bibliography must be in APA 7 format. The rules for this agent are in `instruction_agentic/rule/bibtex_apa_agent.md`.

---

## 20. Validators

Create deterministic validators first. Do not rely only on LLM judgment.
The rules for validation agents are in `instruction_agentic/rule/validation_agents.md`. The manager must ensure that validation tasks are scheduled and that their results are used to inform any necessary reruns or revisions.

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
