# Blink Detection Strategy Comparison: Strategy B vs Strategy C

## Overview

This report compares two blink detection strategies implemented in `pyblinker`:

- **Strategy B** — MNE EOG peak detection with fixed half-window expansion (`tutorial/11_strategy_b.py`)
- **Strategy C** — Autoreject Bayesian-optimized thresholding (`tutorial/14_strategy_c_bayes_opto.py`)

Both strategies were evaluated on the same recording (`S01_20170519_043933`, subject S1) against
human-annotated ground truth, using the same 29 fixed-length 60-second epochs, the same EEG
channels, and the same bandpass filter (1–20 Hz).

---

## Experimental Results

### Strategy B

```
best_channel = E22
tp=128   fp=29   fn=11
precision=0.8153   recall=0.9209   f1=0.8649
```

| Channel | Candidates | TP  | FP  | FN | Precision | Recall | F1     |
|---------|-----------|-----|-----|----|-----------|--------|--------|
| E22     | 157       | 128 | 29  | 11 | 0.8153    | 0.9209 | 0.8649 |
| E9      | 220       | 129 | 91  | 10 | 0.5864    | 0.9281 | 0.7187 |
| E3      | 849       | 133 | 716 | 6  | 0.1567    | 0.9568 | 0.2692 |

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

| Metric    | Strategy B | Strategy C | Improvement     |
|-----------|-----------|-----------|-----------------|
| Precision | 0.8153    | 0.8667    | +0.0514 (+6.3%) |
| Recall    | 0.9209    | 0.9353    | +0.0144 (+1.6%) |
| F1        | 0.8649    | 0.8997    | +0.0348 (+4.0%) |

Strategy C improves on Strategy B by 4% F1, with modest gains in both precision and recall.
Both strategies are competitive — this is a small-margin comparison unlike the A vs C contrast.

---

## Architecture: What Differs

These two strategies use fundamentally different detection mechanisms.

### Strategy B — MNE EOG Peak Detection + Fixed Window

```python
# pyblinker/strategy_b/nathanael_mne.py
events = mne.preprocessing.find_eog_events(raw, ch_name=channel, l_freq=1.0, h_freq=20.0, ...)
peaks = events[:, 0]   # sample index of each detected EOG peak
half_window_samples = round(half_window_s * sfreq)   # half_window_s = 0.10 s
start_blink = peaks - half_window_samples
end_blink   = peaks + half_window_samples
```

`mne.preprocessing.find_eog_events` finds EOG peaks via **cross-correlation** with a
characteristic blink template in the bandpass-filtered signal, then returns the sample index of
each peak. Strategy B then expands a fixed symmetric window of ±0.10 s (±25 samples at 250 Hz)
around each peak to form a candidate region.

The detection is **event-centred**: it finds the peak first, then defines the window. The
threshold is implicit — MNE applies an automatic amplitude threshold to the cross-correlation
score to decide what constitutes a peak. This threshold is data-driven but not
channel-calibrated.

### Strategy C — Autoreject Bayesian Threshold + Crossing Scan

```python
# pyblinker/strategy_c/single_channel_autoreject.py
raw_threshold  = autoreject(...)              # per-channel rejection threshold (Bayesian CV)
scan_threshold = raw_threshold * scan_scale  # scan_scale = 0.12
```

Strategy C **never locates a peak explicitly**. Instead, it finds per-channel amplitude
thresholds via Bayesian optimization, then calls `scan_threshold_crossings_kleifges` to detect
contiguous above-threshold intervals. The candidate boundaries are the first and last samples
where the signal exceeds the threshold — i.e., the **onset and offset of the blink**, not a
window centred on the peak.

---

## What Is Identical

Both strategies share the same evaluation pipeline:

- Same recording, same ground truth, same 29 epochs.
- Same bandpass filter (1–20 Hz, applied before detection in both cases).
- Same scoring function (`evaluate_channel_lanes` with `peak_side_tolerance_s=0.01`).
- Same absence of `apply_minimum_separation` post-processing (bare filtering pipeline).

---

## The Inverted Channel Ranking

The most striking structural difference between the two strategies is that their **best channels
are different** and the **channel rankings are reversed**:

| Channel | Strategy B F1 | Strategy C F1 | Better Strategy |
|---------|--------------|--------------|-----------------|
| E22     | **0.8649**   | 0.7594       | B               |
| E9      | 0.7187       | **0.8997**   | C               |
| E3      | 0.2692       | 0.7842       | C               |

### Why E22 is Strategy B's best channel

MNE's `find_eog_events` uses cross-correlation with a blink template. E22 produces a clean,
template-like blink waveform with a sharp peak that the cross-correlation detects reliably.
With only 157 candidates (vs 220 for E9 and 849 for E3), E22's blink morphology is
sufficiently regular that MNE's automatic threshold suppresses most non-blink events.

### Why E9 is Strategy C's best channel

Strategy C's threshold is calibrated to blink-level amplitude via Bayesian optimization. E9
may have more baseline variance than E22 — which would cause MNE's correlation method to pick
up spurious peaks (fp=91 on E9 in Strategy B) — but autoreject's per-channel calibration sets
the threshold at the precise amplitude that separates blink-contaminated from clean epochs on
that channel, yielding only 20 false positives.

### The E3 divergence

The contrast on E3 is extreme:

| Channel | Strategy B Candidates | Strategy C Candidates |
|---------|-----------------------|-----------------------|
| E3      | 849                   | 190                   |

Strategy B on E3 detects 849 events (716 FP). MNE's template matching on E3 is clearly
sensitive to non-blink signal structure on this channel, generating a large number of spurious
peaks. Strategy C, with an amplitude threshold calibrated to blink-level events, reduces
candidates to 190, most of which are genuine blinks.

---

## Isolating the Effect: Same Channel E9

On the shared channel E9, the candidate counts and precision diverge significantly:

| Strategy   | Channel | Candidates | TP  | FP | Precision | Recall |
|------------|---------|-----------|-----|----|-----------|--------|
| Strategy B | E9      | 220       | 129 | 91 | 0.5864    | 0.9281 |
| Strategy C | E9      | 150       | 130 | 20 | 0.8667    | 0.9353 |

- Both recover approximately the same blinks (129 vs 130 TP).
- Strategy B generates **4.6× more false positives** on E9 (91 vs 20).
- Strategy C's autoreject threshold suppresses spurious MNE peak detections that inflate
  Strategy B's FP count on this channel.

---

## Detection Boundary Characteristics

The two strategies produce candidates with structurally different timing properties.

**Strategy B** always produces candidates of exactly `2 × half_window_s = 0.20 s` duration
(±0.10 s around the detected peak). All candidates have identical width; the only variable is
the peak location.

**Strategy C** produces variable-width candidates bounded by threshold crossings. The window
width reflects the actual signal excursion above the threshold — narrower for brief or sharp
blinks, wider for prolonged or compound blinks. This makes Strategy C's windows more
physiologically shaped.

---

## Configuration Used

| Parameter              | Strategy B                      | Strategy C                          |
|------------------------|---------------------------------|-------------------------------------|
| Detection mechanism    | MNE `find_eog_events` (correlation) | Autoreject (Bayesian optimization) |
| Candidate boundaries   | ±`half_window_s` from peak      | Threshold crossings                 |
| `half_window_s`        | 0.10 s                          | N/A                                 |
| `stage1_scan_scale`    | N/A                             | 0.12                                |
| `autoreject_method`    | N/A                             | `bayesian_optimization`             |
| Scanning function      | `find_eog_events` + expand      | `scan_threshold_crossings_kleifges` |
| `apply_minimum_separation` | No                          | No                                  |
| Filter                 | 1–20 Hz                         | 1–20 Hz                             |
| Epoch duration         | 60 s                            | 60 s                                |
| `peak_side_tolerance_s` | 0.01 s                         | 0.01 s                              |
| Best channel           | E22                             | E9                                  |

---

## Conclusion

Strategy B and Strategy C are competitive: both achieve F1 > 0.86 on the best channel, and
Strategy C leads by a narrow margin (+4% F1). The comparison is structurally different from
the A vs C contrast (where C doubled F1): here both strategies use data-informed detection,
making the difference a matter of method quality rather than method category.

The key findings:

1. **Strategy C is marginally more accurate** overall (F1 0.8997 vs 0.8649), with better
   precision (+6%) and recall (+1.6%). The improvement is modest but consistent across both
   metrics.

2. **The strategies disagree on which channel is best.** Strategy B prefers E22 (clean
   blink morphology for template matching); Strategy C prefers E9 (well-calibrated autoreject
   threshold). This is not a tie-breaking detail — it reflects a genuine difference in what each
   method responds to.

3. **Strategy B degrades severely on E3.** MNE's template correlation produces 849 candidates
   (716 FP) on E3, suggesting that channel E3's signal contains non-blink structure that
   resembles the EOG template. Strategy C's amplitude threshold is immune to this, producing
   only 190 candidates on the same channel.

4. **Fixed-window vs threshold-crossing candidates differ structurally.** Strategy B always
   produces 0.20 s windows; Strategy C produces variable-width windows reflecting actual blink
   duration. Downstream stages that depend on blink timing or morphology will receive
   qualitatively different input from each strategy.

The performance gap between B and C is small enough that channel selection is the dominant
factor: choosing the wrong channel in either strategy costs more than switching from B to C on
the same channel.
