# Full-Pipeline Replication Guide

**Audience:** a future agent who must regenerate the entire study — experiments,
results, and every manuscript table/figure — **automatically and consistently**.

**Key idea.** The pipeline is a straight line with two "glue" scripts that make it
reproducible end to end:

```
Exp1 (both datasets)                 ── run_exp1_raja.py / run_exp1_cao2018.py
     │  (full montage, ranks every channel & group)
     ▼
auto-select top-4 groups + top-4 channels  ── exp1_get_best_region_channel.py
     │  → runs_second_iteration/channel_selection/selected_channels.yaml
     ▼
Exp2..Exp8 (both datasets)           ── run_exp2..8_*.py  (or _run_all_experiments.py)
     │  (evaluate only the selected groups/channels)
     ▼
regenerate ALL manuscript inputs     ── reproduce_manuscript.py build
     │  (tables, figures, NUMBERS_*.md — 26 artifacts, 10 scripts)
     ▼
compile                              ── pdflatex ×2 + biber  (writing/main.tex)
```

Run **everything from the repo root** in the conda env `double_threshold_algo`:

```bash
conda activate double_threshold_algo          # pyblinker 0.5.0 expected
cd /c/Users/balan/IdeaProjects/blink_detection_llm
```

`runs/` is the **read-only baseline** (std_threshold = 3.5). `runs_second_iteration/`
is the **manuscript's source of truth** (std_threshold = 3.0). Never modify `runs/`.
Never print `bot_telegram.md`.

---

## Stage 0 — Prerequisites & configs

- **Env:** `double_threshold_algo`; `pyblinker==0.5.0`, `blink_evaluation`, `autoreject`,
  `mne`, `numpy/pandas/scipy/matplotlib/seaborn/pyyaml`.
- **Data:** raw FIF + annotation CSVs for Raja and Cao2018, resolved through
  `paths.yaml` / `src/project_paths.py` (`get_raja_paths`, `get_cao_paths`).
- **Region maps:** `brain_region_raja.yaml`, `brain_region_cao2018.yaml`
  (channel → region groups). **Raja EGI→10-20 map:** `32_ch.csv` (Raja/EGI hardware
  only; Cao2018 is native 10-20).
- **Experiment configs:** each runner reads `experiment_script/setup/<exp>.yaml`. The
  std=3.0 re-run uses the `<exp>_std30.yaml` variants (these set `std_threshold: 3.0`).
  The orchestrator (Stage 3a) patches each runner to use the `_std30.yaml` config and to
  write into `runs_second_iteration/`.
- **Smoke test before running anything:**
  ```bash
  python -c "import importlib.metadata as m; assert m.version('pyblinker')=='0.5.0'; \
  from pyblinker.double_thresholding import blink_position_strategy_dbo; print('ok')"
  ```

> `std_threshold` (= 3.0), `k`, the MAD multiplier and epoch length are **internal
> parameters** — they live in the YAML configs and must **never** appear in the
> manuscript prose. Report only `det_precision`, `det_recall`, `det_f1`.

---

## Stage 0b — Choose the output folder (decide this first; critical for a "from factory" run)

`runs_second_iteration/` backs the **published manuscript**. A fresh, from-scratch
replication must **not** clobber it. The whole pipeline keys off one environment
variable, **`BLINK_RUNS_DIR`**:

- **Reproduce the existing manuscript:** do nothing — every script defaults to
  `runs_second_iteration/`. (Be aware: re-running experiments in this mode would
  overwrite it.)
- **Run from factory (fresh):** mint a new folder and point the whole pipeline at it.
  Use the helper, which **warns** and never silently reuses the canonical folder:

```bash
# Option A — name your own fresh folder:
python experiment_script/init_replication.py my_run_2026
export BLINK_RUNS_DIR=my_run_2026            # PowerShell: $env:BLINK_RUNS_DIR='my_run_2026'

# Option B — auto-create runs_replica_<timestamp>/ (prints a warning with the name):
python experiment_script/init_replication.py
export BLINK_RUNS_DIR=runs_replica_YYYYMMDD_HHMMSS   # copy the printed name
```

Set `BLINK_RUNS_DIR` **once** in the shell and run all of Stages 1–5 in that same
shell — every runner, `exp1_get_best_region_channel.py`, `_run_all_experiments.py` and
every extraction script reads it, so experiments and manuscript inputs stay consistent.
The regression gate still reads the read-only `runs/` baseline regardless.

---

## Stage 1 — Experiment 1 (channel-selection ablation), both datasets

```bash
python experiment_script/run_exp1_raja.py
python experiment_script/run_exp1_cao2018.py
```

> **Baseline vs std=3.0 — read this.** Running `run_exp*.py` **directly** produces the
> **std=3.5 baseline** in `runs/` (their `OUT_DIR` and config default to the baseline).
> The **std=3.0** results that back the manuscript are produced by the **orchestrator**
> (Stage 3a), which patches each runner to the `_std30` config and redirects output into
> `BLINK_RUNS_DIR`. For a faithful std=3.0 replication, drive Stages 1 **and** 3 through
> the orchestrator — it runs exp1 first (full montage), then exp2–exp8. Run the
> individual `run_exp1_*.py` directly only if you specifically want to (re)build the
> baseline.

- Exp1 deliberately sees the **full montage** (no channel restriction) so it can rank
  **every** individual channel and **every** region group.
- Outputs (per dataset):
  `runs_second_iteration/exp1_channel_{raja,cao}/exp1_channel_selection_*_results.csv`
  (one row per session × selection × channel) and `..._summary.csv`
  (mean over sessions per selection × channel).
- **This CSV is already channel-by-channel:** with `selection=='all'` each row is one
  `(session, channel_in_group)` with its own P/R/F1. The per-channel manuscript table
  (Table `tab:exp1_channel_ablation`) reads exactly these rows — no re-run needed.

---

## Stage 2 — Auto-select top-4 groups + top-4 channels → YAML

```bash
python experiment_script/exp1_step_b_get_best_region_channel.py            # reads runs_second_iteration/
# python experiment_script/exp1_step_b_get_best_region_channel.py runs     # reads the runs/ baseline instead
```

**This is the script that "takes the 4 best automatically and stores it."** It reads the
two Exp1 `*_summary.csv` files and writes, into
`runs_second_iteration/channel_selection/`:

| file | purpose |
|------|---------|
| `selected_channels.yaml` | the `groups_to_run` list per dataset — **consumed by Stage 3** |
| `selected_channels.json` | full detail (P/R/F1 per pick) |
| `selected_channels_report.md` | human-readable table |

- **Criterion:** highest `det_f1` for `proposed_median` (`center_method=median`, `rule=any`).
- **Top-4 regional groups** (excluding `all`, the full-montage reference) + **top-4 single
  channels**. Tune `TOP_N_INDIVIDUAL` / `TOP_N_REGIONAL` / `EXCLUDE_GROUPS` at the top of
  the script.
- **Current std=3.0 selection** (what the YAML contains now):
  - Raja: `groups_to_run = [frontal_left, frontal, frontal_right, central, single:E22, single:E9, single:E3, single:E23]`
  - Cao2018: `groups_to_run = [frontal, frontal_left, frontal_right, central, single:FP1, single:FP2, single:F7, single:F8]`

### Stage 2b — Wire the selection into the runners (the automation link)

The downstream runners (`run_exp2..8_*.py`) currently **hardcode** their `GROUPS_TO_RUN`
set near the top of each file. To make the pipeline fully automatic and guarantee the
experiments use exactly what Stage 2 selected, replace the hardcoded literal with a read
of the YAML:

```python
import yaml
from pathlib import Path
_sel = yaml.safe_load((Path(__file__).resolve().parents[1] /
        "runs_second_iteration/channel_selection/selected_channels.yaml").read_text())
GROUPS_TO_RUN = set(_sel["raja"]["groups_to_run"])      # use "cao2018" in the Cao runners
```

> **Consistency caveat.** The `runs_second_iteration/` CSVs that currently back the
> manuscript were produced with the *historical* hardcoded sets
> (`{frontal, frontal_left, frontal_right, single:E22, single:E9, single:E3, single:E23}` for
> Raja) — i.e. the three frontal groups, **not** `central`. The auto-selector adds `central`
> as the 4th region. If you switch the runners to the YAML, the evaluated set changes
> slightly, so you **must re-run Stage 3** to keep the CSVs consistent with the YAML.
> If you only want to reproduce the *current* manuscript, keep the historical hardcoded
> sets and treat Stage 2 as documentation of how they were chosen.

> A separate, optional mechanism exists: `channel_group_selection.yaml` +
> `channel_group_config.apply_stage_a_channel_group` restrict **Stage-A screening** to one
> approved montage (hard-approval gate; default `all`). It is independent of
> `GROUPS_TO_RUN` (which selects *which selections to evaluate*). Leave it at `all` unless
> you deliberately want to gate Stage A.

---

## Stage 3 — Experiments 2–8, both datasets

### Option (a) — orchestrator (recommended)

```bash
python experiment_script/_run_all_experiments.py
```

- Runs exp1→exp5, exp7, exp8 for **both** datasets, **patching** each runner to use the
  `_std30.yaml` config and write into `runs_second_iteration/`.
- **Regression-gates** every experiment: Proposed-Med macro- & micro-F1 must be ≥ the
  `runs/` baseline − 0.001 on both datasets, else it stops.
- **Resumable:** skips an experiment whose result CSVs already exist.
- **exp6 is intentionally skipped** — it is the ablation that *decided* std=3.0 and is not
  reported.
- The Telegram heartbeat + `codex` AI-insight calls are **optional** (need
  `bot_telegram.md` and a `codex` CLI). They never affect the CSVs; if absent they fail
  silently. The gate logic is the part that matters.

### Option (b) — run each experiment directly

```bash
for e in 2 3 4 5 7 8; do
  python experiment_script/run_exp${e}_raja.py
  python experiment_script/run_exp${e}_cao2018.py
done
```

- Each runner reads its `experiment_script/setup/<exp>.yaml`, evaluates every selection in
  `GROUPS_TO_RUN`, and writes `runs_second_iteration/exp<e>_*/..._results.csv` (+ summary,
  + per-session CSVs under `sessions/`). Set `OVERWRITE=False` to resume.
- To match the std=3.0 run you must point `OUT_DIR` at `runs_second_iteration/...` and the
  config at the `_std30.yaml` (the orchestrator does this patching for you, which is why
  option (a) is recommended).

CSV schema (every experiment): `dataset, session, selection, center_method,
channel_in_group, det_tp, det_fp, det_fn, det_precision, det_recall, det_f1` (+ experiment-
specific columns: `epoch_duration_s`, `iou_threshold`, `min_flagged_epochs`,
`use_epoch_health`, `blink_category`/`n_gt_*`, `condition`).

---

## Stage 4 — Regenerate ALL manuscript inputs (one command)

```bash
python experiment_script/reproduce_manuscript.py build
```

This runs the **10 extraction scripts** that read `runs_second_iteration/` and write every
table, figure and frozen-number file (26 artifacts). Inspect or target them:

```bash
python experiment_script/reproduce_manuscript.py list                 # artifact → script → source → aggregation
python experiment_script/reproduce_manuscript.py provenance tab:exp1_channel_ablation
python experiment_script/reproduce_manuscript.py build --label fig:pr_scatter   # one artifact
python experiment_script/reproduce_manuscript.py build --only regen_paper_tables.py
python experiment_script/reproduce_manuscript.py build --dry-run
python experiment_script/reproduce_manuscript.py custom-example        # per-channel extraction demo
```

The 10 generating scripts (all read `runs_second_iteration/`):

| script | produces |
|--------|----------|
| `regen_paper_tables.py` | most `e_result/tab_*.tex` incl. the per-channel `tab_exp1_channel_ablation` + `tab_egi_channel_map` |
| `plot_exp_boxplot.py` | `fig_exp_boxplot`, `tab_exp_summary`, `tab_exp_stats` |
| `plot_region_performance.py` | `fig_region_performance` (per-channel bars) |
| `plot_pr_operating_points.py` | `fig_pr_scatter` |
| `plot_count_agreement.py` | `fig_count_agreement`, `tab_count_agreement` |
| `build_literature_comparison.py` | `tab_literature_comparison` (qualitative; from the .bib) |
| `analyse_failure_sessions.py` | `tab_failure_analysis` |
| `regen_simple_figs.py` | `fig_condition_prf`, `fig_f1_by_dataset`, `fig_f1_by_epoch` |
| `compute_paper_numbers.py` | `writing/NUMBERS_std30.md` (all frozen headline numbers) |
| `compute_round2_addendum.py` | `writing/NUMBERS_round2.md` (hemisphere/ICC/health) |

All four-condition numbers use **best-channel-per-session** (argmax `det_f1` over selections
per session, then mean). The Exp1 channel table is the one deliberate exception: it is
**per-channel** (mean over sessions of `selection=='all'`, no aggregation).

---

## Stage 5 — Compile the manuscript

```bash
cd writing
pdflatex -interaction=nonstopmode -halt-on-error main.tex
biber main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
cd ..
```

Expected: **46 pages, 0 undefined citations/references.** (9 pre-existing overfull
`\hbox` are acceptable — see `writing/VALUE_AUDIT.md`.)

---

## Scripts you must NOT run

These point at **deleted older runs** or are **superseded** — running them errors or writes
stale inputs:

| script | why not |
|--------|---------|
| `paper_result_figures.py` | reads deleted `runs/exp41_*` |
| `paper_channel_selection_frequency.py` | reads deleted `runs/exp41_*` |
| `paper_error_structure_session.py` | reads deleted `runs/exp41_*` |
| `paper_epoch_duration_figure.py` | reads deleted `runs/exp40_*` |
| `paper_blink_type_recall.py` | reads deleted `runs/extra_blink_type` |
| `update_exp2_latex.py` | superseded by `regen_paper_tables.py` |
| `compute_paper_numbers_addendum.py` | exploratory; superseded by `compute_round2_addendum.py` |
| `run_exp6_*.py` | exp6 is the std-threshold ablation source; not reported |

(`reproduce_manuscript.py list` prints this `DO_NOT_RUN` set too.) Utilities that are
imported, not run directly: `channel_ablation_utils.py`, `condition_runner_utils.py`,
`channel_group_config.py`, `telegram_heartbeat.py`.

---

## One-shot replication (copy-paste)

```bash
conda activate double_threshold_algo
cd /c/Users/balan/IdeaProjects/blink_detection_llm

# 0. (FRESH RUN ONLY) mint a new output folder so runs_second_iteration/ is untouched.
#    Omit this whole step to reproduce/overwrite the existing manuscript folder.
python experiment_script/init_replication.py my_run_2026
export BLINK_RUNS_DIR=my_run_2026     # PowerShell: $env:BLINK_RUNS_DIR='my_run_2026'

# 1+3. Run exp1..exp8 at std=3.0 (orchestrator: applies _std30 config, writes to
#      BLINK_RUNS_DIR, gates vs runs/ baseline, skips exp6, resumable).
python experiment_script/_run_all_experiments.py

# 2. Record the channel selection used (top-4 groups + top-4 channels) → YAML.
#    (To CHANGE the montage: wire each run_exp2..8_*.py GROUPS_TO_RUN to this YAML —
#     Stage 2b — then re-run the orchestrator.)
python experiment_script/exp1_step_b_get_best_region_channel.py

# 4. Regenerate every manuscript table/figure/number from BLINK_RUNS_DIR.
python experiment_script/reproduce_manuscript.py build

# 5. Compile
cd writing && pdflatex -interaction=nonstopmode main.tex && biber main \
  && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && cd ..
```

---

## Customisation hooks

- **How many channels/groups:** `TOP_N_INDIVIDUAL`, `TOP_N_REGIONAL`, `EXCLUDE_GROUPS` in
  `exp1_get_best_region_channel.py`.
- **std_threshold / epoch length / filter:** the `experiment_script/setup/<exp>_std30.yaml`
  configs.
- **Which selections an experiment evaluates:** `GROUPS_TO_RUN` in each runner (or wire to
  the YAML, Stage 2b).
- **Reproduce or customise one artifact:** `reproduce_manuscript.py build --label <label>`;
  or import the helpers `load`, `best_per_session`, `per_channel` from
  `reproduce_manuscript.py` for arbitrary slices.
- **Audit trail:** every number, file and aggregation rule is logged in
  `writing/VALUE_AUDIT.md`; the frozen numbers live in `writing/NUMBERS_std30.md` and
  `writing/NUMBERS_round2.md`.

## Why this is consistent

Every manuscript number flows from `runs_second_iteration/` through one documented
aggregation (best-channel-per-session everywhere except the per-channel Exp1 table), so
regenerating from scratch reproduces identical tables, figures and prose values. The
`reproduce_manuscript.py` manifest is the single source of truth for *what comes from where*;
if a result changes, re-run Stage 4 then Stage 5 and the manuscript stays in sync.
