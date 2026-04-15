# Strategy C Log: Rejection Threshold

This file is the repo-local starter note for a Strategy C branch that explores
the high-level `autoreject.get_rejection_threshold(...)` API instead of the
current `compute_thresholds(...)` path.

Its purpose is to give a future agent a direct starting plan for testing that
alternative API.

---

## Strategy: Strategy C Rejection Threshold

**Date**: 2026-04-04  
**Proposal**: Explore a Strategy C variant that uses `autoreject.get_rejection_threshold(...)` as the threshold-learning entry point instead of `compute_thresholds(...)`, then translate the learned rejection threshold into a Stage 1 candidate-generation backbone suitable for the current project pipeline.  
**Rationale**: The Strategy C development plan explicitly mentions `get_rejection_threshold(...)` as one of the `autoreject` APIs worth exploring. This API is closer to the official high-level global-rejection path in `autoreject`, so it deserves a dedicated branch log rather than being mixed into the current per-channel `compute_thresholds(...)` baseline.  
**Status**: Planned

### Implementation

**Current relevant files**:
- `pyblinker/epoch_detection_strategy_c_autoreject.py`
- `development_strategy/strategy_C/strategy_C_development_plan.md`
- `development_strategy/strategy_c_step1_reference_benchmark.md`
- `development_strategy/strategy_C/log_strategy_c_baseline.md`

**Likely files to change for this branch**:
- `pyblinker/epoch_detection_strategy_c_autoreject.py`
  - add a threshold-source mode such as `compute_thresholds` vs `get_rejection_threshold`
  - convert the returned rejection threshold into a project-local Stage 1 backbone or candidate rule
- `tutorial/14_strategy_c_autoreject_first_5_epochs_debug.py`
  - print the threshold-source API and the learned rejection threshold
- possibly add a separate benchmark test for this branch if it becomes promising

**Relevant vendored `autoreject` sources**:
- `get_rejection_threshold(...)`:
  - `/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/autoreject/autoreject/autoreject.py:195`
- `_GlobalAutoReject`:
  - `/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/autoreject/autoreject/autoreject.py:143`
- validation-curve helper:
  - `/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/autoreject/autoreject/autoreject.py:39`

### Known Starting Point

**Current baseline to compare against**:
- uses `compute_thresholds(...)`
- learns per-channel thresholds on 7 frontal channels
- builds a threshold-normalized weighted-median backbone
- result on the 5-epoch benchmark:
  - `TP=133`
  - `FP=23`
  - `FN=0`

**What is different in this branch**:
- the threshold-learning API itself changes
- this branch should not assume the output shape matches `compute_thresholds(...)`
- `get_rejection_threshold(...)` returns a global rejection-threshold dictionary by channel type, not the same per-channel threshold map used by the current baseline

### Exact `autoreject` API To Explore

**API**:
- `get_rejection_threshold(...)`

**Why this is a distinct branch**:
- current baseline API:
  - `compute_thresholds(...)`
- planned branch API:
  - `get_rejection_threshold(...)`

**Core design question for this branch**:
- once `get_rejection_threshold(...)` returns its global threshold output, how should that be translated into Strategy C Stage 1 candidate regions?

This translation is not yet implemented. That is the main development task for
the next agent.

### Possible Translation Strategies

The next agent should likely choose one of these first:

1. **Global normalization path**
   - use the returned EEG rejection threshold `\tau`
   - normalize selected frontal channels by that shared threshold
   - rebuild a frontal consensus backbone
   - run `get_blink_position(...)` on that backbone

2. **Window-crossing path**
   - use the returned threshold as a direct decision scale on local windows
   - mark windows whose frontal signal PTP crosses the learned rejection threshold
   - merge those windows into candidate regions

3. **Hybrid path**
   - use `get_rejection_threshold(...)` to define the global scale
   - keep the current selective rescue lane unchanged
   - compare whether the backbone or window-crossing path is more stable

### Mathematical Formulation

The exact formulation for this branch is **not fixed yet**, but the main likely
starting point is:

\[
\Delta_{e,c} = \max_t x_{e,c}(t) - \min_t x_{e,c}(t)
\]

and a learned shared threshold:

\[
\tau
\]

One straightforward candidate backbone would be:

\[
s_{\text{global}}(t) = \operatorname{median}_c \left( \frac{x_c(t)}{\tau} \right)
\]

Alternative candidate-generation rule:

\[
\text{flag window if } \Delta_{\text{window}} \ge \tau
\]

This note intentionally leaves the exact final formulation open because that is
the unresolved development choice for the branch.

### Development Plan

1. Read the vendored `get_rejection_threshold(...)` code and confirm the exact return structure on EEG data.
2. Decide how to map that returned threshold into a Strategy C Stage 1 candidate rule.
3. Keep the current baseline intact as the control condition.
4. Implement the simplest translation first:
   - probably a shared-threshold frontal consensus backbone
5. Reuse the same 7 frontal channels as the current baseline for the first test.
6. Keep the selective `EEG F7 - Pz` rescue lane unchanged initially.
7. Benchmark on the same 5-epoch reference slice.
8. Compare against the current baseline on:
   - learned threshold value
   - candidate count
   - rescue dependence
   - `TP`
   - `FP`
   - `FN`

### Validation Plan

**Primary development slice**:
- `sample_data/dev_epo.fif`
- `sample_data/dev_epo_annotations_5_epochs.csv`
- first `5` epochs

**Primary benchmark target**:
- current Strategy C baseline:
  - `TP=133`
  - `FP=23`
  - `FN=0`

**Minimum acceptance rule**:
- `FN` must remain `0`
- if `FN > 0`, treat the branch as an exploratory comparison only

### Risks And Open Questions

- `get_rejection_threshold(...)` may be too coarse for the current project because it is not a direct per-channel threshold-learning API like `compute_thresholds(...)`.
- It is not yet known whether the returned threshold aligns naturally with the current weighted-backbone design.
- If the returned threshold is only meaningful as a drop/reject rule, extra design work may be needed to convert it into candidate regions.
- This branch may overlap conceptually with the global-threshold branch, so the next agent should keep their documentation clearly separated.

### Suggested Next Commands

These commands are suggestions for the next agent. They were **not** run for
this note.

```powershell
python tutorial/14_strategy_c_autoreject_first_5_epochs_debug.py
```

```powershell
python -m pytest -q test/epoch_detection_strategy_c_autoreject/test_stage1_benchmark.py
```

### Performance & Metrics

Not available yet. To be filled after the first implementation and benchmark run.

### Issues Encountered

Not available yet. To be filled after the first implementation and benchmark run.

### Outcome

Not available yet. To be filled after the first implementation and benchmark run.

### Learnings

Not available yet. To be filled after the first implementation and benchmark run.
