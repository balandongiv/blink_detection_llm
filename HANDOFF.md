# HANDOFF — continue the exp1/exp2 "all-channel" pipeline with exp3 → exp8

**Written:** 2026-07-15. **For:** a fresh agent session picking up after exp1 (channel
selection) and exp2 (strategy comparison) were re-run today under a new naming/pipeline
convention. This doc tells you what's done, what changed, and what's next.

---

## 1. What was just done (today, 2026-07-15)

1. Fixed a debug bug in `src/exp/session_worker.py` that silently restricted exp1 to only
   the *last* channel-selection group (`group_names=[group_names[-1]]`) — removed.
2. Ran the full channel-selection ablation, **all channel groups**, both datasets:
   - `experiment_script/exp1_a_channel_selection_cao2018.py` → `runs0/exp1_channel_cao/` (58/58 sessions, 0 errors)
   - `experiment_script/exp1_a_channel_selection_raja.py` → `runs0/exp1_channel_raja/` (46/46 sessions, 0 errors)
3. Generated exp1 plots:
   - `experiment_script/exp1_b_plot_region_boxplot.py` → `writing/figures/fig_exp1_region_boxplot.{pdf,png}`
   - `experiment_script/exp1_b_plot_single_channel.py` → `writing/figures/fig_exp1_single_channel_boxplot.{pdf,png}`
4. Ran exp2 strategy comparison **at the `all_channel` gate** (deliberately — see §3), both
   datasets, 30 s epochs, std=3.0, visible conditions only (no DBO):
   - `experiment_script/exp2_a_strategy_comparison.py --out-dir runs/exp41_cao_30s --visible-conditions-only`
   - 415/416 tasks OK. 1 pre-existing error unrelated to today's changes: Raja session
     `S01/051017m`, condition `MNE-annot`: `can't multiply sequence by non-int of type 'float'`
     (not fixed — flagged for a future session).
5. Generated the exp2 plot:
   - `experiment_script/exp2_b_plot_pr_scatter.py` → `writing/figures/fig_exp2_pr_scatter.{pdf,png}`
   - Raja and Cao2018 are shown **separately** (color = dataset), **not pooled**; marker
     shape = condition. The earlier "frontal-gated" variant
     (`exp2_plot_pr_scatter_frontal.py`) was **deleted** — exp2 intentionally uses the
     whole-montage (32-channel) gate for both datasets, no frontal-only comparison.
6. **Cross-check requested by the user:** exp1's `all_channel`/median **best single channel**
   F1 vs exp2's `Proposed-Med` `all_channel` **combined** macro F1 — should be close (exp2
   combines all channels via the proposed pipeline's own aggregation, so it won't be
   identical to exp1's best individual channel, just in the same ballpark):
   | Dataset | exp1 all_channel/median best chan | exp2 Proposed-Med (all_channel) |
   |---|---|---|
   | Cao2018 | FP1, F1=0.797 | F1=0.807 |
   | Raja | E9, F1=0.868 | F1=0.883 |

   Within ~1-1.5pp — consistent, as expected.

### Headline exp1 finding
Frontal electrodes (FP1/FP2, or Raja's E9/E22) carry almost all of the detectable blink
signal on both datasets; central drops sharply, parietal/occipital/posterior collapse to
near-zero. See `fig_exp1_region_boxplot.png` / `fig_exp1_single_channel_boxplot.png`.

### Headline exp2 finding
Pooled (Raja+Cao2018) condition means, all-channel gate:
- Proposed-Med: P=0.813 R=0.896 **F1=0.840**
- Proposed-Mean: P=0.821 R=0.879 F1=0.835
- BLINKER-concat: P=0.618 R=0.963 F1=0.726 (over-triggers)
- MNE-annot: P=0.646 R=0.663 F1=0.614

Proposed-Med > Proposed-Mean on both datasets; both beat the baselines mainly on precision.

---

## 2. Script naming convention (NEW — read before running anything)

`experiment_script/` scripts that are part of the active pipeline are now named
`exp<N>_<letter>_<what_it_does>.py`, where the letter encodes execution order — so
`ls experiment_script/exp*` sorted alphabetically **is** the run order. Same letter =
order-independent siblings (e.g. the two datasets of the same primary).

**Renamed today** (only exp1 and exp2 — see §3 for why exp3-8 were left alone):

| Old name | New name |
|---|---|
| `exp1_channel_selection_cao2018.py` | `exp1_a_channel_selection_cao2018.py` |
| `exp1_channel_selection_raja.py` | `exp1_a_channel_selection_raja.py` |
| `exp1_plot_region_boxplot.py` | `exp1_b_plot_region_boxplot.py` |
| `exp1_plot_single_channel.py` | `exp1_b_plot_single_channel.py` |
| `exp2_strategy_comparison.py` | `exp2_a_strategy_comparison.py` |
| `exp2_plot_pr_scatter.py` | `exp2_b_plot_pr_scatter.py` |
| `exp2_plot_pr_scatter_frontal.py` | **deleted** (see §1.5) |

All internal references were updated and verified (`py_compile` + a live import check):
`src/utils/condition_runner_utils.py` (imports `exp2_a_strategy_comparison`, used by exp7/exp8),
`experiment_script/paper_blink_type_recall.py` (dynamically loads
`exp2_a_strategy_comparison.py`), `experiment_script/run_std30_orchestrator.py` and
`scripts/run_orchestration.py` (subprocess paths), `src/exp/session_worker.py`,
`src/utils/channel_ablation_utils.py`, `experiment_script/exp1_step_b_get_best_region_channel.py`
(docstrings/messages only).

Figures were also renamed to `fig_exp<N>_<what_about>.png`:
- `fig_region_boxplot.*` → `fig_exp1_region_boxplot.*`
- `fig_single_channel_boxplot.*` → `fig_exp1_single_channel_boxplot.*`
- `fig_exp2_pr_scatter.*` already matched the convention (kept)
- `fig_exp2_pr_scatter_frontal.*` deleted (orphaned — its script is gone and nothing `\input`s it)

## 3. IMPORTANT — why exp3-8 were NOT renamed, and a live dual-pipeline warning

Do not casually rename/delete anything else in `experiment_script/` without reading this.

There are **two separate result-generation pipelines** coexisting in this repo right now:

1. **The new one** (what exp1/exp2 used today): `runs0/`, `runs/exp41_cao_30s/`, gated by
   `channel_group_selection.yaml` (`all_channel` for both datasets, approved 2026-07-13).
   This is a fresh, from-scratch re-run using every EEG channel, requested explicitly today.

2. **The old one** (`runs_second_iteration/`): produced by `run_std30_orchestrator.py` +
   the legacy `run_exp2..8_*.py` runners + `exp1_step_b_get_best_region_channel.py`'s
   "auto top-4 channel" selection. **This is what currently backs most of the compiling
   45-page manuscript** — `writing/e_result/*.tex` and `writing/c_literature_review/*.tex`
   cite `regen_paper_tables.py`, `plot_count_agreement.py`, `plot_pr_operating_points.py`,
   `plot_exp_boxplot.py`, `plot_region_performance.py`, `analyse_failure_sessions.py`,
   `build_literature_comparison.py`, `compute_round2_addendum.py`, `update_exp2_latex.py`
   (and others) as their literal "Source: script" provenance, all reading from
   `runs_second_iteration/`. **These were intentionally left untouched** (not renamed, not
   deleted) — I initially assumed they were pre-refactor dead code and was corrected twice
   by the user after checking `writing/` references. Do not delete or rename any script
   that a `writing/e_result/*.tex` or `writing/c_literature_review/*.tex` file cites by
   filename without first confirming the user wants that provenance chain replaced.

**What this means for you:**
- `exp3_epoch_duration.py` through `exp8_long_blink_analysis.py` (and their supporting
  `paper_*` scripts: `paper_epoch_duration_figure.py`, `paper_channel_selection_frequency.py`,
  `paper_error_structure_session.py`, `paper_blink_type_recall.py`, `paper_result_figures.py`)
  are **still at their old names** — untouched. Whether to run them under the *new*
  `runs0`/`all_channel` pipeline (parallel to what exp1/exp2 just did) or under the *old*
  `runs_second_iteration/` pipeline (to refresh the manuscript's existing tables) is a
  **decision the user needs to make explicitly** — don't assume either way.
- If asked to continue the *new* all-channel work (exp3 onward), check each primary's
  argparse/config against today's approach before running: confirm `--out-dir`,
  confirm it reads `channel_group_selection.yaml` via `channel_group_config.py` (per
  `SCRIPTS_OVERVIEW.md`'s "all-channels warning" — it logs once per dataset when the gate
  is `all_channel`), and confirm it isn't hardcoded to a `GROUPS_TO_RUN` subset from the old
  top-4-channel selection flow.
- If asked to apply the same `exp<N>_<letter>` renaming to exp3-8 and their `paper_*`
  siblings, first re-verify with `grep -rn "<script_name>" writing/` (as was done for exp1/
  exp2) — the set of "live-manuscript-cited" scripts may have grown or changed.
- Before deleting or renaming **anything** further in `experiment_script/`, re-run this
  check:
  ```
  grep -rln "<script_basename_without_.py>" writing/*.md writing/**/*.tex
  ```
  If it hits a non-`.bak` file, treat that script as live manuscript provenance, not legacy.

## 4. Environment

- Conda env: **`double_threshold_algo`** — `C:\Users\balan\anaconda3\envs\double_threshold_algo\python.exe`.
  (`pyblinker_worktree_epoch_blink` mentioned in some old docstrings is stale/wrong.)
- Run everything from the repo root: `C:\Users\balan\IdeaProjects\blink_detection_llm`.
- 24 logical CPUs on this machine. exp1's ablation uses a `ProcessPoolExecutor`
  (n_jobs=20 cao / 16 raja by default); exp2 uses a `ThreadPoolExecutor` (GIL-bound —
  CPU-heavy autoreject work inside it does **not** scale across cores the way exp1's
  process pool does, so exp2 is much slower wall-clock per task; exp2's full run today
  took ~5 hours for 415 tasks). Keep this in mind when estimating exp3-8 runtime, especially
  any of them that reuse the full autoreject pipeline per session.

## 5. Telegram reporting (if continuing the same operating pattern)

`telegram_heartbeat.py` (repo root) — token in `bot_telegram.md` (gitignored), chat_id
hardcoded. Useful commands: `check`, `key --message "..."`, `photo --path P --caption "..."`.
Today's pattern the user asked for and seemed to like:
- A heartbeat/progress message roughly every 10 minutes while a long run is in flight.
- After each experiment fully completes: one `key` message with the analysis (headline
  numbers, comparison to prior results, anything surprising), followed by `photo` for each
  generated PNG.

## 6. Suggested next steps for exp3 onward

1. Ask the user (don't assume) whether exp3-8 should target the new `runs0`/`all_channel`
   pipeline or refresh `runs_second_iteration/` for the existing manuscript — this decides
   which scripts to actually invoke and where output goes.
2. Read `experiment_script/setup/exp3_epoch_duration.yaml` (std=3.0, 100 Hz, epoch grid
   `[10,20,30,40,50,60,120]`, reference 30 s) and `exp3_epoch_duration.py`'s own docstring/
   argparse before running, exactly as was done for exp1/exp2 in this session.
3. Same channel-group-gate sanity check as exp2: confirm `channel_group_selection.yaml`
   is still `all_channel`/approved before any of exp3-8 run (they all pass through
   `channel_group_config.apply_stage_a_channel_group`, per `SCRIPTS_OVERVIEW.md`).
4. Keep using the `exp<N>_<letter>` convention for anything newly created so the sequence
   stays sortable; extend the SCRIPTS_OVERVIEW.md table when you do.
