# Kickoff prompt for the next run

Paste everything below the line into a fresh agent session in this repo
(`C:\Users\balan\IdeaProjects\blink_detection_llm`).

---

You are continuing a multi-session effort to produce a complete academic paper on
EEG eye-blink detection. A previous run left a binding handoff. Do this:

1. **Read these first, in order, and treat them as authoritative:**
   - `HANDOFF.md` (the binding plan — follow it exactly)
   - `instruction_agentic/CODING_LESSONS_LEARNED.md` (avoid re-hitting known traps)
   - `instr.md`, `instruction_agentic/core_principle/principle.md`,
     `instruction_agentic/core_principle/proposed_agent.md`

2. **Honor the hard gate.** Do nothing else until BOTH session tests pass under
   conda env `double_threshold_algo` (use full path
   `C:\Users\balan\anaconda3\Scripts\conda.exe`):
   - ChatGPT UI — `instruction_agentic/chatgpt_ui/session_test.md` (kill Chrome first)
   - GROBID — `instruction_agentic/chatgpt_ui/session_test_grobid.md` (expect `200 true`)
   If either fails, STOP and report.

3. **Then execute HANDOFF.md in order.** The priorities are:
   - **(§1a) Citations from the CSV.** The paper cites a 21-entry hand-made
     `references.bib`; the real library is `instruction_agentic/main_library.csv`
     (161 studies). Regenerate the bib from the CSV
     (`llm_code_agents/ingestion/csv_to_bibtex.py` already emits
     `writing/references_from_csv.bib`) and **re-cite the paper with CSV-backed
     keys**. The **introduction** (`writing/b_intro/p001–p006`) is developed but
     **lacks proper references** — cite every claim using the Study Retrieval
     Agent against the CSV; it is the highest-priority section.
   - **(§1b) Use the agent architecture.** Do NOT do everything inline. Act as the
     Manager: route each task to the correct runner (Codex for code/analysis/
     LaTeX/validation; ChatGPT UI for writing/idea-mining) per
     `instruction_agentic/rule/runner_design.md` and `model_selection.md`, and log
     a manifest per task in `runs/tasks.sqlite`.
   - **(§2) PDFs one-by-one.** For EVERY PDF in `main_library.csv` File
     Attachments (`D:\zoterodb\*.pdf`): GROBID-extract it (esp. the Results
     section), forward that single paper to the **ChatGPT UI**
     (`chatgpt_send_prompt.py`, which verifies the send with composer readback +
     new-turn check + screenshot — never accept an unverified reply), save the
     per-paper proposal. After all PDFs: compile + dedupe + feasibility-check all
     proposals, then **write and run** the code for feasible ones under
     `analysis/new_analysis/<id>/`, and integrate results into the LaTeX.

4. **Rules that override default behavior:**
   - Never fabricate numbers — every table value traces to a real run output.
   - Everything runs under `double_threshold_algo`; never use `conda run python -c`
     with multiline code (write a `.py` file); set `PYTHONIOENCODING=utf-8`.
   - Verify against current code before asserting (the handoff is point-in-time).
   - Finish only when HANDOFF.md §4 "Definition of done" is fully checked and
     `writing/main.tex` compiles with 0 undefined citations/references.

Start by reading `HANDOFF.md`, then run the two session tests, then report your
plan before executing.
