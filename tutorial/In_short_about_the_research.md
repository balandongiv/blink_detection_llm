Is there any diff
if method not in ['bayesian_optimization', 'random_search']:

Since We consider the contribution of all channels, this raise an issue, such that, what is the minimum number of channels that should be considered for detection?
    flagged_epoch_mask = np.any(ptp > threshold_array[np.newaxis, :], axis=1)  # (n_valid_epochs,)

## Proposed Two-Stage Thresholding Approach

The proposed method introduces an epoch-aware thresholding strategy to improve blink detection in Blinker.

Epoching is especially relevant in driving research because long continuous EEG recordings are commonly divided into shorter time segments, or epochs, for analysis. Using epochs for blink detection therefore provides two advantages: it fits naturally within the standard preprocessing workflow for driving studies, and it allows the threshold to be estimated from segments that are more likely to contain blink activity.

**Stage A: Identification of blink-heavy epochs**
Autoreject is first used to identify epochs that are likely to contain substantial blink-related activity.

**Stage B: Robust threshold estimation**
For each channel, a sample-level threshold is estimated using only the epochs flagged in Stage A. The threshold is calculated using robust statistics:

[
\text{threshold} = \text{center} + k \times \text{MAD}
]

where the centre can be either:

* the **median** (default), which is more robust to extreme values; or
* the **mean**, which is more sensitive to large peaks and therefore produces a more conservative threshold.

**Stage C: Blink-region localisation**
The threshold estimated in Stage B is applied using `scan_threshold_crossings_kleifges` to locate blink regions in the signal.

Although the method is described as two-stage thresholding, Stage C does not estimate a new threshold. Stage B estimates the threshold, while Stage C applies it to identify the temporal boundaries of blink events.

## Main Findings

First, we show that considering epochs before threshold estimation substantially improves Blinker performance. When all epochs are concatenated and processed directly, without first identifying blink-heavy epochs, detection performance is approximately 60% when using the mean and 70% when using the median. In contrast, the proposed epoch-aware approach achieves approximately 80% performance.

This result suggests that Blinker is highly dependent on the preprocessing strategy. When threshold statistics are computed from the entire recording, non-blink activity may affect the estimated threshold and reduce detection accuracy. Restricting the calculation to epochs that are likely to contain blinks produces a threshold that is more representative of blink-related signal amplitudes.

Second, we show that the median performs better than the mean for threshold estimation. The original Blinker implementation uses the mean. However, the median is less affected by extreme amplitudes and non-blink artefacts, resulting in a more robust threshold estimate.

Third, the proposed method is relatively insensitive to epoch duration. We evaluated epoch lengths of 10, 20, 30, 40, and 60 seconds, and observed only minimal performance differences across these settings. This indicates that the approach remains stable across a practical range of epoch durations and is not strongly dependent on selecting one specific epoch length.

This indicates that the original Blinker implementation can be improved by introducing two intermediate steps before blink-region detection: first, identifying epochs that are likely to contain blinks; and second, estimating the channel-wise threshold using the median and MAD calculated only from those selected epochs.



1. Identify epochs that are likely to contain blinks.
2. Calculate the channel-wise median and MAD threshold using only those selected epochs.

These modifications make use of the epoch-based structure already commonly applied in driving research, while also improving blink detection performance. In this sense, epoching serves a dual purpose: it supports the standard analysis of long continuous driving data and provides a more reliable basis for estimating blink-detection thresholds.


## Limitation of Stage A

One limitation of Stage A is that epoch selection is based on the peak-to-peak (PTP) amplitude of each channel. For every valid epoch, the PTP value is calculated separately for each channel:

[
\text{PTP} = \max(x) - \min(x)
]

The PTP value for each channel is then compared with its corresponding channel-specific threshold. An epoch is flagged when **at least one channel** exceeds its threshold.

```python
flagged_epoch_mask = np.any(
    ptp > threshold_array[np.newaxis, :],
    axis=1
)
```

Although this approach considers all channels during epoch screening, it does not require consistent evidence across multiple channels. A single channel with a large amplitude fluctuation can cause the entire epoch to be flagged. As a result, Stage A may be sensitive to channel-specific noise or non-blink artefacts, rather than blink activity alone.

Therefore, the selected epochs should be interpreted as epochs containing unusually large signal activity, not necessarily as epochs containing blinks exclusively. Future work could improve this stage by requiring agreement across multiple frontal channels, weighting channels according to their relevance to ocular artefacts, or combining PTP-based screening with additional blink-specific criteria.

The best evaluation is an **ablation study of Stage A**, separating two questions:

1. **Which channels should contribute to flagging an epoch?**
2. **How should their contributions be combined?**

Do not test only “32 vs 64 vs 128 channels” as the main experiment. Channel count changes electrode coverage and montage density at the same time, so it is difficult to identify the real reason for any performance difference. Use channel-count comparisons as a secondary robustness test.

## Recommended experiment design

### 1. Establish epoch-level ground truth

Label an epoch as **blink-containing** when it includes at least one manually annotated blink, or a blink from a trusted reference annotation.

Then evaluate Stage A directly:

* Precision: Of epochs flagged by Stage A, how many truly contain blinks?
* Recall: Of true blink-containing epochs, how many were flagged?
* F1-score
* False-positive rate: How often are non-blink epochs incorrectly selected?
* Percentage of epochs flagged

This is important because downstream Blinker performance alone cannot tell whether Stage A is accurately selecting blink-heavy epochs.

### 2. Compare channel-selection strategies

Test the same Stage A thresholding method under several channel sets:

| Condition                     | Channels used for Stage A                   | Purpose                                              |
| ----------------------------- | ------------------------------------------- | ---------------------------------------------------- |
| Single-channel                | Each channel individually                   | Identifies the most informative electrodes           |
| Frontal-only                  | For example, Fp1, Fp2, AF7, AF8, F7, F8, Fz | Tests whether blink-relevant channels are sufficient |
| Central-only                  | Central electrodes                          | Negative/control comparison                          |
| Posterior-only                | Parietal and occipital electrodes           | Tests sensitivity to non-blink artefacts             |
| All channels                  | Current implementation                      | Baseline                                             |
| Frontal + periocular channels | Frontal channels nearest the eyes           | Likely best physiologically motivated condition      |

The strongest expected result would be: **frontal-channel selection produces similar or better recall but substantially fewer false-positive epochs than all-channel selection.**

### 3. Compare channel-combination rules

Your current code uses an **“any-channel” rule**:

[
\text{flag epoch if any channel exceeds its threshold}
]

This is likely sensitive to one noisy channel. Compare it against:

* **Any-channel rule:** current baseline
* **At least 2 channels exceed threshold**
* **At least 3 channels exceed threshold**
* **At least (p%) of selected channels exceed threshold**
* **At least one frontal channel exceeds threshold**
* **At least two frontal channels exceed threshold**
* **Weighted rule:** frontal channels contribute more than central or posterior channels

For example:

```python
# Current: one channel is enough
flagged_epoch_mask = np.any(ptp > threshold_array[np.newaxis, :], axis=1)

# Alternative: require at least two channels
flagged_epoch_mask = np.sum(
    ptp > threshold_array[np.newaxis, :],
    axis=1
) >= 2
```

A more blink-specific version would require agreement among frontal channels only.

### 4. Evaluate downstream effects

For every Stage A condition, run the full pipeline and report:

* Stage A epoch-selection precision, recall, and F1
* Final blink-detection precision, recall, and F1
* Number/proportion of selected epochs
* Stage B threshold values and their variability across subjects
* Performance across different epoch durations: 10, 20, 30, 40, and 60 seconds

This will show whether a better Stage A selection rule actually improves final blink detection, rather than merely changing the number of selected epochs.

## Best primary comparison

A focused primary experiment could be:

1. **All channels + any-channel rule** — current Stage A baseline
2. **Frontal channels only + any-channel rule**
3. **Frontal channels only + at least two-channel agreement**
4. **All channels + at least two-channel agreement**
5. **Single frontal channel conditions** — for example, Fp1 only and Fp2 only

This directly tests the limitation: whether the current all-channel, any-channel rule is overly affected by isolated activity from non-blink channels.

## Secondary experiment: 32, 64, and 128 channels

You can then test montage density by creating comparable subsets:

* 32-channel subset
* 64-channel subset
* 128-channel full montage

But keep the frontal electrodes as consistent as possible across conditions. Otherwise, better performance at 128 channels may simply occur because the montage includes more electrodes near the eyes.

## Expected interpretation

A useful conclusion could be:

> Stage A is sensitive to the channel aggregation rule because an epoch is currently selected when any channel exceeds its PTP threshold. This may allow a single noisy or non-ocular channel to trigger epoch selection. Comparing spatial channel subsets and multi-channel agreement rules can determine whether blink-heavy epochs are more reliably identified using frontal electrodes and evidence from multiple channels.

The most informative test is therefore **not channel-by-channel alone or 32/64/128 alone**, but a combined **spatial-channel-group and aggregation-rule ablation study**.
