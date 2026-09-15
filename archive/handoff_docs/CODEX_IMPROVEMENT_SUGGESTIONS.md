# Codex Improvement Suggestions — Blink Detection Pipeline

**Date:** 2026-06-26  
**Scope:** Exp1–8 ablation pipeline across Raja (EGI-128, 46 sessions) and Cao2018 (10-20, 58 sessions)  
**Impact key:** 🔴 High · 🟡 Medium · 🟢 Low

---

## A. Algorithm Improvements

### 🔴 A1. Merge-on-gap post-processor for long blinks (Stage C)

Long blinks (≥400 ms) show high recall (~0.67–0.80) but very poor precision (~0.37–0.46), which indicates **undersegmentation**: one detected event spans what the annotator split into multiple short blinks separated by brief partial eye-openings. A targeted fix: after Stage C produces detected intervals, apply a merge pass that joins consecutive detections separated by fewer than `merge_gap_ms=150` ms. This is a deterministic O(n) post-step, adds no tunable training, and would not harm short-blink precision. Add it as an optional `merge_gap_ms` parameter inside `blink_position_strategy_dbo_drop` (in `src/strategy_dbo_drop/core.py`) and run it as Exp9.

### 🔴 A2. Session-adaptive std_threshold via amplitude distribution shape

Currently `std_threshold=2.5` is the empirical winner but is fixed across all sessions. Blink amplitude varies 3–5× across subjects (fatigue, impedance, individual anatomy). A session-adaptive strategy: compute the kurtosis and bimodality coefficient of the per-epoch PTP distribution in Stage B; if the distribution is bimodal (two clusters = blink epochs vs. non-blink epochs), the threshold between modes can be found via Otsu's method on the histogram rather than a fixed σ multiplier. This would eliminate the `std_threshold` hyperparameter entirely. Implement as `center_method="otsu"` alongside existing `"median"/"mean"` in `channel_ablation_utils.py` and compare in Exp6.

### 🟡 A3. Channel-normalised autoreject in Stage A for weak-signal channels

Stage A applies the same autoreject PTP threshold across all channels in a group. On lateral frontal channels (F3/F4/F7/F8), blink amplitude is ~3–5× lower than on FP1/FP2. A z-score normalisation of PTP per channel before group-level voting would give weaker channels proportional representation, potentially recovering some of the F1 lost on lateral frontal channels. In `channel_ablation_utils.py → run_one_session`, the `prepared` object contains per-channel amplitudes; normalise before passing to `blink_position_strategy_dbo_drop`.

### 🟢 A4. Split-on-valley for over-merged detections

Complementary to A1: for very long detected events (>600 ms), look for local amplitude minima within the event that exceed a minimum depth threshold. Split at such minima. This targets the case where a sustained eye-closure is annotated as two blinks with a brief reopening. Low priority because F1 for long blinks is already recall-limited, not precision-limited on Raja.

---

## B. Experimentation Design

### 🔴 B1. Combined "tuned" configuration experiment

No experiment has run all individually-optimal settings together: `std_threshold=2.5` + `min_flagged_epochs=5` + `use_epoch_health=True` + `epoch_duration_s=60s` (Cao2018 optimum). This "tuned proposed" condition belongs in the paper as the ceiling. Add as Exp9 (or a sub-condition of Exp2). Expected gain: ~5–8pp F1 above the current default Proposed on Cao2018 FP1.

### 🔴 B2. Paired per-session statistical tests

Current results report macro-average F1 across 46/58 sessions but contain no uncertainty estimates. For each key comparison (Proposed vs. BLINKER on E9, FP1), run a **Wilcoxon signed-rank test** on the per-session F1 vector (readily available from per-session CSVs under `runs/exp2_*/sessions/`). Report the p-value and effect size (rank-biserial r) in the paper. Without this, a reviewer can reject the +6–10pp claim as potentially driven by outlier sessions.

### 🔴 B3. Bootstrap 95% confidence intervals on macro-F1

In `experiment_script/channel_ablation_utils.py → condition_summary_rows`, replace the plain `np.mean` with a bootstrap CI (e.g., 1000 resamples). Add `det_f1_ci_low` and `det_f1_ci_high` columns to the summary CSV. This requires no new experiments — just a change to the aggregation step — and makes every table in the paper publication-ready.

### 🟡 B4. Cross-dataset parameter transfer experiment

Optimise all hyperparameters on Raja only, then evaluate the **same settings** on Cao2018 without re-tuning. Compare against the per-dataset optimal. This tests generalisability and is a standard requirement for EEG papers claiming a broadly-applicable detector. Currently each dataset gets its own YAML config, which cannot demonstrate transfer.

### 🟡 B5. Ground-truth boundary jitter sensitivity

The IoU experiment (Exp4) varies the *evaluation* threshold but not annotation uncertainty. Run a jitter experiment: perturb each ground-truth blink boundary by ±25ms and ±50ms (uniform random) and recompute all metrics. If F1 drops < 2pp under ±50ms jitter, that strengthens the paper's claim of robustness to annotator disagreement.

### 🟢 B6. Epoch health rejection rate vs. F1 improvement scatter

Exp7 shows `use_epoch_health` gives +12.1pp on Cao2018 but −0.5pp on Raja. The mechanism is unclear. A per-session scatter plot of (% epochs rejected by health filter) on the x-axis versus (ΔF1 from enabling health filter) on the y-axis would reveal whether sessions with high rejection rates are the ones that benefit, confirming the causal story.

---

## C. Code Quality and Architecture

### 🔴 C1. Schema version column in every session CSV

The stale-cache bug from Exp1 (wrong column set in cached files) will recur whenever the output schema changes. Concrete fix: add `SCHEMA_VERSION = "v3"` as a module-level constant in `channel_ablation_utils.py`, write it as a `schema_version` column in every row via `run_one_session`, and in the resume block of `run_exp1_raja.py → main()`, read the first row of each cached CSV and compare `schema_version`; if mismatched, delete the file and add the session back to `todo`. This is a 15-line change that eliminates an entire bug class.

### 🔴 C2. Shared `ExperimentRunner` to eliminate copy-paste across Exp scripts

`run_exp1_raja.py` through `run_exp8_*.py` duplicate: OVERWRITE/MAX_SESSIONS/N_JOBS constants, the `_session_csv()` path function, the `_write_session_csv()` atomic-write pattern, the `ProcessPoolExecutor` loop, and the `condition_summary_rows` + CSV write block. Extract these to `experiment_script/exp_runner.py` exposing a `run_experiment(pairs, worker_fn, out_dir, *, overwrite, max_sessions, n_jobs)` function. Each experiment script becomes a thin wrapper that supplies its own `worker_fn`. This reduces total script length by ~40% and ensures resume logic is fixed in exactly one place.

### 🟡 C3. Pydantic config validation in `load_exp_config`

`src/project_paths.py → load_exp_config()` currently returns a raw `dict`. A misconfigured YAML (e.g., `epoch_duration_s: 300` instead of `30`) causes a silent hours-long run with wrong parameters. Add a `dataclasses.dataclass` or `pydantic.BaseModel` (`ExpConfig`) with type annotations and range checks (e.g., `1 ≤ epoch_duration_s ≤ 300`, `0.5 ≤ std_threshold ≤ 10.0`). Fail fast at startup, not mid-run.

### 🟡 C4. Make `min_flagged_epochs` explicit in every `_SESSION_KWARGS`

In `run_exp1_raja.py`, `_SESSION_KWARGS` does not set `min_flagged_epochs` — it silently defaults to 1 inside `run_one_session`. If the default ever changes, Exp1 results would silently change too. Add `"min_flagged_epochs": 1` explicitly to every `_SESSION_KWARGS` block across all experiment scripts.

### 🟢 C5. Windows-safe session CSV names

`_session_csv()` replaces `/` and `\` but not `:`, which is invalid in Windows file paths. Session names that contain colons (e.g., timestamps) would cause silent write failures. Add `:` to the replacement list: `session_name.replace("/", "__").replace("\\", "__").replace(":", "_")`.

---

## D. Reporting and Paper Figures

### 🔴 D1. Precision-Recall curve by sweeping std_threshold

Since `std_threshold` controls the precision/recall trade-off, a full P-R curve can be generated by sweeping it from 1.5 to 5.0 in 0.25 steps on E9 (Raja) and FP1 (Cao2018). Plot Proposed's P-R curve alongside BLINKER's operating point. Area under the P-R curve (AP) is a stronger single-number metric than F1 at one operating point, and reviewers expect it in detection papers.

### 🔴 D2. Per-session F1 box plots

A figure with two panels (Raja / Cao2018), each showing box plots of per-session F1 across 46/58 sessions for Proposed-Med, BLINKER-concat, and MNE-annot on the primary channels (E9, FP1). This directly answers "is the improvement consistent or driven by a few sessions?" — the most common reviewer question for EEG studies. The data already exists in `runs/exp2_*/sessions/*.csv`.

### 🟡 D3. Calibration plot: F1 vs. IoU threshold (line plot)

Exp4 data exists as a table. Convert to a line plot with Proposed and BLINKER on the same axes, x=IoU threshold, y=F1. This visualises that BLINKER's boundary quality degrades faster than Proposed's as the match criterion tightens — a compelling argument for temporal precision.

### 🟡 D4. Long blink sub-table broken down by duration bin

Exp8 reports a binary split at 400 ms. Break it into bins: 100–200 ms (normal), 200–400 ms (extended normal), 400–600 ms (short long), >600 ms (sustained closure). If F1 degrades monotonically with duration, this is a strong finding. The `load_annotation_as_reference` function already reads blink duration; binning is a post-processing step on the Exp8 CSVs.

### 🟢 D5. Confusion matrix at blink-category level

A 2×2 confusion matrix heatmap (normal vs. long blinks, correct vs. missed) would make a compact supplementary figure summarising Exp8 at a glance.

---

## E. Scalability and Reproducibility

### 🔴 E1. Add `environment.yml` to the repository

The `double_threshold_algo` conda environment is documented in memory files but not in the repository. Any collaborator or reviewer who clones the repo has no way to reproduce the environment. Run `conda env export --from-history > environment.yml` from the active env and commit it. Include a minimal `requirements.txt` as a fallback for pip users.

### 🔴 E2. Regression smoke-test suite

Add a `tests/test_exp_smoke.py` with one pytest per experiment (Exp1–8) that runs `MAX_SESSIONS=1` and asserts the reported F1 matches the value in `BENCHMARK_GROUND_TRUTH.md` within ±0.01. The `BENCHMARK_GROUND_TRUTH.md` already contains the reference values; wire them in as pytest `approx()` checks. This would have caught the stale-schema bug and the `import time` omission before they caused multi-hour reruns.

### 🟡 E3. Retry logic in `send_telegram_chunked`

In `experiment_script/exp_tg_report.py → send_telegram_chunked`, the `except Exception: pass` silently swallows network failures. A 3-attempt exponential backoff (1s, 2s, 4s) using `urllib.request` with a timeout guard would make the notification reliable without adding a new dependency.

### 🟡 E4. Document non-determinism boundaries

`autoreject_random_state=42` seeds autoreject but `numpy` global state and MNE's internal RNG calls may not be fully seeded. Add a call to `np.random.seed(42)` and `random.seed(42)` at the top of each experiment's `main()` and document in a comment exactly which components are stochastic (autoreject AR fitting) vs. deterministic (Stage B median, Stage C threshold application). This prevents "why are my numbers slightly different?" confusion for any future contributor.

### 🟢 E5. Parallelise across channel groups within a session, not just sessions

In `run_exp1_raja.py → _process_one_session`, the inner loop over `group_names` is serial within a worker process. For sessions with many groups (e.g., `GROUPS_TO_RUN=None` → ~20 groups), the single-session wall time is long. Switch the inner loop to a `ThreadPoolExecutor` with 4 threads (groups share the same raw data already loaded; the GIL is released during autoreject's numpy-heavy operations). This would reduce Exp1's per-session time by ~3–4× on multi-core machines.
