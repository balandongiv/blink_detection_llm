# Completed Work — Blink-Detection Paper Pipeline

_Last updated: 2026-06-15 (live; mining still running in background)_

This file tracks what is **done** against HANDOFF.md §4 Definition of Done.
Status legend: ✅ done · 🔄 in progress · ⏳ queued.

## 2026-06-17 — Round 3 (compute-first: R3 epochs, R4 channels, re-enabled extras) (latest)
Full report: `runs/reports/MANAGER_CONSOLIDATED_REPORT_ROUND3.md`. Verified numbers:
`runs/reports/ROUND3_VERIFIED_NUMBERS.md`.
- ✅ **R3 epoch sweep** extended to 10/20/30/40/60 s (Manager-run parallel compute; Codex fixed runner +
  regenerated table/figure/Wilcoxon). No duration differs significantly from 30 s (Bonferroni α=0.0125).
- ✅ **R4 channel-selection frequency** — frontal dominance (Raja E9/E22; Cao2018 FP1/FP2); new subsection,
  `tab_channel_selection` + `fig_channel_selection`; `tutorial/47`.
- ✅ **008 error-structure** + **009 best/worst session** recomputed on Raja+Cao2018, Murat removed; `tutorial/48`.
- ✅ **010 blink-type recall** recomputed (81,852 normal / 7,377 long; no DBO); `tutorial/50`.
- ✅ All 5 result paragraphs written via ChatGPT-UI with Manager-verified numbers (p003/p009/p006/p007/p004),
  wired into `result.tex` by Codex. Compile: **22 pp, 0 undefined, 0 forbidden terms**.
- ✅ Follow-on (same day): **all checklist.md items A–J ticked**. Method rewritten (F, 6 subsections),
  Result restructured (G), Discussion extended (H/E, p003+p005), citation audit JSON (I, 163 claims),
  D:\ figure generator moved into `tutorial/51` (B), final QC PASS (J): **23 pp, 0 undefined, 0 forbidden**;
  removed a stray "Pending refresh" draft note from the PDF.
- Optional only (not a checklist item): archiving unused `analysis/new_analysis` stub dirs.
- ⚠ Data-quality flags: Cao2018 `S01/060227n` MNE-annot `best_channel="vehicle position"` (1/232).

## 2026-06-16 — Cao2018 re-run + HANDOFF §5 completion round

> Datasets re-based **Murat2018 → Cao2018**, primary epoch **60 s → 30 s** (user decisions).
> exp41/40/42 re-run on **Raja (46) + Cao2018 (58)**, 4 visible methods, DBO excluded, run
> process-parallel (~19/24 cores, CPU ~98%). `writing/main.pdf` = **20 pages, 0 undefined
> citations/references, 0 visible DBO/Murat/pre-rejection/n_min**.
> Central result unchanged: **Proposed-Med best**, pooled macro-$F_1$ **0.867**, significant over all
> three other conditions (Wilcoxon, Bonferroni = C(4,2)=6).

HANDOFF §5 items: ✅ 5.2 channel-robustness (4-method) · ✅ 5.2/5.3 four-condition stats + Bonferroni=6 +
Table 3 @30 s ref · ✅ 5.4 Murat→Cao2018 swap + dataset labels · ✅ 5.5 unsupported claims removed
(pre-rejection, n_min), boundary integrated, morphology softened · ✅ 5.6 abstract/novelty/causal
softened, 30 s primary · ✅ 5.7 thresholding justification · ✅ 5.8 epoching + limitations · ✅ 5.9
results expanded (cross-dataset gap now Cao2018>Raja) · ✅ 5.10/5.11 tables near text + provenance
comments · ✅ 5.12 atomic-claim/proof extraction (`proof_extraction/`; 5 unsupported softened) · ✅ 5.13
Related Work expanded (ML/DL paragraph, 10 verified cites) · ✅ 5.14 T5 validator (minor fixes applied) ·
✅ 5.15 DBO check (rendered grep clean).
Source of truth: `runs/reports/TCAO4_stats.json`. Consolidated report:
`runs/reports/MANAGER_CONSOLIDATED_REPORT_NEXT_ROUND.md`.
Deferred (essential-scope): blink-type/error-structure/best-session tables + morphology figure
(left disabled, see consolidated report §2/§13).

---


## Definition-of-Done checklist

| # | Item | Status |
|---|------|--------|
| 1 | Both session tests pass (GROBID + ChatGPT UI) | ✅ |
| 2 | `references.bib` regenerated from `main_library.csv`; paper re-cited with CSV-backed keys; **0 undefined citations** | ✅ |
| 3 | Every PDF processed one-by-one (GROBID + ChatGPT UI) with send-proof | ✅ 72/72 |
| 4 | Proposals compiled, feasibility-checked, feasible ones coded **and run** | ✅ 6 integrated |
| 5 | Each task routed through correct runner/model, logged in `runs/tasks.sqlite` | ✅ |
| 6 | `main.tex` compiles clean; new results integrated; no fabricated numbers | ✅ 20pp |
| 7 | Validators run | ✅ all PASS |

> **All Definition-of-Done items met** as of 2026-06-15 21:02. `writing/main.pdf` = 20 pages,
> 0 undefined citations/references. Validation report: `runs/reports/T5_validation.md`.

## 2026-06-16 — restructure + write-up round (ChatGPT UI)

- **Archived** 12 empty `new_analysis` stubs + stray root PDF to `D:\Research Related\threshold_3_stage\`
  (with `HANDOFF_RESTART.md`); experiment-generated tables kept in repo as source of truth.
  `FILE_INVENTORY.md` recataloged.
- **Result section** rewritten via ChatGPT UI into per-paragraph folders `e_result/p001–p008/`
  (incl. write-ups for the extra analyses: error-structure, best/worst session, channel robustness).
  **4 statistical bar charts** added (`e_result/figures/`, generated from exp CSVs) and embedded.
- **Discussion** written via ChatGPT UI into `f_discussion/p001–p006/`; a citation pass added 10
  `\citep` calls using only real CSV-backed peer-reviewed keys (numbers preserved).
- **Intro** citation pass: each claim-sentence now carries a citation (all keys verified in the
  172-entry bib); stray non-comment "theme:" lines removed.
- All paragraph prose grounded in CSV-verified numbers supplied by the manager (no fabrication).
- Final compile: **23 pages, 0 undefined citations/references**.

## Completed in detail

### Infrastructure / gates
- ✅ **GROBID session test** — container `academic_paper_maker_grobid` on :8070 returns 200.
- ✅ **ChatGPT Selenium session test** — profile `C:\selenium\chatgpt-profile` sends + receives.
- ✅ **Sender hardened** (`instruction_agentic/chatgpt_ui/chatgpt_send_prompt.py`):
  - Ignores transient "Thinking"/"Reasoning" placeholders (was being captured as the reply).
  - Waits out streaming via the stop-button check.
  - Refactored to `make_driver()` + `send_on_driver(new_chat=True)` so **one browser is reused**
    across all papers (new chat per paper) instead of relaunching Chrome each time.

### Citations (T1) — DONE
- ✅ `writing/references_from_csv.bib` regenerated from the CSV-backed `studies` table.
- ✅ **11 genuinely-missing, DOI-verified references ingested** into `data/db/paper_sources.sqlite`
  **and** `instruction_agentic/main_library.csv` (croft2000removal, klein2013reliable,
  kleifges2017blinker/BLINKER, guttmann2019new, tran2021detection, wang2025sliding,
  alyan2023blink, cao2019multichannel, kaya2018large, saito2015precision, salles2024softed).
- ✅ Bib now **172 entries**; all **18** manuscript cite keys resolve.
- ✅ `main.log` and `main.blg`: **0 undefined citations**. PDF builds at **18 pages**.

### Experiments already reproduced (prior runs, verified present)
- ✅ Strategy comparison (5 conditions) — `runs/exp41_full/exp41_strategy_comparison_results.csv`.
- ✅ Epoch-duration sweep — `runs/exp40/exp1_epoch_duration_results.csv`.
- ✅ Boundary-tolerance sweep — `runs/exp42*/exp42_boundary_tolerance_results.csv`.
- ✅ DBO scan-scale tuning — `runs/exp46/exp46_scan_scale_results.csv`.
- ✅ Morphological event counts — `runs/exp45_exp6/exp45_morphological_event_counts.csv`.
- ✅ Blink-type recall — `runs/extra_blink_type/recall_by_blink_type.csv`.

### Extra analyses (status)
- ✅ Computed **and integrated** into the paper (6):
  - `tab_cross_dataset_gap` (← new_007), `tab_blink_type_recall`,
    `tab_effect_different_epoch_size`, `tab_comparison_60s_epoch`, `tab_experiment_code_summary`,
    and the newly wired `tab_error_structure` (← new_008), `tab_best_session` (← new_009),
    `tab_channel_robustness` (← new_016) with grounded result paragraphs + Task W narrative.
- ⏳ **Stub only (no outputs)** — 13 dirs new_001–006, 010–015, 017 (scaffold, not run);
  their idea families are already covered by the integrated analyses (see `FILE_INVENTORY.md`).
- ⏳ Tables present but **orphaned** (no `\input` anywhere): `tab_boundary_tolerance`,
  `tab_dbo_scan_scale_tuning`, `tab_failure_analysis`, `tab_strategy_by_dataset` — candidates to drop.

### Idea mining (T3) — DONE
- ✅ One-by-one GROBID→ChatGPT mining: **72/72 papers, 0 failures**, each with per-paper send-proof in
  `runs/extra_analysis/per_pdf/<sid>/` (`response.md`, `chatgpt_user_echo.txt`, `chatgpt_proof.png`).
- ✅ Proposals compiled → `runs/extra_analysis/compiled_proposals.md` (298 candidates).

## Remaining
- **None for the Definition of Done** — all 7 items complete.
- Optional cleanup (see `FILE_INVENTORY.md`): archive the 13 stub `new_analysis` dirs, resolve the
  4 orphaned tables, move the stray root PDF. Left for user approval (no deletions performed).
