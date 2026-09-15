# archive/

Historical, non-code artifacts moved out of the repo root on 2026-09-14 to reduce clutter,
as part of the manuscript result-pipeline audit (see `reports/final_cleanup_summary.md`).
Nothing here was deleted; everything is moved with its git history intact (the `.md` files
via `git mv`) or as a plain filesystem move (the `.log` files, which were never git-tracked
to begin with).

## `archive/logs/`

Run logs from earlier experiment re-runs and the Telegram progress-reporting daemon
(`exp1_{cao,raja}_full_rerun*.log`, `exp1_raja_rerun2_e83.log`, `telegram_daemon.log`,
`telegram_heartbeat.log`). Dated 2026-06-17 and 2026-09-07 — informational run history, not
referenced by any script's runtime behavior (confirmed by grep before moving).

## `archive/handoff_docs/`

Planning, handoff, and lessons-learned documents from earlier phases of this project, all
dated between 2026-05-25 and 2026-07-22 — predating the manuscript's later restructuring
into the current `writing/a_abstract`-`g_conclusion` modular layout and the `publication_results/`
result set. Not linked from `README.md`, i.e. not treated as current documentation even
before this move:

- `HANDOFF.md`, `HANDOFF_round2_additional_analysis.md`, `HANDOFF_std30_academic_writing.md`
- `BENCHMARK_GROUND_TRUTH.md`, `CODEX_IMPROVEMENT_SUGGESTIONS.md`, `PRACTICAL_LESSONS.md`
- `EXPERIMENT_INSTRUCTIONS.md`, `REPLICATION_GUIDE.md`, `RESTART_EXPERIMENT.md`,
  `SYNCTEX_SUMATRA_LESSONS.md`

Three scripts cite these docs in a comment/docstring for historical rationale
(`experiment_script/compute_paper_numbers.py`, `experiment_script/init_replication.py`,
`experiment_script/run_exp123_orchestrator.py`) — none read them at runtime, and their
citations were updated to the new `archive/handoff_docs/` path.
