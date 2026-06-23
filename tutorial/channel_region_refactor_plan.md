# Per-dataset region refactor + extended channel experiment — review

**Status:** code written, restructured, and smoke-tested (1 session/dataset). **No full sweep run yet.**
Review this; once you confirm, I run the full sweep (commands in §7).

---

## 0. The finding that drove the design (read first)

The two region files are correctly *named*, but their labels are in each dataset's native
convention, which does **not** match the FIF channel names. Verified against the recordings:

| File | Labels | FIF channels | Matches via |
|------|--------|--------------|-------------|
| `brain_region_raja.yaml` | bare ints `13, 28, …` (EGI HydroCel) | `E1 … E128` | prefix `E` → `E13` |
| `brain_region_cao2018.yaml` | `C3, FC3, Fp1, …` (10‑20) | `FP1, FC3, C3, …` | case-insensitive (`Fp1`→`FP1`) |

With the old exact-string loader **both new files match zero channels and crash**. Fix: a
`resolve_channel_names` normalization layer (E-prefix / case-insensitive; already-correct strings
like `E22` still match). Backward-compatible; also un-breaks ~13 other Raja tutorials.

---

## 1. New layout — all experiment scripts moved to `experiment_script/`

Renamed to the **result-section academic outline** (numbering follows §5, *not* the old
`40/41/42/45` filenames). `git mv` preserved history for the moved files.

| New file | Was | Role (outline §) |
|----------|-----|------------------|
| `experiment_script/exp1_channel_selection_raja.py` | `tutorial/43a_…` (new) | II — channel ablation (Raja) — **runs first** |
| `experiment_script/exp1_channel_selection_cao2018.py` | `tutorial/43b_…` (new) | II — channel ablation (Cao2018) |
| `experiment_script/exp2_strategy_comparison.py` | `tutorial/41_…` | I — main comparison + estimator |
| `experiment_script/exp3_epoch_duration.py` | `tutorial/40_…` | III — robustness |
| `experiment_script/exp4_boundary_tolerance.py` | `tutorial/42_…` | III — robustness |
| `experiment_script/exp5_nmin_sensitivity.py` | `tutorial/45_exp7_…` | III — robustness |
| `experiment_script/exp6_morphological.py` | `tutorial/45_exp6_…` | IV — characterization |
| `experiment_script/exp7_epoch_health_effect.py` | — (new) | III — robustness (preprocessing) |
| `experiment_script/exp8_long_blink_analysis.py` | — (new) | IV — characterization |
| `experiment_script/channel_ablation_utils.py` | — (new) | exp1 engine |
| `experiment_script/butterfly_report.py` | — (new) | exp1 butterfly report |
| `experiment_script/condition_runner_utils.py` | — (new) | exp7/exp8 reuse exp2 runners |
| `experiment_script/__init__.py` | — (new) | package marker |

> **Sequence note:** the channel-selection ablation is now **exp1** (runs first) and the
> strategy comparison is **exp2**; exp3–exp8 keep their numbers.

The supporting post-processing scripts (now `paper_channel_selection_frequency.py`,
`paper_error_structure_session.py`, `paper_epoch_duration_figure.py`, `paper_blink_type_recall.py`,
`paper_result_figures.py`, formerly `47–51`) were also moved here (purpose, paper section, and
which experiment each depends on are documented in `experiment_script/SCRIPTS_OVERVIEW.md`).

> **Resample rate:** the pipeline now downsamples to **100 Hz** (`RESAMPLE_RATE = 100`).
> This is **results-affecting** — the full sweep must be re-run; cached results predating
> this change are invalid.

`tutorial/tutorial_utils.py` stays put (shared by ~20 other tutorials). `scripts/run_orchestration.py`
updated to the new paths. **Stale provenance comments** (`% Source: … tutorial/4x_…`) in
`writing/e_result/*.tex` still need updating — flagged, not yet done (paper edits gated on approval).

---

## 2. Checklist of changes

### Foundation (non-breaking)
- [x] `src/io/eeg_channels.py` — `resolve_channel_names`, `load_brain_region_map`, hardened loader.
- [x] `tutorial/tutorial_utils.py` — `DEFAULT_RAJA_REGION_YAML` / `DEFAULT_CAO_REGION_YAML`;
  `load_cao_raw(…, brain_region_yaml=None)` subsetting; per-dataset `make_dataset_loaders(...)`;
  promoted `valid_epoch_indices_for_pair` / `load_gt_annotations_for_pair`.
- [x] `src/strategy_dbo_drop/core.py` — optional `flagged_valid_epoch_indices_override` (default `None` = unchanged).

### Refactor of the moved main experiments
- [x] exp1 / exp3 / exp4 / exp5 / exp6 — per-dataset region YAML; Murat → Cao2018; shared helpers.
- [x] exp1 default flipped to **Raja+Cao2018** (Murat behind `--use-murat2018`).

### Extended experiment (exp2) — restructured per your feedback
- [x] **Full 3 stages run per channel-selection group** (Stage A→B→C on the channel *subset*, not all channels).
- [x] **median vs mean run for every group** (estimator sweep folded into the channel experiment).
- [x] Stage-A epoch metrics (vs epoch-level GT) **and** downstream event metrics per condition.
- [x] **Butterfly report** — per-subject + all-subject TP/FN/FP blink-region waveforms, per group, for visual inspection.

### Verified
- [x] `py_compile` clean on every file; `exp4/5/6` import-clean after rename.
- [x] Smoke (1 session, ≤12 epochs): exp1, exp3, and exp2 (Raja **and** Cao, incl. butterfly HTML) all run;
  per-group detection now differs (subset pipeline active) and median≠mean.

### NOT done (await confirmation)
- [ ] Full sweep — §7.   - [ ] `writing/` reorder + provenance fixes — §5/§1.   - [ ] Open questions — §3.

---

## 3. Decisions — please confirm or correct

- **Q1 (highest impact). Cao detection now subset to its ~22 region channels** (was all 32) — consistent
  with Raja, but **changes Cao headline numbers** → exp1 must be re-run and the paper tables updated.
  *Alternative:* keep Cao all-channels in exp1 (`cao_region_yaml=None`) and use regions only in exp2.
- **Q2. Murat dropped** from exp3/4/5/6 (kept as `exp1 --use-murat2018`). OK?
- **Q3. exp2 sweep size.** Default = every group × `{median, mean}` × rule `any`. Multi-channel
  agreement rules (`min2`,`min3`) are available via `--rules any,min2,min3` but **off by default** to
  keep the sweep bounded. Want them on by default?
- **Q4. Butterfly scope.** Default renders groups `all, frontal, posterior` at the median centre.
  Configurable via `--butterfly-groups`. Reasonable, or render all groups?

---

## 4. exp2 — what it computes (the extended experiment)

Per session, learn per-channel PTP thresholds once (autoreject is per-channel, so a subset's
thresholds equal the full-montage ones). Then for each **group** × **rule** × **centre**:

- Build a subset detector (only the group's channels) and run the **complete Stage A→B→C**.
- **Stage-A epoch metrics** vs epoch-level GT (epoch = blink-containing iff ≥1 annotated blink):
  precision / recall / F1 / FPR / % flagged.
- **Downstream** best-channel event precision / recall / F1.
- For the requested butterfly groups (centre=median): collect TP/FN/FP blink-region windows →
  `…_butterfly.html` (all-subject + per-subject overlays).

`(all, any, *)` reproduces the standard Proposed pipeline — a built-in sanity baseline.
**Groups:** `all, frontal, frontal_left, frontal_right, central, parietal, occipital, posterior`,
plus `single:<ch>` per frontal channel (`--no-single-frontal` to skip).

**Expected story (from `extende_experiment.md`):** frontal selection keeps recall while cutting
false-positive epochs vs. all-channel `any`; the butterfly plots let you *see* whether a group's
detections are real blinks (clean, time-locked TP morphology) or artefacts (ragged FP morphology).

---

## 5. Proposed result outline (reordered for contrast)

Old order scattered the design-justifying ablations. New order: **contribution → mechanism →
robustness → characterization**.

| Part | Result subsection | Script |
|------|-------------------|--------|
| **I. Contribution** | Strategy comparison: Proposed‑Med/Mean vs BLINKER‑concat, MNE‑annot; estimator median vs mean | `exp1` |
| **II. Mechanism (why it works)** | **Channel-selection ablation** — full pipeline per channel group, median vs mean, with butterfly visual inspection (turns the "any-channel rule is fragile" limitation into a controlled result) | `exp2` |
| **III. Robustness** | Epoch-duration stability · Boundary-tolerance (IoU) stability · `n_min`/Stage‑B fallback · **epoch-health exclusion effect** | `exp3` · `exp4` · `exp5` · `exp7` |
| **IV. Characterization & generalization** | Blink-region morphology (butterfly) · **long-blink (drowsiness) recall** · cross-dataset Raja↔Cao2018 gap (from exp1) · error structure / channel frequency (existing `48`/`47`) | `exp6` · `exp8` · `exp1` · — |

### Why the two new analyses matter (motivation)

* **exp7 — epoch-health exclusion (Part III).** Excluding low-health epochs is a *preprocessing*
  decision applied to every method, not part of any detector. A reviewer will rightly ask whether
  the headline numbers are partly an artefact of that exclusion. exp7 answers it head-on: running
  every condition with and without the exclusion shows (a) how much performance is preprocessing vs
  detector, and (b) whether the proposed method depends on the exclusion *less* than the baselines
  (a robustness claim). It is cheap because the `health_on` side is reused from exp1.
* **exp8 — long-blink recall (Part IV).** In a drowsy-driving context the long eye closures
  (microsleep, ≥0.5 s) are the safety-critical events, yet shape-based detectors (BLINKER,
  MNE-annot) are tuned to short blinks and tend to reject wide-plateau closures. exp8 quantifies the
  normal-vs-long recall gap per detector, turning "our method also handles long closures" from a
  claim into a measured result — and it pairs naturally with the exp6/exp2 butterfly figures that
  *show* the long-closure morphology.

### Reuse, not re-run

Following the same layering as the `47–51` post-processors, the new analyses consume prior outputs
where the settings are identical: **exp7 reuses exp1**'s rows for the `health_on` side
(`--reuse-exp1-csv …`), computing only the `health_off` side. exp8 runs the same valid-epoch
pipeline as exp1/`50` and adds the normal/long split + DBO. See
`experiment_script/SCRIPTS_OVERVIEW.md` → *Reuse of prior results*.

**Why it reads better:** the headline lands first; the *two* design choices that cause the gain
(robust estimator + epoch-screening channel design) come straight after as a single "mechanism"
block; robustness checks then show it isn't cherry-picked; characterization closes. exp2 is the
strongest single addition — it both justifies Stage A and gives a figure (butterfly) you can argue from.

---

## 6. Reasons (summary)

Normalization layer (one fix, also un-breaks other tutorials) · per-dataset region configs (two
montages) · Cao subset for Raja/Cao consistency · shared Cao-aware helpers (no duplication) ·
`flagged_override` lets exp1 (channel ablation) reuse the unchanged Stage B/C · full-3-stages-per-group so each channel
group is a real detector (not just a Stage-A flag over all channels) · median-vs-mean per group so the
estimator claim is tested under every spatial selection · butterfly for visual, figure-able evidence.

---

## 7. Full-sweep commands (run only after you confirm)

> Resample is now **100 Hz** (results-affecting); the full sweep below must be re-run.

```bash
# conda env: pyblinker_worktree_epoch_blink
# Sequence: exp1 (channel selection) runs FIRST, then exp2 (strategy comparison), then exp3..exp8.

# exp1. Channel-selection ablation (full pipeline per group, median vs mean, + butterfly report)
python experiment_script/exp1_channel_selection_raja.py     --out-dir runs/exp1_channel_raja
python experiment_script/exp1_channel_selection_cao2018.py  --out-dir runs/exp1_channel_cao

# exp2. Main strategy comparison (Raja + Cao2018, 30 s) — re-baseline after the Cao subset change
# (output basenames stay legacy exp41_* and feed the paper_* helpers + result.tex + run_orchestration)
python experiment_script/exp2_strategy_comparison.py --epoch-duration-s 30 --out-dir runs/exp2_strategy_30s

# exp3-exp5. Robustness
python experiment_script/exp3_epoch_duration.py             --out-dir runs/exp3_epoch
python experiment_script/exp4_boundary_tolerance.py --epoch-duration-s 30 --out-dir runs/exp4_tolerance
python experiment_script/exp5_nmin_sensitivity.py
# exp7 reuses exp2 (strategy comparison) for the health_on side; only health_off is computed
python experiment_script/exp7_epoch_health_effect.py --out-dir runs/exp7_health \
    --reuse-exp1-csv runs/exp2_strategy_30s/exp41_strategy_comparison_results.csv

# exp6, exp8. Characterization
python experiment_script/exp6_morphological.py --epoch-duration-s 30 --out-dir runs/exp6_morphology
python experiment_script/exp8_long_blink_analysis.py --out-dir runs/exp8_long_blink
```

Quick re-check (no full corpus):
`python experiment_script/exp1_channel_selection_cao2018.py --max-sessions 1 --n-epochs 12 --no-single-frontal --no-multithread`
