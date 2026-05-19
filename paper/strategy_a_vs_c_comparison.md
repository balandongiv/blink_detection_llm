# Blink Detection Strategy Comparison: Strategy A vs Strategy C

## Overview

This report compares two blink detection strategies implemented in `pyblinker`:

- **Strategy A** — Kleifges/BLINKER-style statistical thresholding (`tutorial/10_strategy_a.py`)
- **Strategy C** — Autoreject Bayesian-optimized thresholding (`tutorial/14_strategy_c_bayes_opto.py`)

Both strategies were evaluated on the same recording (`S01_20170519_043933`, subject S1) against
human-annotated ground truth, using the same 29 fixed-length 60-second epochs, the same EEG
channels, and the same bandpass filter (1–20 Hz).

---

## Experimental Results

### Strategy A

```
best_channel = E3
tp=134   fp=319   fn=5
precision=0.2958   recall=0.9640   f1=0.4527
```

| Channel | Candidates | TP  | FP  | FN | Precision | Recall | F1     |
|---------|-----------|-----|-----|----|-----------|--------|--------|
| E3      | 453       | 134 | 319 | 5  | 0.2958    | 0.9640 | 0.4527 |
| E22     | 480       | 131 | 349 | 8  | 0.2729    | 0.9424 | 0.4233 |
| E9      | 564       | 130 | 434 | 9  | 0.2305    | 0.9353 | 0.3698 |

### Strategy C (Bayesian Optimization)

```
best_channel = E9
tp=130   fp=20   fn=9
precision=0.8667   recall=0.9353   f1=0.8997
```

| Channel | Candidates | TP  | FP | FN | Precision | Recall | F1     |
|---------|-----------|-----|----|----|-----------|--------|--------|
| E9      | 150       | 130 | 20 | 9  | 0.8667    | 0.9353 | 0.8997 |
| E3      | 190       | 129 | 61 | 10 | 0.6789    | 0.9281 | 0.7842 |
| E22     | 206       | 131 | 75 | 8  | 0.6359    | 0.9424 | 0.7594 |

### Performance Delta

| Metric    | Strategy A | Strategy C | Improvement       |
|-----------|-----------|-----------|-------------------|
| Precision | 0.2958    | 0.8667    | +0.5709 (+193%)   |
| Recall    | 0.9640    | 0.9353    | −0.0287 (−3%)     |
| F1        | 0.4527    | 0.8997    | +0.4470 (+99%)    |

Strategy C nearly doubles F1 score while sacrificing only 3% recall.

---

## Architecture: What Is Identical

Both strategies invoke the same scanning function:

```python
# pyblinker/blinker/get_blink_positions.py
def scan_threshold_crossings_kleifges(
    blink_component, threshold, min_blink_frames, *, progress_bar, channel_name
):
    in_blink = False
    for idx in range(blink_component.size):
        value = blink_component[idx]
        if (not in_blink) and (value > threshold):
            start = idx
            in_blink = True
        if in_blink and (value < threshold):
            if (idx - start) > min_blink_frames:
                start_blinks.append(start)
                end_blinks.append(idx)
            in_blink = False
    return np.asarray(start_blinks), np.asarray(end_blinks)
```

The loop is deterministic and stateless — given the same signal and the same `threshold`, it
produces identical output. **The scanning function is not the variable.** The performance
difference is caused entirely by the threshold passed to it.

### Bare Filtering: What Both Strategies Deliberately Omit

Both Strategy A and Strategy C use `scan_threshold_crossings_kleifges` with only one
post-crossing filter: the **minimum duration gate** (`min_blink_frames`). A candidate is
accepted only if the time spent above the threshold exceeds `min_event_len * sfreq` samples
(default: 0.05 s × sfreq). Any crossing shorter than this is silently discarded.

This is intentionally minimal — it is a **bare filtering pipeline**. Neither strategy applies
the additional `apply_minimum_separation` step that exists in the original pyblinker codebase.

### The Original pyblinker Post-Processing Step

The reference implementation in `pyblinker/blinker/get_blink_positions.py` uses
`get_blink_position_with_threshold`, which goes one step further after the crossing scan:

```python
# pyblinker/blinker/get_blink_positions.py
def get_blink_position_with_threshold(params, *, blink_component, threshold, ...):
    # Step 1 — same crossing scan
    start_blinks, end_blinks = _scan_threshold_crossings(
        blink_component, threshold, min_blink_frames, ...
    )

    # Step 2 — apply_minimum_separation (absent in Strategy A and C)
    min_event_sep = float(params.get("min_event_sep", params["min_event_len"]))
    start_blinks, end_blinks = apply_minimum_separation(
        start_blinks, end_blinks,
        sfreq=params["sfreq"],
        min_event_sep=min_event_sep,   # in seconds (default 0.05 s)
    )
    return pd.DataFrame({"start_blink": start_blinks, "end_blink": end_blinks})
```

`apply_minimum_separation` removes both members of any adjacent blink pair whose inter-event
gap is shorter than `min_event_sep` seconds:

```python
# pyblinker/blinker/get_blink_positions.py
def apply_minimum_separation(start_blinks, end_blinks, *, sfreq, min_event_sep):
    delta = (start_blinks[1:] - end_blinks[:-1]) / sfreq   # gap in seconds
    too_close = np.flatnonzero(delta <= min_event_sep)
    position_mask[too_close]     = False   # remove the earlier blink
    position_mask[too_close + 1] = False   # remove the later blink
    return start_blinks[position_mask], end_blinks[position_mask]
```
However, for fair comparison, both Strategy A and Strategy C deliberately omit this step and use only the raw crossing output.



### Why These Strategies Use Bare Filtering

Both strategies are designed as **Stage 1 candidate scanners** — their job is to produce a
broad set of candidate windows for downstream validation, not to deliver a final clean blink
list. Omitting `apply_minimum_separation` is therefore intentional:

- Strategy A is evaluated as a baseline to characterise the behaviour of raw statistical
  thresholding without any cleanup.
- Strategy C is evaluated to isolate the contribution of the autoreject threshold quality. Any
  additional post-processing would obscure whether the improvement comes from the threshold or
  from the filter.

The absence of `apply_minimum_separation` in both strategies means their false-positive counts
are higher than they would be in the full original pyblinker pipeline. The comparison is
therefore a controlled experiment: **same scanner, same post-processing (none), different
threshold source**.

---

## The Decisive Difference: Threshold Computation

### Strategy A — Statistical Threshold

```python
# pyblinker/strategy_a/thresholding.py
SCALING_FACTOR = 1.4826   # MAD-to-sigma conversion constant (Kleifges 2017)
mean_value     = np.mean(blink_component)
robust_std     = SCALING_FACTOR * mad(blink_component)
threshold      = mean_value + std_threshold * robust_std   # std_threshold = 1.50 (default)
```

The threshold is placed **1.5 robust standard deviations above the signal mean**. Because MAD
is computed from all samples — the majority of which are non-blink baseline — it reflects
background noise amplitude, not blink amplitude. Setting the bar only 1.5σ above the mean is
extremely permissive: muscle twitches, slow baseline drift, and eye movement artefacts all cross
this level and are counted as blink candidates.

### Strategy C — Autoreject Bayesian-Optimized Threshold

```python
# pyblinker/strategy_c/single_channel_autoreject.py
raw_threshold  = autoreject(...)              # per-channel rejection threshold (Bayesian CV)
scan_threshold = raw_threshold * scan_scale  # scan_scale = 0.12
```

`autoreject` uses Bayesian optimization with cross-validation across epochs to find, for each
channel, the amplitude above which an epoch is considered artifactual. For EOG-adjacent channels
(E3, E9, E22), this threshold is naturally calibrated to blink-level amplitude — it is the
amplitude that distinguishes clean epochs from blink-contaminated ones.

Multiplying by `scan_scale = 0.12` lowers the threshold to the **onset region** of a blink
(the rising edge before the signal reaches its peak), improving temporal sensitivity without
introducing the noise of the purely statistical threshold.

---

## Isolating the Effect: Same Channel E9, Same TP

The cleanest evidence that the threshold — and only the threshold — drives the difference:

| Strategy   | Channel | Candidates | TP  | FP  | Precision |
|------------|---------|-----------|-----|-----|-----------|
| Strategy A | E9      | 564       | 130 | 434 | 0.23      |
| Strategy C | E9      | 150       | 130 | 20  | 0.87      |

- Same channel, same recording, same scanning function.
- Both detect **130 true positives** — exactly the same blinks.
- Strategy A produces **3.8× more candidates** (564 vs 150), of which 434 are false positives.

The statistical threshold on E9 is low enough to flag 434 non-blink events. The autoreject
threshold reduces that to 20.

---

## Why the Statistical Threshold Fails

The signal distribution on a typical EOG/frontal EEG channel has a heavy right tail: most
samples sit near zero (baseline), with rare large excursions from blinks. MAD is robust to
outliers, so it estimates the spread of the baseline bulk and is blind to the blink tail.

A threshold at `mean + 1.5 * MAD` therefore sits very close to the baseline distribution:

```
signal amplitude
 ──────────────────────────────────────────────────────────────
 │ ██████████████████████████│                                │
 │ ██████████████████████████│← threshold (mean + 1.5·MAD)   │
 │ ████████████████████████  │                                │  ← actual blinks
 │ baseline noise ───────────┘                                │
```

Everything above this low bar is a candidate — baseline excursions, slow drift, and genuine
blinks alike.

---

## Why the Autoreject Threshold Succeeds

Autoreject cross-validates across epochs: it measures each epoch's peak amplitude per channel
and uses Bayesian search to find the threshold that separates "good" from "bad" epochs with
minimal reconstruction error. For frontal/EOG channels, "bad" means a blink is present, so the
learned threshold sits at the characteristic blink amplitude:

```
signal amplitude
 ──────────────────────────────────────────────────────────────
 │                                      ← autoreject threshold │
 │ ──────────────────────────────────── (0.12 × raw_threshold) │← scan threshold
 │ ██████████████████████████                                  │
 │ baseline noise                                              │
```

The scan threshold at 12% of the rejection threshold catches the beginning of the blink event
without being confused by baseline noise.

---

## Configuration Used

| Parameter              | Strategy A          | Strategy C                          |
|------------------------|---------------------|-------------------------------------|
| Threshold method       | Statistical (MAD)   | Autoreject (Bayesian optimization)  |
| `std_threshold`        | 1.50                | N/A                                 |
| `stage1_scan_scale`    | N/A                 | 0.12                                |
| `stage1_threshold_scope` | N/A               | `per_channel`                       |
| `autoreject_method`    | N/A                 | `bayesian_optimization`             |
| Scanning function      | `scan_threshold_crossings_kleifges` | `scan_threshold_crossings_kleifges` |
| `apply_minimum_separation` | No            | No                                  |
| Filter                 | 1–20 Hz             | 1–20 Hz                             |
| Epoch duration         | 60 s                | 60 s                                |
| `peak_side_tolerance_s` | 0.01 s            | 0.01 s                              |

---

## Conclusion

The scanning loop (`scan_threshold_crossings_kleifges`) is a neutral, deterministic mechanism.
It finds threshold crossings of a specified minimum duration — nothing more. Its output quality
is determined entirely by the quality of the threshold fed into it.

- **Strategy A's weakness** is its threshold: `mean + 1.5·MAD` is too permissive for raw EEG
  and picks up hundreds of non-blink events per channel.
- **Strategy C's strength** is its threshold: autoreject Bayesian optimization produces a
  per-channel amplitude that is empirically grounded in what actually constitutes an artifact
  in the recording, yielding dramatically fewer false positives with virtually the same recall.

The F1 improvement (+99%) is achieved without any change to the detection loop, the channel
selection logic, or the post-processing pipeline. It is a pure consequence of threshold quality.
