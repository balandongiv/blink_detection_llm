# Strategy C 5-Epoch Variant Summary

## Scope

This summary is based on the saved batch outputs in
`development_strategy/strategy_C/output` produced by:

- `tutorial/14_strategy_c_autoreject_first_5_epochs_output_batch_runner_step1.py`

All runs use the same slice:

- `sample_data/dev_epo.fif`
- first `5` epochs only
- reference: `sample_data/dev_epo_annotations_5_epochs.csv`

Compared runs:

- Strategy A Step 1 baseline
- Strategy B Step 1 baseline
- Strategy C random search / per-channel / no backbone
- Strategy C Bayesian optimization / per-channel / no backbone
- Strategy C global threshold / no backbone
- Strategy C random search / per-channel / with weighted frontal backbone
- Strategy C Bayesian optimization / per-channel / with weighted frontal backbone
- Strategy C global threshold / with weighted frontal backbone

## Run Health

All `8/8` saved runs completed successfully according to
`development_strategy/strategy_C/output/step1_batch_manifest.jsonl`.

| Run | Status | Elapsed s |
| --- | --- | ---: |
| Strategy A Step 1 baseline | `ok` | 2.434913 |
| Strategy B Step 1 baseline | `ok` | 0.465697 |
| Strategy C random search / per-channel / no backbone | `ok` | 6.142272 |
| Strategy C Bayesian optimization / per-channel / no backbone | `ok` | 4.989365 |
| Strategy C global threshold / no backbone | `ok` | 3.853441 |
| Strategy C random search / per-channel / with backbone | `ok` | 6.407262 |
| Strategy C Bayesian optimization / per-channel / with backbone | `ok` | 5.263493 |
| Strategy C global threshold / with backbone | `ok` | 3.722117 |

## Step 1 Baselines

These baseline values are taken from the saved batch outputs, not from older
mixed-stage notes.

| Baseline | Detector | Channel | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Strategy A Step 1 | `get_blink_position(...)` | `EEG X1 - Pz` | 165 | 133 | 32 | 0 | 0.806061 | 1.000000 | 0.892617 |
| Strategy B Step 1 | `find_eog_candidate_regions(...)` | `EEG X1 - Pz` | 161 | 133 | 28 | 0 | 0.826087 | 1.000000 | 0.904762 |

## Best Lane Per Variant

This table compares the strongest single Strategy C lane in each saved run.

| Variant | Backbone | Threshold Scope | Method | Best Lane | Source | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Strategy C random search | `False` | `per_channel` | `random_search` | `EEG Fp1 - Pz` | `channel_threshold` | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| Strategy C Bayesian optimization | `False` | `per_channel` | `bayesian_optimization` | `EEG Fp1 - Pz` | `channel_threshold` | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| Strategy C global threshold | `False` | `global` | `random_search` | `EEG Fp1 - Pz` | `channel_threshold` | 145 | 131 | 14 | 2 | 0.903448 | 0.984962 | 0.942446 |
| Strategy C random search | `True` | `per_channel` | `random_search` | `EEG Fp1 - Pz` | `channel_threshold` | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| Strategy C Bayesian optimization | `True` | `per_channel` | `bayesian_optimization` | `EEG Fp1 - Pz` | `channel_threshold` | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| Strategy C global threshold | `True` | `global` | `random_search` | `EEG Fp1 - Pz` | `channel_threshold` | 145 | 131 | 14 | 2 | 0.903448 | 0.984962 | 0.942446 |

## Channel-By-Channel Results

### Random Search, Per-Channel, No Backbone

| Channel | Source | Threshold | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `EEG Fp1 - Pz` | `channel_threshold` | 0.000046855240 | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| `EEG X1 - Pz` | `channel_threshold` | 0.000112397900 | 150 | 132 | 18 | 1 | 0.880000 | 0.992481 | 0.932862 |
| `EEG F7 - Pz` | `channel_threshold` | 0.000044616530 | 146 | 130 | 16 | 3 | 0.890411 | 0.977444 | 0.931900 |
| `EEG Fp2 - Pz` | `channel_threshold` | 0.000044278900 | 154 | 131 | 23 | 2 | 0.850649 | 0.984962 | 0.912892 |
| `EEG F3 - Pz` | `channel_threshold` | 0.000017598050 | 155 | 124 | 31 | 9 | 0.800000 | 0.932331 | 0.861111 |
| `EEG Fz - Pz` | `channel_threshold` | 0.000015759880 | 151 | 117 | 34 | 16 | 0.774834 | 0.879699 | 0.823944 |
| `EEG F4 - Pz` | `channel_threshold` | 0.000026031150 | 116 | 91 | 25 | 42 | 0.784483 | 0.684211 | 0.730924 |
| `EEG F8 - Pz` | `channel_threshold` | 0.000058654380 | 53 | 42 | 11 | 91 | 0.792453 | 0.315789 | 0.451613 |
| `EEG Cz - Pz` | `channel_threshold` | 0.000010381620 | 87 | 42 | 45 | 91 | 0.482759 | 0.315789 | 0.381818 |
| `EEG C3 - Pz` | `channel_threshold` | 0.000024079900 | 23 | 13 | 10 | 120 | 0.565217 | 0.097744 | 0.166667 |
| `EEG T4 - Pz` | `channel_threshold` | 0.000011069090 | 89 | 17 | 72 | 116 | 0.191011 | 0.127820 | 0.153153 |
| `EEG C4 - Pz` | `channel_threshold` | 0.000020108620 | 21 | 9 | 12 | 124 | 0.428571 | 0.067669 | 0.116883 |
| `EEG X3 - Pz` | `channel_threshold` | 0.000000065118 | 90 | 12 | 78 | 121 | 0.133333 | 0.090226 | 0.107623 |
| `EEG P3 - Pz` | `channel_threshold` | 0.000007690420 | 67 | 10 | 57 | 123 | 0.149254 | 0.075188 | 0.100000 |
| `EEG P4 - Pz` | `channel_threshold` | 0.000010797800 | 82 | 8 | 74 | 125 | 0.097561 | 0.060150 | 0.074419 |
| `EEG T6 - Pz` | `channel_threshold` | 0.000025303090 | 201 | 12 | 189 | 121 | 0.059701 | 0.090226 | 0.071856 |
| `EEG O2 - Pz` | `channel_threshold` | 0.000025179800 | 44 | 6 | 38 | 127 | 0.136364 | 0.045113 | 0.067797 |
| `EEG X2 - Pz` | `channel_threshold` | 0.000045878340 | 113 | 8 | 105 | 125 | 0.070796 | 0.060150 | 0.065041 |
| `EEG T3 - Pz` | `channel_threshold` | 0.000024670580 | 16 | 4 | 12 | 129 | 0.250000 | 0.030075 | 0.053691 |
| `EEG O1 - Pz` | `channel_threshold` | 0.000015242540 | 124 | 4 | 120 | 129 | 0.032258 | 0.030075 | 0.031128 |
| `EEG A1 - Pz` | `channel_threshold` | 0.000019405540 | 17 | 1 | 16 | 132 | 0.058824 | 0.007519 | 0.013333 |
| `EEG T5 - Pz` | `channel_threshold` | 0.000016129180 | 43 | 1 | 42 | 132 | 0.023256 | 0.007519 | 0.011364 |
| `EEG CM - Pz` | `channel_threshold` | 0.001460936000 | 4 | 0 | 4 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG A2 - Pz` | `channel_threshold` | 0.000016552560 | 44 | 0 | 44 | 133 | 0.000000 | 0.000000 | 0.000000 |

### Bayesian Optimization, Per-Channel, No Backbone

| Channel | Source | Threshold | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `EEG Fp1 - Pz` | `channel_threshold` | 0.000046783510 | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| `EEG X1 - Pz` | `channel_threshold` | 0.000107322300 | 150 | 132 | 18 | 1 | 0.880000 | 0.992481 | 0.932862 |
| `EEG F7 - Pz` | `channel_threshold` | 0.000045042910 | 146 | 130 | 16 | 3 | 0.890411 | 0.977444 | 0.931900 |
| `EEG Fp2 - Pz` | `channel_threshold` | 0.000043299270 | 154 | 131 | 23 | 2 | 0.850649 | 0.984962 | 0.912892 |
| `EEG F3 - Pz` | `channel_threshold` | 0.000014595290 | 169 | 126 | 43 | 7 | 0.745562 | 0.947368 | 0.834437 |
| `EEG Fz - Pz` | `channel_threshold` | 0.000016685050 | 143 | 114 | 29 | 19 | 0.797203 | 0.857143 | 0.826087 |
| `EEG F4 - Pz` | `channel_threshold` | 0.000028344410 | 99 | 80 | 19 | 53 | 0.808081 | 0.601504 | 0.689655 |
| `EEG Cz - Pz` | `channel_threshold` | 0.000007923737 | 150 | 56 | 94 | 77 | 0.373333 | 0.421053 | 0.395760 |
| `EEG F8 - Pz` | `channel_threshold` | 0.000062571580 | 27 | 21 | 6 | 112 | 0.777778 | 0.157895 | 0.262500 |
| `EEG T4 - Pz` | `channel_threshold` | 0.000010907830 | 94 | 19 | 75 | 114 | 0.202128 | 0.142857 | 0.167401 |
| `EEG P3 - Pz` | `channel_threshold` | 0.000005168025 | 198 | 24 | 174 | 109 | 0.121212 | 0.180451 | 0.145015 |
| `EEG O2 - Pz` | `channel_threshold` | 0.000017235380 | 58 | 8 | 50 | 125 | 0.137931 | 0.060150 | 0.083770 |
| `EEG T6 - Pz` | `channel_threshold` | 0.000025792070 | 194 | 12 | 182 | 121 | 0.061856 | 0.090226 | 0.073394 |
| `EEG P4 - Pz` | `channel_threshold` | 0.000015196370 | 40 | 6 | 34 | 127 | 0.150000 | 0.045113 | 0.069364 |
| `EEG C4 - Pz` | `channel_threshold` | 0.000024844970 | 9 | 4 | 5 | 129 | 0.444444 | 0.030075 | 0.056338 |
| `EEG C3 - Pz` | `channel_threshold` | 0.000028470720 | 12 | 4 | 8 | 129 | 0.333333 | 0.030075 | 0.055172 |
| `EEG T5 - Pz` | `channel_threshold` | 0.000011057450 | 95 | 5 | 90 | 128 | 0.052632 | 0.037594 | 0.043860 |
| `EEG T3 - Pz` | `channel_threshold` | 0.000028047100 | 13 | 3 | 10 | 130 | 0.230769 | 0.022556 | 0.041096 |
| `EEG X2 - Pz` | `channel_threshold` | 0.000065534760 | 67 | 4 | 63 | 129 | 0.059701 | 0.030075 | 0.040000 |
| `EEG O1 - Pz` | `channel_threshold` | 0.000018242160 | 89 | 3 | 86 | 130 | 0.033708 | 0.022556 | 0.027027 |
| `EEG A1 - Pz` | `channel_threshold` | 0.000021587190 | 11 | 1 | 10 | 132 | 0.090909 | 0.007519 | 0.013889 |
| `EEG CM - Pz` | `channel_threshold` | 0.001395145000 | 3 | 0 | 3 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG X3 - Pz` | `channel_threshold` | 0.000000094395 | 14 | 0 | 14 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG A2 - Pz` | `channel_threshold` | 0.000016358210 | 45 | 0 | 45 | 133 | 0.000000 | 0.000000 | 0.000000 |

### Global Threshold, No Backbone

| Channel | Source | Threshold | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `EEG Fp1 - Pz` | `channel_threshold` | 0.000058000000 | 145 | 131 | 14 | 2 | 0.903448 | 0.984962 | 0.942446 |
| `EEG Fp2 - Pz` | `channel_threshold` | 0.000058000000 | 143 | 129 | 14 | 4 | 0.902098 | 0.969925 | 0.934783 |
| `EEG F7 - Pz` | `channel_threshold` | 0.000058000000 | 138 | 125 | 13 | 8 | 0.905797 | 0.939850 | 0.922509 |
| `EEG X1 - Pz` | `channel_threshold` | 0.000058000000 | 164 | 133 | 31 | 0 | 0.810976 | 1.000000 | 0.895623 |
| `EEG F8 - Pz` | `channel_threshold` | 0.000058000000 | 53 | 42 | 11 | 91 | 0.792453 | 0.315789 | 0.451613 |
| `EEG X2 - Pz` | `channel_threshold` | 0.000058000000 | 75 | 8 | 67 | 125 | 0.106667 | 0.060150 | 0.076923 |
| `EEG F3 - Pz` | `channel_threshold` | 0.000058000000 | 6 | 4 | 2 | 129 | 0.666667 | 0.030075 | 0.057554 |
| `EEG O2 - Pz` | `channel_threshold` | 0.000058000000 | 24 | 4 | 20 | 129 | 0.166667 | 0.030075 | 0.050955 |
| `EEG Fz - Pz` | `channel_threshold` | 0.000058000000 | 6 | 3 | 3 | 130 | 0.500000 | 0.022556 | 0.043165 |
| `EEG F4 - Pz` | `channel_threshold` | 0.000058000000 | 3 | 2 | 1 | 131 | 0.666667 | 0.015038 | 0.029412 |
| `EEG CM - Pz` | `channel_threshold` | 0.000058000000 | 84 | 2 | 82 | 131 | 0.023810 | 0.015038 | 0.018433 |
| `EEG C3 - Pz` | `channel_threshold` | 0.000058000000 | 1 | 1 | 0 | 132 | 1.000000 | 0.007519 | 0.014925 |
| `EEG T3 - Pz` | `channel_threshold` | 0.000058000000 | 4 | 1 | 3 | 132 | 0.250000 | 0.007519 | 0.014599 |
| `EEG A2 - Pz` | `channel_threshold` | 0.000058000000 | 0 | 0 | 0 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG X3 - Pz` | `channel_threshold` | 0.000058000000 | 0 | 0 | 0 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG A1 - Pz` | `channel_threshold` | 0.000058000000 | 1 | 0 | 1 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG C4 - Pz` | `channel_threshold` | 0.000058000000 | 1 | 0 | 1 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG Cz - Pz` | `channel_threshold` | 0.000058000000 | 1 | 0 | 1 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG P3 - Pz` | `channel_threshold` | 0.000058000000 | 2 | 0 | 2 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG T4 - Pz` | `channel_threshold` | 0.000058000000 | 2 | 0 | 2 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG T5 - Pz` | `channel_threshold` | 0.000058000000 | 2 | 0 | 2 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG P4 - Pz` | `channel_threshold` | 0.000058000000 | 4 | 0 | 4 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG T6 - Pz` | `channel_threshold` | 0.000058000000 | 10 | 0 | 10 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG O1 - Pz` | `channel_threshold` | 0.000058000000 | 11 | 0 | 11 | 133 | 0.000000 | 0.000000 | 0.000000 |

### Random Search, Per-Channel, With Weighted Frontal Backbone

| Channel | Source | Threshold | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `EEG Fp1 - Pz` | `channel_threshold` | 0.000046855240 | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| `EEG X1 - Pz` | `channel_threshold` | 0.000112397900 | 150 | 132 | 18 | 1 | 0.880000 | 0.992481 | 0.932862 |
| `EEG F7 - Pz` | `channel_threshold` | 0.000044616530 | 146 | 130 | 16 | 3 | 0.890411 | 0.977444 | 0.931900 |
| `front7_autoreject_weighted_median` | `weighted_median_backbone` | 0.080000000000 | 143 | 128 | 15 | 5 | 0.895105 | 0.962406 | 0.927536 |
| `EEG Fp2 - Pz` | `channel_threshold` | 0.000044278900 | 154 | 131 | 23 | 2 | 0.850649 | 0.984962 | 0.912892 |
| `EEG F3 - Pz` | `channel_threshold` | 0.000017598050 | 155 | 124 | 31 | 9 | 0.800000 | 0.932331 | 0.861111 |
| `EEG Fz - Pz` | `channel_threshold` | 0.000015759880 | 151 | 117 | 34 | 16 | 0.774834 | 0.879699 | 0.823944 |
| `EEG F4 - Pz` | `channel_threshold` | 0.000026031150 | 116 | 91 | 25 | 42 | 0.784483 | 0.684211 | 0.730924 |
| `EEG F8 - Pz` | `channel_threshold` | 0.000058654380 | 53 | 42 | 11 | 91 | 0.792453 | 0.315789 | 0.451613 |
| `EEG Cz - Pz` | `channel_threshold` | 0.000010381620 | 87 | 42 | 45 | 91 | 0.482759 | 0.315789 | 0.381818 |
| `EEG C3 - Pz` | `channel_threshold` | 0.000024079900 | 23 | 13 | 10 | 120 | 0.565217 | 0.097744 | 0.166667 |
| `EEG T4 - Pz` | `channel_threshold` | 0.000011069090 | 89 | 17 | 72 | 116 | 0.191011 | 0.127820 | 0.153153 |
| `EEG C4 - Pz` | `channel_threshold` | 0.000020108620 | 21 | 9 | 12 | 124 | 0.428571 | 0.067669 | 0.116883 |
| `EEG X3 - Pz` | `channel_threshold` | 0.000000065118 | 90 | 12 | 78 | 121 | 0.133333 | 0.090226 | 0.107623 |
| `EEG P3 - Pz` | `channel_threshold` | 0.000007690420 | 67 | 10 | 57 | 123 | 0.149254 | 0.075188 | 0.100000 |
| `EEG P4 - Pz` | `channel_threshold` | 0.000010797800 | 82 | 8 | 74 | 125 | 0.097561 | 0.060150 | 0.074419 |
| `EEG T6 - Pz` | `channel_threshold` | 0.000025303090 | 201 | 12 | 189 | 121 | 0.059701 | 0.090226 | 0.071856 |
| `EEG O2 - Pz` | `channel_threshold` | 0.000025179800 | 44 | 6 | 38 | 127 | 0.136364 | 0.045113 | 0.067797 |
| `EEG X2 - Pz` | `channel_threshold` | 0.000045878340 | 113 | 8 | 105 | 125 | 0.070796 | 0.060150 | 0.065041 |
| `EEG T3 - Pz` | `channel_threshold` | 0.000024670580 | 16 | 4 | 12 | 129 | 0.250000 | 0.030075 | 0.053691 |
| `EEG O1 - Pz` | `channel_threshold` | 0.000015242540 | 124 | 4 | 120 | 129 | 0.032258 | 0.030075 | 0.031128 |
| `EEG A1 - Pz` | `channel_threshold` | 0.000019405540 | 17 | 1 | 16 | 132 | 0.058824 | 0.007519 | 0.013333 |
| `EEG T5 - Pz` | `channel_threshold` | 0.000016129180 | 43 | 1 | 42 | 132 | 0.023256 | 0.007519 | 0.011364 |
| `EEG CM - Pz` | `channel_threshold` | 0.001460936000 | 4 | 0 | 4 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG A2 - Pz` | `channel_threshold` | 0.000016552560 | 44 | 0 | 44 | 133 | 0.000000 | 0.000000 | 0.000000 |

### Bayesian Optimization, Per-Channel, With Weighted Frontal Backbone

| Channel | Source | Threshold | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `EEG Fp1 - Pz` | `channel_threshold` | 0.000046783510 | 149 | 132 | 17 | 1 | 0.885906 | 0.992481 | 0.936170 |
| `EEG X1 - Pz` | `channel_threshold` | 0.000107322300 | 150 | 132 | 18 | 1 | 0.880000 | 0.992481 | 0.932862 |
| `EEG F7 - Pz` | `channel_threshold` | 0.000045042910 | 146 | 130 | 16 | 3 | 0.890411 | 0.977444 | 0.931900 |
| `front7_autoreject_weighted_median` | `weighted_median_backbone` | 0.120000000000 | 144 | 129 | 15 | 4 | 0.895833 | 0.969925 | 0.931408 |
| `EEG Fp2 - Pz` | `channel_threshold` | 0.000043299270 | 154 | 131 | 23 | 2 | 0.850649 | 0.984962 | 0.912892 |
| `EEG F3 - Pz` | `channel_threshold` | 0.000014595290 | 169 | 126 | 43 | 7 | 0.745562 | 0.947368 | 0.834437 |
| `EEG Fz - Pz` | `channel_threshold` | 0.000016685050 | 143 | 114 | 29 | 19 | 0.797203 | 0.857143 | 0.826087 |
| `EEG F4 - Pz` | `channel_threshold` | 0.000028344410 | 99 | 80 | 19 | 53 | 0.808081 | 0.601504 | 0.689655 |
| `EEG Cz - Pz` | `channel_threshold` | 0.000007923737 | 150 | 56 | 94 | 77 | 0.373333 | 0.421053 | 0.395760 |
| `EEG F8 - Pz` | `channel_threshold` | 0.000062571580 | 27 | 21 | 6 | 112 | 0.777778 | 0.157895 | 0.262500 |
| `EEG T4 - Pz` | `channel_threshold` | 0.000010907830 | 94 | 19 | 75 | 114 | 0.202128 | 0.142857 | 0.167401 |
| `EEG P3 - Pz` | `channel_threshold` | 0.000005168025 | 198 | 24 | 174 | 109 | 0.121212 | 0.180451 | 0.145015 |
| `EEG O2 - Pz` | `channel_threshold` | 0.000017235380 | 58 | 8 | 50 | 125 | 0.137931 | 0.060150 | 0.083770 |
| `EEG T6 - Pz` | `channel_threshold` | 0.000025792070 | 194 | 12 | 182 | 121 | 0.061856 | 0.090226 | 0.073394 |
| `EEG P4 - Pz` | `channel_threshold` | 0.000015196370 | 40 | 6 | 34 | 127 | 0.150000 | 0.045113 | 0.069364 |
| `EEG C4 - Pz` | `channel_threshold` | 0.000024844970 | 9 | 4 | 5 | 129 | 0.444444 | 0.030075 | 0.056338 |
| `EEG C3 - Pz` | `channel_threshold` | 0.000028470720 | 12 | 4 | 8 | 129 | 0.333333 | 0.030075 | 0.055172 |
| `EEG T5 - Pz` | `channel_threshold` | 0.000011057450 | 95 | 5 | 90 | 128 | 0.052632 | 0.037594 | 0.043860 |
| `EEG T3 - Pz` | `channel_threshold` | 0.000028047100 | 13 | 3 | 10 | 130 | 0.230769 | 0.022556 | 0.041096 |
| `EEG X2 - Pz` | `channel_threshold` | 0.000065534760 | 67 | 4 | 63 | 129 | 0.059701 | 0.030075 | 0.040000 |
| `EEG O1 - Pz` | `channel_threshold` | 0.000018242160 | 89 | 3 | 86 | 130 | 0.033708 | 0.022556 | 0.027027 |
| `EEG A1 - Pz` | `channel_threshold` | 0.000021587190 | 11 | 1 | 10 | 132 | 0.090909 | 0.007519 | 0.013889 |
| `EEG CM - Pz` | `channel_threshold` | 0.001395145000 | 3 | 0 | 3 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG X3 - Pz` | `channel_threshold` | 0.000000094395 | 14 | 0 | 14 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG A2 - Pz` | `channel_threshold` | 0.000016358210 | 45 | 0 | 45 | 133 | 0.000000 | 0.000000 | 0.000000 |

### Global Threshold, With Weighted Frontal Backbone

| Channel | Source | Threshold | Candidates | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `EEG Fp1 - Pz` | `channel_threshold` | 0.000058000000 | 145 | 131 | 14 | 2 | 0.903448 | 0.984962 | 0.942446 |
| `EEG Fp2 - Pz` | `channel_threshold` | 0.000058000000 | 143 | 129 | 14 | 4 | 0.902098 | 0.969925 | 0.934783 |
| `EEG F7 - Pz` | `channel_threshold` | 0.000058000000 | 138 | 125 | 13 | 8 | 0.905797 | 0.939850 | 0.922509 |
| `EEG X1 - Pz` | `channel_threshold` | 0.000058000000 | 164 | 133 | 31 | 0 | 0.810976 | 1.000000 | 0.895623 |
| `front7_autoreject_weighted_median` | `weighted_median_backbone` | 0.005000000000 | 49 | 44 | 5 | 89 | 0.897959 | 0.330827 | 0.483516 |
| `EEG F8 - Pz` | `channel_threshold` | 0.000058000000 | 53 | 42 | 11 | 91 | 0.792453 | 0.315789 | 0.451613 |
| `EEG X2 - Pz` | `channel_threshold` | 0.000058000000 | 75 | 8 | 67 | 125 | 0.106667 | 0.060150 | 0.076923 |
| `EEG F3 - Pz` | `channel_threshold` | 0.000058000000 | 6 | 4 | 2 | 129 | 0.666667 | 0.030075 | 0.057554 |
| `EEG O2 - Pz` | `channel_threshold` | 0.000058000000 | 24 | 4 | 20 | 129 | 0.166667 | 0.030075 | 0.050955 |
| `EEG Fz - Pz` | `channel_threshold` | 0.000058000000 | 6 | 3 | 3 | 130 | 0.500000 | 0.022556 | 0.043165 |
| `EEG F4 - Pz` | `channel_threshold` | 0.000058000000 | 3 | 2 | 1 | 131 | 0.666667 | 0.015038 | 0.029412 |
| `EEG CM - Pz` | `channel_threshold` | 0.000058000000 | 84 | 2 | 82 | 131 | 0.023810 | 0.015038 | 0.018433 |
| `EEG C3 - Pz` | `channel_threshold` | 0.000058000000 | 1 | 1 | 0 | 132 | 1.000000 | 0.007519 | 0.014925 |
| `EEG T3 - Pz` | `channel_threshold` | 0.000058000000 | 4 | 1 | 3 | 132 | 0.250000 | 0.007519 | 0.014599 |
| `EEG A2 - Pz` | `channel_threshold` | 0.000058000000 | 0 | 0 | 0 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG X3 - Pz` | `channel_threshold` | 0.000058000000 | 0 | 0 | 0 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG A1 - Pz` | `channel_threshold` | 0.000058000000 | 1 | 0 | 1 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG C4 - Pz` | `channel_threshold` | 0.000058000000 | 1 | 0 | 1 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG Cz - Pz` | `channel_threshold` | 0.000058000000 | 1 | 0 | 1 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG P3 - Pz` | `channel_threshold` | 0.000058000000 | 2 | 0 | 2 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG T4 - Pz` | `channel_threshold` | 0.000058000000 | 2 | 0 | 2 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG T5 - Pz` | `channel_threshold` | 0.000058000000 | 2 | 0 | 2 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG P4 - Pz` | `channel_threshold` | 0.000058000000 | 4 | 0 | 4 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG T6 - Pz` | `channel_threshold` | 0.000058000000 | 10 | 0 | 10 | 133 | 0.000000 | 0.000000 | 0.000000 |
| `EEG O1 - Pz` | `channel_threshold` | 0.000058000000 | 11 | 0 | 11 | 133 | 0.000000 | 0.000000 | 0.000000 |

## Observations

- Across all six Strategy C saved runs, the strongest single lane is
  `EEG Fp1 - Pz`, not `EEG X1 - Pz`.
- For both per-channel runs, `EEG Fp1 - Pz` is best with:
  - `TP=132`
  - `FP=17`
  - `FN=1`
  - `precision=0.885906`
  - `recall=0.992481`
  - `F1=0.936170`
- The optional weighted frontal backbone never wins the lane ranking on this
  slice.
- The backbone is competitive only in the per-channel runs:
  - random search backbone: `TP=128`, `FP=15`, `FN=5`, `F1=0.927536`
  - Bayesian backbone: `TP=129`, `FP=15`, `FN=4`, `F1=0.931408`
- The global-threshold backbone is much weaker:
  - `TP=44`, `FP=5`, `FN=89`, `F1=0.483516`
- Compared with the saved baselines:
  - Strategy A: `133/32/0`
  - Strategy B: `133/28/0`
  - best Strategy C lane: `132/17/1`
- So the best Strategy C lane reduces false positives sharply, but it gives up
  one true blink relative to both saved baselines.
- If recall-first remains the strict Step 1 priority, `EEG X1 - Pz` is still
  the only Strategy C lane that preserves `FN=0`:
  - per-channel: `TP=132`, `FP=18`, `FN=1`, so not enough
  - global: `TP=133`, `FP=31`, `FN=0`, which matches recall but is worse than
    Strategy B and only slightly better than Strategy A on false positives
- The per-channel methods are effectively tied at the top:
  - same best lane
  - same `TP/FP/FN`
  - same `F1`
  - Bayesian optimization only changes lower-ranked channels and runtime

## Conclusion

The saved Step 1 outputs do not support the earlier conclusion that Strategy C
already has a strictly better recall-first operating point than the saved
Strategy A and Strategy B baselines.

What the saved reruns now show:

- The cleanest single Strategy C lane is `EEG Fp1 - Pz`.
- That lane is the best result in both per-channel variants, with and without
  the optional weighted frontal backbone.
- Its operating point is:
  - `TP=132`
  - `FP=17`
  - `FN=1`
  - `precision=0.885906`
  - `recall=0.992481`
  - `F1=0.936170`
- This is a real precision improvement over both saved baselines:
  - versus Strategy A: `FP 32 -> 17`
  - versus Strategy B: `FP 28 -> 17`
- But it is not recall-preserving:
  - both saved baselines keep `TP=133` and `FN=0`
  - the best Strategy C lane falls to `TP=132` and `FN=1`

So the current evidence splits Strategy C into two useful but incomplete
options:

- Per-channel Strategy C is the best precision-leaning Step 1 candidate, but it
  misses one blink.
- Global-threshold Strategy C preserves the recall-first target on `EEG X1 - Pz`
  with `TP=133` and `FN=0`, but its false positives rise to `31`, which is only
  a marginal improvement over Strategy A and still worse than Strategy B.

The weighted frontal backbone does not currently justify itself on this slice.
It never becomes the best lane, and enabling it does not improve the winning
channel or the winning metrics for any of the three threshold modes.

The current best-supported conclusion is therefore:

- If the Step 1 requirement is still strict recall-first, Strategy C has not
  yet beaten the saved Strategy A or Strategy B baselines.
- If the priority shifts toward lowering false positives while accepting one
  missed blink, the strongest current Strategy C lane is `EEG Fp1 - Pz` under
  either per-channel random search or per-channel Bayesian optimization.
