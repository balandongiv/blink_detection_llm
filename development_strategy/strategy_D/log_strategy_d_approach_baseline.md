# Strategy D Log: Baseline

This file is the repo-local baseline note for Strategy D. Its job is to keep
one clear record of:

- what the current Strategy D baseline is
- why this path should be treated as Strategy D instead of Strategy C
- which historical Strategy C log entries still matter as comparison context
- what is currently runnable in this worktree
- how to rerun the available baseline-related commands

---

## Strategy: Strategy D Baseline Reference

**Date**: 2026-04-04  
**Proposal**: Reclassify the current frontal-consensus plus selective-rescue baseline as Strategy D and keep one repo-local baseline note under `development_strategy/strategy_D/` so future experiments can distinguish the non-`autoreject` path from the true Strategy C path.  
**Rationale**: This currently runnable path does not implement, use, or tap `autoreject` logic. It relies on filtered epoch preparation, the legacy `get_blink_position(...)` detector, frontal consensus aggregation, and a selective `EEG F7 - Pz` rescue rule. That makes it inconsistent with the stated Strategy C definition, which is `autoreject`-based, so it is clearer to treat this as Strategy D.  
**Status**: Active reference

### Implementation

**Files Changed**:
- `development_strategy/strategy_D/log_strategy_d_approach_baseline.md`: Repo-local baseline reference note for the non-`autoreject` frontal-consensus plus rescue path, reclassified as Strategy D.

**Reference Sources**:
- `development_strategy/strategy_C/obs/log_strategy_c_approach1.md`
- `development_strategy/strategy_C/obs/log_strategy_c_approach2.md`
- `development_strategy/strategy_C/obs/log_strategy_c_approach3.md`
- `development_strategy/strategy_c_step1_reference_benchmark.md`
- `scripts/explore_strategy_c_stage1_fn_recovery.py`

**Commits**:
- None yet.

### Performance & Metrics

**Before**: There was no repo-local baseline note that separated the non-`autoreject` frontal-consensus path from the true Strategy C `autoreject` concept. Baseline facts were scattered across the Strategy C approach logs and the Step 1 benchmark note.  
**After**: This file now acts as the single baseline note for Strategy D under `development_strategy/strategy_D/`.  
**Change**:

**Historical Strategy C baseline retained as comparison context**:
- Stage 1 autoreject union baseline, as recorded in `development_strategy/strategy_C/obs/log_strategy_c_approach1.md` and reused in `development_strategy/strategy_C/obs/log_strategy_c_approach3.md`:
  - `TP=135`
  - `FN=0`
  - `FP=717`
  - `recall=1.0`
  - `n_candidates=852`
- Historical final staged baseline from `development_strategy/strategy_C/obs/log_strategy_c_approach1.md`:
  - Stage 6 result: `TP=135`, `FN=0`, `FP=616`, `recall=1.0`

**Reference Step 1 external baselines from `development_strategy/strategy_c_step1_reference_benchmark.md`**:
- Strategy A Step 1:
  - `TP=133`
  - `FP=32`
  - `FN=0`
  - `precision=0.80`
  - `recall=1.0`
  - `f1=0.89`
- Strategy B Step 1:
  - `TP=131`
  - `FP=14`
  - `FN=2`
  - `precision=0.903`
  - `recall=0.98`
  - `f1=0.94`

**Current reproducible Step 1 runner available in this worktree for Strategy D**:
- `scripts/explore_strategy_c_stage1_fn_recovery.py`
- On the current workspace, that script reports:
  - Strategy A local rerun: `TP=133`, `FP=32`, `FN=0`
  - Strategy B local rerun: `TP=133`, `FP=28`, `FN=0`
  - Strategy D 7-channel frontal median candidate: `TP=132`, `FP=25`, `FN=1`
  - Strategy D 7-channel frontal median + selective `EEG F7 - Pz` rescue: `TP=133`, `FP=25`, `FN=0`

### Implementation Benefits

**Why keep a dedicated baseline note at all**:
- It separates the non-`autoreject` baseline definition from the true Strategy C concept, so future work does not confuse a pyblinker-based consensus path with the `autoreject`-based Strategy C design.
- It makes the difference between historical Strategy C references and the current Strategy D candidate explicit.

**Why this should be Strategy D, not Strategy C**:
- The current runnable path never imports `autoreject` and never calls `compute_thresholds(...)`, `AutoReject`, or `RejectLog` logic.
- Its detection core is built from pyblinker and Strategy A helper code: filtered epoch preparation, `BlinkDetector._build_detector_params(...)`, `get_blink_position(...)`, epoch remapping, and a custom selective rescue rule.
- Because the implementation does not satisfy the stated Strategy C requirement of using `autoreject`-style threshold learning, treating it as Strategy D is the cleaner classification.

**Current exploratory Step 1 implementation benefits for Strategy D**:
- Versus Strategy A, this approach is a better Stage 1 foundation because it separates the candidate backbone from the blind-spot recovery rule. The 7-channel frontal median provides the main detector, while the selective `EEG F7 - Pz` rescue lane stays narrow and replaceable. That is easier to extend than keeping all Step 1 behavior inside one detector path.
- Versus Strategy A, it also reduces dependence on a single fixed signal choice. The primary detector is an explicit multi-channel frontal consensus signal, which is closer to the intended Strategy C design of using subject-specific frontal evidence instead of one channel standing in for the whole problem.
- Versus Strategy B, this approach keeps the decision logic inside the project. The backbone signal, the seed-cluster rule, and the rescue lane are all inspectable project artifacts instead of mainly relying on one imported event finder call.
- Versus Strategy B, it preserves a candidate-region output that is easier to pass into later Stages 2 to 6 and easier to debug when a blink is missed, because the failure can be localized to the frontal backbone, the seed detector, or the rescue filter.
- The main implementation caveat is that this is still only an exploratory runner. The design advantage is real at the Step 1 logic level, but it is not yet realized in a staged Strategy D pipeline until the new mode is wired into production code.

**Implementation benefits beyond metrics**:
- When judging this Strategy D Step 1 path, do not look only at `TP`, `FP`, and `FN`. There are also implementation-level benefits that can make it the better foundation even when two detectors are numerically close.

**Against Strategy A**:
- Strategy A Step 1 is simple and strong on recall, but it is mostly a single-detector path built around one legacy threshold-crossing routine on one prepared signal.
- A good Strategy D Step 1 can be a better implementation foundation because it can combine multiple frontal channels into one explicit candidate backbone instead of depending on one fixed channel choice.
- It can add narrow rescue lanes for known blind spots without replacing the main detector.
- It can preserve one stable candidate-region output contract while still evolving the internal candidate logic.
- It gives a cleaner path to later long-closure support because Stage 1 is already framed as a modular candidate generator rather than a single hardcoded detector.

**Against Strategy B**:
- Strategy B Step 1 uses `mne.preprocessing.find_eog_events(...)`, which is useful as a baseline, but it is a less controllable implementation base for this project.
- A good Strategy D Step 1 can be a better implementation foundation because it keeps the detector logic inside the project rather than delegating the core candidate generator to an external event finder.
- It can expose intermediate reasoning such as channel support, consensus signal choice, seed clusters, and rescue logic, which makes debugging easier.
- It produces candidate regions in a form that is easier to align with downstream Stages 2 to 6 than a peak-only event list.
- It can be tuned in project terms, frontal consensus rules, learned thresholds, and selective rescue paths, instead of mainly adjusting an imported event detector's settings.

**Practical rule**:
- If two Step 1 candidates are close on metrics, prefer the one that preserves Strategy A's recall target, is easier to inspect and debug than Strategy B, keeps a stable candidate-region interface for downstream Stages 2 to 6, and can absorb targeted rescue logic without becoming a large monolithic rule set.

**Current limitation**:
- The historical full Strategy C baseline is not fully runnable from the current worktree, because the older pipeline modules and historical helper scripts referenced by the old logs are not all present anymore.
- The current Strategy D runner still has a historical name, `scripts/explore_strategy_c_stage1_fn_recovery.py`, even though the implementation fits Strategy D better than Strategy C.
- Because of that, this baseline note remains partly a documented reclassification and partly a directly runnable baseline.

### Issues Encountered

- **Issue 1**: The old Strategy C logs describe runnable baseline scripts such as `scripts/compare_step1_strategies.py` and `scripts/validate_epoch_pipeline.py`, but those files are not present in the current worktree.
  - *Resolution*: This baseline note explicitly distinguishes between historical baseline commands and the commands that are currently runnable.
  - *Impact*: The note is accurate for the present repo state and does not pretend that the older full baseline can be rerun unchanged.
  - *Status*: Resolved in documentation.

- **Issue 2**: The current runnable path was originally documented as Strategy C follow-up work even though it does not use `autoreject`.
  - *Resolution*: This file reclassifies that path as Strategy D while still preserving the historical Strategy C logs as comparison evidence.
  - *Impact*: Strategy naming is now better aligned with the actual implementation logic.
  - *Status*: Resolved in documentation.

## Code Flowchart

This flowchart describes the **Strategy D path only** in the current runnable
baseline-related runner:

- `python scripts/explore_strategy_c_stage1_fn_recovery.py`

It starts from loading the `.fif` file and ends at the final Strategy D result:

- 7-channel frontal median candidate
- 7-channel frontal median + selective `EEG F7 - Pz` rescue

```text
Load dev FIF + reference CSV
  |
  +--> main()
        in scripts/explore_strategy_c_stage1_fn_recovery.py
  |
  +--> _load_slice(FRONTAL_MEDIAN_CHANNELS)
        - read first 5 epochs from sample_data/dev_epo.fif
        - pick 7 frontal channels:
          Fp1, Fp2, F7, F8, F3, Fz, F4
        - preprocess epoch data
        - find valid epoch indices
        - load reference blink table
  |
  +--> prepare_epoch_detection_input(...)
        in pyblinker/epoch_detection_strategy_a/epoch_blink_pipeline.py
        - load epoch tensor
        - apply legacy blinker bandpass
        - keep prepared filtered data for all chosen frontal channels
  |
  +--> get_valid_epoch_indices(...)
        in pyblinker/epoch_detection_strategy_a/bad_epoch_utils.py
        - decide which epochs contribute to the run
  |
  +--> load_reference_blink_table(...)
        + filter_reference_to_valid_epochs(...)
        in pyblinker/epoch_detection_strategy_a/epoch_validation.py
        - load sample_data/dev_epo_annotations_5_epochs.csv
        - keep only reference rows for valid epochs
  |
  +--> BlinkDetector._build_detector_params(...)
        in pyblinker/blinker/pyblinker.py
        - build detector parameter dictionary
        - set sfreq for downstream detection
  |
  +--> Strategy D backbone signal
        in scripts/explore_strategy_c_stage1_fn_recovery.py
        - compute median across the 7 frontal channels
        - flatten epoch-wise median signal into one concatenated 1D signal
  |
  +--> _detect_legacy_candidates(...)
        -> get_blink_position(...)
        in scripts/explore_strategy_c_stage1_fn_recovery.py
        and pyblinker/blinker/get_blink_positions.py
        - run legacy threshold-crossing detector on the frontal-median signal
        - produce candidate blink intervals
  |
  +--> _map_candidates(...)
        -> map_concatenated_blinks_to_epochs(...)
        in scripts/explore_strategy_c_stage1_fn_recovery.py
        and pyblinker/epoch_detection_strategy_a/epoch_channel_processor.py
        - map concatenated detections back to epoch-local onset/duration
  |
  +--> match_blink_tables(...)
        in pyblinker/epoch_detection_strategy_a/epoch_validation.py
        - compare frontal-median detections against reference CSV
        - compute TP / FP / FN / precision / recall / f1
  |
  +--> _build_selective_rescue_lane(...)
        in scripts/explore_strategy_c_stage1_fn_recovery.py
        - take EEG F7 - Pz only
        - run a looser seed detector on concatenated F7
        - cluster nearby micro-seed events
        - keep only narrow uncovered blind-spot style clusters
        - open a local +-0.35 s window around cluster center
        - rerun low-threshold local detector inside that window
        - keep rescued intervals that satisfy duration and center constraints
  |
  +--> _dedup_union(...)
        in scripts/explore_strategy_c_stage1_fn_recovery.py
        - merge frontal-median candidates + rescue candidates
        - remove duplicates by epoch/onset/overlap matching
  |
  +--> match_blink_tables(...)
        in pyblinker/epoch_detection_strategy_a/epoch_validation.py
        - compare merged Strategy C result against reference CSV
        - compute final Strategy D metrics
  |
  +--> Print final Strategy D result
        in main()
        - frontal median metrics
        - frontal median + selective F7 rescue metrics
```

### Python code responsible

- `scripts/explore_strategy_c_stage1_fn_recovery.py`
  - `main()`: top-level Strategy D run orchestration
  - `_load_slice(...)`: loads the FIF slice, selected channels, and reference table
  - `_detect_legacy_candidates(...)`: wrapper for Stage 1 candidate generation
  - `_map_candidates(...)`: wrapper for epoch-local mapping
  - `_build_selective_rescue_lane(...)`: Strategy D rescue logic for the blind-spot event
  - `_dedup_union(...)`: merges backbone and rescue outputs into the final Strategy D candidate table

- `pyblinker/epoch_detection_strategy_a/epoch_blink_pipeline.py`
  - `prepare_epoch_detection_input(...)`: prepares filtered epoch arrays from the FIF data

- `pyblinker/epoch_detection_strategy_a/bad_epoch_utils.py`
  - `get_valid_epoch_indices(...)`: decides which epochs are valid

- `pyblinker/epoch_detection_strategy_a/epoch_channel_processor.py`
  - `map_concatenated_blinks_to_epochs(...)`: converts concatenated detections back to epoch-local timing

- `pyblinker/epoch_detection_strategy_a/epoch_validation.py`
  - `load_reference_blink_table(...)`: loads the reference CSV
  - `filter_reference_to_valid_epochs(...)`: aligns the reference table to valid epochs
  - `match_blink_tables(...)`: computes the final Strategy C evaluation metrics

- `pyblinker/blinker/get_blink_positions.py`
  - `get_blink_position(...)`: legacy threshold-crossing detector used by the current Strategy D backbone and rescue logic

- `pyblinker/blinker/pyblinker.py`
  - `BlinkDetector._build_detector_params(...)`: builds the parameter dictionary used by Strategy D detection

## How to run the Strategy D baseline

### Current repo state

The current worktree does **not** contain all of the historical baseline runner
files referenced by the older Strategy C logs.

In particular, these historical commands are referenced in the old logs, but
their scripts are not currently present in `scripts/`:

```powershell
python scripts/compare_step1_strategies.py
python scripts/validate_epoch_pipeline.py
```

Treat those as **historical commands**, not as currently runnable commands in
this worktree.

### Currently runnable command

The currently available baseline-related runner in this worktree is:

```powershell
python scripts/explore_strategy_c_stage1_fn_recovery.py
```

That command will:

- rerun the local Step 1 Strategy A baseline
- rerun the local Step 1 Strategy B baseline
- run the current 7-channel frontal-median Strategy C candidate
- run the selective `EEG F7 - Pz` rescue variant

### Expected output from the current runner

You should see sections like:

- `Reference Benchmark Targets`
- `Local Baseline Rerun - Strategy A Step 1`
- `Local Baseline Rerun - Strategy B Step 1`
- `Exploratory Strategy C - 7 Channel Frontal Median`
- `Exploratory Strategy C - 7 Channel Frontal Median + Selective F7 Rescue`

### Practical note

If you want to restore the **historical full Strategy C baseline** exactly as
described in the old logs, you will first need to restore the missing Strategy C
pipeline modules and the missing runner scripts that those logs refer to.

For the reclassified non-`autoreject` baseline described in this file, the
currently runnable command remains:

```powershell
python scripts/explore_strategy_c_stage1_fn_recovery.py
```

That script name is historical, but the implementation documented here is now
treated as Strategy D.
