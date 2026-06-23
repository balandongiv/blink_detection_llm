## 1. Core principle

Refer to `instruction_agentic/core_principle/principle.md` for the core principle of this project. All agents and tasks must align with this principle. The manager must ensure that all task prompts and instructions reflect this principle and that any deviations are flagged for review.

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

## 3. Algorithm and Dataset 
This paper develop an algorithm to detect eye blinks in EEG data. The example of the algorithm is as demonstrated in `tutorial/10d_strategy_autoreject_drop_threshold.py`.

This paper validate the proposed method with the dataset from Raja and Murat2018.
We also compare the proposed method against several existing technique as demonstrated in `tutorial/41_exp1_exp2_strategy_comparison.py`

The code has been developed in a way that allows easy rerunning of the existing code and comparison of results. The manager should ensure that the Experiment Rerun Agent and Result Diff Agent are used to verify that reruns produce consistent results before making any changes to the code or analysis.

Once we confirm that reruns are consistent, we can use the Extra Analysis Idea Miner Agent to propose additional analyses based on the supplied PDFs. The manager should ensure that any proposed analyses are checked for feasibility using the Analysis Feasibility Agent before proceeding with coding and running new analyses.



## 4. Proposed multi-agent architecture

The are several agents that will be responsible for different tasks in the pipeline. The manager will orchestrate these agents, ensuring that they follow the defined rules and that their outputs are properly integrated into the overall workflow. The list of agents includes as explain in `instruction_agentic/core_principle/proposed_agent.md`
---

## 5. Existing Analysis

There are several python code that has been developed to perform the analysis. These code are located in `tutorial/` and `analysis/scripts/`. The manager should ensure that these existing scripts are used as a starting point for the analysis agents and that any new code is integrated with the existing codebase. The manager should also ensure that the Experiment Rerun Agent is used to verify that rerunning existing scripts produces consistent results before making any changes.

The existing code includes:

```text
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

The Data Ingestion Agent must convert the csv a SQLite database. The SQLite DB will be the source of truth for all data retrieval and analysis tasks. The agent must create appropriate tables, indexes, and full-text search capabilities to enable efficient querying by the Retrieval Agent. The rules for this agent are in `instruction_agentic/rule/csv_to_sqlite.md`.

The csv files are in `instruction_agentic/main_library.csv`


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
The path to the `.pdf` file also available in the `instruction_agentic/main_library.csv` under the column `File Attachments`.
However, if the pdf file is not available, just read the paper abstract which is available in the column `Abstract Note`


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
llm_code_agents/
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

## 22. Special Rule for the Introduction section

The latex write up for the introduction section is well draft but does not have any citations. The manager should use the `Retrieval Agent` to extract relevant studies and quotes from the SQLite database and the extracted PDF text. The `Paragraph Structure Agent` should then create paragraph plans that incorporate these studies, and the `Academic Writing Agent` should write the introduction paragraphs with proper citations and evidence. The manager must ensure that the retrieved studies are relevant and that the introduction effectively sets up the research gap and motivation for the paper.
The introduction section is as in
`writing/b_intro`
The path to the `.pdf` file also available in the `instruction_agentic/main_library.csv` under the column `File Attachments`.
However, if the pdf file is not available, just read the paper abstract which is available in the column `Abstract Note`


### Final recommended agent order

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
