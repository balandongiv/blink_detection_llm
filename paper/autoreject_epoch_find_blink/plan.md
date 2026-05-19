
# Blink Detection Plan: Two-Stage Thresholding

## 1. Goal

We want to separate two different decisions that are currently being mixed together.

The first decision is:

> Which epochs are suspicious or artifact-heavy?

The second decision is:

> Within those suspicious epochs, where exactly does the blink start and end?

These are not the same job, so they should not use the same threshold.

The proposed design uses two thresholds, one for each job.

The existing autoreject code already supports the first job well: it computes channel-level thresholds from epoch-wise peak-to-peak values and uses them to mark bad segments and bad epochs.

The second job is better handled with a separate sample-level threshold computed directly on the blink component, because `scan_threshold_crossings_kleifges(...)` works on sample amplitudes, not epoch PTP values.

---

## 2. High-level proposal

### Stage A: Epoch-level screening

Use the existing autoreject logic to identify epochs that are likely blink-heavy or artifact-heavy.

This stage answers:

> Which epochs are suspicious?

### Stage B: Sample-level blink-region threshold

Take the epoch time series and restrict the analysis to the epochs flagged in Stage A. 
From those flagged epoch, for each channel, compute a second threshold using robust statistics such as median or mean plus MAD-scaled dispersion.

This stage answers:

> What amplitude level looks blink-like within suspicious epochs?

### Stage C: Blink-region detection

For each of threshold for each channel calculated in Stage B, threshold as input to `scan_threshold_crossings_kleifges(...)` to find blink start and end indices.

This stage answers:

> Where is the blink region in time?

---

## 3. Why this design is better

The existing autoreject threshold is an epoch-level cutoff. For one channel, it is selected from the sorted epoch PTP values, and an epoch is considered acceptable for that channel when its PTP is below or equal to the threshold.

That is useful for deciding whether an epoch is suspicious, but it is not the same as a threshold for sample-by-sample crossing.

Your later blink scan function expects a threshold that can be applied directly to the blink signal at each sample:

* start blink when value goes above threshold
* end blink when value goes below threshold
* keep only segments long enough to count as a blink

So the proposed design keeps the epoch-level logic where it belongs and introduces a second threshold for region finding.

This avoids forcing one threshold to do two incompatible jobs.

---

## 4. Detailed stage design

## Stage A: Epoch-level screening

### Purpose

Identify epochs that are likely contaminated by blink or large-amplitude artifact.

### Existing code to reuse

Use the existing autoreject workflow rather than rebuilding this logic from scratch.

Relevant code already exists in the package  autoreject implementation:
`C:\Users\balan\IdeaProjects\find_blink_epoch_worktree\autoreject\autoreject\autoreject.py`

`C:\Users\balan\IdeaProjects\find_blink_epoch_worktree\autoreject\autoreject\bayesopt.py`


* `compute_thresholds(...)`
* `_compute_thresholds(...)`
* `_compute_thresh(...)`
* `_ChannelAutoReject`
* `_AutoReject.get_reject_log(...)`
* `_vote_bad_epochs(...)`
* `_get_bad_epochs(...)`

The tutorial for autoreject also provides a good reference for how to use the package to get the desired outputs.
C:\Users\balan\IdeaProjects\blink_detection_llm\autoreject\examples

We also use the autoreject style for the strategy c
`tutorial/14_strategy_c_bayes_opto.py`
### Recommended implementation path

Prefer using the public/high-level API instead of private helpers when possible.

Best existing options:

1. `AutoReject(...).fit(epochs)` followed by `.get_reject_log(epochs)`
2. If only thresholds are needed, `compute_thresholds(...)`

For actual flagged epochs, `get_reject_log(...)` is the most useful because it gives:

* per-channel labels
* bad epochs mask
* interpolation status

That is already the structure needed for Stage A.

### Output of Stage A

A boolean mask or index list of suspicious epochs, for example:

* `flagged_epoch_mask`
* `flagged_epoch_indices`

Optional additional outputs:

* channel-level vote counts
* per-channel bad labels
* reject log object

### Human interpretation

This stage does not claim to find exact blink timing. It only says:

> These epochs are suspicious enough to inspect more closely.

---

## Stage B: Sample-level blink threshold from flagged epochs

### Purpose

Compute a representative threshold for sample-level blink-region detection.

### Core idea

Instead of computing the later threshold from all epochs, restrict the calculation to the epochs already flagged in Stage A.

This is reasonable because those epochs are more likely to contain true blink-like events.

### Input

The flagged epochs from Stage A.

### Threshold formula

We want to explore different formulas strategy.

##  blinker approach

which is available in `pyblinker/strategy_a/thresholding.py`
```python


def compute_basic_statistics(
params: dict,
blink_component: np.ndarray,
) -> tuple[float, float]:
"""Return MATLAB-equivalent thresholding statistics."""
SCALING_FACTOR = 1.4826  # From original paper: by default, BLINKER eliminates
mean_value = float(np.mean(blink_component, dtype=np.float64))
robust_std = float(SCALING_FACTOR * mad(blink_component))
min_blink_frames = float(params["min_event_len"] * params["sfreq"])
threshold = float(mean_value + params["std_threshold"] * robust_std)
return min_blink_frames, threshold
```
## Median + MAD approach
A robust threshold is preferred.

Recommended default:

```python
center = median(flagged_samples)
dispersion = 1.4826 * MAD(flagged_samples)
threshold = center + k * dispersion
```

Where `k` is something like `params["std_threshold"]`.

This is conceptually similar to your existing `compute_basic_statistics(...)`, but median is preferred over mean because it is less distorted by large blink peaks.

### Why robust statistics

Flagged epochs are likely to contain outliers by design. Using robust statistics reduces the chance that a few very large peaks dominate the threshold.

### Expected output

A single scalar threshold each channel

* `blink_region_threshold`

Optional diagnostics:

* center value
* robust dispersion value
* number of flagged samples used
* number of flagged epochs used

### Human interpretation

This threshold is no longer an epoch-quality threshold. It is now a region-detection threshold for the blink signal itself.

### Important caveat

Using only flagged epochs may bias the threshold upward. That can make the detector insensitive to smaller blinks.

To handle this, the design should include fallback or tuning behavior:

* default to robust median + MAD
* expose `k` as a parameter
* consider fallback to all epochs if too few flagged epochs exist
* consider comparing against a clean-baseline threshold later if sensitivity becomes an issue

---

## Stage C: Blink-region detection

### Purpose

Find blink onset and offset indices.

### Existing function to reuse

Use the existing function:

* `scan_threshold_crossings_kleifges(...)`

This function already provides the right control flow for onset/offset extraction:

* enter blink when value exceeds threshold
* exit blink when value falls below threshold
* keep only intervals longer than `min_blink_frames`

So the plan is to keep this function and only improve how its input threshold is chosen.

### Recommended input

Feed the Stage B threshold into this function, using the same `blink_component` used to estimate that threshold.

### Output

Two arrays:

* `start_blinks`
* `end_blinks`


