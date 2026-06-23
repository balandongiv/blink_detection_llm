# HANDOFF — Next Run Instructions

**Author:** previous agent run (2026-06-15)
**Read this together with:** `instr.md`, `instruction_agentic/CODING_LESSONS_LEARNED.md`,
`instruction_agentic/core_principle/principle.md`, `instruction_agentic/core_principle/proposed_agent.md`.

This handoff is **binding**. Do the steps in order. Do not skip the gated
pre-checks. Do not fabricate any numbers — every reported value must come from an
actual run output file.

---

## 0. Preconditions (HARD GATE — do first, every run)

Both session tests MUST pass before any other work, under conda env
`double_threshold_algo` (full path `C:\Users\balan\anaconda3\Scripts\conda.exe`):

1. ChatGPT UI session — `instruction_agentic/chatgpt_ui/session_test.md`
   (kill Chrome first: `Stop-Process -Name chrome -Force`).
2. GROBID API — `instruction_agentic/chatgpt_ui/session_test_grobid.md`
   (`docker start academic_paper_maker_grobid`, expect `200 true`).

If either fails, STOP and report. Do not proceed.

---

## 1. CRITICAL gaps from the last run (fix these)

### 1a. Citations are NOT sourced from the CSV  ← REQUIRED FIX
The paper currently cites `writing/references.bib`, which has only **21
hand-curated entries**. The real library is **`instruction_agentic/main_library.csv`
(161 studies)**, already ingested into `data/db/paper_sources.sqlite`.

**You MUST regenerate the bibliography from the CSV** (instr.md §19, BibTeX/APA
Agent, `instruction_agentic/rule/apa_style.md`):
- Build a BibTeX entry for every CSV row that is cited, using the columns
  `Author`, `Publication Year`, `Title`, `Publication Title`, `DOI`, `ISSN`,
  `Url`. Generate a stable cite key (e.g. `firstauthorYEAR`).
- Write `writing/references.bib` (or `references_csv.bib`) from the CSV — do NOT
  keep hand-typing keys.
- Re-cite the paper (intro, related work, method, discussion) with CSV-derived
  keys. Every `\citep{...}` must resolve to a CSV-backed entry, and every claim
  that needs evidence must cite the CSV study that supports it
  (`instruction_agentic/rule/evidence_original_text.md`).
- Verify: `latexmk -pdf` then check `main.log` has **0 undefined citations**.

**Introduction specifically (instr.md §22):** the introduction IS developed
(`writing/b_intro/p001–p006/paragraph.tex`, six paragraphs) but **lacks proper
references**. The last run added only a few `\citep` keys from the 21-entry
hand-made bib; that is not enough and not CSV-backed. This run you MUST:
- Use the **Study Retrieval Agent** to find, for each introduction paragraph, the
  CSV studies (`paper_sources.sqlite` / `study_fts`) that support its claims.
- Add CSV-backed citations to every claim in `b_intro/p001–p006` (and the
  related-work / method / discussion sections) with an evidence record
  (`instruction_agentic/rule/evidence_original_text.md`).
- The introduction is the highest-priority section for citation coverage — do not
  leave any factual claim uncited.

### 1b. The instr.md agent architecture was NOT used  ← REQUIRED FIX
Last run, one agent did everything directly. instr.md (§4, §18) and
`proposed_agent.md` define a **manager + runners** architecture that must be used:
- The **Manager** only plans/routes/inspects/decides — it must NOT write paper
  text/code/LaTeX itself (`core_principle/principle.md`).
- Route each task to the correct **runner** (`instruction_agentic/rule/runner_design.md`):
  **Codex (terminal)** for code/analysis/LaTeX/validation; **ChatGPT UI** for
  academic writing/discussion/conclusion/idea-mining.
- Pick the **model tier** per `instruction_agentic/model_selection.md` (default
  low, escalate on failure).
- Record a **manifest per task** (runner, model_hint, input/output hash,
  instruction files consulted) in `runs/tasks.sqlite`
  (`instruction_agentic/resume/resume_rule.md`).
- Agents defined but not exercised last run — USE them this run: Study Retrieval,
  Paragraph Structure, Academic Writing (for citations), BibTeX/APA, Validation,
  Soundness/Flow, and the experiment sub-agents (Preliminary Result Registry,
  Experiment Rerun, Result Diff, New Analysis Idea, Analysis Feasibility, New
  Analysis Coding, Experiment Documentation).

The DAG scaffolding already exists: `llm_code_agents/manager/manager.py`
(`run | status | validate | graph | sweep`), `config/pipeline.yaml`.

---

## 2. MANDATORY workflow — PDF → ChatGPT UI, ONE BY ONE

The last run batched all abstracts into a single ChatGPT prompt. This run you
MUST process **each PDF individually** through GROBID and the ChatGPT UI, then
compile all proposals and write code. Concretely:

For **every** PDF in `main_library.csv` `File Attachments` (paths like
`D:\zoterodb\*.pdf`; 73 exist, query the DB for the list):

1. **GROBID-extract that one PDF** to TEI + text (esp. the **Results / Experiment
   section**, which is the richest source of analysis ideas):
   `instruction_agentic/chatgpt_ui/extract_grobid_fulltext.py --pdf <path>`
   (Results-only: `extract_grobid_results.py`).
2. **Forward that single paper to the ChatGPT UI** and ask for extra-analysis
   ideas mapped to our Raja/Murat variables, in the required JSON schema
   (`instruction_agentic/rule/extra_analysis_agent.md`):
   `instruction_agentic/chatgpt_ui/chatgpt_send_prompt.py --prompt-file <one_paper_prompt> --out-file runs/extra_analysis/per_pdf/<study_id>.json`
   - The sender is instrumented and MUST verify the send (reads the composer
     back, requires a NEW assistant turn, saves a screenshot). If the composer is
     empty it aborts — do not accept a reply without this proof. Kill Chrome
     before each send.
3. **Save the per-paper proposal** under `runs/extra_analysis/per_pdf/`.

After all PDFs are processed:
4. **Compile all proposals**: dedupe, validate each `inspired_by` study_id against
   the DB, map required variables to what Raja/Murat actually provide, run the
   **Analysis Feasibility Agent**, and rank.
5. **Write the code** for every feasible analysis under
   `analysis/new_analysis/<id>/` (idea_source.json, feasibility_report.md, run.sh,
   analysis.py, outputs/, manifest.json — exact structure in
   `extra_analysis_agent.md`). **Run** each, then write a result paragraph + a
   rerun-note paragraph into the LaTeX.

Available per-session variables for feasibility: dataset, condition, tp/fp/fn,
precision/recall/f1, macro/micro, epoch_duration_s, IoU, n_flagged (Stage-A),
theta_c (Stage-B), best_channel, frontal EEG channels, GT blink onset/duration/
label, per-epoch peak-to-peak amplitude, pre-rejection withholding rate.

---

## 3. State already established (do NOT redo blindly; verify, then build on)

- **Experiments reproduce EXACTLY** (deterministic, `random_state=42`): exp41 main
  comparison, exp40 epoch-duration, exp42 boundary-tolerance (run at
  `--epoch-duration-s 30`), exp46 DBO-scan. Outputs in `runs/exp41_full`, etc.
- **Paper** `writing/main.tex` compiles to 18pp (latexmk + biber, MiKTeX). Nested
  `\input` paths already fixed; conclusion written; Experiments 8 (cross-dataset
  gap) and 9 (blink type) + supplementary (best subject, channel robustness)
  added.
- **Extra analyses already run**: new_007 cross-dataset gap, new_008 error
  decomposition, new_009 best subject, new_010 blink-type recall, new_016 channel
  robustness. Ideas new_011–new_017 mined but NOT yet implemented (need per-blink
  amplitude / per-window data → new detection runs).
- **Datasets**: `D:\dataset\...` (Raja + Murat2018). PDFs: `D:\zoterodb\*.pdf`.

---

## 4. Definition of done

- [ ] Both session tests pass.
- [ ] `references.bib` regenerated from `main_library.csv`; paper re-cited with
      CSV-backed keys; `main.log` shows 0 undefined citations.
- [ ] Every PDF processed one-by-one through GROBID + ChatGPT UI; per-paper
      proposals saved with send-proof.
- [ ] Proposals compiled, feasibility-checked, feasible ones coded AND run.
- [ ] Each task routed through the correct runner/model and logged in
      `runs/tasks.sqlite` (manager architecture actually used).
- [ ] `writing/main.tex` compiles clean; new results integrated; no fabricated
      numbers.
- [ ] Validators run (`instruction_agentic/rule/validator.md`).
