# Strategy F Improvement Plan
## Objective: Win Recall AND F1 Against Strategy A

**Author:** Generated 2026-04-18  
**Status:** Ready for implementation  
**Development dataset:** `drowsy_driving_raja_processed` only  
**Validation dataset:** `murat_2018` (only after dev results are satisfactory)

---

## 0. Current Code State (read this first)

Before starting, check the actual default values in each file:

| file | parameter | current value | note |
|------|-----------|---------------|------|
| `pyblinker/strategy_f/core.py` line ~67 | `std_threshold` default | **1.5** | changed from 3.5 |
| `pyblinker/strategy_f/runner.py` line ~47 | `std_threshold` default | **3.5** | original (linter reverted) |
| `tutorial/20_strategy_comparison.py` line ~82 | `STD_THRESHOLD` constant | **3.5** | original (linter reverted) |
| `tutorial/21_strategy_comparison_murat2018.py` line ~85 | `STD_THRESHOLD` constant | **3.5** | original (linter reverted) |

**What this means in practice:**

- `tutorial/20` and `tutorial/21` pass `STD_THRESHOLD` explicitly to `channel_results_strategy_f`,
  so those benchmarks run at **k=3.5** regardless of `core.py` default.
- `runner.py`'s `run_strategy_f()` also defaults to **k=3.5**.
- Only a direct call to `channel_results_strategy_f(prepared, ..., setting={})` with no
  `std_threshold` key would use `core.py`'s default of 1.5.

**Before running the G1/G2/G3 experiments, decide which baseline to start from:**

- **Option A (start from k=1.5 — recommended):** Set `STD_THRESHOLD = 1.5` in `tutorial/20`,
  `runner.py` default to `1.5`, and keep `core.py` at 1.5. This gives F new baseline
  (recall beats A). G1/G2/G3 then try to recover F1 without sacrificing that recall.
- **Option B (start from k=3.5 — conservative):** Leave everything at 3.5. G1/G2/G3 must
  then simultaneously improve recall AND F1. This is harder.

**Recommendation: use Option A.** The k=1.5 result already proves recall > A is achievable;
the experiments below try to recover F1.

---

## 1. Current Situation

### What we have

Two variants of Strategy F exist:

| variant | micro_R (drowsy, 10p) | micro_F1 (drowsy, 10p) | micro_R (murat, 3p) | micro_F1 (murat, 3p) |
|---------|----------------------|------------------------|---------------------|----------------------|
| Strategy A | 0.9253 | 0.5257 | 0.9666 | 0.5712 |
| F old (k=3.5) | ~0.9039 (9p) | ~0.8375 (9p) | 0.7979 | 0.8161 |
| **F new (k=1.5)** | **0.9267** | **0.5828** | **0.9628** | **0.6335** |

**F new (k=1.5) beats Strategy A on both recall and F1.** This is confirmed on drowsy (10 pairs) and murat_2018 (3 pairs).

### The remaining problem

F new (k=1.5) achieves the minimum and practical success targets, but its F1 (0.5828) is far below the old F baseline (0.8375). The gap comes from **2684 FP** vs A's 3415 FP — F is cleaner than A but not as clean as the old F (k=3.5, ~400 FP).

### Ideal target

| metric | current F new | target |
|--------|---------------|--------|
| micro_R | 0.9267 | >= 0.9267 (must not regress) |
| micro_F1 | 0.5828 | as high as possible while keeping recall >= 0.9267 |
| FP | 2684 | reduce toward the old F baseline (400 FP) without losing TP |

The challenge: at k=1.5, detecting all blinks means accepting many borderline detections that are actually noise. We need to surgically remove the FPs without removing TPs.

---

## 2. Root Cause of the Recall-F1 Tradeoff

### How Strategy F computes its threshold

```
Stage A  →  autoreject PTP screening → flags "blink-heavy" epochs
Stage B  →  threshold = median(flagged_epochs) + k * 1.4826 * MAD(flagged_epochs)
Stage C  →  detect blinks: scan signal, emit event whenever signal > threshold for >= min_blink_frames
```

The single threshold `k * dispersion` controls BOTH:
- **Recall**: lower k → lower threshold → catches weaker blinks (more TP)
- **Precision**: higher k → higher threshold → rejects noise (fewer FP)

At k=1.5 we catch all blinks AND catch noise. At k=3.5 we reject noise AND reject weak blinks.
There is no single k that wins both.

### Why FPs are hard to eliminate by duration

Experiment 3 showed that max_event_len filtering at ≤1.0s removes TPs as fast as FPs:
- At 0.7s: lose 19 TP, gain only 12 fewer FP (terrible ratio)
- The FPs at k=1.5 are short noise events with durations overlapping real blinks

### The key insight

The problem is that a **single gate** (threshold crossing) is used for both candidate generation and candidate acceptance. If we **decouple** these two roles, we can:
- Use a **permissive gate** (k_low=1.5) to ensure no real blink is missed (high recall)
- Use a **strict confirmation** on each candidate to reject noise (high precision)

---

## 3. Proposed Improvements (in priority order)

---

### Approach G1: Two-Tier Peak Confirmation (HIGHEST PRIORITY)

#### Hypothesis

When a blink is detected by crossing threshold at k_low=1.5, the peak amplitude of the event tells us whether it is a true blink (large, sharp peak) or noise (small, barely-exceeding event). Real blinks have peaks well above the detection threshold; noise events barely exceed it.

A second check — "does the event peak exceed center + k_confirm * dispersion?" — should filter noise without losing blinks.

#### How to implement

**File to modify:** `pyblinker/strategy_f/core.py`, function `blink_position_strategy_f`

**New parameters (add to `setting` dict):**

```python
k_confirm = options.get("k_confirm", None)  # float or None; if None, no confirmation step
```

**After the `scan_threshold_crossings_kleifges` call, add:**

```python
# Stage D: peak confirmation filter.
# Keep only events whose signal peak exceeds center + k_confirm * dispersion.
# This decouples candidate generation (k=1.5, permissive) from acceptance (k_confirm, strict).
if k_confirm is not None and len(start_blinks) > 0:
    center_val     = float(threshold_result.centers[channel_name])
    dispersion_val = float(threshold_result.dispersions[channel_name])
    confirm_level  = center_val + float(k_confirm) * dispersion_val

    keep_mask = np.array([
        float(concatenated_signal[s:e].max()) >= confirm_level
        for s, e in zip(start_blinks, end_blinks)
    ], dtype=bool)
    start_blinks = start_blinks[keep_mask]
    end_blinks   = end_blinks[keep_mask]
```

Note: `threshold_result.centers` and `threshold_result.dispersions` are already computed per-channel in Stage B. No additional data is needed.

**Also add `k_confirm` to the result dict for diagnostics:**

```python
results.append({
    ...
    "k_confirm": k_confirm,
    "confirm_level": confirm_level if k_confirm is not None else None,
})
```

#### Experiment grid

Run `tutorial/22_strategy_f_recall_experiments.py` (or a new script) with:

```
std_threshold = 1.5       # fixed (detection gate)
k_confirm ∈ {None, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0}
```

Expected outcome:
- k_confirm=None → same as F_k1.5 (baseline, recall=0.9267, F1=0.5828)
- k_confirm=3.5  → approaches old F (k=3.5) but with recall floor of k=1.5
- Somewhere between 2.0 and 3.5: recall > A + F1 significantly above 0.5828

#### Why this is principled

The center and dispersion are already computed from flagged epochs (Stage B). The confirmation threshold reuses these statistics without introducing new data. The `k_confirm` parameter has a clear physical interpretation (number of robust standard deviations above baseline that the blink peak must reach).

---

### Approach G2: Per-Epoch Threshold (MEDIUM PRIORITY)

#### Hypothesis

The current Stage B computes ONE threshold per channel across ALL flagged epochs. If an epoch has low baseline noise, the global threshold is too high for it (misses weak blinks). If an epoch has high baseline noise, the global threshold is too low for it (generates FPs).

Computing a separate threshold per epoch adapts to local conditions:
- Quiet epochs: lower threshold → catches weak blinks
- Noisy epochs: higher threshold → fewer FPs

#### How to implement

**File to modify:** `pyblinker/strategy_f/core.py`

**Add a new parameter:**

```python
per_epoch_threshold = bool(options.get("per_epoch_threshold", False))
```

**If True, replace the single-signal scan with an epoch-by-epoch scan:**

```python
if per_epoch_threshold:
    start_blinks_list = []
    end_blinks_list   = []
    offset = 0
    for ep_local_idx, ep_global_idx in enumerate(valid_epoch_indices):
        ep_signal = prepared.data[ep_global_idx, channel_idx, :]
        # Compute epoch-specific threshold
        ep_center, ep_disp, ep_thresh = compute_threshold_from_samples(
            ep_signal, std_threshold, center_method=center_method
        )
        ep_starts, ep_ends = scan_threshold_crossings_kleifges(
            ep_signal, ep_thresh, min_blink_frames,
            progress_bar=False, channel_name=channel_name,
        )
        # Shift indices to concatenated-signal frame of reference
        start_blinks_list.extend(ep_starts + offset)
        end_blinks_list.extend(ep_ends   + offset)
        offset += prepared.epoch_length_samples

    start_blinks = np.array(start_blinks_list, dtype=int)
    end_blinks   = np.array(end_blinks_list,   dtype=int)
else:
    # Original single-threshold scan
    ...
```

Note: `compute_threshold_from_samples` is already importable from `pyblinker.strategy_f.blink_threshold`.

#### Expected outcome

- Quiet epochs get epoch-calibrated thresholds (lower) → recall improves on low-amplitude blinks
- Noisy epochs get epoch-calibrated thresholds (higher) → precision improves on noisy pairs
- Net effect on F1: depends on dataset, but likely better than global threshold at the same k

#### Caution

Per-epoch threshold estimation from 60-second windows is statistically stable. However, if a single epoch is dominated by blink peaks (e.g., rapid blinking), the epoch median is still at baseline (median is robust) but MAD could be inflated. Verify with verbose diagnostics.

---

### Approach G3: Epoch-Type Split Threshold (MEDIUM PRIORITY)

#### Hypothesis

Currently, Stage B computes ONE threshold from flagged (blink-heavy) epochs and applies it everywhere. A principled extension:

- **Flagged epochs** (autoreject says blink-heavy): threshold from flagged-epoch statistics, k=3.5 (signal is strong; use strict gate to suppress noise)
- **Non-flagged epochs** (autoreject says clean): threshold from all-epoch statistics, k=1.5 (signal might be weak; use permissive gate to catch weak blinks)

This uses autoreject's information more fully: flagged epochs have well-captured blinks (no need for permissive gate); non-flagged epochs might have subtle blinks that need a sensitive detector.

#### How to implement

**File to modify:** `pyblinker/strategy_f/core.py`

**New parameters:**

```python
k_flagged    = float(options.get("k_flagged",    3.5))  # threshold for flagged epochs
k_nonflagged = float(options.get("k_nonflagged", 1.5))  # threshold for non-flagged epochs
```

**In Stage C, scan epoch-by-epoch and apply appropriate threshold:**

```python
flagged_set = set(screen_result.flagged_valid_epoch_indices)

start_blinks_list = []
end_blinks_list   = []
offset = 0

# Compute both thresholds once per channel (reuse Stage B)
thresh_flagged    = compute_flagged_epoch_threshold(
    prepared, valid_epoch_indices,
    screen_result.flagged_valid_epoch_indices,
    std_threshold=k_flagged, center_method=center_method,
)
thresh_nonflagged = compute_flagged_epoch_threshold(
    prepared, valid_epoch_indices,
    [],  # empty → uses all valid epochs as fallback
    std_threshold=k_nonflagged, center_method=center_method,
)

for ep_global_idx in valid_epoch_indices:
    ep_signal = prepared.data[ep_global_idx, channel_idx, :]
    if ep_global_idx in flagged_set:
        ep_thresh = thresh_flagged.thresholds[channel_name]
    else:
        ep_thresh = thresh_nonflagged.thresholds[channel_name]

    ep_starts, ep_ends = scan_threshold_crossings_kleifges(
        ep_signal, ep_thresh, min_blink_frames,
        progress_bar=False, channel_name=channel_name,
    )
    start_blinks_list.extend(ep_starts + offset)
    end_blinks_list.extend(ep_ends   + offset)
    offset += prepared.epoch_length_samples
```

#### Experiment grid

```
k_flagged    ∈ {3.5, 3.0, 2.5}    # threshold for strong-blink epochs
k_nonflagged ∈ {1.5, 1.0}          # threshold for potentially weak-blink epochs
```

All combinations: 6 experiments. Focus on k_flagged=3.5 + k_nonflagged=1.5 first.

---

### Approach G4: Combine G1 + G3 (STRETCH)

Apply G3 for recall (epoch-split thresholds) AND G1 for precision (peak confirmation on G3 candidates).

Only pursue this if G1 and G3 individually show partial improvement, and combining them is needed to hit the target.

---

## 4. Implementation Files

| file | role | what to change |
|------|------|----------------|
| `pyblinker/strategy_f/core.py` | main detection loop | add `k_confirm`, `per_epoch_threshold`, or `k_flagged/k_nonflagged` parameters |
| `pyblinker/strategy_f/runner.py` | public API | expose new parameters with their defaults |
| `pyblinker/strategy_f/blink_threshold.py` | threshold computation | already has `compute_flagged_epoch_threshold`; reuse for per-epoch or split-threshold approaches |
| `tutorial/22_strategy_f_recall_experiments.py` | experiment runner | extend `_build_variants()` with new parameter dicts; extend `run_one()` to pass new params |
| `tutorial/20_strategy_comparison.py` | official benchmark | update `STD_THRESHOLD` and any new params when freezing the final design |
| `tutorial/21_strategy_comparison_murat2018.py` | validation benchmark | update only AFTER drowsy results are satisfactory |

---

## 5. Evaluation Protocol

### Step 1: Develop on drowsy_driving_raja_processed

Run experiments using `tutorial/22_strategy_f_recall_experiments.py`.

For each experiment report:
```
variant label | TP | FP | FN | micro_P | micro_R | micro_F1 | dR_vs_A | dF1_vs_A | note
```

**Every variant must be compared against the fixed A baseline in the same run.**

### Step 2: Check minimum success criteria before proceeding

| criterion | target |
|-----------|--------|
| micro_R > A micro_R | **mandatory** — if this fails, reject the variant |
| micro_F1 > current F_new micro_F1 (0.5828) | must improve on the k=1.5 baseline |
| micro_F1 > A micro_F1 (0.5257) | must beat A on F1 |

If a variant passes Step 2, compute the F1 improvement over F_new baseline and over old F baseline (0.8375):

```
F1 recovery = (variant_F1 - F_new_F1) / (F_old_F1 - F_new_F1)
```

A recovery of 1.0 means full F1 restoration without recall loss. Aim for the highest recovery that still satisfies recall > A.

### Step 3: Lock the design

After finding the best variant on drowsy, freeze ALL parameters. Do not re-tune on murat_2018.

### Step 4: Validate on murat_2018

Run `tutorial/21_strategy_comparison_murat2018.py` with the frozen parameters.

Report:
- old F (k=3.5) baseline on murat: micro_R=0.7979, micro_F1=0.8161
- new F (k=1.5) baseline on murat: micro_R=0.9628, micro_F1=0.6335
- A on murat: micro_R=0.9666, micro_F1=0.5712

Check that the new variant:
1. Recall ≥ F_new recall on murat (does not regress from k=1.5)
2. F1 ≥ F_new F1 on murat (improves over k=1.5)

---

## 6. Experiment Scaffolding

### How to extend the experiment script

In `tutorial/22_strategy_f_recall_experiments.py`, extend `_build_variants()`:

```python
# G1: Peak confirmation sweep
for k_c in [None, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
    label = f"G1_kc{k_c}" if k_c is not None else "G1_kc_none"
    variants.append({
        "label": label,
        "std_threshold": 1.5,   # detection gate fixed
        "center_method": "median",
        "max_event_len": None,
        "k_confirm": k_c,       # NEW: confirmation gate
    })
```

In `run_one()`, pass the new parameter to the strategy:

```python
setting = {
    ...
    "std_threshold": std_threshold,
    "k_confirm":     variant.get("k_confirm", None),
}
```

### How to run (always use the correct conda env)

```bash
PYTHONIOENCODING=utf-8 \
  /c/Users/balan/anaconda3/envs/pyblinker_worktree_epoch_blink/python.exe \
  tutorial/22_strategy_f_recall_experiments.py 2>&1 | \
  grep -E "^(variant|A |G|F_|=|-)"
```

---

## 7. Key Constraints (non-negotiable)

1. **Do not tune on murat_2018** until drowsy results are locked.
2. **Do not remove pairs or subjects** to make results look better.
3. **Do not weaken Strategy A** or modify the benchmark unfairly.
4. **Report all experiments** (wins and losses).
5. **Every change must be a parameter or design change** — no dataset-specific hacks.
6. **Recall must not regress below current F new (0.9267 on drowsy)** when adding a confirmation step.
7. The "recall floor" is k=1.5. Any addition on top (G1, G2, G3) must preserve this floor.

---

## 8. Current Baseline Numbers (frozen reference)

### drowsy_driving_raja_processed (10 pairs)

```
strategy     n_pairs  TP(sum)  FP(sum)  FN(sum)  micro_P  micro_R  micro_F1
A                 10     1981     3415      160   0.3671   0.9253   0.5257
B                 10     1517     1272      624   0.5439   0.7085   0.6154
C                 10     1960      706      181   0.7352   0.9155   0.8155
F(k=1.5)new       10     1984     2684      157   0.4250   0.9267   0.5828
```

The F(k=3.5) old baseline on 9 pairs was: micro_R=0.9039, micro_F1=0.8375.
When the experiment runs on 10 pairs with k=3.5, expect approximately similar FP (~500) and lower recall (~0.90–0.91).

### murat_2018 (3 pairs)

```
strategy     n_pairs  TP(sum)  FP(sum)  FN(sum)  micro_P  micro_R  micro_F1
A                  3     1535     2252       53   0.4053   0.9666   0.5712
F(k=3.5)old        3     1267      250      321   0.8352   0.7979   0.8161
F(k=1.5)new        3     1529     1710       59   0.4721   0.9628   0.6335
```

---

## 9. What the Next Agent Should Do First

1. **Read** `pyblinker/strategy_f/core.py` (Stage C section, lines ~95–148).
2. **Implement Approach G1** (two-tier peak confirmation) — it is the smallest, most targeted change.
3. **Run the experiment grid** for G1 (k_confirm sweep) on drowsy.
4. **Report the summary table** with the dR_vs_A and dF1_vs_F_new columns.
5. If G1 achieves recall > 0.9267 AND F1 > 0.6500 (a reasonable initial target), freeze and validate on murat.
6. If G1 is insufficient, implement G2 or G3 as described above.
7. Do NOT try all three at once — test sequentially, understand each result before adding complexity.

---

## 10. Architecture Reference

```
Strategy F pipeline (current state, k=1.5)
==========================================
Epochs (valid)
    │
    ├─ Stage A: autoreject PTP screening
    │           → flags blink-heavy epochs
    │
    ├─ Stage B: compute threshold per channel
    │           samples   = concat(flagged_epochs)
    │           center    = median(samples)
    │           dispersion= 1.4826 * MAD(samples)
    │           threshold = center + 1.5 * dispersion
    │
    └─ Stage C: scan concatenated signal
                for each sample:
                  if signal > threshold: enter blink region
                  if below threshold and duration > min_frames: emit event
                → (start_blinks, end_blinks) per channel

--- proposed Stage D (G1 only) ---
    └─ Stage D: peak confirmation filter
                for each (start, end) event:
                  peak = max(signal[start:end])
                  if peak >= center + k_confirm * dispersion: keep
                  else: discard
                → filtered (start_blinks, end_blinks)
```

Key functions and locations:
- `scan_threshold_crossings_kleifges` — `pyblinker/blinker/get_blink_positions.py:138`
- `compute_threshold_from_samples` — `pyblinker/strategy_f/blink_threshold.py:22`
- `compute_flagged_epoch_threshold` — `pyblinker/strategy_f/blink_threshold.py:116`
- `screen_epochs_with_autoreject` — `pyblinker/strategy_f/autoreject_epoch_screener.py:37`
- `blink_position_strategy_f` — `pyblinker/strategy_f/core.py:24`
