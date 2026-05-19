# Strategy A Current Results

This note captures the current observed performance of the Strategy A implementation based on:

- [tutorial/10_strategy_a_first_epoch_debug.py](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/tutorial/10_strategy_a_first_epoch_debug.py)
- [tutorial/11_strategy_a_stage1_benchmark.py](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/tutorial/11_strategy_a_stage1_benchmark.py)

The stage-1 benchmark is specifically based on [get_blink_positions.py](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/pyblinker/blinker/get_blink_positions.py), using the `get_blink_position(...)` function as the direct Strategy A Step 1 detector.

## Benchmark settings

```python
TARGET_CHANNEL = "EEG X1 - Pz"
N_EPOCHS = 5
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
EXPECTED_STAGE1_REGIONS = 185
```

## Current benchmark result

```python
{
    'true_positives': 135,
    'false_positives': 30,
    'false_negatives': 0,
    'precision': 0.8181818181818182,
    'recall': 1.0,
    'f1': 0.9,
    'epoch_blink_agreement': 1.0,
    'blink_count_agreement': 0.0,
}
```

## Interpretation

- Strategy A currently achieves full recall on this benchmark: `recall = 1.0`
- It detects all reference blinks in the evaluated set: `false_negatives = 0`
- The remaining error is due to extra detections: `false_positives = 30`
- Overall event-level balance is: `precision = 0.8181818181818182`, `f1 = 0.9`
- Epoch-level blink presence matches perfectly: `epoch_blink_agreement = 1.0`
- Exact per-epoch blink counts do not match: `blink_count_agreement = 0.0`

## Notes

- The stage-1 benchmark script is intended to serve as a reusable baseline for later strategy comparisons.
- Manual observation for Strategy A Step 1 on the first 5 epochs and channel `EEG X1 - Pz` is that the detector should produce about `185` blink regions before later filtering stages.
