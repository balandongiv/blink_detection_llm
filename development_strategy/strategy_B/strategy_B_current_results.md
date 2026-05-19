# Strategy B Current Results

This note captures the current observed performance of the Strategy B implementation based on:

- [tutorial/12_strategy_b_first_5_epochs_debug.py](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/tutorial/12_strategy_b_first_5_epochs_debug.py)
- [tutorial/13_strategy_b_stage1_benchmark.py](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/tutorial/13_strategy_b_stage1_benchmark.py)

Strategy B now follows the same concatenated-epoch pipeline shape as Strategy A:

- concatenate valid epochs channel by channel
- run MNE `find_eog_events(...)` as Step 1
- pass those candidate regions through the same downstream refinement stack:
  `FitBlinks -> get_blink_statistic -> get_good_blink_mask -> BlinkProperties -> pAVR restriction`
- select the representative channel using the same legacy channel-ranking logic

## Benchmark settings

```python
CHANNELS = ["EEG X1 - Pz", "EEG Fp1 - Pz", "EEG Fp2 - Pz"]
N_EPOCHS = 5
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None
MNE_HALF_WINDOW_S = 0.10
TARGET_CHANNEL = "EEG X1 - Pz"
EXPECTED_STAGE1_CANDIDATE_REGIONS = 161
EXPECTED_FINAL_REGIONS = 145
```

## Current benchmark result

```python
{
    'selected_channel': 'EEG X1 - Pz',
    'true_positives': 132,
    'false_positives': 13,
    'false_negatives': 3,
    'precision': 0.9103448275862069,
    'recall': 0.9777777777777777,
    'f1': 0.9428571428571428,
    'epoch_blink_agreement': 1.0,
    'blink_count_agreement': 0.2,
}
```

## Interpretation

- Strategy B currently selects `EEG X1 - Pz` on this 5-epoch development slice.
- The MNE Step 1 candidate generator produces `161` initial candidate regions on that selected channel.
- After the shared refinement stack, the selected channel keeps `145` final regions.
- The final result reaches `TP=132`, `FP=13`, `FN=3`.
- Overall event-level balance is: `precision = 0.9103448275862069`, `recall = 0.9777777777777777`, `f1 = 0.9428571428571428`.
- Epoch-level blink presence still matches perfectly: `epoch_blink_agreement = 1.0`.

## Notes

- This is no longer the earlier union baseline. The current implementation matches your requested Strategy A-style execution model and only swaps the Stage 1 candidate generator.
- With the current 3-channel dev slice, Strategy B is substantially more precise than the earlier union experiment, but it still misses `3` reference blinks on the first 5 epochs.
