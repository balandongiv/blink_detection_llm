# Strategy C Log: Approach 2

## Strategy: Local AutoReject Reject-Log Candidate Detector

**Date**: 2026-04-03  
**Proposal**: Replace the current Stage 1 sample-level threshold crossing rule with a true mini-window `autoreject` detector. Split each valid epoch into short overlapping frontal windows, fit local `AutoReject`, convert the learned `RejectLog` into blink candidate regions, and require frontal consensus before exporting a Stage 1 candidate. Keep a narrow rescue path for the one currently recovered only by Strategy C's loose union.  
**Rationale**: The current Stage 1 only uses `compute_thresholds(...)` and then applies a very permissive sample-crossing rule. That preserves recall, but it bypasses the parts of `autoreject` that are actually meant to control false positives: sensor-wise voting, learned consensus (`kappa`), limited interpolation (`rho`), and the `RejectLog` itself. This is consistent with the current result on the 5-epoch slice: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`. The paper and local `autoreject` code both support a stricter window-level decision rule than the current union-over-channels crossing logic.  
**Status**: Completed, not adopted

### Implementation

**Files Changed**:
- `scripts/explore_strategy_c_approach2.py`: Added a dedicated exploratory runner for mini-window local `AutoReject`, `RejectLog`-derived candidate generation, and comparison against the 5-epoch reference slice.
- `development_strategy/log_strategy_c/log_strategy_c_approach2.md`: Replaced the proposal-only note with measured findings and the outcome.

**Commands Used**:

```powershell
& 'C:\Users\balan\anaconda3\envs\pyblinker\python.exe' scripts\compare_step1_strategies.py
```

```powershell
& 'C:\Users\balan\anaconda3\envs\pyblinker\python.exe' scripts\explore_strategy_c_approach2.py
```

```powershell
& 'C:\Users\balan\anaconda3\envs\pyblinker\python.exe' scripts\explore_strategy_c_approach2.py --config default --config high_res
```

### Performance & Metrics

**Data**: `sample_data/dev_epo.fif` and `sample_data/dev_epo_annotations_5_epochs.csv`, evaluated on the first 5 valid epochs and the 4 frontal bipolar channels (`EEG Fp1 - Pz`, `EEG Fp2 - Pz`, `EEG F7 - Pz`, `EEG F8 - Pz`).  

**Important inference**: local `AutoReject` could not run directly on the dev slice because the bipolar frontal channel names have no usable sensor positions. For the exploratory only, the mini-window epochs were temporarily renamed to `Fp1`, `Fp2`, `F7`, `F8` and assigned the standard `10-20` montage so interpolation-based local `AutoReject` could execute. This is an approximation, not a production-ready montage solution.

**Reference baseline**:
- Existing Strategy C Stage 1 autoreject union: `TP=135`, `FN=0`, `FP=717`, `recall=1.0`
- Frontal-mean baseline from Approach 1: `TP=134`, `FN=1`, `FP=26`, `recall=0.992593`

**Approach 2 exploratory results**:
- `window=0.5 s`, `step=0.25 s`, learned local `AutoReject` chose `consensus=1.0`, `n_interpolate=1`
  - `bad_epoch_cov1`: `TP=82`, `FN=53`, `FP=28`, `recall=0.607407`
  - `bad_epoch_cov2`: `TP=106`, `FN=29`, `FP=31`, `recall=0.785185`
- `window=0.25 s`, `step=0.125 s`, learned local `AutoReject` chose `consensus=0.75`, `n_interpolate=2`
  - fixed-support fallback `support4_cov1`: `TP=124`, `FN=11`, `FP=29`, `recall=0.918519`
  - `support4_cov1 + frontal_mean` union rescue: `TP=132`, `FN=3`, `FP=30`, `recall=0.977778`

**Blind-spot finding**:
- The known missed blink at `epoch_index=2`, `blink_onset=4.40667`, `blink_duration=0.366661072` did not become a `bad_epoch` at the recommended `0.5 s / 0.25 s` windowing.
- In that region, the mini-windows reached only `support=2`, so the strict `RejectLog.bad_epochs` route dropped the event.

### Issues Encountered

- **Issue 1**: Local `AutoReject` failed immediately on the raw bipolar frontal names because valid sensor positions were missing.
  - *Resolution*: For the exploratory only, normalized the temporary mini-window channel names to `Fp1`, `Fp2`, `F7`, `F8` and applied `standard_1020`.
  - *Impact*: The experiment became runnable, but the spatial model remains approximate.
  - *Status*: Resolved for exploratory only.

- **Issue 2**: Converting overlapping bad windows back into Stage 1 candidate regions caused large recall loss.
  - *Resolution*: Measured both direct bad-window unions and a stricter overlap-based conversion (`cov2`), then tested a higher-resolution fixed-support fallback.
  - *Impact*: False positives stayed low, but recall did not stay near the Stage 1 target.
  - *Status*: Measured, not solved.

- **Issue 3**: A narrow rescue path did not close the gap enough to beat the existing frontal-mean baseline.
  - *Resolution*: Tested unioning the strongest local-`AutoReject` fallback with the frontal-mean candidate signal.
  - *Impact*: The union improved recall versus pure local `AutoReject`, but still ended at `TP=132`, `FN=3`, `FP=30`, which is worse than the frontal-mean baseline's `TP=134`, `FN=1`, `FP=26`.
  - *Status*: Measured, not solved.

### Session Findings

- This session reproduced the current Stage 1 baselines first, then added a dedicated exploratory runner `scripts/explore_strategy_c_approach2.py` so the local-`AutoReject` path can be rerun without editing pipeline code.
- The runner separates the expensive step from the cheap ones:
  - one local `AutoReject` fit per mini-window configuration
  - multiple cheap post-fit rule sweeps over the cached `RejectLog`
- The recommended Approach 2 setting from the proposal, `window=0.5 s` and `step=0.25 s`, did not meet the core acceptance requirement. It reduced false positives, but recall collapsed to `0.607407` to `0.785185` depending on the window-to-region conversion rule.
- A higher-resolution fallback, `window=0.25 s` and `step=0.125 s`, partially recovered recall, but the best measured result still remained worse than the existing frontal-mean baseline:
  - high-resolution fixed-support fallback: `TP=124`, `FN=11`, `FP=29`
  - fallback plus frontal-mean rescue union: `TP=132`, `FN=3`, `FP=30`
  - frontal-mean baseline from Approach 1: `TP=134`, `FN=1`, `FP=26`
- The known blind-spot blink around `epoch_index=2`, `blink_onset=4.40667`, survives only as a `support=2` local event in the recommended windowing. That means the strict `RejectLog.bad_epochs` rule drops the exact event this path was supposed to preserve.
- The local-`AutoReject` exploratory remains sensitive to montage assumptions because the underlying bipolar frontal names do not ship with valid sensor positions in the dev slice.

### Outcome

**Negative exploratory result**: This approach did reduce false positives relative to the current Stage 1 union, but it did not preserve enough recall on the 5-epoch development slice. The recommended `RejectLog.bad_epochs` path was too strict, and even the higher-resolution fixed-support fallback plus a simple rescue union remained inferior to the cheaper frontal-mean baseline from Approach 1.

### Learnings

- With only 4 frontal channels, the learned local-consensus rule is unstable enough to saturate at strict settings (`1.0` in the recommended `0.5 s / 0.25 s` run), which drops real blink windows.
- The missing sensor-position metadata is not a minor detail: local `AutoReject` interpolation requires a montage workaround before the approach can even be tested.
- Window-level `RejectLog` labels are not enough by themselves to recover Stage 1 candidate regions with both high recall and low false positives on this dev slice.
- The known blind-spot blink survives only as a lower-support event, so a strict `bad_epoch` criterion removes exactly the case Strategy C was supposed to rescue.
- The next Stage 1 iteration should not replace the current pipeline with this `RejectLog` path as-is. If local `AutoReject` is reused at all, it is more promising as an auxiliary signal than as the primary candidate generator.

### Recommendation

**Recommendation**: Reject this path as the primary Stage 1 replacement for Strategy C.

**Reason**:
- It does not satisfy the acceptance target of preserving `TP=135`, `FN=0`, or even match the stronger practical baseline from Approach 1.
- The best result measured in this session is still worse than the cheaper frontal-mean candidate path on both recall and false positives.
- The path also carries an extra implementation dependency, montage normalization for bipolar frontal channels, before it can even run reliably.

**Future recommendation**:
- Do not spend more iteration time trying to make `RejectLog`-derived windows the main Stage 1 detector on this dev slice.
- Keep the exploratory runner only as archived evidence and as a reusable probe if local `AutoReject` is later revisited for a narrower role.
- Only reopen this path if one of these conditions changes:
  - a proper channel-location mapping for the bipolar frontal montage is added
  - more frontal channels become available, so learned consensus is less brittle
  - local `AutoReject` is used only as an auxiliary feature or veto signal rather than the primary candidate generator
