# Strategy C Step 1 Reference Benchmark

This note is the short reference benchmark for **Strategy C Step 1** development.

It summarizes the current **Step 1 baselines** from:

- [strategy_A_current_results.md](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/development_strategy/strategy_A/strategy_A_current_results.md)
- [strategy_B_current_results.md](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/development_strategy/strategy_B/strategy_B_current_results.md)

The goal is to give future Strategy C work a simple benchmark target for the candidate-generation stage.

## Why This Benchmark Matters

For **Step 1**, the priority is:

- high `TP`
- low `FN`

This means the Step 1 detector should be **recall-first**.

`FP` still matters, but it is more recoverable later because the downstream pipeline can theoretically reduce false positives using:

```python
FitBlinks(...).dprocess()
get_blink_statistic(...)
get_good_blink_mask(...)
BlinkProperties(...)
pAVR restriction
```

So for Step 1 development, a detector that loses true blinks early is usually worse than one that keeps extra candidates.

## Common Evaluation Slice

Both baselines below are measured on the same reduced development slice:

- `sample_data/dev_epo.fif`
- first `5` epochs
- reference: `sample_data/dev_epo_annotations_5_epochs.csv`

## Step 1 Baselines

### Strategy A Step 1

Source:

- [11_strategy_a_stage1_benchmark.py](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/tutorial/11_strategy_a_stage1_benchmark.py)

Step 1 detector:

- `get_blink_position(...)`

Measured result:

```python
{
    'TP': 133,
    'FP': 32,
    'FN': 0,
    'precision': 0.80,
    'recall': 1.0,
    'f1': 0.89,
}
```

Interpretation:

- This is the strongest current **recall** baseline.
- It misses **no** reference blinks on the 5-epoch slice.
- Any proposed Strategy C Step 1 should treat this as the most important baseline to beat on `TP` and `FN`.

### Strategy B Step 1

Source:

- [13_strategy_b_stage1_benchmark.py](/C:/Users/balan/IdeaProjects/find_blink_epoch_worktree/tutorial/13_strategy_b_stage1_benchmark.py)

Step 1 detector:

- `mne.preprocessing.find_eog_events(...)`

Measured result:

```python
{
    'TP': 131,
    'FP': 14,
    'FN': 2,
    'precision': 0.903,
    'recall': 0.98,
    'f1': 0.94,
}
```

Interpretation:

- Strategy B is currently more precise than Strategy A on this slice.
- But for Step 1 development it is weaker on recall because it misses `3` true blinks.
- Strategy C should still beat this baseline as well, but **Strategy A is the harder recall target**.

## Direct Comparison

| Strategy | Step 1 detector |  TP | FP | FN | Precision | Recall | F1 |
| --- | --- |----:|---:|---:|----------:|-------:| ---: |
| Strategy A | `get_blink_position(...)` | 133 | 32 |  0 |      0.80 |    1.0 | 0.9 |
| Strategy B | `find_eog_events(...)` | 131 | 14 |  2 |      0.93 |   0.98 | 0.98|

## Implementation Benefits Beyond Metrics

When judging Strategy C Step 1, do not look only at `TP`, `FP`, and `FN`.
There are also implementation-level benefits that can make Strategy C the
better foundation even when two detectors are numerically close.

### Against Strategy A

Strategy A Step 1 is simple and strong on recall, but it is mostly a
single-detector path built around one legacy threshold-crossing routine on one
prepared signal.

A good Strategy C Step 1 can be a better implementation foundation because:

- it can combine multiple frontal channels into one explicit candidate backbone
  instead of depending on one fixed channel choice
- it can add narrow rescue lanes for known blind spots without replacing the
  main detector
- it can preserve one stable candidate-region output contract while still
  evolving the internal candidate logic
- it gives a cleaner path to later long-closure support because Stage 1 is
  already framed as a modular candidate generator rather than a single hardcoded
  detector

### Against Strategy B

Strategy B Step 1 uses `mne.preprocessing.find_eog_events(...)`, which is useful
as a baseline, but it is a less controllable implementation base for this
project.

A good Strategy C Step 1 can be a better implementation foundation because:

- it keeps the detector logic inside the project rather than delegating the
  core candidate generator to an external event finder
- it can expose intermediate reasoning such as channel support, consensus
  signal choice, seed clusters, and rescue logic, which makes debugging easier
- it produces candidate regions in a form that is easier to align with the
  downstream Stages 2 to 6 than a peak-only event list
- it can be tuned in project terms, frontal consensus rules, learned
  thresholds, and selective rescue paths, instead of mainly adjusting an
  imported event detector's settings

### Practical Rule

If two Step 1 candidates are close on metrics, prefer the one that:

1. preserves Strategy A's recall target
2. is easier to inspect and debug than Strategy B
3. keeps a stable candidate-region interface for downstream Stages 2 to 6
4. can absorb targeted rescue logic without becoming a large monolithic rule set

## What Strategy C Step 1 Must Do

A proposed Strategy C Step 1 should perform better than both Strategy A and Strategy B Step 1 baselines.

In practice, that means:

- do **not** regress below Strategy A on `TP` and `FN`
- ideally keep `TP = 133` and `FN = 0`
- if possible, reduce `FP` below Strategy A's `32`
- at minimum, be clearly defensible versus both:
  - Strategy A as the recall-first baseline
  - Strategy B as the precision-leaning MNE baseline

## Practical Rule For Strategy C Iteration

When evaluating a new Strategy C Step 1 candidate, ask:

1. Does it keep `TP` as high as Strategy A?
2. Does it keep `FN` as low as Strategy A?
3. If `FP` is still high, can later stages plausibly reduce it?

If the answer to the first two questions is no, the Step 1 candidate is usually not good enough yet, even if its precision looks better.
