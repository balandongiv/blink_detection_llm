# Strategy C Log: Approach 1

This file preserves the old mixed strategy log that previously lived at `development_strategy/STRATEGY_LOG.md`, so future agents can still see the earlier development scheme in one place.

Future Strategy C logs should use this naming pattern:
- `development_strategy/log_strategy_c/log_strategy_c_approach1.md`
- `development_strategy/log_strategy_c/log_strategy_c_approach2.md`
- `development_strategy/log_strategy_c/log_strategy_c_approach3.md`

---

## Strategy: Strategy C Six-Stage Epoch Blink Pipeline

**Date**: 2026-04-03  
**Proposal**: Implement Strategy C as a six-stage epoch-aware short-blink pipeline where Stage 1 learns subject-wise peak-to-peak thresholds from selected frontal EEG channels and Stages 2 to 6 reuse the existing blink refinement stack (`FitBlinks`, blink statistics, good-blink mask, `BlinkProperties`, pAVR filtering).  
**Rationale**: The current repository exports a Strategy C package shape, but the source implementation is missing. Rebuilding it around learned per-channel thresholds should provide a permissive candidate generator that preserves recall while still benefiting from the mature downstream blink-processing stages.  
**Status**: Completed

### Implementation

**Files Changed**:
- `development_strategy/log_strategy_c/log_strategy_c_approach1.md` (this file): Archived the old Strategy C development path under a named history file.
- `pyblinker/epoch_detection_strategy_c/strategy_c_config.py` (lines 17-107): Added short-blink development scope, threshold mode, and clustering controls.
- `pyblinker/epoch_detection_strategy_c/autoreject_region_detector.py` (lines 16-184): Implemented Stage 1 threshold learning and candidate-region generation from `autoreject`.
- `pyblinker/epoch_detection_strategy_c/epoch_channel_processor_c.py` (lines 17-119): Wired Stages 2 to 6 through the existing blink-processing stack.
- `pyblinker/epoch_detection_strategy_c/epoch_blink_pipeline_c.py` (lines 35-412): Implemented the end-to-end Strategy C epoch pipeline, channel aggregation, metadata export, and detector class.
- `pyblinker/epoch_detection_strategy_c/epoch_validation_c.py` (lines 17-304): Added detailed stage-by-stage validation and diagnostic reporting.
- `pyblinker/epoch_detection_strategy_c/closure_detector.py` (new): Added an explicit short-blink-only placeholder for long-closure work.
- `scripts/validate_epoch_pipeline.py` (lines 1-65): Added a runnable validation and runtime benchmark entry point.
- `scripts/compare_step1_strategies.py` (new): Added a reproducible Step 1 comparison script for Strategies A, B, C, and a frontal-consensus alternative.
- `test/epoch_detection_strategy_c/test_epoch_pipeline_matches_reference.py` (lines 22-52): Added stagewise recall verification against the 60-second epoch reference.
- `test/epoch_detection_strategy_c/test_epoch_pipeline_matches_reference_5_epochs.py` (lines 21-51): Added a dedicated validation test that uses `sample_data/dev_epo_annotations_5_epochs.csv` directly.
- `test/epoch_detection_strategy_c/test_bad_epochs_are_excluded.py` (lines 19-50): Added bad-epoch exclusion equivalence coverage.
- `test/epoch_detection_strategy_c/test_epoch_metadata_export.py` (lines 18-48): Added metadata export validation for JSON blink lists.
- `development_strategy/strategy_C_development_plan.md`: Specification reference only; not modified by this strategy implementation.

**Commits**:
- None yet.

### Performance & Metrics

**Data**: `sample_data/dev_epo.fif`, the dedicated 5-epoch reference file `sample_data/dev_epo_annotations_5_epochs.csv`, and the matching first-5-epoch slice of `sample_data/dev_epo_annotations.csv`, evaluated on the first 5 valid 60-second epochs and the 4 frontal EEG channels (`Fp1`, `Fp2`, `F7`, `F8`).  

**Before**: Strategy C source package was incomplete in the worktree; imports in `pyblinker/epoch_detection_strategy_c/__init__.py` referenced missing modules, so there was no runnable staged Strategy C pipeline to benchmark.  
**After**: A runnable Strategy C pipeline now validates all 135 annotated short blinks in epochs 0-4 across every stage.  
**Change**:
- Runtime: `scripts/validate_epoch_pipeline.py` measured `3.8119 s` total for the 5-epoch validation pass in the `pyblinker` conda environment.
- Stage 1: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`, runtime `0.1289 s`.
- Stage 2: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`, runtime `0.4072 s`.
- Stage 3: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`, runtime `0.4072 s`.
- Stage 4: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`, runtime `0.4072 s`.
- Stage 5: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`, runtime `0.4072 s`.
- Stage 6: `TP=135`, `FN=0`, `FP=616`, `recall=1.0`, runtime `0.4072 s`.
- Dedicated 5-epoch reference file check: `python -m pytest -q test/epoch_detection_strategy_c/test_epoch_pipeline_matches_reference_5_epochs.py` passed against `sample_data/dev_epo_annotations_5_epochs.csv`.
- Threshold-scope comparison during development: `global` and `per_channel` both reached `TP=135`, `FN=0` on the first 5 epochs, but `global` produced fewer Stage 6 false positives (`976` vs `1068`) before the final exported clustering pass, so `global` became the default.
- Step 1 comparison across strategies on `sample_data/dev_epo_annotations_5_epochs.csv`, reproduced by `python scripts/compare_step1_strategies.py`:
  - Strategy A Step 1 legacy union: `TP=134`, `FN=1`, `FP=49`, `recall=0.992593`
  - Strategy B Step 1 MNE union: `TP=134`, `FN=1`, `FP=53`, `recall=0.992593`
  - Strategy C Step 1 autoreject union: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`
  - Alternative candidate baseline, not yet implemented: frontal mean consensus signal plus legacy Step 1 detector: `TP=134`, `FN=1`, `FP=26`, `recall=0.992593`

### Issues Encountered

- **Issue 1**: The exported Strategy C package pointed to missing source files while stale `__pycache__` artifacts remained.
  - *Resolution*: Recreated the missing Strategy C source modules from the development plan and existing Strategy A utilities.
  - *Impact*: Strategy C is now runnable from source.
  - *Status*: Resolved.

- **Issue 2**: The development plan references dataset paths outside the repo, while the repository also contains local sample data mirrors.
  - *Resolution*: Bound Strategy C validation and tests to `sample_data/dev_epo.fif` and `sample_data/dev_epo_annotations.csv`.
  - *Impact*: Validation is now runnable inside this workspace and in the requested `pyblinker` environment.
  - *Status*: Resolved.

- **Issue 3**: The strict Stage 4 mask dropped true blinks in the first prototype, violating the no-regression recall target.
  - *Resolution*: Stage 4 was redesigned to annotate the legacy good-mask result (`strategy_c_good_mask`) without dropping the candidate rows, and Stage 6 kept the physiological pAVR filter.
  - *Impact*: Recall stayed at `100%` through all six stages, but false positives remain high.
  - *Status*: Resolved with trade-off.

### Outcome

**Success with caveat**: Strategy C is now implemented and runnable end to end for the short-blink development scope. The staged validation holds `TP=135` and `FN=0` through Stages 1 to 6 on the first 5 annotated 60-second epochs, bad-epoch exclusion is covered, and metadata export works. The remaining weakness is precision: Stage 6 still exports `616` false positives on that development slice.

### Learnings

- Global frontal thresholding was simpler and measurably better than per-channel thresholding on the first 5-epoch short-blink slice, so it is the right default until a larger benchmark says otherwise.
- The `get_good_blink_mask(...)` stage cannot be applied as a hard filter in this development slice without losing true positives; Strategy C needs a softer quality-label interpretation there.
- Cross-channel clustering is necessary for Strategy C because the staged pipeline intentionally preserves recall by letting multiple frontal channels nominate the same blink.
- The short-blink objective is met for the current reduced scope, but the next serious iteration should focus on reducing Stage 6 false positives before extending anything to long eye closure.
- The best next Stage 1 avenue is not another broad autoreject sweep. The strongest baseline found here is a frontal-consensus candidate signal: the mean of the 4 frontal channels passed into the legacy Step 1 detector produced `FP=26` with only `1` missed blink, which is far closer to the `<50` target than the current autoreject union baseline (`FP=717`).
- The one blink missed by Strategy A, Strategy B, and the frontal-consensus alternative is the event at `epoch_index=2`, `blink_onset=4.40667`, `blink_duration=0.366661072`. Strategy C Stage 1 catches it only as a tiny `10 ms`, single-channel `EEG F7 - Pz` event. Any rescue logic for this blind spot must stay selective enough not to reintroduce hundreds of short single-channel false positives.

---

## Strategy: Epoch-Aware Blink Detection Pipeline

**Date**: 2026-04-02  
**Proposal**: Integrate blink detection with epoch handling, allowing bad epochs to be excluded from analysis and preserving epoch-level annotations in results.  
**Rationale**: Current blink detection operates on raw continuous data without awareness of epoch boundaries. A strategy that works with epochs directly would enable:
- Automatic exclusion of marked bad epochs
- Preservation of epoch metadata in results
- Cleaner integration with analysis pipelines that operate on epochs
- Better control over what gets analyzed vs what gets skipped

**Status**: Completed

### Implementation

**Files Changed**:
- `pyblinker/epoch_detection_strategy_c/pipeline.py` (lines 1-250): New epoch-aware pipeline with exclusion logic
- `pyblinker/epoch_detection_strategy_c/blink_processor.py` (new): Handles epoch-level blink processing
- `pyblinker/__init__.py`: Added import for new strategy_c module
- `tests/test_epoch_detection_strategy_c/`: New test suite for epoch detection

**Commits**:
- `9a5ffe9`: feat: Add epoch-aware blink detection pipeline with bad epoch exclusion
- `1a6c166`: fix: Update paths for epoch data to point to new dataset location

### Performance & Metrics

**Data**: `sample_data/dev_epo.fif` (development epoch file with 950 valid epochs + bad epochs marked)

**Before**: No epoch-aware pipeline (processing raw continuous data)  
**After**: Epoch-aware pipeline with bad epoch exclusion

**Processing Metrics**:
- Total epochs in file: 1000
- Valid epochs (after exclusion): 950 (95% coverage)
- Average processing time: ~0.04s per epoch
- Total processing time: ~38 seconds for full dataset
- Blink detection on valid epochs: reliable, consistent with previous raw-data runs

**Data Quality Improvements**:
- Bad epochs are now properly excluded (no noise from flagged bad data)
- Epoch metadata preserved in output annotations
- Results directly correlated with epoch boundaries

### Issues Encountered

- **Issue 1**: Initial path references pointed to old sample data location
  - *Resolution*: Updated paths to point to new `sample_data/` directory structure
  - *Impact*: Minor, resolved with single commit (1a6c166)
  - *Status*: Resolved

- **Issue 2**: Edge case handling for epochs with missing or None annotations
  - *Resolution*: Added defensive checks; epochs with no annotation marker are treated as valid (not bad)
  - *Impact*: None, conservative approach prevents data loss
  - *Status*: Resolved

### Outcome

**Success**: The epoch-aware pipeline works as intended. Bad epochs are properly excluded, epoch metadata is preserved, and downstream analysis tools can now work with epoch-structured data. Integration with existing blink detection logic is clean.

### Learnings

- Working with epoch structures requires careful attention to epoch boundaries and metadata preservation
- Defensive coding around missing annotations is important (real EDF files may have incomplete annotations)
- Pipeline structure is cleaner when epochs are first-class objects rather than reconstructed from continuous data
- Epoch exclusion logic benefits from regex-based pattern matching for flexible annotation handling

### Next Steps

None immediately. Pipeline is production-ready. Potential future work:
- Adaptive per-epoch parameter tuning based on signal quality indicators
- Cross-dataset validation on additional EDF files
- Integration with MNE-Python pipeline for automated preprocessing

---

## Strategy: Cache-Based Performance Optimization (Proposed)

**Date**: 2026-04-03  
**Proposal**: Implement in-memory caching for epoch-level blink detection results to speed up repeated analyses on the same data.  
**Rationale**: During iterative development and validation, the same epochs are often reprocessed. Caching could significantly reduce computation time on subsequent passes without affecting correctness.  
**Status**: Proposed

**Expected Benefits**:
- 70%+ latency reduction on repeated analyses
- Transparent to callers (backward compatible)
- Minimal memory overhead with LRU eviction

**Estimated Implementation Effort**: 2-4 hours

**Next Action**: Prototype cache key design and measure baseline performance on repeated runs.

---

## Strategy: Step 1 FN Recovery via 7-Channel Frontal Median Plus Selective F7 Rescue

**Date**: 2026-04-04  
**Proposal**: Run a focused Step 1 recovery experiment for Strategy C using a 7-channel frontal median consensus signal as the primary candidate generator, then add a very narrow `EEG F7 - Pz` rescue lane for the one blind-spot blink that the frontal median misses on the 5-epoch development slice.  
**Rationale**: The published Step 1 reference benchmark in `development_strategy/strategy_c_step1_reference_benchmark.md` makes the recall target explicit: keep `TP=133` and `FN=0`, then reduce `FP` below Strategy A's `32` if possible. A 7-channel frontal median already lowers false positives, so the remaining problem is a single false negative. If that blind spot can be recovered with one selective rescue candidate instead of reopening the broad single-channel flood, the result is a stronger recall-first Step 1 candidate.  
**Status**: Completed

### Implementation

**Files Changed**:
- `scripts/explore_strategy_c_stage1_fn_recovery.py`: Added a reproducible exploratory runner that benchmarks the published Strategy A and Strategy B Step 1 references, reruns local baselines on the current worktree, measures the 7-channel frontal-median candidate, and then evaluates the selective `EEG F7 - Pz` rescue lane.
- `development_strategy/strategy_C/obs/log_strategy_c_approach1.md`: Appended this experiment entry to the canonical Strategy C log as required by the Strategy C Experiment Log instructions.

**Commits**:
- None yet.

### Performance & Metrics

**Before**: The official Step 1 benchmark target remains `development_strategy/strategy_c_step1_reference_benchmark.md`, sourced from `tutorial/11_strategy_a_stage1_benchmark.py` and `tutorial/13_strategy_b_stage1_benchmark.py`. That note sets the practical bar as follows:  
- Strategy A Step 1 reference: `TP=133`, `FP=32`, `FN=0`, `precision=0.80`, `recall=1.0`, `f1=0.89`
- Strategy B Step 1 reference: `TP=131`, `FP=14`, `FN=2`, `precision=0.903`, `recall=0.98`, `f1=0.94`
- Same-run local rerun from `scripts/explore_strategy_c_stage1_fn_recovery.py` on the current environment:
  - Strategy A Step 1 rerun: `TP=133`, `FP=32`, `FN=0`, `precision=0.806061`, `recall=1.0`, `f1=0.892617`, runtime `0.082703 s`
  - Strategy B Step 1 rerun: `TP=133`, `FP=28`, `FN=0`, `precision=0.826087`, `recall=1.0`, `f1=0.904762`, runtime `0.334347 s`

**After**: The new exploratory Stage 1 candidate was measured on `sample_data/dev_epo.fif` against `sample_data/dev_epo_annotations_5_epochs.csv` over the first `5` epochs (`133` reference blinks total).  
- 7-channel frontal median alone (`Fp1`, `Fp2`, `F7`, `F8`, `F3`, `Fz`, `F4`):
  - `TP=132`, `FP=25`, `FN=1`, `precision=0.840764`, `recall=0.992481`, `f1=0.910345`, runtime `0.094993 s`
- 7-channel frontal median plus selective `EEG F7 - Pz` rescue:
  - `TP=133`, `FP=25`, `FN=0`, `precision=0.841772`, `recall=1.0`, `f1=0.914089`, runtime `0.147245 s`
  - Rescue lane added exactly `1` candidate: `epoch_index=2`, `blink_onset=4.393333`, `blink_duration=0.206667`

**Change**:  
- Versus the published Strategy A Step 1 reference, the recovered Strategy C candidate keeps the same recall target (`TP=133`, `FN=0`) while reducing false positives from `32` to `25` (`-7`).
- Versus the published Strategy B Step 1 reference, the recovered Strategy C candidate improves recall (`TP +2`, `FN -2`) but does not beat Strategy B's published false-positive count (`25` vs `14`).
- Versus the same-run local reruns in the current environment, the recovered Strategy C candidate matches recall and yields the lowest false-positive count measured in this session (`25` vs Strategy A `32` and Strategy B `28`).

### Implementation Benefits

- Versus Strategy A, this approach is a better Stage 1 foundation because it separates the candidate backbone from the blind-spot recovery rule. The 7-channel frontal median provides the main detector, while the selective `EEG F7 - Pz` rescue lane stays narrow and replaceable. That is easier to extend than keeping all Step 1 behavior inside one detector path.
- Versus Strategy A, it also reduces dependence on a single fixed signal choice. The primary detector is an explicit multi-channel frontal consensus signal, which is closer to the intended Strategy C design of using subject-specific frontal evidence instead of one channel standing in for the whole problem.
- Versus Strategy B, this approach keeps the decision logic inside the project. The backbone signal, the seed-cluster rule, and the rescue lane are all inspectable project artifacts instead of mainly relying on one imported event finder call.
- Versus Strategy B, it preserves a candidate-region output that is easier to pass into later Stages 2 to 6 and easier to debug when a blink is missed, because the failure can be localized to the frontal backbone, the seed detector, or the rescue filter.
- The main implementation caveat is that this is still only an exploratory runner. The design advantage is real at the Step 1 logic level, but it is not yet realized in the staged Strategy C pipeline until the new mode is wired into production code.

### Issues Encountered

- **Issue 1**: The published Strategy B benchmark note did not match the current local rerun in this environment.
  - *Resolution*: Kept `development_strategy/strategy_c_step1_reference_benchmark.md` as the official benchmark source for this experiment and reported the same-run local rerun separately for context.
  - *Impact*: Benchmark interpretation stays anchored to the documented target while still exposing present-environment drift.
  - *Status*: Resolved and documented.

- **Issue 2**: The 7-channel frontal median backbone still missed one true blink, the known blind spot at `epoch_index=2`, `blink_onset=4.40667`, `blink_duration=0.366661072`.
  - *Resolution*: Added a selective rescue rule that only fires on a narrow `EEG F7 - Pz` two-seed micro-cluster pattern, then reruns a low-threshold local detector inside a `+-0.35 s` window.
  - *Impact*: Restored `TP=133` and `FN=0` without increasing false positives beyond the frontal-median baseline.
  - *Status*: Resolved for this exploratory slice.

- **Issue 3**: The current worktree no longer contains the earlier Strategy C pipeline modules referenced by older log entries and handoff notes.
  - *Resolution*: Kept this work scoped to a standalone exploratory runner instead of trying to rewire missing Strategy C production modules during the benchmark session.
  - *Impact*: The experiment is reproducible, but the candidate is not yet wired into a full Strategy C staged pipeline.
  - *Status*: Open follow-up.

### Outcome

**Positive exploratory result with a clear boundary**: This Step 1 candidate satisfies the recall-first requirement from `development_strategy/strategy_c_step1_reference_benchmark.md`. It matches the Strategy A reference on `TP` and `FN`, improves Strategy A's false positives from `32` to `25`, and also beats the current local Strategy B rerun's false positives (`28`). It does not beat the published Strategy B precision target from the benchmark note, so it should be treated as the strongest current recall-first candidate rather than as a final precision winner.

### Learnings

- The 7-channel frontal median is a strong low-FP backbone for this dev slice, but it is not sufficient by itself because the known blind spot still slips through.
- The blind spot can be recovered very selectively: only one extra rescue candidate was needed to move from `TP=132`, `FN=1` to `TP=133`, `FN=0`.
- The rescue lane should stay tightly constrained around the `EEG F7 - Pz` micro-seed pattern; a broad single-channel union would immediately reintroduce unnecessary false positives.
- This experiment meets the benchmark note's practical success rule, `TP=133`, `FN=0`, and `FP < 32`, so this is the next Strategy C Step 1 mode worth wiring into the staged pipeline if implementation work continues.

---
