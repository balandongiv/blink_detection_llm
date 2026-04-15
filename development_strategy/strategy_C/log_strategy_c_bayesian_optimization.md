# Strategy C Log: Bayesian Optimization

## Status

**Date**: 2026-04-05  
**State**: Updated after the multi-lane Stage 1 refactor

Strategy C no longer routes Random Search or Bayesian Optimization through one
hard-coded consensus backbone channel.

The current implementation now:

- learns Stage 1 rejection thresholds for all eligible EEG channels
- builds the weighted frontal median only when the configured frontal subset is
  actually available
- applies learned Stage 1 thresholds directly during candidate scanning instead
  of calling `get_blink_position(...)` to derive a fresh threshold
- evaluates blink statistics for every Stage 1 lane
- shortlists the best 3 representative lanes with the same
  `channel_selection(...)` filtering logic used elsewhere in the codebase
- unions candidates across those representative lanes before the final
  `FitBlinks(...)` pass
- only runs the narrow `EEG F7 - Pz` rescue lane when the representative set
  includes the optional backbone lane

## Key API Changes

- Renamed:
  - `self._build_stage1_backbone(...)`
  - to `self.get_channel_rejection_threshold(...)`
- `_detect_stage1_candidates(...)` now calls
  `get_blink_position_with_threshold(...)`, which forwards the already learned
  threshold into `_scan_threshold_crossings(...)`
- `tutorial/strategy_c_autoreject_first_5_epochs_common.py` now documents the
  multi-lane candidate-generation and representative-lane selection flow

## Current Implementation Notes

Relevant files:

- `pyblinker/epoch_detection_strategy_c_autoreject.py`
- `pyblinker/blinker/get_blink_positions.py`
- `test/epoch_detection_strategy_c_autoreject/test_stage1_benchmark.py`
- `tutorial/strategy_c_autoreject_first_5_epochs_common.py`
- `tutorial/14_strategy_c_autoreject_first_5_epochs_random_search.py`
- `tutorial/14_strategy_c_autoreject_first_5_epochs_bayasian_optimization.py`

Important behavior changes in `pyblinker/epoch_detection_strategy_c_autoreject.py`:

- thresholds are learned across all picked EEG channels, not only the configured
  frontal subset
- the configured `stage1_channels` tuple is now used to define the optional
  frontal backbone lane, not to limit all Stage 1 detection
- the chosen output channel on the 5-epoch slice is now the representative EEG
  lane `EEG X1 - Pz`, not `front7_autoreject_weighted_median`
- the Stage 1 summary now exposes:
  - representative lanes
  - optional backbone channels
  - the scan-threshold scale used to translate `autoreject` rejection thresholds
    into sample-level scan thresholds

## Benchmark Snapshot

Observed from the updated method-specific tutorial entrypoints on 2026-04-05:

### Random Search

- command:
  - `python tutorial/14_strategy_c_autoreject_first_5_epochs_random_search.py`
- selected output lane:
  - `EEG X1 - Pz`
- representative Stage 1 lanes:
  - `EEG X1 - Pz, EEG Fp1 - Pz, EEG Fp2 - Pz`
- Stage 1 threshold-learning API:
  - `compute_thresholds`
- Stage 1 scan-threshold scale:
  - `0.08`
- Stage 1 candidate count:
  - `156`
- rescue candidate count:
  - `0`
- `number_good_blinks`:
  - `151`
- `strategy_c_good_mask_passed`:
  - `144`
- `strategy_c_pavr_passed`:
  - `153`
- metrics:
  - `TP=133`
  - `FP=23`
  - `FN=0`
  - `precision=0.8525641025641025`
  - `recall=1.0`
  - `f1=0.9204152249134947`

### Bayesian Optimization

- command:
  - `python tutorial/14_strategy_c_autoreject_first_5_epochs_bayasian_optimization.py`
- selected output lane:
  - `EEG X1 - Pz`
- representative Stage 1 lanes:
  - `EEG X1 - Pz, EEG Fp1 - Pz, EEG Fp2 - Pz`
- Stage 1 threshold-learning API:
  - `compute_thresholds`
- Stage 1 scan-threshold scale:
  - `0.12`
- Stage 1 candidate count:
  - `156`
- rescue candidate count:
  - `0`
- `number_good_blinks`:
  - `151`
- `strategy_c_good_mask_passed`:
  - `144`
- `strategy_c_pavr_passed`:
  - `153`
- metrics:
  - `TP=133`
  - `FP=23`
  - `FN=0`
  - `precision=0.8525641025641025`
  - `recall=1.0`
  - `f1=0.9204152249134947`

## Why This Refactor Matters

This fixes the original rigidity in three ways:

1. Strategy C now runs when frontal channels are missing because raw EEG lanes
   remain valid Stage 1 candidates even with no backbone lane.
2. Learned Stage 1 thresholds are now consumed in candidate detection instead of
   being ignored and replaced by a second threshold search inside
   `get_blink_position(...)`.
3. Random Search and Bayesian Optimization now differ only in how
   `compute_thresholds(...)` learns channel thresholds, not in a forced
   dependency on one synthetic consensus lane.

## Fallback Cases Covered

The updated test suite now includes:

- a no-frontal-channel run with `EEG O1 - Pz`, `EEG O2 - Pz`, and `EEG X1 - Pz`
- a single-channel run with only `EEG X1 - Pz`

In both cases Strategy C skips backbone construction and still completes
successfully using channel-level thresholds.

## Suggested Commands

```powershell
python tutorial/14_strategy_c_autoreject_first_5_epochs_random_search.py
```

```powershell
python tutorial/14_strategy_c_autoreject_first_5_epochs_bayasian_optimization.py
```

```powershell
python -m pytest -q test/epoch_detection_strategy_c_autoreject/test_stage1_benchmark.py
```
