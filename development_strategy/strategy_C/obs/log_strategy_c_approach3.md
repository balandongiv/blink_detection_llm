# Strategy C Log: Approach 3

## Strategy: Whole-Head Threshold Voting With Frontal-Dominance Gating

**Date**: 2026-04-03  
**Proposal**: Redesign Strategy C Stage 1 so it uses all available epoch EEG channels for threshold learning and mini-window voting, but only exports candidates whose bad-channel pattern is frontal-dominant rather than whole-head. Keep a narrow frontal-mean rescue lane for windows that are not globally diffuse.  
**Rationale**: The current 4-channel Strategy C union is too permissive and produces `FP=717` at Stage 1. Approach 2 reduced false positives, but recall collapsed because local consensus was still being learned from only 4 frontal channels. Approach 3 tested the opposite direction: use the full montage for negative evidence and only keep windows whose vote pattern is blink-like because it is frontally dominant.  
**Status**: Completed, not adopted

### Implementation

**Files Changed**:
- `scripts/explore_strategy_c_approach3.py`: Added a dedicated exploratory runner for full-montage threshold learning, whole-head mini-window vote scoring, frontal-dominance rule sweeps, and the narrow frontal-mean rescue lane.
- `handoff/2026-04-03_strategy_c_approach3_experiment.md`: Recorded the run scope, command, and final measured results.
- `development_strategy/log_strategy_c/log_strategy_c_approach3.md`: Replaced the proposal-only note with the completed exploratory findings.

**Commands Used**:

```powershell
& 'C:\Users\balan\anaconda3\envs\pyblinker\python.exe' scripts\explore_strategy_c_approach3.py
```

### Performance & Metrics

**Data**: `sample_data/dev_epo.fif` and `sample_data/dev_epo_annotations_5_epochs.csv`, evaluated on the first 5 valid epochs and all EEG channels except `Trigger` (`24` EEG channels total in the dev slice).  

**Runtime**: `168.948 s` for the full exploratory sweep in the `pyblinker` conda environment.

**Reference baselines reproduced in the same run**:
- Current Strategy C Stage 1 autoreject union: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`, `n_candidates=852`
- Frontal-mean baseline: `TP=134`, `FN=1`, `FP=26`, `recall=0.992593`, `n_candidates=160`

**Best whole-head primary rule found**:
- `window=0.25 s`, `step=0.125 s`
- `vote_factor=0.30`
- `frontal_support >= 1`
- `frontal_ratio >= 0.3`
- `posterior_support <= 99`
- `global_support_ratio <= 0.50`
- Result: `TP=126`, `FN=9`, `FP=63`, `recall=0.933333`, `n_candidates=189`

**Best whole-head rule plus the narrow frontal-mean rescue lane**:
- `window=0.25 s`, `step=0.125 s`
- `vote_factor=0.40`
- `frontal_support >= 2`
- `frontal_ratio >= 0.3`
- `posterior_support <= 1`
- `global_support_ratio <= 0.50`
- Result: `TP=131`, `FN=4`, `FP=26`, `recall=0.970370`, `n_candidates=157`

**Important comparison**:
- The best proposal-faithful rescue result matched the frontal-mean baseline's false positives (`26`) but lost three additional true blinks (`FN=4` vs `FN=1`).
- No evaluated whole-head configuration matched the current Strategy C recall target (`TP=135`, `FN=0`).
- No evaluated whole-head configuration beat the frontal-mean baseline on both recall and false positives.

### Issues Encountered

- **Issue 1**: The first exploratory pass failed on an empty-table union edge case inside the new runner.
  - *Resolution*: Added a guard in `_union_tables(...)` so empty primary and rescue outputs return a valid empty table instead of raising `ValueError`.
  - *Impact*: The full sweep became runnable end to end.
  - *Status*: Resolved.

- **Issue 2**: The whole-head vote logic did not recover the known blind-spot blink.
  - *Resolution*: Swept both the primary frontal-dominance rules and the narrow frontal-mean rescue lane across the recommended window sizes and rule families.
  - *Impact*: The exploratory established that the failure is structural for this dev slice, not a single bad parameter choice.
  - *Status*: Measured, not solved.

### Session Findings

- The new runner uses the full EEG montage for threshold learning via `compute_thresholds(...)` with `augment=False`, then converts each mini-window into a whole-head vote pattern using channel-wise peak-to-peak to threshold ratios.
- The most recall-friendly primary rules were all in the higher-resolution setting, `window=0.25 s` and `step=0.125 s`. The coarser `0.5 s / 0.25 s` settings were consistently worse.
- Even the best full-montage primary rule still ended at `TP=126`, `FN=9`, `FP=63`, which is far below the acceptance target and still worse than the simpler frontal-mean baseline.
- The narrow rescue lane also failed to promote the approach into a viable replacement. Its best result, `TP=131`, `FN=4`, `FP=26`, preserved the frontal-mean baseline's false positives but gave up additional recall.
- The known missed blink at `epoch_index=2`, `blink_onset=4.40667`, `blink_duration=0.366661072` was never recovered by any evaluated rule.
- Window inspection around that blink showed why the approach failed there: the overlapping whole-head vote maps were not frontal-dominant at all. For the best primary rule, the critical windows had `frontal_support=0` and were driven by channels such as `Cz`, `X3`, `P3`, `O1`, `X1`, `T4`, and `T6`.
- That means the proposal's core assumption, "the difficult blink should still look frontally dominant when seen through a whole-head vote map," was not true on this 5-epoch reference slice.

### Outcome

**Negative exploratory result**: Whole-head threshold voting plus frontal-dominance gating reduced false positives relative to the current Strategy C Stage 1 union, but it did not preserve enough recall and it did not fix the known blind spot. The measured evidence does not support adopting this design as the next Strategy C Stage 1 replacement.

### Learnings

- Adding more channels did not solve the Stage 1 problem by itself. On this dev slice, the hardest missed blink does not become more frontal when seen through a whole-head threshold-vote representation.
- The high-resolution mini-window setting, `0.25 s / 0.125 s`, is still the only plausible setting worth trying for this family. The coarser windowing was consistently weaker.
- A narrow frontal-mean rescue lane is not enough when the whole-head rule family misses the wrong blinks. It can trim candidate count, but it does not recover the critical blind-spot event.
- The best whole-head primary rules were only competitive when the frontal-dominance constraints were relaxed substantially (`frontal_support >= 1`, `frontal_ratio >= 0.3`, no meaningful posterior cap). That weakens the original motivation for the approach.
- The frontal-mean baseline remains the strongest practical low-FP Stage 1 reference among the explored alternatives, despite its single missed blink.

### Recommendation

**Recommendation**: Reject this path as the primary Stage 1 replacement for Strategy C.

**Reason**:
- It does not satisfy the acceptance target of preserving `TP=135`, `FN=0`.
- It does not beat the frontal-mean baseline on the 5-epoch development slice.
- Its central promise, using whole-head negative evidence to keep the hard blink while removing diffuse artifacts, did not hold for the known blind spot.

**Future recommendation**:
- Do not spend the next Strategy C iteration budget on more whole-head frontal-dominance sweeps of this same design.
- Keep `scripts/explore_strategy_c_approach3.py` as archived evidence and as a reusable probe if whole-head vote features are later reused in a narrower supporting role.
- Shift the next Stage 1 investigation toward approaches that explicitly target the `epoch_index=2`, `blink_onset=4.40667` blind spot rather than assuming it will be rescued by broader spatial context.
