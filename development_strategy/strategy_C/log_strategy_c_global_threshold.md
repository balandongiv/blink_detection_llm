# Strategy C Log: Global Threshold

This file is the repo-local starter note for a Strategy C branch that explores
one shared global threshold instead of per-channel thresholds.

Its purpose is to give a future agent a concrete starting plan for evaluating a
global-threshold interpretation of the `autoreject` idea.

---

## Strategy: Strategy C Global Threshold

**Date**: 2026-04-04  
**Proposal**: Explore a Strategy C variant that replaces the current per-channel threshold vector `\tau_c` with one shared threshold `\tau` across the selected frontal channels, then rebuilds the Stage 1 backbone and candidate logic around that single global scale.  
**Rationale**: The current Strategy C baseline uses per-channel threshold learning via `compute_thresholds(...)`. Historical Strategy C notes also mention global-threshold thinking, and `autoreject` provides global-threshold logic through validation-curve and global-rejection paths. A single global threshold may simplify the backbone and may reduce channel-to-channel scale instability, but it needs to be benchmarked against the current baseline.  
**Status**: Implemented and benchmarked

### Implementation

**Current relevant files**:
- `pyblinker/epoch_detection_strategy_c_autoreject.py`
- `development_strategy/strategy_C/log_strategy_c_baseline.md`
- `development_strategy/strategy_C/obs/log_strategy_c_approach1.md`
- `development_strategy/strategy_c_step1_reference_benchmark.md`

**Likely files to change for this branch**:
- `pyblinker/epoch_detection_strategy_c_autoreject.py`
  - add a threshold-scope mode such as `per_channel` vs `global`
  - implement one shared threshold path
- `tutorial/14_strategy_c_autoreject_first_5_epochs_debug.py`
  - print the threshold scope and learned global threshold
- optionally add a dedicated benchmark test for the global-threshold variant

**Files changed in this implementation**:
- `pyblinker/epoch_detection_strategy_c_autoreject.py`
  - added `stage1_threshold_scope` with `per_channel` and `global`
  - implemented the `global` path with vendored `autoreject.get_rejection_threshold(...)`
  - exported Stage 1 scope, API, and learned global-threshold metadata
- `tutorial/strategy_c_autoreject_first_5_epochs_common.py`
  - prints the Stage 1 threshold scope, exact learning API, and shared threshold value
- `tutorial/14_strategy_c_autoreject_first_5_epochs_global_threshold.py`
  - added a dedicated runnable entrypoint for the global-threshold branch
- `tutorial/14_strategy_c_autoreject_first_5_epochs_debug.py`
  - clarified that the dedicated global-threshold entrypoint now exists
- `test/epoch_detection_strategy_c_autoreject/test_stage1_benchmark.py`
  - added benchmark coverage for the global-threshold branch

**Relevant vendored `autoreject` sources**:
- `validation_curve(...)`:
  - `/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/autoreject/autoreject/autoreject.py:39`
- `_GlobalAutoReject`:
  - `/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/autoreject/autoreject/autoreject.py:143`
- global threshold helper:
  - `/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/autoreject/autoreject/autoreject.py:195`

### Known Starting Point

**Current baseline that this branch should compare against**:
- per-channel thresholds learned with `compute_thresholds(...)`
- threshold-normalized frontal weighted-median backbone
- narrow `EEG F7 - Pz` rescue lane
- current Step 1 benchmark result:
  - `TP=133`
  - `FP=23`
  - `FN=0`

**Historical Strategy C context**:
- `development_strategy/strategy_C/obs/log_strategy_c_approach1.md` mentions a threshold-scope comparison between `global` and `per_channel`, but the currently runnable worktree does not contain that old implementation.
- This branch should treat that note as historical guidance, not as runnable code.

### Candidate `autoreject` Techniques For This Branch

There are at least two plausible global-threshold interpretations that a future
agent could evaluate:

1. **Manual global threshold from pooled frontal PTP values**
   - pool epoch-wise PTP values across the selected frontal channels
   - optimize one shared `\tau`
   - rebuild the Strategy C backbone using that one `\tau`

2. **Global threshold guided by `autoreject` global-threshold logic**
   - use the `validation_curve(...)` or global-rejection formulation from the vendored code
   - adapt it to the selected frontal-channel slice
   - derive one shared threshold for the branch

This log does not lock the next agent into one of those two implementations,
but it does define the branch objective clearly: one shared threshold, not a
per-channel threshold vector.

### Mathematical Formulation

**Current baseline formulation**:

\[
s(t) = \operatorname{median}_c \left( \frac{x_c(t)}{\tau_c} \right)
\]

**Planned global-threshold alternatives**:

Option A:

\[
s_{\text{global}}(t) = \operatorname{median}_c \left( \frac{x_c(t)}{\tau} \right)
\]

Option B:

\[
s_{\text{global}}(t) = \frac{1}{C} \sum_c \frac{x_c(t)}{\tau}
\]

where:
- `\tau` is one shared global threshold learned from the selected frontal channels
- `C` is the number of channels in the selected frontal set

**Global threshold quantity**:
- one plausible starting point is still the same epoch-level PTP quantity:

\[
\Delta_{e,c} = \max_t x_{e,c}(t) - \min_t x_{e,c}(t)
\]

but the optimization would now produce one threshold:

\[
\tau \text{ instead of } \tau_c
\]

### Development Plan

1. Decide which global-threshold implementation path to try first:
   - manual pooled PTP optimization
   - or explicit `autoreject` global-threshold helper path
2. Add a branch-safe configuration flag so the current per-channel baseline remains available.
3. Learn one shared threshold on the same 7 frontal channels currently used by the baseline.
4. Rebuild the backbone using that one threshold.
5. Keep the selective `EEG F7 - Pz` rescue lane unchanged for the first comparison.
6. Benchmark the result on the same 5-epoch reference slice.
7. Compare against the current baseline on:
   - threshold magnitude
   - candidate count
   - rescue dependence
   - `TP`
   - `FP`
   - `FN`
8. Only after Step 1 behavior is understood, decide whether the downstream flags should be reinterpreted for the global-threshold branch.

### Validation Plan

**Primary slice**:
- `sample_data/dev_epo.fif`
- `sample_data/dev_epo_annotations_5_epochs.csv`
- first `5` epochs

**Primary benchmark to compare against**:
- current Strategy C baseline:
  - `TP=133`
  - `FP=23`
  - `FN=0`

**Minimum acceptance rule**:
- `FN` must remain `0` before this branch is considered promising
- if `FN > 0`, treat the branch as exploratory only

### Risks And Open Questions

- A single global threshold may underfit channel-specific frontal amplitude structure and reduce recall.
- The blind-spot rescue lane may become more or less necessary depending on how the global threshold rescales the backbone.
- If the threshold is too low, false positives may rise quickly because all channels now share the same scale.
- If the threshold is too high, subtle blinks may disappear, especially the known blind spot.
- It is not yet decided whether the global threshold should be learned from:
  - all selected frontal channels pooled equally
  - or a consensus signal built first and thresholded later

### Suggested Next Commands

These commands are suggestions for the next agent. They were **not** run for
this note.

```powershell
python tutorial/14_strategy_c_autoreject_first_5_epochs_debug.py
```

```powershell
python tutorial/14_strategy_c_autoreject_first_5_epochs_global_threshold.py
```

```powershell
python -m pytest -q test/epoch_detection_strategy_c_autoreject/test_stage1_benchmark.py
```

### Performance & Metrics

**Implementation choice used for the first branch run**:
- threshold scope: `global`
- threshold learner: vendored `autoreject.get_rejection_threshold(...)`
- backbone formula:

\[
s_{\text{global}}(t) = \operatorname{median}_c \left( \frac{x_c(t)}{\tau} \right)
\]

**Primary benchmark command**:
- `python tutorial/14_strategy_c_autoreject_first_5_epochs_global_threshold.py`

**Measured global-threshold result on the first 5 epochs**:
- learned global threshold:
  - `tau = 0.000521429811711358`
- Stage 1 candidate count: `158`
- selective rescue candidate count: `1`
- Step 1 metrics:
  - `TP=133`
  - `FP=25`
  - `FN=0`
  - `precision=0.8417721518987342`
  - `recall=1.0`
  - `f1=0.9140893470790378`
  - `epoch_blink_agreement=1.0`
  - `blink_count_agreement=0.0`

**Comparison against the current per-channel Strategy C baseline**:
- current per-channel baseline from `development_strategy/strategy_C/log_strategy_c_baseline.md`:
  - `TP=133`
  - `FP=23`
  - `FN=0`
- global branch delta versus that baseline:
  - `delta_tp = 0`
  - `delta_fp = +2`
  - `delta_fn = 0`

**Acceptance-rule readout**:
- The branch meets the minimum acceptance rule because `FN=0`.
- It does not beat the current per-channel baseline on false positives on this slice, so `per_channel` remains the default mode.

### Issues Encountered

- **Issue 1**: The current runnable Strategy C baseline used `compute_thresholds(...)` only, so the tutorial/debug text incorrectly implied that per-channel learning was the only available Stage 1 path.
  - *Resolution*: Added explicit threshold-scope reporting plus a dedicated global-threshold tutorial entrypoint.
  - *Impact*: The branch can now be rerun and inspected without ambiguity.
- **Issue 2**: Vendored `autoreject.get_rejection_threshold(...)` uses cross-validation, which can be brittle on very small epoch counts.
  - *Resolution*: Added a one-epoch fallback inside the global-threshold builder that uses the observed max PTP directly when fewer than two valid epochs are available.
  - *Impact*: The new branch is safer to call on tiny development slices.

### Outcome

**Mixed result**: The global-threshold branch is now implemented, documented, and benchmarked. On the 5-epoch reference slice it preserves the key recall target, `TP=133` and `FN=0`, but it is slightly worse than the current per-channel baseline on false positives, `FP=25` versus `FP=23`. The branch is therefore viable as an exploratory option, but not strong enough on this slice to replace the default baseline path.

### Learnings

- A single shared frontal threshold learned from vendored `autoreject` global-rejection logic is sufficient to preserve `FN=0` on the documented 5-epoch slice.
- In the current repo-local Strategy C backbone, the global threshold slightly increases Stage 1 candidate count and false positives relative to the per-channel baseline.
- The right product decision for the current worktree is to keep `per_channel` as the default while leaving `global` available as a first-class comparison mode for future larger-slice benchmarking.
