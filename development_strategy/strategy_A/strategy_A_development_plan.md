

# Agent Instruction: Add an Epoch-Aware Blink Detection Pipeline

## Objective

Implement a new **epoch-aware blink-detection pipeline** that reuses the existing legacy six-step blink logic, while ensuring that **bad epochs never contribute to any computation**.

The new pipeline must:

* operate on an `mne.Epochs` object loaded from a FIF file
* support both:

    * clean epoch files with no bad epochs marked
    * epoch files where some epochs are marked bad
* write detected blink outputs back to epoch-level results using:

    * `blink_onset`
    * `blink_duration`
* preserve the existing blink-detection algorithm as much as possible

For initial development, use only:

* `sample_data/dev_epo.fif`
* `sample_data/dev_epo_annotations.csv`

Reference truth for validation comes from the legacy continuous-signal pipeline run on:

* `sample_data/1.edf`
* `sample_data/seed_exp01_pyblinker_results_1.pkl`

with cropping performed by `load_edf_seed.py`.

---

## Core design principle

Do **not** redesign the blink detector.

The goal is to adapt the **execution model**, not replace the legacy algorithm.

### Legacy execution model

* one long continuous signal per channel

### New epoch-aware execution model

* collect all **valid epochs** for the same channel
* concatenate only those valid epoch signals
* run the legacy six-step blink pipeline on that concatenated valid signal
* use the resulting detections and statistics for channel selection
* map detected blink regions back to their original epochs for final export

### Non-negotiable rule

**Bad epochs must be excluded before any blink-related computation begins.**

That means bad epochs must not contribute to:

* blink candidate search
* blink fitting
* blink statistics
* good blink mask estimation
* blink property computation
* pAVR restriction
* candidate channel selection

---

## Required legacy steps

The following six steps must remain the core of the detection process and should be reused in the same order whenever possible:

1. Get blink positions
2. Fit blinks
3. Extract blink statistics
4. Get good blink mask
5. Compute blink properties
6. Apply pAVR restriction

Do not rewrite these steps unless absolutely necessary for epoch compatibility.

---

## High-level implementation requirements

Create a new epoch-mode pipeline that is separate from the existing continuous-mode pipeline.

The new pipeline should:

1. load `mne.Epochs` from FIF
2. determine which epochs are valid
3. exclude bad epochs centrally and explicitly
4. process each channel using only valid epochs
5. aggregate per-channel results across valid epochs only
6. select the candidate channel using only valid-epoch results
7. map blink detections back to epoch-level outputs
8. return:

    * updated epoch metadata
    * a normalized blink table for validation and analysis

---

## Suggested top-level API

```python
detector = BlinkDetectorEpoch(
    epoch=epoch,
    visualize=False,
    annot_label=None,
    filter_low=1.0,
    filter_high=20.0,
    resample_rate=30,
    n_jobs=2,
    use_multiprocessing=True,
    blink_params=blinker_params,
)

annotations, channel, _good, _df, _fig_data, _selected, epoch = detector.get_blink()
```

After execution, `epoch.metadata` should include:

* `blink_onset`
* `blink_duration`
* `blink_count`
* `candidate_channel`

The exact return signature can be adjusted if needed, but the pipeline must expose both:

* updated epoch metadata
* normalized blink-event table

---

## 1. Valid and bad epoch handling

Create a helper whose sole responsibility is to determine which epochs are allowed to contribute.

Suggested function:

```python
def get_valid_epoch_indices(epochs) -> list[int]:
    ...
```

### Rules

* If the `Epochs` object contains bad epochs, those epochs must be excluded.
* If the loaded epoch file already contains only retained epochs, then all loaded epochs are treated as valid.
* This filtering rule must be enforced centrally, not scattered across multiple functions.

Also create a reproducible helper for validation experiments that can randomly mark or simulate dropped epochs.

Suggested function:

```python
def simulate_bad_epochs(
    epochs,
    drop_ratio: float,
    random_state: int,
) -> tuple[mne.Epochs, list[int]]:
    ...
```

This helper is only for validation experiments.

---

## 2. Per-channel processing in epoch mode

Create a wrapper that lets the legacy six-step pipeline run on a signal formed by concatenating all valid epochs for one channel.

Suggested function:

```python
def process_concatenated_epoch_channel(
    detector_params,
    concatenated_signal: np.ndarray,
    channel: str,
    valid_epoch_indices: list[int],
    epoch_boundaries: list[tuple[int, int]],
    sfreq: float,
    verbose: bool = True,
) -> EpochChannelBlinkResult:
    ...
```

### Requirements

This wrapper should call the same legacy components in the same order:

* `get_blink_position(...)`
* `FitBlinks(...).dprocess()`
* `get_blink_statistic(...)`
* `get_good_blink_mask(...)`
* `BlinkProperties(...)`
* pAVR restriction

### Important detail

Because the channel signal is created by concatenating valid epochs, you must preserve enough boundary information to map detected blinks back to their source epochs afterward.

---

## 3. Channel-level aggregation

For each channel, aggregate results across valid epochs only.

Useful aggregated summaries may include:

* total detected blinks
* total good blinks
* number of valid epochs with at least one blink
* fraction of valid epochs with detections
* median or mean quality statistics
* number of pAVR-passed events

Keep aggregation simple and compatible with the legacy channel-selection logic.

---

## 4. Candidate channel selection

Prefer to reuse the existing channel-selection logic if possible.

If direct reuse is not possible, implement a simple compatible ranking based on:

* number of good blinks
* fraction of usable valid epochs with detections
* median blink quality statistics
* number of pAVR-passed events

### Constraint

The candidate channel must be selected using **only valid epochs**.

Do not invent a substantially new selection strategy unless required for compatibility.

---

## 5. Map detections back to epoch-level outputs

Once the candidate channel is selected, map the final blink detections back to individual epochs.

### Primary output: `epochs.metadata`

Store the following columns in `epochs.metadata`:

* `blink_onset`
* `blink_duration`
* `blink_count`
* `candidate_channel`

Since one epoch may contain multiple blinks, store `blink_onset` and `blink_duration` as JSON-serialized lists.

Example:

```python
blink_onset = "[0.42, 1.87]"
blink_duration = "[0.11, 0.09]"
```

This is preferred over forcing a single scalar value.

### Secondary output: normalized blink table

Also return or save a long-form dataframe with one row per blink, for example:

* `epoch_index`
* `channel`
* `blink_onset`
* `blink_duration`
* optional morphology or quality fields from `BlinkProperties`

This long-form table should be the main artifact used for validation.

---

## 6. Parallelization

Use at least 2 CPU cores.

### Preferred strategy

Parallelize over **channels**, where each worker processes all valid epochs for one channel.

This is preferred because:

* channels are naturally independent
* it aligns with candidate-channel selection
* it avoids repeatedly serializing large MNE objects

### Implementation guidance

* pre-extract epoch data into NumPy arrays before parallel work
* use `joblib.Parallel` or `concurrent.futures.ProcessPoolExecutor`
* enforce:

```python
n_jobs = max(2, requested_n_jobs)
```

Do not leave parallelism disabled during initial development.

---


## 7. Development sequence

### Phase 1: loading, epoch validity, and simulated drops

Implement:

* load epoched FIF
* resolve valid versus bad epochs
* create a reproducible random-drop helper for validation
* extract epoch data per channel

Deliverable:

* a helper that prints or returns valid epoch indices before and after simulated dropping

### Phase 2: channel wrapper around legacy six-step logic

Implement:

* concatenation of valid epoch signals for one channel
* execution of the legacy six-step blink logic on the concatenated signal
* preservation of epoch boundaries for backward mapping

### Phase 3: channel aggregation and candidate selection

Implement:

* per-channel aggregation across valid epochs
* candidate channel selection using valid-epoch results only

### Phase 4: epoch-level export

Implement:

* mapping final detections back to epoch-local onset and duration
* metadata export into `epochs.metadata`
* normalized long-form blink table

### Phase 5: validation harness

Implement a script such as:

```bash
python scripts/validate_epoch_pipeline.py
```

This script should:

* run multiple random-drop experiments
* compare predictions against `sample_data/dev_epo_annotations.csv`
* print summary metrics
* fail if F1 < 0.90

---

## 8. Suggested file layout

```text
pyblinker/
   epoch_detection_strategy_a/
      epoch_blink_pipeline.py
      epoch_channel_processor.py
      epoch_result_aggregation.py
      epoch_metadata_export.py
      epoch_validation.py
      bad_epoch_utils.py

scripts/
  validate_epoch_pipeline.py

test/
    epoch_detection_strategy_a/
      test_bad_epochs_are_excluded.py
      test_epoch_pipeline_matches_reference.py
      test_epoch_metadata_export.py
      test_random_drop_similarity.py
      
```

---

## 11. Implementation constraints

The coding agent must follow all of the following constraints:

* do not rewrite the core six legacy blink steps unless absolutely necessary
* do not allow bad epochs anywhere in the computation graph
* keep epoch mode separate from legacy continuous mode
* make the pipeline deterministic under a fixed random seed
* use at least 2 CPU cores
* focus on one-file working development first, then refactor
* use metadata plus a normalized blink table as the main outputs
* use `unittest` only; do not use `pytest`

---

## 12. Definition of done

This feature is complete only when all of the following are true:

* the new epoch-aware pipeline runs on `sample_data/dev_epo.fif`
* bad epochs are excluded from all blink computations
* a candidate channel is selected using only valid epochs
* blink regions are written back as `blink_onset` and `blink_duration`
* validation against `sample_data/dev_epo_annotations.csv` reaches at least 90% similarity
* the implementation uses at least 2 CPU cores
* tests cover both clean and bad-epoch scenarios

---

Use the pleminary plan, but, if the result is poor, you have the autonomy to suggest new plan 