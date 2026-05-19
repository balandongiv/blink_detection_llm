# Strategy E Expand-Bridge: Exploratory Improvement Plan

## Scope

This note proposes the next exploratory experiments for improving
`strategy_e_expand_bridge` as a Step 1 detector.

This is a strategy document only. It does not prescribe implementation details
beyond the experiment logic and evaluation order.

## Baseline

Current best reliable baseline:

- Variant: `strategy_e_expand_bridge`
- Aggregate result: `micro F1 = 0.6592`
- Recall: `0.7460`
- Precision: `0.5905`
- TP / FP / FN: `30,901 / 21,428 / 10,523`
- Failures: `0`

Current design, from the existing reports:

1. Use the E5-style per-epoch threshold as the main detection threshold.
2. Detect initial candidates at the high threshold.
3. Expand each candidate outward to a lower threshold.
4. Bridge nearby gaps within `80 ms`.

Relevant context:

- [report_first_iteration.md](./report_first_iteration.md)
- [strategy_e_derivative.md](./strategy_e_derivative.md)
- [strategy_e_derivative_2nd.md](./strategy_e_derivative_2nd.md)

## Working Hypothesis

`strategy_e_expand_bridge` is strong because it fixes two real failure modes of
basic threshold crossing:

- under-estimated blink boundaries
- split detections caused by brief dips around the blink peak

The remaining gap is likely not "find even more events." The remaining gap is
more likely:

- over-expansion in noisy epochs
- over-bridging of nearby non-blink transients
- weak low-amplitude candidates that survive because the detector is still
  recall-first
- some non-ocular artifacts that need a lightweight trust or morphology check

So the next gains should come from **better trust management around expansion
and bridging**, not from simply making thresholding more permissive.

## Goal

Beat the current `strategy_e_expand_bridge` baseline while keeping the defining
strengths of the E family:

- `0` failures
- recall at least competitive with `strategy_a`
- no catastrophic pair-level regressions

## Success Criteria

### Minimum win

- `micro F1 > 0.6592`
- `0` failures
- recall `>= 0.7419` to stay at or above `strategy_a`

### Strong win

- `micro F1 >= 0.662`
- `0` failures
- recall `>= 0.742`
- FP below the current `21,428` baseline, or close to it with a clear pair-level
  stability gain

### High-confidence win

- `micro F1 >= 0.665`
- `0` failures
- better or equal pair-level robustness than the current baseline
- no new cluster of severe regressions on specific subjects or segments

## Experiment Principles

1. Keep `expand_bridge` as the base kernel unless there is a clear reason to
   replace the onset detector.
2. Prefer narrow, hypothesis-driven sweeps over broad parameter grids.
3. Change one idea at a time before testing hybrids.
4. Promote only variants that improve both aggregate metrics and pair-level
   stability.
5. Treat recall loss as expensive. A precision gain is only interesting if it
   does not materially damage the Step 1 role.

## Phase 1: Low-Risk Expand-Bridge Refinements

These are the first experiments because they preserve the current structure and
target the most plausible remaining error sources.

### 1. Dynamic Low-Threshold Expansion

Replace the fixed expansion threshold with an adaptive one.

Candidate directions:

- fixed sweep around the current low threshold:
  - lower than current
  - equal to current
  - higher than current
- epoch-aware rule:
  - noisier epoch -> less aggressive expansion
  - quieter epoch -> more aggressive expansion
- candidate-aware rule:
  - high-prominence event -> allow wider expansion
  - weak event -> restrict expansion

Hypothesis:

- current `T_low` is probably too permissive in some noisy epochs and too rigid
  in some quiet epochs
- making `T_low` conditional should reduce FP without giving back the core
  boundary-recovery benefit

### 2. Dynamic Bridge Gap

Replace the fixed `80 ms` bridge with a conditional bridge rule.

Candidate directions:

- simple sweep: `40 / 60 / 80 / 100 ms`
- shorter bridge for weak or short events
- longer bridge only for strong candidates with blink-like morphology
- suppress bridging when the gap valley is too deep relative to the local peak

Hypothesis:

- some false positives are likely created by merging unrelated nearby transients
- a conditional bridge rule should preserve split-blink repair while reducing
  accidental merges

### 3. Confidence-Tagged Expansion and Bridging

Assign each candidate a simple confidence level before applying aggressive
post-processing.

Possible confidence cues:

- peak amplitude above threshold
- local prominence
- duration near the expected blink band
- whether the event required heavy bridging to exist

Experiment:

- strong candidates get full expand-and-bridge
- ambiguous candidates get reduced expansion, reduced bridging, or no bridging

Hypothesis:

- the current baseline treats all threshold crossings too similarly
- selective aggression should remove the weakest FP cases first

## Phase 2: Hybridize With Nearby Strong Variants

These experiments use `expand_bridge` as the base and borrow the strongest ideas
from the best neighboring E-family variants.

### 4. Sliding-Window Onset + Expand-Bridge Boundary Recovery

Use the stricter, more local onset logic from `strategy_e_sliding_window`, then
apply the `expand_bridge` boundary recovery afterward.

Why this is high priority:

- `strategy_e_sliding_window` is the closest competitor on F1
- it has much lower FP than `expand_bridge`
- its main weakness is lost recall
- `expand_bridge` may recover part of that lost recall if used only for boundary
  recovery after a cleaner onset detector

Target outcome:

- inherit the cleaner candidate starts from `sliding_window`
- recover duration and overlap quality using `expand_bridge`

### 5. Adaptive-k Expand-Bridge

Use the `adaptive_k` idea for the high threshold, then keep the current
expand-and-bridge post-processing.

Why this is plausible:

- `adaptive_k` is close to `strategy_c` on F1 with `0` failures
- it may give a better starting threshold on mixed-noise recordings
- `expand_bridge` can then handle boundary completion

Target outcome:

- slightly cleaner candidate pool before expansion
- preserve the current recall advantage from boundary repair

### 6. Self-Trained Soft Gate After Expand-Bridge

Use a conservative pass to learn pair-specific event priors, then apply only a
soft gate to the weakest `expand_bridge` candidates.

Important constraint:

- do not repeat the hard precision-favoring behavior of `E12`
- use the learned priors only to trim low-confidence tails

Candidate priors:

- peak amplitude
- prominence
- duration
- local frontal dominance if available

Hypothesis:

- the remaining FP likely live in the low-confidence tail
- pair-calibrated soft gating should reduce FP more safely than a hard fixed rule

## Phase 3: Spatial and Guardrail Extensions

These are more ambitious, but they have a stronger chance of moving beyond
threshold tuning.

### 7. Frontal-Contrast Expand-Bridge

Run `expand_bridge` not only on raw channels, but also on one or two virtual
frontal-dominance lanes.

Examples of strategy, not exact formulas:

- frontal average minus posterior average
- left frontal contrast
- right frontal contrast

Why this matters:

- the reports suggest threshold-only improvements are nearing diminishing returns
- spatial contrast is a plausible way to cut non-ocular artifacts without losing
  blink amplitude

Recommended evaluation:

- compare raw best lane vs virtual lane
- then compare a small routed pool over both, not a broad OR-fusion over many lanes

### 8. Expand-Bridge + Lightweight Strategy C Guardrail

Use `expand_bridge` for proposal generation, then apply a lightweight artifact
guardrail inspired by Strategy C.

Possible guardrails:

- reject or downweight candidates from obviously bad epochs
- reject candidates with implausible local peak-to-peak behavior
- use a two-feature score combining E confidence and a simple artifact score

Important constraint:

- use the guardrail mostly on ambiguous candidates
- do not let the guardrail erase the recall advantage that makes E valuable

Why this is promising:

- Strategy C's main advantage is artifact awareness, not raw recall
- `expand_bridge` already solves the proposal side well
- combining them selectively is one of the few high-probability ways to improve
  F1 further

### 9. Conditional Shape Guard

Revisit the idea behind `slope_guard`, but only for suspicious candidates.

Do not apply a global morphology filter to every event.

Instead, apply shape checks only when one or more of these are true:

- candidate is low amplitude
- candidate required aggressive bridging
- candidate duration is near the minimum
- candidate occurs in an artifact-prone epoch

Hypothesis:

- shape rules are too expensive when applied globally
- they may still be useful as an ambiguity resolver

## Recommended Priority Order

### Tier 1

1. `sliding_window_onset + expand_bridge`
2. `self_trained_soft_gate + expand_bridge`
3. `dynamic_low_threshold + dynamic_bridge_gap`

These are the best first bets because they target the precise trade-off exposed
by the current leaderboard:

- `expand_bridge` has the best recall/F1 balance
- `sliding_window` has cleaner onsets
- `self_train` offers pair-specific filtering without needing a full new detector

### Tier 2

4. `adaptive_k + expand_bridge`
5. conditional shape guard

These are worthwhile, but less directly compelling than the Tier 1 hybrids.

### Tier 3

6. frontal-contrast `expand_bridge`
7. Strategy C-style guardrail

These may deliver the biggest conceptual gain, but they should follow after the
cheaper low-risk hybrids are tested.

## Suggested Experiment Matrix

Start with a small, disciplined matrix:

1. `expand_bridge_dynamic_low`
2. `expand_bridge_dynamic_gap`
3. `expand_bridge_confidence_weighted`
4. `expand_bridge_sw_onset`
5. `expand_bridge_adaptive_k`
6. `expand_bridge_soft_gate`

Then promote the best two into second-round hybrids:

1. `expand_bridge_sw_onset_soft_gate`
2. `expand_bridge_dynamic_gap_soft_gate`
3. `expand_bridge_frontal_contrast_guardrail`

## Evaluation Protocol

For every candidate variant, compare against:

- `strategy_e_expand_bridge`
- `strategy_e_sliding_window`
- `strategy_e13_self_train`
- `strategy_c`
- `strategy_a`

Track:

- micro precision / recall / F1
- TP / FP / FN
- failures
- pair-level win/loss count vs current baseline
- worst-pair regression
- whether regressions cluster by subject or by artifact-heavy segments

Also classify residual false positives into coarse buckets:

- over-bridged doublets
- low-amplitude noise
- plateau or drift events
- non-frontal/global artifacts
- lane-selection mistakes

This matters because the next round should be driven by **what kind of FP
remain**, not only by the aggregate counts.

## Ablation Rule

Any winning hybrid should be decomposed and checked with a minimal ablation:

1. base `expand_bridge`
2. base + component A
3. base + component B
4. base + A + B

If the hybrid wins only as a bundle, keep it.
If one component carries nearly all the gain, simplify.

## What Not To Repeat

The current results already argue against spending the next round on:

- broad OR-fusion over many channels
- strict majority voting with too few channels
- absolute-polarity detection
- large threshold-only grids without a new trust mechanism
- hard global pruning that pushes recall down toward precision-first behavior

## Recommended First Three Experiments

If only three experiments should be run first, they should be:

1. **`expand_bridge_sw_onset`**
   - highest chance to combine the two best current F1 profiles
2. **`expand_bridge_soft_gate`**
   - best chance to remove weak FP without losing the recall identity of the model
3. **`expand_bridge_dynamic_gap_low`**
   - cheapest direct refinement of the current winner

## Bottom Line

The next round should treat `strategy_e_expand_bridge` as the correct base, not
as something to replace.

The most credible path forward is:

1. keep the expand-and-bridge boundary repair
2. make onset trust slightly cleaner
3. make post-processing conditional on candidate confidence
4. add spatial or artifact-aware guardrails only where ambiguity is high

In short:

> The next win is most likely to come from making `expand_bridge` more selective
> about **when** it expands and bridges, not from making it broadly more
> permissive.
