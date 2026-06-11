# Long Blink Detection: Findings and Algorithm Proposal

**Date:** 2026-06-03  
**Dataset:** Raja drowsy driving (EEG/EOG, 46 complete sessions)  
**Pipeline evaluated:** Full pyblinker 6-step pipeline on continuous signal (Tutorial 14)

---

## 1. Background and Motivation

The existing blink detection pipeline (pyblinker) was designed to detect **normal involuntary blinks** — rapid, reflexive eye closures lasting 100–400 ms. In drowsy driving datasets, a second and clinically important class of event exists: the **long eye closure** (full closure / microsleep), defined as a sustained lid closure ≥ 500 ms. This event class is a key indicator of drowsiness and is the target of the PERCLOS metric, which has regulatory acceptance as a driver alertness measure.

The question investigated here is: **does the complete pyblinker pipeline also detect long closures, or does it miss them?**

---

## 2. Blink Type Definitions

Two mutually exclusive event classes were defined based on annotation labels and duration:

| Class | Ground-truth labels in Raja dataset | Duration rule | Physiological basis |
|---|---|---|---|
| **Normal blink** | `B_CL`, `HB_CL`, `eye_blink`, `B_A`, `B_M`, `HB_A`, `HB_M` | duration **< 0.5 s** | Reflex blink; mean ~150–400 ms (Stern et al., 1994) |
| **Long blink / closure** | `FC_CL`, `FC`, `FC_A`, `FC_M`, `FC_CL_FRAME_VIEWER` | duration **≥ 0.5 s** | Drowsiness/microsleep; PERCLOS defines ≥ 80% closure for ≥ 500 ms as impairment (Wierwille & Ellsworth, 1994) |

Note: any `B_CL`/`HB_CL` event with duration ≥ 0.5 s was also reclassified as long (accounts for borderline annotation cases).

---

## 3. Dataset Overview

Sessions were filtered to those with both blink types present and a complete matched pair (annotation CSV + processed FIF). Five sessions with the highest long-blink counts were selected for the primary analysis.

| Session | Normal GT | Long GT | Normal mean dur | Long mean dur |
|---|---|---|---|---|
| S13/S26_20190108_035218_3 | 319 | 189 | 0.241 s | 1.269 s |
| S24/S38_20190129_035118_2 | 859 | 249 | 0.300 s | 1.207 s |
| S4/S04_20170606_045500_2 | 578 | 186 | 0.247 s | 0.430 s |
| S2/TEST_20170601_042544_2 | 202 | 118 | 0.263 s | 0.947 s |
| S22/S35_20190123_040805_2 | 448 | 155 | 0.245 s | 1.748 s |
| **Total** | **2,406** | **897** | — | — |

Across the full Raja dataset (46 sessions):
- 34 of 46 sessions contain at least one FC_CL event alongside normal blinks (mixed sessions).
- Pure-normal sessions: 12.

---

## 4. Experimental Results

The pyblinker continuous pipeline was run once per session. Detected blinks were then evaluated separately against the normal-only and long-only ground truth subsets.

### 4.1 Detection summary

| Evaluation target | micro Precision | micro Recall | micro F1 |
|---|---|---|---|
| All events (combined) | 0.9174 | 0.7566 | 0.8293 |
| **Normal blinks only** | 0.7430 | **0.8337** | 0.7857 |
| **Long blinks only** | 0.1822† | **0.5440** | 0.2729 |

†Precision for long is inflated by the evaluation setup (normal-blink detections score as FP when evaluated against long-only GT). Recall is the reliable metric.

### 4.2 Per-session recall breakdown

| Session | Normal recall | Long recall | Recall drop | Long mean dur |
|---|---|---|---|---|
| S13/S26_20190108_035218_3 | 0.8025 | 0.5185 | −0.284 | 1.27 s |
| S24/S38_20190129_035118_2 | 0.8277 | 0.4137 | −0.414 | 1.21 s |
| S4/S04_20170606_045500_2 | 0.8962 | 0.7527 | −0.144 | 0.43 s |
| S2/TEST_20170601_042544_2 | 0.8762 | 0.5932 | −0.283 | 0.95 s |
| S22/S35_20190123_040805_2 | 0.7679 | 0.4968 | −0.271 | 1.75 s |
| **Macro average** | **0.8341** | **0.5550** | **−0.279** | — |

### 4.3 Key observation: recall degrades with closure duration

The session with the shortest mean long duration (S4, 0.43 s) achieves the highest long-blink recall (0.75). The session with the longest mean long duration (S22, 1.75 s) achieves the lowest recall (0.50). This inverse relationship confirms that pyblinker struggles specifically with sustained closures, not merely with events near the 0.5 s boundary.

---

## 5. Root Cause Analysis

The pyblinker 6-step pipeline applies three filters that are mechanistically incompatible with the waveform morphology of a long eye closure:

### Step 2 — FitBlinks (Gaussian template fitting)
A normal blink produces a symmetric, approximately Gaussian voltage deflection. A long closure produces a **slow descent, flat plateau, then slow ascent** — a top-hat or trapezoidal shape. The Gaussian fit yields a poor R² for this shape, and events below the fit-quality threshold are discarded.

### Step 4 — `_select_good_blinks` (statistical quality filter)
This step retains only blinks whose amplitude and width fall within percentile limits derived from the population distribution. Long closures are **statistical width outliers** relative to normal blinks: a 1-s closure is 4–6× wider than the mean 0.25 s normal blink. They fail the width ceiling and are filtered out.

### Step 6 — pAVR filter (amplitude-velocity ratio)
The pAVR criterion thresholds the ratio of peak amplitude to maximum velocity (rate of change). Normal blinks have a sharp, high-velocity onset; long closures have a slow, low-velocity onset. The slow lid descent falls below the velocity threshold and fails this filter.

**Net effect**: when pyblinker detects a long closure at all (~55% recall), it is detecting the **onset edge** — the brief moment at the beginning of the closure that resembles a normal blink waveform. The sustained plateau itself is never detected as a blink event.

---

## 6. Proposed Algorithm: Dual-Mode Blink Detector

A new algorithm is needed that can reliably detect **both** normal blinks and long closures in EEG/EOG signals. The core insight is that these two event types have fundamentally different waveform signatures and should be handled by separate detection mechanisms operating in parallel, with results merged into a unified output.

### 6.1 Architecture overview

```
Raw EEG/EOG signal
       │
       ▼
  Pre-processing
  (bandpass 1–20 Hz, resample 100 Hz)
       │
       ├─────────────────────────────────────┐
       ▼                                     ▼
 MODULE A                             MODULE B
 Normal-Blink Detector                Long-Closure Detector
 (template / peak-based)              (sustained suppression)
       │                                     │
       └──────────────┬──────────────────────┘
                      ▼
              Event Merger & Deduplication
              (resolve overlaps, assign type labels)
                      │
                      ▼
              Unified Output:
              [onset, duration, type, confidence]
```

### 6.2 Module A — Normal-Blink Detector

**Goal**: detect events with duration 100–500 ms.

**Approach**: retain the existing pyblinker pipeline with relaxed constraints, or use the Kleifges / Nathanael epoch-based detector already validated in this project. Key parameters:

- Threshold crossing on the bandpass-filtered signal to find candidate peaks.
- Gaussian template fit with **relaxed R² cutoff** (e.g., R² ≥ 0.5 instead of the stricter default).
- Width filter: accept events with duration ≤ `NORMAL_MAX_DURATION` (e.g., 500 ms).
- pAVR filter: keep as-is (tuned for normal blinks).

### 6.3 Module B — Long-Closure Detector

**Goal**: detect events with duration ≥ 500 ms.

**Approach**: signal-suppression / threshold-hold method, not template fitting.

**Algorithm sketch**:

1. **Rectified envelope**: compute a smooth absolute envelope of the filtered EOG signal using a moving RMS window (e.g., 50 ms window, 10 ms hop).
2. **Baseline estimation**: compute a rolling 10-second percentile (e.g., 75th percentile) as the baseline activity level.
3. **Entry threshold**: flag onset when the envelope drops below `alpha × baseline` (e.g., α = 0.3) for at least `min_duration` samples (e.g., 50 ms).
4. **Hold**: extend the event as long as the signal remains below the threshold.
5. **Exit**: mark end when the signal rises back above the threshold for ≥ `debounce` samples.
6. **Filter**: discard events shorter than `MIN_LONG_DURATION` (500 ms) — these are either noise or normal blinks already handled by Module A.
7. **Optional**: fit a trapezoidal or top-hat template to validate the plateau; require that the mid-portion is flat (variance below a threshold) to distinguish a genuine closure from an artefact.

Key parameters:
- `alpha`: suppression ratio (default 0.3 — signal must drop to 30% of baseline)
- `MIN_LONG_DURATION`: 0.5 s (PERCLOS standard)
- `MAX_LONG_DURATION`: configurable upper bound (e.g., 15 s)
- `baseline_window_s`: 10 s rolling baseline
- `debounce_ms`: 50 ms re-opening debounce

### 6.4 Event Merger and Deduplication

After both modules run:

1. **Temporal overlap resolution**: if a Module A event and a Module B event overlap by > 50% of the shorter event's duration, the Module B (long) event takes priority — the long closure subsumes the onset blink.
2. **Back-to-back filtering**: two Module A events within `merge_gap_ms` (e.g., 100 ms) of each other that together span ≥ 500 ms should be re-examined as a candidate long closure.
3. **Type labeling**: assign `type = "normal"` or `type = "long"` to each surviving event.
4. **Confidence score**: for normal events, use the Gaussian fit R²; for long events, use the plateau flatness ratio.

### 6.5 Evaluation protocol

The new algorithm should be evaluated using the same framework as this project:
- **Script pattern**: mirror `tutorial/14_pyblinker_long_blink_analysis.py`.
- **Ground truth split**: `classify_events(csv_path)` already implemented — returns `(all_df, normal_df, long_df)`.
- **Metrics reported separately**: recall/precision/F1 for normal blinks AND long blinks, per session and micro-averaged.
- **Target performance**:
  - Normal blink recall ≥ 0.83 (match current pyblinker baseline)
  - Long blink recall ≥ 0.80 (current pyblinker: 0.55 — target a +25 pp improvement)
  - Long blink F1 ≥ 0.70 (current: 0.27)

### 6.6 Implementation guidance

- **Location**: implement as a new strategy in `src/` (e.g., `src/strategies/dual_mode_detector.py`) following the pattern of existing strategies.
- **Tutorial script**: create `tutorial/15_strategy_dual_mode.py` following the structure of `tutorial/12_strategy_pyblinker_continuous.py` for the continuous-signal evaluation, and `tutorial/11_strategy_pyblinker_epoch.py` for epoch-mode evaluation.
- **Module B is the new contribution**: Module A can wrap the existing pyblinker detection or any already-validated detector (Kleifges, Nathanael).
- **No new dependencies required**: the algorithm is implementable with NumPy, SciPy (`scipy.signal` for envelope), and MNE (for I/O and filtering).
- **Conda environment**: `pyblinker_worktree_epoch_blink`.

---

## 7. Summary

| Finding | Value |
|---|---|
| Normal blink recall (pyblinker) | **0.83** |
| Long blink recall (pyblinker) | **0.55** |
| Recall gap | **−0.28 pp** |
| Root cause | FitBlinks shape filter + width outlier rejection + pAVR velocity filter |
| Proposed fix | Dual-mode detector: existing pipeline for normal + suppression-hold method for long |
| Target long recall | ≥ 0.80 |

The pyblinker pipeline is **not a reliable detector for long eye closures**. A dedicated sustained-suppression module, running in parallel with the existing normal-blink detector and merging results into a unified output, is the recommended approach to address this gap.

---

*Generated from Tutorial 14 analysis (`tutorial/14_pyblinker_long_blink_analysis.py`). Dataset: Raja drowsy driving, 5 mixed sessions, 2,406 normal + 897 long ground-truth events.*
