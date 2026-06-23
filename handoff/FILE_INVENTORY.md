# File Inventory — Essential vs Auxiliary

_Generated 2026-06-15 to clarify which files matter for the paper vs scaffolding._

## Round 3 additions (2026-06-17) — ESSENTIAL
| Path | Role |
|---|---|
| `tutorial/47_exp_channel_selection_frequency.py` | R4 channel-selection analysis (→ `runs/exp_channel_selection/`, `tab_channel_selection`, `fig_channel_selection`) |
| `tutorial/48_exp_error_structure_session.py` | 008 error-structure + 009 best/worst session (→ `runs/exp_error_session/`, `tab_error_structure`, `tab_best_session`) |
| `tutorial/49_exp_epoch_figure.py` | R3 epoch figure generator (→ `fig_f1_by_epoch`) |
| `tutorial/50_exp_blink_type_recall.py` | 010 blink-type recall (→ `runs/extra_blink_type/`, `tab_blink_type_recall`) |
| `runs/exp40_cao/exp1_epoch_duration_*.csv` | R3 5-duration sweep results (10/20/30/40/60 s) |
| `runs/exp_channel_selection/*.csv`, `runs/exp_error_session/*.csv`, `runs/extra_blink_type/recall_by_blink_type.csv` | Round-3 result CSVs |
| `writing/e_result/{p003,p004,p006,p007,p009}/paragraph.tex` | Round-3 result paragraphs (ChatGPT-UI) |
| `writing/e_result/tab_channel_selection.tex`, `figures/fig_channel_selection.pdf` | new R4 table+figure |
| `runs/reports/MANAGER_CONSOLIDATED_REPORT_ROUND3.md`, `ROUND3_VERIFIED_NUMBERS.md` | Round-3 report + anti-fabrication number source |


Goal: tell apart **ESSENTIAL** (needed to build/justify the paper), **SUPPORTING**
(tooling/data that produces essentials), and **AUXILIARY** (scratch, stubs, stray
files that can be archived/ignored).

---

## ESSENTIAL — the paper and its verified inputs

| Path | Why essential |
|---|---|
| `writing/main.tex` + `writing/main.pdf` | The manuscript (compiles to **20 pp, 0 undefined cites/refs**; 2026-06-16 Cao2018 round). |
| `writing/a_*` … `writing/g_*` (`b_intro/`, `c_literature_review/p001+p002`, `d_method/`, `e_result/`, `f_discussion/`, `g_conclusion/`) | Section sources actually `\input` by `main.tex`. `c_literature_review/p002` = new ML/DL Related Work paragraph. |
| `writing/references_from_csv.bib` | **Active** bibliography (CSV-backed, 172 entries). |
| `instruction_agentic/main_library.csv` | Source-of-truth library (161 + 11 ingested). |
| `data/db/paper_sources.sqlite` | Ingested studies/text powering bib + feasibility checks. |
| **Integrated result tables** (currently `\input` into `result.tex`): `tab_experiment_code_summary`, **`tab_comparison_30s_epoch`** (renamed from `_60s`), `tab_effect_different_epoch_size`, `tab_cross_dataset_gap`, `tab_channel_robustness`, **`tab_boundary_tolerance`** (re-enabled). | Updated to the raja+cao2018 @30 s numbers (TCAO4/TCAO5). |
| **Disabled tables** (no Cao2018 recompute; commented in `result.tex`): `tab_blink_type_recall`, `tab_error_structure`, `tab_best_session` | Await a Cao2018 recompute; kept as source. |
| **NEW result CSVs (source of truth for current numbers)**: `runs/exp41_cao_30s/`, `runs/exp40_cao/`, `runs/exp42_cao_30s/`; stats `runs/reports/TCAO4_stats.json` + `TCAO4_derived_stats.md` | Provenance for every number in the current manuscript — **do not delete**. |
| `proof_extraction/` (introduction + discussion + SUMMARY) | Atomic-claim/proof QA artifact (TCAO9). |
| `analysis/new_analysis/new_007, 008, 009, 010, 016` | Extra-analysis dirs (legacy provenance). |
| `src/` (pyblinker + evaluation) | Code that produces the experiment numbers. |
| Legacy result CSVs (60 s / murat2018 era — superseded, kept for history): `runs/exp40/…`, `runs/exp41_full/…`, `runs/exp42*/…`, `runs/exp45_exp6/…`, `runs/exp46/…`, `runs/extra_blink_type/…` | Superseded by the `*_cao_30s` / `*_cao` dirs; **do not delete** (history). |
| `runs/tcao2_full_rerun.py`, `runs/progress_probe.py`, `tutorial/tutorial_utils.py::discover_cao_pairs` | Cao2018 process-parallel runner + progress probe + loader. |
| `telegram_heartbeat.py` (+ `bot_telegram.md` git-ignored) | Agent heartbeat/notifier (token secret). |

## SUPPORTING — tooling that builds the essentials (keep, not in paper)

| Path | Role |
|---|---|
| `llm_code_agents/ingestion/csv_to_bibtex.py` | Generates the active bib from the DB. |
| `runs/scripts/ingest_missing_refs.py` | Ingested the 11 DOI-verified refs. |
| `llm_code_agents/manager/log_task.py`, `runs/tasks.sqlite` | Task manifests (manager architecture). |
| `instruction_agentic/chatgpt_ui/*.py` | GROBID extract + prompt build + ChatGPT sender (mining). |
| `runs/scripts/mine_pdfs_one_by_one.py`, `compile_proposals.py`, `list_pdfs.py` | Mining + proposal pipeline. |
| `runs/extra_analysis/per_pdf/<sid>/` | Per-paper idea JSON + send-proof (Definition-of-Done evidence). |
| `analysis/new_analysis/new_007/008/009/016/` | The 4 extra analyses that actually produced `outputs/`. |
| `HANDOFF.md`, `instr.md`, `instruction_agentic/` rules | The binding plan + agent rules. |

## ARCHIVED — moved out of the repo (2026-06-16, NOT deleted)

Moved to **`D:\Research Related\threshold_3_stage\`** (see its `HANDOFF_RESTART.md`):

| Item | New location |
|---|---|
| 12 empty stub `new_analysis` dirs (new_001–006, 011–015, 017 — no `outputs/`, no `manifest.json`, never run) | `…\archived_new_analysis_stubs\` |
| `AbhijitBhattacharyy2023.pdf` (was at repo root) | `…\stray\` |

To restore any item, move its folder back under `analysis/new_analysis/`.

## AUXILIARY — scratch still in repo (safe to ignore)

| Path | Why auxiliary |
|---|---|
| `HANDOFF_PROMPT.md`, `instr_quickcheck_findings.md` | Working notes, not part of the deliverable. |
| `runs/exp41_smoke/`, `runs/exp42_30s/` | Smoke/auxiliary experiment variants superseded by `exp41_full` / `exp42` (kept — still experiment output). |
| `runs/extra_analysis/*.RAW_NO_JSON.txt`, `*/error.txt`, `mine_resume*_stdout.log` | Mining scratch/retry artifacts. |
| `find_blink_epoch_worktree.iml` | IDE project file. |

_Note: the 4 previously-"orphaned" tables are now classified ESSENTIAL (experiment-generated,
kept as reference) per the source-of-truth rule, not archived._

See `COMPLETED.md` for status against the Definition of Done.
