# HANDOFF — Blink-Detection Paper (manager + runners) — 2026-06-16

You are the **Manager agent** continuing this EEG eye-blink-detection paper in a FRESH chat.
Read this file first. The previous run's handoff is archived at `HANDOFF_run1_archived.md`.

---

## ROUND 3 (CURRENT) — New agenda, 2026-06-17

**Status of prior work:** The Cao2018 re-run round (§5 below) is **COMPLETE** — see
`runs/reports/MANAGER_CONSOLIDATED_REPORT_NEXT_ROUND.md`. Manuscript = `writing/main.pdf`, 20 pp,
0 undefined cites/refs, datasets Raja (46) + Cao2018 (58) @30 s primary, DBO excluded.
**Run the §0 ChatGPT-UI gate first.** §1 architecture still binds: Manager only plans/routes/inspects;
**ChatGPT UI = all manuscript prose**; **Codex = all code/analysis/LaTeX-mechanics/figures/tables/
validation/file-hygiene**. The Manager extracts real numbers from CSVs and feeds them to ChatGPT
(anti-fabrication). Log EVERY task to `runs/tasks.sqlite`.

Reusable skills now live in the `agent-skillbook` repo (editable-installed) — prefer them:
`write-results-section`, `write-discussion-section`, `literature-review-writing`, `find-extra-analysis`,
`atomise-claims`, `citation-audit`, `telegram-heartbeat`.

### Runner cascade at a glance
| # | Task | Primary runner | Hand-off |
|---|------|----------------|----------|
| R1 | Review archived stubs + implement missing analyses (both datasets) | **Codex** | Manager inspects stubs first |
| R2 | Place/move analysis code into `tutorial/`, sequential naming | **Codex** | Manager verifies provenance |
| R3 | Add 10 s & 20 s epoch-duration experiments | **Codex** (run) → **ChatGPT UI** (prose) | Manager feeds numbers |
| R4 | EEG channel-selection frequency analysis + tables/figures | **Codex** (analysis+viz) → **ChatGPT UI** (narrative) | Manager feeds numbers |
| R5 | Method section rewrite (formal academic structure) | **ChatGPT UI** (prose) | **Codex** verifies dataset facts from files |
| R6 | Result section → one subsection per analysis | **ChatGPT UI** (`write-results-section` skill) → **Codex** (LaTeX scaffolding + compile) | Manager feeds numbers |

---

### R1 — Review existing analysis stubs and implement missing analyses  — **CODEX** (Manager inspects)
- **Manager:** inspect the archived stubs at
  `D:\Research Related\threshold_3_stage\archived_new_analysis_stubs` and the requirements in
  `analysis/new_analysis`. Build a coverage matrix of which analyses exist for **Raja** vs **Cao2018**.
- **Codex:** there is no Python yet for the missing analyses. Implement the missing analyses for BOTH
  datasets where applicable, grounded in the `analysis/new_analysis` requirements. Reuse the existing
  Cao2018 process-parallel runner pattern (`runs/tcao2_full_rerun.py`, `discover_cao_pairs`) and the
  resumable per-session caching. Output result CSVs under `runs/` and a coverage report.
- **Codex:** never fabricate; if a required input is missing, flag it. Use the
  `find-extra-analysis` skill to sanity-check which analyses are worth running for each claim.

### R2 — Python code location and naming convention  — **CODEX**
- All new analysis Python goes under `C:\Users\balan\IdeaProjects\blink_detection_llm\tutorial` with
  sequential, descriptive names: `47_exp_<descriptive_analysis_name>.py`,
  `48_exp_<descriptive_analysis_name>.py`, etc.
- **Codex:** move any Python under `D:\Research Related\threshold_3_stage` (or subfolders) into
  `tutorial/` **iff its output is used in the paper**. Preserve git history where possible; record each
  move (source → destination) in the round report. **Manager** verifies each moved file is actually a
  paper input before approving the move.

### R3 — Additional epoch-duration analysis (10 s and 20 s)  — **CODEX** then **CHATGPT UI**
- **Codex:** extend the epoch-duration sweep to add **10 s** and **20 s** epochs (alongside the existing
  30/40/60 s) for the relevant method(s)/datasets; generate and save result CSVs; recompute the
  epoch-sensitivity table + figure and the Wilcoxon-vs-reference stats so the new durations are included.
- **Manager:** extract the new exact numbers.
- **ChatGPT UI:** update the epoch-duration results paragraph and the discussion epoching paragraph so
  10/20/30/40/60 s are discussed consistently with the rest of the paper (no fabricated numbers).

### R4 — EEG channel-selection analysis  — **CODEX** then **CHATGPT UI**
- **Codex:** analyse which EEG channels are selected most frequently, across **subjects**, **datasets**
  (Raja, Cao2018), and **algorithms** (the 4 visible methods). Determine whether common channels are
  repeatedly selected. Produce clear paper-ready **tables and/or figures** (e.g. selection-frequency
  per channel, per dataset, per method; cross-method/cross-dataset overlap). Save outputs under `runs/`
  and the figures under `writing/e_result/figures/`.
- **Manager:** feed the verified frequencies to the writer.
- **ChatGPT UI:** write the channel-selection results narrative (and any discussion implication),
  referencing the new table(s)/figure(s).

### R5 — Method section revision (formal academic structure)  — **CHATGPT UI** (Codex verifies facts)
- **ChatGPT UI:** rewrite the Method section in conventional academic style with clear subsections:
  **Dataset usage, Preprocessing, Epoch duration, Feature extraction, Model/algorithm configuration,
  Evaluation protocol, Statistical/comparative analysis.**
- **Codex / Manager:** confirm every stated fact (sampling rate, channels, filters, epoch set,
  evaluation metric, datasets) against the actual code/config files before it is written; supply these
  to ChatGPT. Do not let the writer invent setup details.
- **TODO (do NOT invent):** the manuscript has an incomplete sentence
  *"in the method, for the EEG dataset, we only focus ..."*. **Codex/Manager:** try to confirm the
  intended focus from existing project files. If it cannot be confirmed, leave an explicit `% TODO`
  flag in the manuscript / revision notes rather than fabricating the missing detail.

### R6 — Result section revision (one subsection per analysis)  — **CHATGPT UI** + **CODEX**
- **ChatGPT UI:** using the **`write-results-section`** skill, present every analysis in its own
  subsection (main comparison, epoch duration incl. 10/20 s, cross-dataset gap, channel robustness,
  channel-selection frequency, boundary tolerance, etc.), each number sourced from verified artifacts.
- **Codex:** provide the LaTeX subsection scaffolding (`\subsection{...}` + `\input` wiring + table/
  figure placement near the text), then compile (`pdflatex → biber → pdflatex → pdflatex`) and verify
  0 undefined cites/refs and no forbidden terms (DBO/Murat). 

### Definition of done (Round 3)
ChatGPT-UI gate passed; every task logged; R1–R6 each completed or explicitly deferred with a reason;
all new analysis code under `tutorial/` with sequential names; numbers never fabricated; method TODO
either resolved from files or flagged; `writing/main.tex` compiles clean (0 undefined, no DBO/Murat);
update `COMPLETED.md`, `FILE_INVENTORY.md`, and a new
`runs/reports/MANAGER_CONSOLIDATED_REPORT_ROUND3.md`.

---
# Python code
By default, use multithread or multiprocess parallelism (as in `runs/tcao2_full_rerun.py`) for all new analysis code. Avoid single-threaded loops over subjects or datasets. 

# Heartbeat
Use the `telegram-heartbeat` skill to send a Telegram message at the start and end of each long-running Codex task (R1, R3, R4) so you can monitor progress without leaving the terminal.
If fif file is process, must show like tqdm, how many percent left to be done, and ETA. 

## 0. HARD GATE — verify ChatGPT UI works BEFORE doing anything else
Do NOT start any task until the ChatGPT UI Selenium session is confirmed working. Steps:

```bash
# kill Chrome first (the Selenium profile allows one process)
# PowerShell:  Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
PYTHONIOENCODING=utf-8 "C:/Users/balan/anaconda3/Scripts/conda.exe" run -n double_threshold_algo \
  python "C:/Users/balan/IdeaProjects/academic_paper_maker/test_chatgpt_session.py"
```
Expected: an assistant reply (e.g. "SESSION OK" — note the model may render a transient "Thinking"
placeholder first). Procedure: `instruction_agentic/chatgpt_ui/session_test.md`.
**If the session FAILS (login page / timeout), STOP and report — do not continue.** A logged-out
cookie needs a one-time manual login into profile `C:\selenium\chatgpt-profile` (see session_test.md).
If you will mine PDFs again, also confirm GROBID per `session_test_grobid.md` (likely not needed now).

---

## 1. Architecture (BINDING — do not deviate)
- **Manager** only plans / routes / inspects / decides. It must NOT write paper prose, code, or
  LaTeX itself (`instruction_agentic/core_principle/principle.md`).
- **Runners — every task goes to one of these:**
  - **ChatGPT UI** = the ONLY agent allowed to do manuscript WRITE-UP / rewriting (intro, results,
    discussion, abstract, conclusion, citations). This is the specialist writing agent. ALWAYS use it
    for prose.
  - **Codex** (terminal CLI) = code, analysis, LaTeX mechanics, figure generation, validation, audit,
    file hygiene. Reports/audits/reviews are Codex (they are analysis, not manuscript prose).
- **Anti-fabrication rule:** the Manager extracts the real numbers from the result CSVs and embeds
  them in each ChatGPT prompt, so the writing agent only writes prose around given facts. Never let an
  agent invent numbers. Citations must use only keys that exist in the bib.
- Log EVERY task to `runs/tasks.sqlite` via `llm_code_agents/manager/log_task.py`
  (`--id --agent --runner codex|chatgpt --model --requires-internet 0|1 --instruction-files --status --log --created`).

## 2. Environment & known traps
- conda env **`double_threshold_algo`**, full path `C:\Users\balan\anaconda3\Scripts\conda.exe` (conda not on PATH).
- Always `set PYTHONIOENCODING=utf-8`. **Never** run multiline `conda run python -c` (write a `.py`).
- **latexmk is broken** here → compile manually from `writing/`:
  `pdflatex -interaction=nonstopmode main` → `biber main` → `pdflatex` → `pdflatex`.
- ChatGPT Selenium: kill Chrome first; ONE browser is reused (new chat per item). A usage cap appears
  after ~25 sends/session (timeouts / click-intercept) — resume in a fresh session; the orchestrator
  is resumable.
- Codex invocation: `codex exec --cd <repo> -s workspace-write -c approval_policy="never" --skip-git-repo-check - < promptfile`.

## 3. Tooling that already exists — REUSE it (don't rebuild)
- `runs/scripts/write_section_chatgpt.py` — ChatGPT-UI writing agent. Modes:
  `--task write --section result|discussion` (CSV-grounded paragraphs into `pNNN/` folders),
  `--task cite --section discussion|intro` (insert real-key citations, no wording change),
  `--task dbo` (remove DBO from a fixed prose-file list), `--task extra` (new/rewrite specific files).
  Add new plans/file-lists here for new writing batches.
- `instruction_agentic/chatgpt_ui/chatgpt_send_prompt.py` — `make_driver()` + `send_on_driver(driver,
  prompt, out, new_chat=True)`; handles the "Thinking" placeholder + resilient submit (click→JS→Enter).
- `runs/scripts/bib_catalog.py` → `runs/extra_analysis/bib_catalog.txt` (172 key | title) for safe citing.
- `analysis/new_analysis/new_018_result_figures/make_figures.py` — regenerates the 4 result figures
  (its `CONDITIONS` list already excludes DBO).
- `llm_code_agents/ingestion/csv_to_bibtex.py` — regenerates `writing/references_from_csv.bib` from the DB.




### 5.1 Mandatory first gate

Before any task starts, verify that the ChatGPT UI Selenium session works, exactly as described in §0.

If the ChatGPT UI session fails, stop and report. Do not begin Codex or manuscript tasks until the UI writing agent is available.

---

### 5.2 Channel-robustness recomputation over four methods


```

If details such as sampling rate, annotation protocol, preprocessing, or exact citation are missing, flag them instead of inventing them.


### 5.5 Claimed-but-unreported experiment audit

Current issue: the abstract and contribution section may claim analyses that are not actually reported.

**Codex tasks:**

Check whether the following analyses exist in code, result files, tables, figures, and manuscript text:

* boundary tolerance,
* pre-rejection,
* morphology,
* `n_min` sensitivity.

Inspect:

```text
tutorial/40_exp1_epoch_duration.py
tutorial/41_exp1_exp2_strategy_comparison.py
tutorial/42_exp4_boundary_tolerance.py
tutorial/45_exp6_morphological_detailed.py
tutorial/45_exp7_nmin_sensitivity.py
```

Produce a claim-to-evidence matrix:

| Claimed analysis | Where claimed | Code exists? | Results exist? | Manuscript text exists? | Action needed |
| ---------------- | ------------- | ------------ | -------------- | ----------------------- | ------------- |

**Decision rule:**

* If results exist and are reliable, integrate them.
* If results do not exist, remove or soften the claim.
* Do not leave unsupported contribution claims in the abstract, contribution paragraph, Results, or Discussion.

**ChatGPT UI tasks:**

Rewrite the affected manuscript prose after the Manager provides the verified claim-to-evidence matrix.

---

### 5.11 LaTeX code-provenance comments

For reproducibility, every analysis table, figure, and statistical result in LaTeX should have nearby comments explaining which Python script produced it.

**Codex task.**

Add comments near each relevant LaTeX table, figure, or result statement.

Example:

```latex
% Analysis source: tutorial/40_exp1_epoch_duration.py
% Output source: runs/exp40/...
```

If the mapping is uncertain:

```latex
% Analysis source: UNKNOWN - requires manual verification
```

Comments must not appear in the compiled PDF and must not break compilation.

Required output:

* list of LaTeX files updated,
* table/figure/result-to-code mapping,
* unknown mappings requiring manual review.


---

### 5.14 T5 validator pass

Because this round added substantial prose and many citations, rerun the T5 validator pass.

**Codex task.**

Scope:

* Abstract,
* Introduction,
* Related Work,
* Results,
* Discussion,
* tables,
* figures,
* captions,
* newly added citations.

Checks:

1. Soundness and overclaiming:

    * unsupported claims,
    * overstated novelty,
    * unjustified causal wording,
    * claims beyond the experiments.

2. Citation spot-check:

    * each new citation must support the claim where it appears,
    * weak or irrelevant citations must be flagged.

3. Number spot-check:

    * F1 scores,
    * p-values,
    * percentages,
    * rankings,
    * epoch-duration references,
    * table values,
    * figure values.


Required output:

```text
runs/reports/SA_T5_VALIDATOR_NEXT_ROUND.md
```

The report must include:

* soundness and overclaiming issues,
* citation spot-check findings,
* numerical consistency findings,
* claims requiring revision,
* claims requiring stronger citation support,
* recommended edits,
* final validator recommendation.

---


## 6. Definition of done — next round
Tick the `checklist.md` items as they are completed, but do not consider the round complete until all items are either done or explicitly deferred with a reason. The Manager is responsible for verifying each item and marking it as complete or deferred.
