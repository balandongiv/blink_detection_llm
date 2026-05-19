---

# Exploratory Strategy C Specification

## Goal

Implement **Strategy C** as a staged blink detection pipeline for EEG data.

The main idea is:

* **Stage 1** uses **peak-to-peak rejection threshold learning** to detect blink-crossing candidates for each signal, per epoch and per channel.
* **Stages 2 to 6** refine those candidates using the existing blink-processing pipeline.
* First, optimize the pipeline for **normal short blinks only**.
* Only after the normal-blink pipeline is stable should the method be extended to **long eye closure / long blink**.
* At every refinement step, ensure that improvements for long closure do **not degrade short blink performance**.

---

# Core Idea of Strategy C

## Stage 1: Subject-wise peak-to-peak threshold learning

Strategy C starts by using **autoreject-style peak-to-peak threshold learning** to determine blink candidate thresholds.

The intention is:

* Learn a **subject-specific threshold** for pick EEG channel.
* Use the threshold to identify candidate blink events within each epoch.
* This stage acts as the broad candidate generator.
* The thresholds should be learned from the subject’s own data, not from a global fixed threshold.

From the autoreject codebase, the relevant logic is:

* `_compute_thresholds()` computes channel-level thresholds
* `_compute_thresh()` computes the optimal threshold for a single channel
* peak-to-peak values are computed with `np.ptp(..., axis=1)`
* learned thresholds are stored in `ar.threshes_`

This means Strategy C Stage 1 should adopt the same principle:

* for each subject
* for each selected EEG channel
* compute or learn a peak-to-peak threshold
* use threshold crossing as the first blink candidate detector

## Practical interpretation for Strategy C

For each selected epoch and each EEG channel:

1. Compute the signal peak-to-peak behavior
2. Use a learned subject-wise threshold to detect candidate blink crossings
4. Preserve recall at this stage; this stage should favor **not missing true blinks**

This stage is intended to be permissive. It is acceptable if it yields extra or noisy candidates, as long as **true positives remain 100%**.

---

# Proposed Stages for Strategy C

Strategy C should now be treated as a **6-stage pipeline**.

## Stage 1. Representative threshold candidate generation

### Purpose

This is exploratory, but the core idea is to use `autoreject`-style peak-to-peak threshold learning to generate candidate blink crossing regions for each epoch and channel.
for example, use

from autoreject import validation_curve  # noqa
from autoreject import get_rejection_threshold  # noqa

_, test_scores, param_range = validation_curve(
epochs, param_range=param_range, cv=5, return_param_range=True, n_jobs=1)

test_scores = -test_scores.mean(axis=1)
best_thresh = param_range[np.argmin(test_scores)]

###############################################################################
# We can also get the best threshold more efficiently using Bayesian
# optimization
reject2 = get_rejection_threshold(epochs, random_state=0, cv=5)

whereby we emply the bayesian optimization function to learn the optimal threshold for each channel or all the channel,
and we can assume, from this threshold, we seperate the blink.


or we also can explore
from autoreject import get_rejection_threshold  


reject = get_rejection_threshold(epochs, decim=2)

or we can also explore

from autoreject import compute_thresholds  # noqa

# Get a dictionary of rejection thresholds
threshes = compute_thresholds(epochs, picks=picks, method='random_search',
random_state=42, augment=False,
verbose=True)

or use something from
autoreject/examples/plot_auto_repair.py

explore all this and decide on the best way to learn the thresholds and apply them to generate candidate blink crossing regions.
### Behavior

* Use the subject’s own data to learn thresholds
* Apply thresholds to each epoch/channel signal
* Generate candidate blink crossing regions

### Acceptance rule

* **TP must be 100%**
* False negatives must 0%
* This stage must be repeatedly tuned until it reliably captures all true blink opportunities

---

## Stage 2. Fit blinks

Use the existing `FitBlinks` logic to fit the blink candidates produced by Stage 1.

Example existing code:

```python
fitblinks = FitBlinks(
    candidate_signal=detector.raw_data.get_data(picks=channel)[0],
    df=df,
    params=detector.params,
)
fitblinks.dprocess()
df = fitblinks.frame_blinks
```

### Purpose

Refine raw threshold-crossing candidates into fitted blink events.

### Acceptance rule

* **TP must remain 100%**
* * False negatives must 0%
* **False Positive (Stage 2) < False Positive(Stage 1)**

---

## Stage 3. Extract blink statistics

Use `get_blink_statistic(...)` to estimate blink amplitude-related statistics.

Example:

```python
blink_stats = get_blink_statistic(
    df,
    detector.params["z_thresholds"],
    signal=detector.raw_data.get_data(picks=channel)[0],
)
blink_stats["ch"] = channel
```

### Purpose

Estimate blink statistics that can later be used for filtering and quality control.

### Acceptance rule

* **TP must remain 100%**
* * False negatives must 0%
* **False Positive (Stage 3) < False Positive(Stage 2)**


---

## Stage 4. Get good blink mask

Use `get_good_blink_mask(...)` to retain only blinks that satisfy the quality mask.

Example:

```python
_, df = get_good_blink_mask(
    df,
    blink_stats["best_median"],
    blink_stats["best_robust_std"],
    detector.params["z_thresholds"],
)
```

If no good blinks remain:

```python
if df.empty and verbose:
    logger.warning("No good blinks found in channel: %s", channel)
    return
```

### Purpose

Filter poor blink candidates while preserving all true blink detections.

### Acceptance rule

* **TP must remain 100%**
* * False negatives must 0%
* **False Positive (Stage 4) < False Positive(Stage 3)**



---

## Stage 5. Compute blink properties

Use `BlinkProperties(...)` to compute detailed blink features.

Example:

```python
df_in = df.copy()
df_out = BlinkProperties(
    detector.raw_data.get_data(picks=channel)[0],
    df_in,
    detector.params["sfreq"],
    detector.params,
).df
```

### Purpose

Compute the blink properties needed for later validation and filtering.

### Acceptance rule

* **TP must remain 100%**
* * False negatives must 0%
* **False Positive (Stage 5) < False Positive(Stage 4)**

---

## Stage 6. Apply pAVR restriction

Use the current pAVR restriction logic:

```python
condition_1 = df_out["pos_amp_vel_ratio_zero"] < detector.params["p_avr_threshold"]
condition_2 = df_out["max_value"] < (
    blink_stats["best_median"] - blink_stats["best_robust_std"]
)
df_out = df_out[~(condition_1 & condition_2)]
```

### Purpose

Apply the final physiological or morphological restriction to reject weak/non-blink candidates.

### Acceptance rule

* **TP must remain 100%**
* * False negatives must 0%
* **False Positive (Stage 6) < False Positive(Stage 5)**

This is the final refinement stage for normal blink detection.

---

# Recommended Development Scope for Initial Iteration

For the first development phase:

* assume **no dropped epochs**
* use only **5 epochs**, not all 100, similar to `10_strategy_a_first_5_epoch_debug.py`
* use only **4 frontal EEG channels**
* if `autoreject` supports it robustly, optionally allow **2 frontal channels minimum**
* focus only on **normal short blinks**

This reduced scope is for fast development and fast test iteration.

---


For Strategy C, the learned thresholds should be used as the Stage 1 signal-crossing thresholds.


## Decision rule

Choose the approach that best satisfies:

1. **TP remains 100%**
2. False negatives must 0%
3. runtime is acceptable
4. the output works well with Stages 2 to 6
5. Focus on stage and it should be better than the stage 1 of in- [strategy_A_current_results.md](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/development_strategy/strategy_A/strategy_A_current_results.md)
- [strategy_B_current_results.md](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/development_strategy/strategy_B/strategy_B_current_results.md), as describe in `development_strategy/strategy_c_step1_reference_benchmark.md`

Unless evidence shows otherwise, prefer the simpler implementation that best preserves recall and precision.

---

# Unit Test Strategy for Strategy C

## Main rule

The unit tests must verify **every blink event individually** and must provide detailed diagnostics before failing.

The tests are not only for pass/fail. They must tell the agent exactly where the pipeline is failing.

## Ground truth source

Refer to `development_strategy/test_file.md` for the  ground truth `tutorial/10_strategy_a_first_5_epoch_debug.py` and `tutorial/11_strategy_a_stage1_benchmark.py`

---

## What each test must do

For each stage:

1. compare detected blink events against CSV ground truth
2. inspect every blink individually
3. identify missed or problematic regions
4. print the full problematic list first
5. only then raise an assertion failure

---

## Diagnostic output required before assertion failure

Each failing test must print:

* strategy name
* stage name
* subject id
* epoch index
* channel
* blink index or blink time range
* expected ground-truth region
* detected region
* mismatch type

Suggested mismatch types:

* missed blink
* wrong onset/offset boundary
* split blink
* merged blink
* bad threshold crossing
* channel mismatch
* masking too strict
* pAVR rejection too strict

Also print stage summary:

* TP
* FN
* FP if tracked
* recall
* runtime

Only after printing all problematic items should the test fail.

---

# Stage-by-Stage Test Rules

## Stage 1 test

Validate peak-to-peak threshold candidate generation against ground truth.

Required outcome:

* **TP = 100%**
* false negatives recorded and analyzed
* test output must reveal which blink candidates were missed

Because Stage 1 is the broad candidate generator, it must be iterated until TP and FN is stable.

---

---

# Regression Policy

Every time Strategy C is modified:

* rerun tests for all earlier stages
* verify no previously correct blink is lost
* verify short blink performance has not regressed

This is especially important later when long blink support is added.

---
