# Strategy C Autoreject API And Execution Flow

## Purpose

This note documents the current Strategy C Stage 1 flow after the multi-lane
thresholding refactor.

The key point is that Strategy C no longer forces all candidate detection
through `front7_autoreject_weighted_median`.

## Main API Surface

Primary implementation:

- `pyblinker/epoch_detection_strategy_c_autoreject.py`

Relevant helper:

- `pyblinker/blinker/get_blink_positions.py`

Main Stage 1 method names:

- `get_channel_rejection_threshold(...)`
- `_build_stage1_candidate_lanes(...)`
- `_detect_stage1_candidates(...)`

## Stage 1 Threshold Learning

Strategy C first prepares valid-epoch EEG data and builds one `mne.EpochsArray`
containing all eligible EEG channels.

Then it learns thresholds with one of these APIs:

- per-channel mode:
  - `autoreject.compute_thresholds(...)`
- global mode:
  - `autoreject.get_rejection_threshold(...)`

The returned thresholds are cached in:

- `detector.stage1_thresholds_`

and are reused directly in candidate detection.

## Optional Backbone Lane

The weighted frontal backbone is now optional.

It is only constructed when at least two configured `stage1_channels` are
present in the prepared EEG data.

Current formula:

```python
weighted = stage1_data / threshold_vec[np.newaxis, :, np.newaxis]
backbone = np.median(weighted, axis=1).reshape(-1)
```

If that frontal subset is unavailable, Strategy C skips backbone construction
and continues with raw EEG lanes only.

## Candidate Lanes

Stage 1 candidate generation now supports:

- every eligible EEG channel
- the optional weighted frontal backbone lane

Each lane has:

- a `channel` name
- a `signal`
- a learned threshold-derived scan threshold
- a `candidate_source`

## Candidate Detection

`_detect_stage1_candidates(...)` no longer calls `get_blink_position(...)` in a
way that recomputes a new threshold from the candidate signal.

Instead it calls `get_blink_position_with_threshold(...)`, which forwards the
already learned threshold into `_scan_threshold_crossings(...)`.

That flow is:

```python
positions = get_blink_position_with_threshold(
    self.params,
    blink_component=lane.signal,
    threshold=lane.threshold,
    ch=lane.channel,
    progress_bar=False,
    min_blink_frames=min_blink_frames,
)
```

## Representative Lane Selection

After candidate detection, Strategy C computes per-lane blink statistics and
shortlists representative lanes with the same filtering logic used elsewhere in
the codebase:

- `channel_selection(...)`
- `filter_blink_amplitude_ratios(...)`
- `filter_good_blinks(...)`
- `filter_good_ratio(...)`

The current flow is:

1. detect candidates on every lane
2. compute lane-level blink statistics
3. shortlist the best 3 representative lanes
4. select the final representative lane for downstream waveform fitting
5. union candidate intervals across the shortlisted representative lanes
6. run the F7 rescue lane only if the shortlisted set includes the optional
   backbone lane
7. run `FitBlinks(...)` and downstream quality flags on the chosen
   representative lane signal

## Current Debug Output

The tutorial helper now exposes:

- `stage1_channels`
- `stage1_backbone_channels`
- `stage1_thresholds`
- `stage1_scan_threshold_scale`
- representative Stage 1 lanes
- selected lane summary

## Current 5-Epoch Slice Behavior

On `sample_data/dev_epo.fif` for the first 5 epochs:

- both random search and Bayesian optimization currently select `EEG X1 - Pz`
- representative lanes are:
  - `EEG X1 - Pz`
  - `EEG Fp1 - Pz`
  - `EEG Fp2 - Pz`
- both methods currently reach:
  - `TP=133`
  - `FP=23`
  - `FN=0`

## Fallback Behavior

Strategy C now completes when:

- no frontal channels exist
- only one EEG channel is available

In those cases:

- no backbone lane is built
- representative selection is applied over the available raw EEG lanes only
