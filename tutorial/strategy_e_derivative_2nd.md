# Strategy E Derivatives: Second Iteration Ideas

This note proposes a second wave of **Strategy E derivatives** that are **not already covered** in `tutorial/strategy_e_derivative.md`.

The target is stricter than the first iteration:

1. keep the **0-failure** behavior of the E family
2. keep **recall at least as strong as strategy_e**
3. reduce FP enough to beat the practical quality of the first report
4. ideally beat **strategy_c micro F1 = 0.6530** while remaining more robust

---

# What the first iteration already taught us

From `tutorial/report_first_iteration.md`:

- `strategy_e` is the strongest recall-first baseline: **TP=30,872**, **FN=10,552**, **micro recall=0.7453**, **0 failures**
- `strategy_e3_hysteresis` and `strategy_e4_multiscale` push recall higher, but the FP cost is too large
- `strategy_e5_global_floor` is the best practical E-variant so far: **TP=30,811**, **FP=24,470**, **FN=10,613**, **micro F1=0.6372**, **0 failures**
- `strategy_c` still has the best F1 overall: **micro F1=0.6530**, but it has **1 failed pair**

So the main lesson is clear:

> The next E derivatives should not just lower threshold more aggressively.
> They need to make the per-epoch thresholding **smarter**, especially in how
> they decide when local adaptation is trustworthy and when a candidate is
> truly blink-like.

The first iteration already covered median, hard floors, hysteresis, and multiscale union.
The next step should focus on **adaptive trust**, **spatial structure**, and
**two-stage scoring**.

---

# New Derivative Ideas

## E6. Soft-Shrinkage Threshold

### Core idea

Replace the hard floor in E5 with a **soft interpolation** between local and global thresholds:

```text
T_local,e = median(epoch_e) + k * MAD(epoch_e)
T_global  = mean(full_signal) + k_g * MAD(full_signal)
T_e       = alpha_e * T_local,e + (1 - alpha_e) * T_global
```

where `alpha_e` is not fixed. It should depend on how trustworthy the epoch is.

Example:

```text
alpha_e = clip(MAD(epoch_e) / MAD(full_signal), 0.2, 0.9)
```

### Why this is new

`strategy_e5_global_floor` uses `max(T_local, T_global_floor)`, which is a hard guardrail.
That prevents collapse, but it can also over-correct and remove useful local adaptivity.

### Why it may beat first iteration

- quieter epochs get pulled toward the global threshold without being fully clamped
- noisier epochs can still benefit from local adaptation
- likely outcome: **between E1 and E5 on recall**, but **better than E1 on FP**

### Best use

This is the most natural next experiment after E5.

---

## E7. Iterative Background Refit

### Core idea

Run Strategy E in two passes:

1. first pass: detect permissive candidates
2. mask those candidate regions
3. recompute epoch statistics on the remaining background only
4. rerun the scan with the refit threshold

```text
pass 1 -> provisional candidates
background_e = epoch_e minus provisional candidate intervals
T_refit,e = median(background_e) + k * MAD(background_e)
pass 2 -> final candidates
```

### Why this is new

Median helps against outliers, but it still treats the whole epoch as one pool.
This variant explicitly estimates the **background distribution after removing blink-like regions**.

### Why it may beat first iteration

- large blink bursts no longer distort the statistics used for the same epoch
- noisy transient segments can be masked before threshold estimation
- can improve both directions:
  - recover moderate blinks hidden by inflated thresholds
  - suppress junk caused by contaminated local statistics

### Best use

Try this on top of E5 or E6, not on top of the raw mean-based E0.

---

## E8. Change-Point Adaptive Segmentation

### Core idea

Strategy E currently assumes fixed 60-second epochs are the right unit of adaptation.
That is convenient, but not necessarily the correct noise stationarity scale.

Instead:

1. split each long epoch into shorter stationary regions using change points in robust energy, median, or MAD
2. estimate one threshold per stationary region
3. scan each region independently

### Why this is new

This is different from sliding-window thresholding.
Sliding windows move continuously inside an epoch.
Change-point segmentation creates **piecewise-stationary blocks** with stable thresholds.

### Why it may beat first iteration

- quiet sub-regions are not forced to share threshold with noisy sub-regions
- abrupt movement artifacts can be isolated instead of contaminating a full minute
- should be more stable than a highly local rolling threshold

### Best use

Strong option if the data contains long sessions with posture or impedance shifts.

---

## E9. Frontal-Dominance Spatial Contrast

### Core idea

Do not run Strategy E only on raw single channels.
Create one or more **virtual blink channels** that emphasize frontal ocular activity and suppress brain-wide artifacts.

Examples:

```text
V_front = mean(Fp1, Fp2, AF7, AF8) - mean(Cz, Pz, Oz)
V_left  = Fp1 - Fz
V_right = Fp2 - Fz
```

Then run Strategy E on these virtual channels.

### Why this is new

This is not ordinary multi-channel voting.
It is a **spatial projection** step before thresholding.
The objective is to make blinks larger relative to non-ocular background.

### Why it may beat first iteration

- many false positives are likely global transients or non-frontal artifacts
- a frontal-dominance projection should preserve blink peaks while suppressing broad activity
- this is one of the strongest ways to improve **precision without giving up recall**

### Best use

Very high priority. This has a better chance of improving F1 than another threshold-only tweak.

---

## E10. Cross-Epoch Threshold Regularization

### Core idea

A threshold for one epoch should not jump wildly unless the signal really changes.
Regularize thresholds across neighboring epochs:

```text
T'_e = 0.25 * T_{e-1} + 0.50 * T_e + 0.25 * T_{e+1}
```

or use an exponential smoother:

```text
T'_e = lambda * T_e + (1 - lambda) * T'_{e-1}
```

### Why this is new

This is not a within-epoch sliding window.
It is a **between-epoch stability prior**.

### Why it may beat first iteration

- prevents isolated threshold collapse in one unusually quiet epoch
- keeps the E-family adaptive, but less twitchy
- likely to reduce FP with only a small recall penalty

### Best use

Good companion to E6. The combination is simple and cheap.

---

## E11. Dynamic Lane Routing Instead of One Best Channel Per Pair

### Core idea

The current benchmark chooses one best channel for the full pair.
That may be too rigid.

Instead:

1. run Strategy E on all candidate frontal lanes
2. pool all detections
3. cluster detections occurring within a short tolerance
4. keep the representative from the lane with the highest local score

Possible local score:

```text
score = peak_z * prominence * frontal_dominance / duration_penalty
```

### Why this is new

This is not OR fusion and not 2-of-N voting.
It is **per-candidate routing**.

### Why it may beat first iteration

- different channels can be optimal at different times
- preserves multi-lane recall without counting every lane's artifact as a separate blink
- directly attacks one likely source of FP inflation in multi-channel settings

### Best use

High-value experiment if channel quality drifts across a recording.

---

## E12. Strategy E + Strategy C Guardrail Cascade

### Core idea

Use Strategy E for proposal generation, then use a lightweight Strategy C-style cue as a guardrail.

Possible versions:

1. keep E candidates only if the source epoch is not an autoreject outlier
2. keep E candidates only if local peak-to-peak is inside a learned acceptable range
3. use a two-feature score:

```text
score = w1 * E_amplitude_score + w2 * C_ptp_score
```

### Why this is new

This is not replacing E with C.
It is using C's strongest idea, namely **per-epoch artifact sensitivity**, as a veto or secondary score on top of E.

### Why it may beat first iteration

- E contributes recall
- C contributes artifact awareness
- this is the clearest path to beating `strategy_c` on robustness while approaching or exceeding its F1

### Best use

This is the most promising hybrid if the objective is to beat the first report rather than only extend E in isolation.

---

## E13. Pair-Calibrated Self-Training

### Core idea

Use the most confident E5 or E6 detections as pseudo-labels to learn pair-specific blink characteristics.

Pipeline:

1. run a conservative high-precision E pass
2. collect top-confidence events
3. estimate pair-specific priors:
   - duration range
   - prominence range
   - frontal/posterior amplitude ratio
   - left-right symmetry
4. rescore all permissive candidates using these learned priors

### Why this is new

This is not generic template matching.
The template and priors are learned from the same recording pair.

### Why it may beat first iteration

- subject/session variability is one of the main reasons fixed rules fail
- pair-specific calibration can improve robustness without manual tuning
- especially useful when one subject's blink morphology differs from the population

### Best use

Best as a second-stage extension after E6 or E12.

---

# Which ideas have the best chance to win

If the goal is specifically to beat `tutorial/report_first_iteration.md`, I would prioritize these:

## Tier 1

1. **E9 frontal-dominance spatial contrast**
2. **E12 Strategy E + Strategy C guardrail cascade**
3. **E6 soft-shrinkage threshold**
4. **E11 dynamic lane routing**

These four have the strongest chance to improve F1 while preserving E-family robustness.

## Tier 2

5. **E7 iterative background refit**
6. **E10 cross-epoch threshold regularization**

These are lower-risk engineering upgrades that should improve stability.

## Tier 3

7. **E8 change-point adaptive segmentation**
8. **E13 pair-calibrated self-training**

These are more ambitious and may give larger gains, but they are also more complex.

---

# Recommended experimental roadmap

## Phase 1: cheap upgrades to E5

Start from `strategy_e5_global_floor` and add:

1. soft shrinkage instead of hard floor
2. threshold smoothing across epochs
3. iterative background refit

This phase is cheap and directly targets the known failure mode: threshold instability in quiet epochs.

## Phase 2: add spatial intelligence

Build virtual frontal-dominance channels and compare:

- raw best lane
- virtual contrast lane
- dynamic lane routing over both raw and virtual lanes

This phase likely offers the best precision gain.

## Phase 3: build the hybrid winner

Take the best Phase 2 variant and add a Strategy C-style guardrail score.

This is the strongest candidate for a new robust pipeline because it combines:

- E-family recall
- C-family artifact awareness
- zero-failure design preference

---

# Success criteria for the second iteration

To claim the second report beats the first one, I would use these targets:

## Minimum practical win

- **0 failures**
- **micro recall >= 0.7453** to match or beat `strategy_e`
- **micro F1 > 0.6372** to beat `strategy_e5_global_floor`
- FP clearly below E3 and E4

## Strong win

- **0 failures**
- **micro F1 >= 0.6477** to beat `strategy_a`
- recall still near E-family levels

## Best-case win

- **0 failures**
- **micro F1 > 0.6530** to beat `strategy_c`
- recall materially above `strategy_c`

That last target should be the real benchmark for a publishable second iteration.

---

# Final recommendation

If only one direction should be implemented next, it should be:

> **E12 = Strategy E proposals + Strategy C guardrail, built on top of E9 frontal-dominance spatial contrast and E6 soft-shrinkage thresholding.**

Reason:

- E-only threshold variants have already shown diminishing returns
- the remaining gap is not just threshold choice, but **artifact discrimination**
- spatial contrast plus a C-style guardrail is the most credible way to improve F1
  without sacrificing the zero-failure, recall-first advantages of Strategy E

In short:

> The second iteration should move from "better thresholding" to
> "better trust management and better spatial discrimination."

