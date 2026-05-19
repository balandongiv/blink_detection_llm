# Strategy E Derivative Ideas

If **Strategy E is the Step 1 recall-first baseline**, the best next move is to
keep its **per-epoch adaptivity** but make it less naive than "single threshold +
crossing."

The goal is to:

- keep **TP high**
- reduce **FN further if possible**
- avoid FP exploding too much
- remain robust across all 65 pairs

Here are strong **exploratory variants of Strategy E** to test.

---

## 1. Two-Threshold Hysteresis Strategy E

Instead of one threshold per epoch, use:

- a **high threshold** to start a blink candidate
- a **low threshold** to continue or close the event

```math
T_{high} = \mu_e + k_h \cdot 1.4826 \cdot MAD_e
```

```math
T_{low} = \mu_e + k_l \cdot 1.4826 \cdot MAD_e,\quad k_l < k_h
```

Why this helps:

- reduces fragmented detections
- stabilizes event boundaries
- can preserve weak blinks once initiated
- often improves recall without as much FP inflation as lowering one global threshold

Good starting values:

- `k_h = 1.5`
- `k_l = 1.0` or `0.8`

This is one of the most natural upgrades to Strategy E.

---

## 2. Robust Local Baseline Instead Of Epoch Mean

Current Strategy E uses:

```math
T_e = \text{mean}(epoch_e) + k \cdot 1.4826 \cdot MAD(epoch_e)
```

A better version may be:

```math
T_e = \text{median}(epoch_e) + k \cdot 1.4826 \cdot MAD(epoch_e)
```

Why:

- mean can be pulled upward by large blink peaks already inside the epoch
- median is more stable under outliers
- lower bias in noisy or skewed epochs
- may recover moderate blinks that are suppressed by inflated means

This is a very clean experiment:

- **E-mean**
- **E-median**

I would test this first.

---

## 3. Sliding-Window MAD Threshold Inside Each Epoch

Right now, Strategy E adapts at the **epoch level**. You can push it further to
**sub-epoch adaptation**.

For each epoch, compute the threshold in a rolling window, such as:

- 0.5 s
- 1.0 s
- 2.0 s

Then detect crossings against a **time-varying threshold**.

Why this may help:

- handles intra-epoch drift
- handles posture or movement changes inside long epochs
- may catch weak blinks in locally quiet regions

Trade-off:

- more unstable if the window is too short
- can increase FP if the threshold fluctuates too aggressively

This is a strong exploratory direction, especially if epochs are long.

---

## 4. Channel-Fusion Strategy E

If you have multiple frontal channels, do not rely only on independent threshold
hits. Use per-channel Strategy E, then fuse detections.

Three good fusion modes:

### 4a. OR Fusion

A blink is proposed if detected on **any** frontal channel.

- best for recall
- FP rises

### 4b. 2-Of-N Voting

A blink is proposed only if detected in at least two channels within a small time
tolerance.

- good recall / FP compromise
- likely strongest practical upgrade

### 4c. Weighted Fusion

Channels closer to the eye get stronger votes.

This may be one of the most effective upgrades if your current method is
single-channel dominant.

---

## 5. Multi-Scale Strategy E

Run Strategy E several times with different settings and union the candidates.

Example branches:

- **E1:** `k = 1.2`, min length = 40 ms
- **E2:** `k = 1.5`, min length = 50 ms
- **E3:** `k = 1.8`, min length = 70 ms

Then merge overlapping detections.

Why this helps:

- small sharp blinks and broader slower blinks may need different thresholds
- one detector rarely covers all blink morphologies
- union of multi-scale proposals often improves recall

This is especially useful for Step 1 because some FP growth is tolerable.

---

## 6. Candidate Expansion Around Threshold Crossings

Sometimes the detector catches the blink peak but underestimates event
boundaries.

After finding a crossing:

- expand left until slope or amplitude falls below a relaxed condition
- expand right similarly
- then merge nearby segments

Why useful:

- improves overlap with ground truth
- can convert borderline FP/FN matching failures into TP
- especially useful if evaluation requires event overlap quality

You can also add a **gap-bridging rule**:

- merge candidates separated by less than 30-80 ms

That often fixes split blinks.

---

## 7. Duration-Aware Strategy E

Keep recall-first thresholding, but use relaxed duration classes.

Instead of one minimum event length, use a duration band:

- reject very tiny spikes: `< 30-40 ms`
- accept likely blink range: `50-400 ms`
- keep uncertain events separately

You can even create three classes:

- **strong candidates**
- **weak candidates**
- **artifact-like candidates**

For Step 1, pass strong and weak candidates into Step 2.

This is better than hard rejection because it preserves recall.

---

## 8. Slope-Assisted Strategy E

Threshold crossing alone is amplitude-based. Add simple first-derivative logic.

A candidate is stronger if it has:

- rising slope before peak
- falling slope after peak
- minimum peak prominence
- limited plateau width

This is still lightweight and exploratory, but it helps distinguish:

- real blink waveform
- slow drift
- flat noise bursts

This is a very good Step 1.5 filter because it removes obvious junk without being
too strict.

---

## 9. Asymmetric Thresholding For Positive And Negative Blink Polarity

Depending on preprocessing and channel orientation, blinks may not be symmetric.

Try:

- positive-only threshold detection
- negative-only threshold detection
- absolute-amplitude detection
- polarity-adaptive per channel

If one subject's blink polarity flips, a fixed-sign detector can lose recall
badly.

A strong exploratory variant is:

- detect on `|x - baseline|`, not just `x`

This can recover missed events across subjects.

---

## 10. Subject-Adaptive `k` Instead Of Fixed `k = 1.5`

BLINKER default `k = 1.5` is a good start, but Step 1 may benefit from subject
tuning.

Exploratory grid:

- `k = 1.0`
- `k = 1.2`
- `k = 1.5`
- `k = 1.8`
- `k = 2.0`

You can choose:

- one best global `k` for recall
- a subject-level `k` based on signal statistics

Even a simple rule like this may work:

- noisier subjects -> larger `k`
- quieter subjects -> smaller `k`

This preserves adaptivity beyond epoch level.

---

## 11. Quantile-Based Threshold Instead Of MAD-Only

Another exploratory path:

```math
T_e = Q_p(epoch_e)
```

where `Q_p` is a high quantile, such as:

- 90th percentile
- 92.5th percentile
- 95th percentile

Or combine with MAD:

```math
T_e = \max(\text{median} + k \cdot MAD,\ Q_p)
```

Why useful:

- quantiles can be more intuitive for skewed distributions
- may be more stable when MAD is too small in very quiet epochs
- prevents threshold collapsing too low

This could directly address the FP growth in Strategy E.

---

## 12. Noise-Floor Constrained Strategy E

One problem with per-epoch adaptivity is that in very quiet epochs the threshold
may become too permissive.

You can add a lower bound:

```math
T_e = \max(T_{epoch}, T_{global\_floor})
```

where:

- `T_epoch` = per-epoch MAD threshold
- `T_global_floor` = subject-level minimum threshold

This is a very practical fix.

It keeps Strategy E adaptive, but prevents pathological low thresholds. This may
reduce FP substantially while keeping most of the recall gain.

---

## 13. Template Matching After Strategy E Candidate Proposal

Keep Strategy E exactly as-is for proposal generation, then do a cheap second
pass.

For each candidate:

- extract local waveform window
- correlate with blink template
- compute peak symmetry, width, and prominence

Then keep:

- all strong template matches
- borderline matches as soft candidates

This is probably the most realistic path if you want:

- Step 1 high recall
- small FP cleanup before full Step 2

---

## 14. Strategy E With Refractory Constraint

Add a minimum separation between blink peaks, for example:

- 100 ms
- 150 ms
- 200 ms

If two candidates are too close:

- keep the stronger one
- or merge them

This suppresses threshold chatter and split events. It is very easy to test and
often helpful.

---

## 15. Confidence-Scored Strategy E Instead Of Binary Output

This is a strong research direction.

Instead of outputting only blink / non-blink, output a candidate score based on:

- peak height above threshold
- event duration
- local prominence
- number of supporting channels
- slope consistency
- template correlation

Then Step 2 can operate on ranked proposals.

This is often better than hard filtering because it preserves recall while still
organizing FP.

---

## Best Exploratory Variants To Try First

If you want the **highest-value next experiments**, prioritize these:

### Tier 1

1. **E-median:** replace mean with median
2. **E-hysteresis:** high/low thresholds
3. **E-floor:** per-epoch threshold with subject-level minimum floor
4. **E-vote:** 2-of-N frontal channel voting

These are likely to improve robustness with minimal complexity.

### Tier 2

5. **E-multiscale:** union of several `k` values
6. **E-refractory:** merge/suppress overly close detections
7. **E-template-lite:** cheap morphology scoring after proposal

### Tier 3

8. **E-sliding-window:** local adaptive threshold inside epoch
9. **E-confidence:** ranked candidate system
10. **E-quantile hybrid:** MAD + quantile floor

---

## Experimental Roadmap

You could frame the exploratory pipeline like this:

### Baseline

- **E0:** current Strategy E

### Robust Threshold Family

- **E1:** median + MAD
- **E2:** median + MAD + floor
- **E3:** hysteresis MAD

### Structural Refinement Family

- **E4:** E0 + merge nearby detections
- **E5:** E0 + refractory rule
- **E6:** E0 + duration bands

### Multi-Channel Family

- **E7:** OR fusion
- **E8:** 2-of-N voting
- **E9:** weighted fusion

### Recall-Maximizing Family

- **E10:** multi-k union
- **E11:** sliding-window MAD
- **E12:** absolute-polarity adaptive detection

Then compare on:

- TP
- FN
- recall
- FP
- precision
- failures

For Step 1, sort primarily by:

1. **lowest FN**
2. **highest recall**
3. **acceptable FP growth**
4. **zero failures**
