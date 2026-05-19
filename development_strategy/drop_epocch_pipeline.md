# Drop Epoch Pipeline Debug Runbook

This runbook is for line-by-line IntelliJ IDEA or PyCharm debugging of the new epoch-aware blink pipeline.

It follows the smallest-real-input rule:

- real file: `sample_data/dev_epo.fif`
- real reference: `sample_data/dev_epo_annotations.csv`
- one drop ratio: `0.2`
- one seed: `0`
- three real channels only:
  - `EEG X1 - Pz`
  - `EEG Fp1 - Pz`
  - `EEG Fp2 - Pz`
- native sampling:
  - `resample_rate=None`
- no process workers during stepping:
  - `--disable-multiprocessing`

## Preferred IntelliJ entrypoint

Use the existing thin validation entrypoint instead of the full test suite:

`python scripts/validate_epoch_pipeline.py --channels "EEG X1 - Pz" "EEG Fp1 - Pz" "EEG Fp2 - Pz" --drop-ratios 0.2 --seeds 0 --n-jobs 2 --disable-multiprocessing`

Why this path:

- it exercises the real production call order
- it keeps the run small enough to hold in working memory
- it forces a real random-drop path
- it stays serial enough for stepping

## IntelliJ run configuration

Use a Python Script configuration.

- Script path:
  - `scripts/validate_epoch_pipeline.py`
- Working directory:
  - project root
- Parameters:
  - `--channels "EEG X1 - Pz" "EEG Fp1 - Pz" "EEG Fp2 - Pz" --drop-ratios 0.2 --seeds 0 --n-jobs 2 --disable-multiprocessing`
- Environment variables:
  - `_MNE_FAKE_HOME_DIR=$ProjectFileDir$/.mne_home`
- Interpreter:
  - the same interpreter used to run the repo tests

Debugger settings:

- disable any setting that skips library scripts if you want to step into MNE or pandas
- keep "single instance only" off if you want to compare two runs side by side

## Breakpoint order

Set breakpoints in this order before starting:

1. `scripts/validate_epoch_pipeline.py`
   - `main()`
2. `pyblinker/epoch_detection/epoch_validation.py`
   - `load_reference_blink_table()`
3. `pyblinker/epoch_detection/epoch_validation.py`
   - `run_random_drop_validation()`
4. `pyblinker/epoch_detection/epoch_blink_pipeline.py`
   - `prepare_epoch_detection_input()`
5. `pyblinker/epoch_detection/bad_epoch_utils.py`
   - `simulate_bad_epochs()`
6. `pyblinker/epoch_detection/bad_epoch_utils.py`
   - `get_valid_epoch_indices()`
7. `pyblinker/epoch_detection/epoch_blink_pipeline.py`
   - `run_epoch_blink_pipeline()`
8. `pyblinker/epoch_detection/epoch_blink_pipeline.py`
   - `_channel_task_payload()`
9. `pyblinker/epoch_detection/epoch_blink_pipeline.py`
   - `_execute_channel_tasks()`
10. `pyblinker/epoch_detection/epoch_channel_processor.py`
    - `process_concatenated_epoch_channel()`
11. Step Into from `process_concatenated_epoch_channel()` into:
    - `pyblinker/blinker/get_blink_positions.py`
      - `get_blink_position()`
12. Step back and then Step Into:
    - `pyblinker/blinker/fit_blink.py`
      - `FitBlinks.dprocess()`
13. Step Into:
    - `pyblinker/utils/statistics_utils.py`
      - `get_blink_statistic()`
14. Step Into:
    - `pyblinker/utils/statistics_utils.py`
      - `get_good_blink_mask()`
15. Step Into:
    - `pyblinker/blink_features/waveform_features/extract_blink_properties.py`
      - `BlinkProperties`
16. Back to:
    - `pyblinker/epoch_detection/epoch_channel_processor.py`
      - `map_concatenated_blinks_to_epochs()`
17. Back to:
    - `pyblinker/epoch_detection/epoch_result_aggregation.py`
      - `select_candidate_channel_from_results()`
18. Back to:
    - `pyblinker/epoch_detection/epoch_blink_pipeline.py`
      - `_finalize_blink_table()`
19. `pyblinker/epoch_detection/epoch_metadata_export.py`
    - `attach_epoch_blink_metadata()`
20. `pyblinker/epoch_detection/epoch_validation.py`
    - `match_blink_tables()`
21. `pyblinker/epoch_detection/epoch_validation.py`
    - `assert_validation_target()`

## What to inspect at each stop

### 1. `main()`

Inspect:

- resolved epochs path
- resolved reference CSV path
- chosen channel subset
- drop ratio and seed list

Expected:

- one ratio only
- one seed only
- three channels only

### 2. `load_reference_blink_table()`

Inspect:

- `reference.shape`
- first few rows
- renamed columns:
  - `epoch_index`
  - `blink_onset`
  - `blink_duration`

Expected:

- non-empty table
- epoch indices covering the retained sample

### 3. `run_random_drop_validation()`

Inspect:

- `base_epochs.ch_names`
- `len(base_epochs)`
- `prepared` after creation

Expected:

- 50 epochs before dropping
- 3 channels

### 4. `prepare_epoch_detection_input()`

Inspect:

- `picks`
- `channel_names`
- `orig_sfreq`
- `target_sfreq`
- `raw_data.shape`
- `prepared.data.shape`

Expected:

- `target_sfreq == orig_sfreq` for this debug run
- shape should stay `epochs x channels x samples`

### 5. `simulate_bad_epochs()`

Inspect:

- `n_bad`
- `bad_indices`
- updated `metadata["is_bad_epoch"]`

Expected:

- exactly 10 bad epochs for `drop_ratio=0.2` on 50 epochs

### 6. `get_valid_epoch_indices()`

Inspect:

- returned list length
- whether any flagged bad epoch leaked through

Expected:

- 40 valid epochs
- no bad epoch index in the returned list

### 7. `run_epoch_blink_pipeline()`

Inspect:

- `effective_jobs`
- `valid_epoch_indices`
- whether `selected_channel` is empty or not after processing

Expected:

- `effective_jobs >= 2`
- valid list length 40

### 8. `_channel_task_payload()`

Inspect:

- one task per channel
- `epoch_boundaries`
- `concatenated_signal.shape`

Expected:

- 3 tasks
- each concatenated signal spans only valid epochs
- boundary count equals valid epoch count

### 9. `_execute_channel_tasks()`

Inspect:

- whether the run stays in threaded mode for debugging
- no process-worker branch during this debug path

Expected:

- no process spawn noise

### 10. `process_concatenated_epoch_channel()`

Inspect:

- `channel`
- `len(df_positions)`
- `len(good_df)`
- `len(final_blinks)`
- `blink_stats`

Expected:

- this is the best place to compare channels
- channel selection inputs are built here

### 11. `get_blink_position()`

Inspect:

- threshold inputs
- `start_blinks`
- `end_blinks`

Expected:

- monotonic blink windows
- no contribution from dropped epochs because the signal was already reduced to valid epochs only

### 12. `FitBlinks.dprocess()`

Inspect:

- `self.df`
- `self.frame_blinks`
- `left_zero`
- `right_zero`

Expected:

- fitted frame should carry blink geometry columns forward

### 13. `get_blink_statistic()`

Inspect:

- `number_blinks`
- `number_good_blinks`
- `best_median`
- `best_robust_std`
- `good_ratio`

This is the key breakpoint for debugging why channel ranking changes.

### 14. `get_good_blink_mask()`

Inspect:

- how many rows survive
- whether `specified_median` or `specified_std` are `NaN`

If this collapses unexpectedly, the later stages will look empty for that channel.

### 15. `BlinkProperties`

Inspect:

- whether the expected blink property columns are populated
- whether `pos_amp_vel_ratio_zero` looks reasonable

This is the best Step Into point if the issue is morphology or pAVR rejection.

### 16. `map_concatenated_blinks_to_epochs()`

Inspect:

- mapped `epoch_index`
- `blink_onset`
- `blink_duration`
- `valid_epoch_indices`

Expected:

- no mapped row should land on a dropped epoch

### 17. `select_candidate_channel_from_results()`

Inspect:

- aggregated summary frame
- `number_good_blinks`
- `good_ratio`
- `blink_amp_ratio`
- final selected `ch`

This is the breakpoint for channel selection disagreements.

### 18. `_finalize_blink_table()`

Inspect:

- `epoch_selection`
- optional `epoch_id`
- sort order

Expected:

- one long-form row per blink

### 19. `attach_epoch_blink_metadata()`

Inspect:

- `blink_onset`
- `blink_duration`
- `blink_count`
- `candidate_channel`
- `valid_epoch`

Expected:

- JSON-list strings in metadata
- dropped epochs should keep empty lists and `blink_count == 0`

### 20. `match_blink_tables()`

Inspect:

- `tp`
- `fp`
- `fn`
- per-epoch matching behavior

This is the breakpoint for validation disagreements even when detection itself looks right.

### 21. `assert_validation_target()`

Inspect:

- minimum `f1`

Expected:

- should clear `0.90` in this narrowed debug run

## Best step-into boundaries

Use Step Into intentionally at these boundaries:

- from `process_concatenated_epoch_channel()` into `get_blink_position()`
- from `process_concatenated_epoch_channel()` into `FitBlinks.dprocess()`
- from `process_concatenated_epoch_channel()` into `get_blink_statistic()`
- from `process_concatenated_epoch_channel()` into `get_good_blink_mask()`
- from `process_concatenated_epoch_channel()` into `BlinkProperties`

These are all repo-local paths, not remote black boxes:

- `pyblinker/blinker/get_blink_positions.py`
- `pyblinker/blinker/fit_blink.py`
- `pyblinker/utils/statistics_utils.py`
- `pyblinker/blink_features/waveform_features/extract_blink_properties.py`

## Fast branch-specific debug goals

If the bug is about bad-epoch leakage:

- start at `simulate_bad_epochs()`
- then `get_valid_epoch_indices()`
- then `map_concatenated_blinks_to_epochs()`
- verify no dropped epoch appears in `blink_table`

If the bug is about wrong selected channel:

- start at `process_concatenated_epoch_channel()`
- then `get_blink_statistic()`
- then `select_candidate_channel_from_results()`

If the bug is about wrong metadata export:

- start at `_finalize_blink_table()`
- then `attach_epoch_blink_metadata()`

If the bug is about validation mismatch:

- start at `match_blink_tables()`
- compare one predicted blink row and one reference row inside the same `epoch_index`

## Secondary entrypoint for clean-path debugging

If you want the non-drop path first, use this unit test in IntelliJ:

- target:
  - `test/epoch_detection/test_epoch_pipeline_matches_reference.py`
- test:
  - `TestEpochPipelineMatchesReference.test_clean_epoch_file_still_works`

That path is useful when you want to debug detection and channel selection before you add dropped epochs.

## What not to do

- do not start with the full repo test suite
- do not start with all channels and multiple seeds
- do not enable process workers while stepping line by line
- do not replace the real FIF and CSV with synthetic data for first-pass debugging

## Recommended first debug session

Use this exact sequence:

1. Debug `scripts/validate_epoch_pipeline.py` with the narrowed arguments above.
2. Stop at `prepare_epoch_detection_input()` and confirm shapes and sampling rate.
3. Stop at `simulate_bad_epochs()` and confirm exactly which epochs were dropped.
4. Step through one channel in `process_concatenated_epoch_channel()`.
5. Compare the channel summary at `select_candidate_channel_from_results()`.
6. Confirm metadata rows at `attach_epoch_blink_metadata()`.
7. Confirm event matching and final `f1` at `match_blink_tables()`.

That session gives the shortest real path from input file to final validation metric.
