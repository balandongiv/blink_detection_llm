# Blink Threshold Center Methods: Median vs Mean

This document explains the two center strategies available in
`pyblinker/strategy_f/blink_threshold.py` for Stage B threshold estimation.

---

## What both methods have in common

Both methods compute a threshold using the same three-step formula:

1. Compute a **center** — a representative amplitude level from the flagged epoch samples.
2. Compute a **dispersion** — a robust spread estimate using the Median Absolute Deviation (MAD):

   ```
   dispersion = 1.4826 * MAD(samples)
   ```

   The factor `1.4826` normalises MAD to the same scale as the standard deviation for a
   Gaussian distribution (since MAD ≈ 0.6745 * std for a normal distribution).

3. Compute the **threshold**:

   ```
   threshold = center + std_threshold * dispersion
   ```

   where `std_threshold` (default 3.5) controls how many robust standard deviations above
   the center the threshold is placed.

The only difference between the two strategies is step 1 — how the center is computed.

---

## Median-based center (`center_method="median"`)

The center is set to the **median** of the sample amplitudes from the flagged epochs:

```python
center = np.median(samples)
```

### Why this is the recommended default

- The median depends only on the **rank** of the values, not their magnitude.
  A handful of very large blink peaks cannot pull the median upward.
- MAD is also rank-based and shares this robustness property.
- Together, `median + 1.4826 * MAD` produces a threshold that is **stable even when
  the flagged epochs contain strong outliers** — which is expected, because those epochs
  were flagged precisely because they look blink-like.

### When to choose this method

- When robustness is the priority.
- When the flagged epochs are strongly right-skewed (large positive blink peaks dominate).
- As the default, conservative-in-threshold but sensitive-in-detection choice.

**Effect:** The threshold is lower compared to the mean-based method on skewed data,
so the detector tends to **find more blink regions**, including smaller ones.

---

## Mean-based center (`center_method="mean"`)

The center is set to the **arithmetic mean** of the sample amplitudes:

```python
center = np.mean(samples, dtype=np.float64)
```

### Behaviour on blink-heavy data

- The arithmetic mean is sensitive to outliers. Large positive blink peaks pull the mean
  upward relative to the median.
- On the right-skewed distributions typical of flagged blink epochs, the mean is
  **systematically higher than the median**.
- A higher center produces a higher threshold.

### When to choose this method

- When comparing against legacy behaviour that used mean-based thresholds (e.g. the
  original BLINKER MATLAB pipeline, which uses `mean + k * 1.4826 * MAD`).
- When you want a **deliberately conservative detector** that only captures the most
  prominent, large-amplitude blink events.
- As an experimental upper bound to understand how sensitive results are to the center
  choice.

**Effect:** The threshold is higher, so the detector tends to **find fewer blink regions**,
skipping smaller or borderline events.

---

## Practical consequence

| Method | Center | Threshold level | Detection sensitivity |
|--------|--------|-----------------|-----------------------|
| median | Lower (unaffected by peaks) | Lower | Higher — finds more blinks |
| mean   | Higher (pulled by peaks)    | Higher | Lower — finds fewer blinks |

In practice:

- The **median-based threshold usually detects more blink regions**, including smaller ones.
- The **mean-based threshold usually detects fewer, more conservative regions**.

---

## Numeric example

```
samples = [0, 0, 1, 1, 2, 2, 10, 12]

median = 1.5
mean   = 3.5
```

With `std_threshold = 3.5`:

```
MAD(samples) = median(|x - median(x)|) = median([1.5, 1.5, 0.5, 0.5, 0.5, 0.5, 8.5, 10.5])
             = 1.0
dispersion   = 1.4826 * 1.0 = 1.4826

threshold (median) = 1.5  + 3.5 * 1.4826 = 1.5  + 5.189 = 6.69
threshold (mean)   = 3.5  + 3.5 * 1.4826 = 3.5  + 5.189 = 8.69
```

The mean-based threshold (8.69) is 2 units higher than the median-based threshold (6.69).
In this toy example, only samples with amplitude above 8.69 would be considered blink-like
under the mean strategy, while the median strategy would already flag anything above 6.69.

---

## Summary

Use `center_method="median"` (the default) unless you have a specific reason to compare
against mean-based behaviour. The median is more robust to the skewed distributions that
arise naturally when thresholding is estimated from blink-heavy flagged epochs.
