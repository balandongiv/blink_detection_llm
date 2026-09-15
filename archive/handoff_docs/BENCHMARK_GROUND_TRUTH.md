# Benchmark Ground Truth — Exp1–8 Reference Results

**Date:** 2026-06-26  
**Environment:** `double_threshold_algo` conda env, i7-13700F, N_JOBS=16  
**Resample rate:** 100 Hz  
**Epoch duration (default):** 30 s  
**Std threshold (default):** 3.5  
**Min flagged epochs (default):** 1  
**IoU threshold (default):** 0.1  

Naming convention: `proposed_<center>_<selection>_<channel>`  
Only `det_precision`, `det_recall`, `det_f1` are reported (no Stage A metrics).

Any refactored version of this codebase must reproduce these values within ±0.002 F1 under identical parameters.

---

## Exp1 — Channel Selection Ablation

### Raja Dataset (EGI-128, 46 sessions)

#### Top 4 Individual Channels (proposed_median, single-channel mode)

| Label | Channel | det_P | det_R | det_F1 |
|-------|---------|-------|-------|--------|
| `proposed_median_single_e22_e22` | E22 | 0.9007 | 0.7908 | **0.8099** |
| `proposed_median_single_e9_e9` | E9 | 0.8990 | 0.7884 | **0.8084** |
| `proposed_median_single_e3_e3` | E3 | 0.8879 | 0.5947 | **0.6716** |
| `proposed_median_single_e23_e23` | E23 | 0.8194 | 0.5431 | **0.6042** |

#### Top 4 Regional Groups (proposed_median, best channel within group)

| Label | Selection | Best Ch | det_P | det_R | det_F1 |
|-------|-----------|---------|-------|-------|--------|
| `proposed_median_all_e9` | all | E9 | — | — | **0.8545** |
| `proposed_median_frontal_left_e22` | frontal_left | E22 | — | — | **0.8312** |
| `proposed_median_frontal_e9` | frontal | E9 | — | — | **0.8299** |
| `proposed_median_frontal_right_e9` | frontal_right | E9 | — | — | **0.8150** |

#### Full Frontal Group Per-Channel (proposed_median vs baselines)

| Channel | proposed_median F1 | blinker_concat F1 | mne_annot F1 |
|---------|-------------------|-------------------|--------------|
| E9 | **0.8299** | 0.7342 | 0.5021 |
| E22 | **0.8241** | 0.7451 | 0.5456 |
| E3 | **0.7054** | 0.7333 | 0.4404 |
| E23 | **0.6448** | 0.6931 | 0.4619 |
| E24 | 0.3388 | 0.5689 | 0.3478 |
| E33 | 0.0479 | 0.1993 | 0.0906 |
| E124 | 0.3126 | 0.5980 | 0.2405 |

---

### Cao2018 Dataset (10-20 system, 58 sessions)

#### Top 4 Individual Channels (proposed_median, single-channel mode)

| Label | Channel | det_P | det_R | det_F1 |
|-------|---------|-------|-------|--------|
| `proposed_median_single_fp1_fp1` | FP1 | 0.7957 | 0.7548 | **0.7434** |
| `proposed_median_single_fp2_fp2` | FP2 | 0.7936 | 0.7105 | **0.7131** |
| `proposed_median_single_f7_f7` | F7 | 0.7188 | 0.3862 | **0.4512** |
| `proposed_median_single_f8_f8` | F8 | 0.7304 | 0.3612 | **0.4377** |

#### Top 4 Regional Groups (proposed_median, best channel within group)

| Label | Selection | Best Ch | det_P | det_R | det_F1 |
|-------|-----------|---------|-------|-------|--------|
| `proposed_median_all_fp1` | all | FP1 | — | — | **0.7800** |
| `proposed_median_frontal_fp1` | frontal | FP1 | — | — | **0.7692** |
| `proposed_median_frontal_left_fp1` | frontal_left | FP1 | — | — | **0.7471** |
| `proposed_median_frontal_right_fp2` | frontal_right | FP2 | — | — | **0.7420** |

#### Full Frontal Group Per-Channel (proposed_median vs baselines)

| Channel | proposed_median F1 | blinker_concat F1 | mne_annot F1 |
|---------|-------------------|-------------------|--------------|
| FP1 | **0.7692** | 0.6874 | 0.3603 |
| FP2 | **0.7469** | 0.6780 | 0.3521 |
| F7 | 0.4977 | **0.6400** | 0.2922 |
| F8 | 0.4821 | **0.6293** | 0.2655 |
| F3 | 0.4725 | **0.6441** | 0.2023 |
| F4 | 0.4545 | **0.6361** | 0.1741 |

**Note:** Inversions on F3/F4/F7/F8 are expected — these lateral frontal channels have weak blink signals. BLINKER achieves high recall (~0.92) via permissive threshold at the cost of precision (~0.52). Proposed wins on periorbital channels (FP1/FP2).

---

## Exp2 — Strategy Comparison

### Raja — Key channels (proposed_median vs baselines)

| Label | det_P | det_R | det_F1 |
|-------|-------|-------|--------|
| `proposed_median_single_e9_e9` | 0.8990 | 0.7884 | **0.8084** |
| `proposed_median_single_e22_e22` | 0.9007 | 0.7908 | **0.8099** |
| `blinker_concat_single_e9_e9` | 0.6414 | 0.9589 | 0.7342 |
| `blinker_concat_single_e22_e22` | 0.6526 | 0.9572 | 0.7451 |
| `mne_annot_single_e9_e9` | 0.6446 | 0.5303 | 0.5021 |
| `mne_annot_single_e22_e22` | 0.6235 | 0.5955 | 0.5456 |

### Cao2018 — Key channels (proposed_median vs baselines)

| Label | det_P | det_R | det_F1 |
|-------|-------|-------|--------|
| `proposed_median_single_fp1_fp1` | 0.7957 | 0.7548 | **0.7434** |
| `proposed_median_single_fp2_fp2` | 0.7936 | 0.7105 | **0.7131** |
| `blinker_concat_single_fp1_fp1` | 0.5590 | 0.9955 | 0.6874 |
| `blinker_concat_single_fp2_fp2` | 0.5489 | 0.9902 | 0.6780 |
| `mne_annot_single_fp1_fp1` | 0.4819 | 0.3744 | 0.3603 |
| `mne_annot_single_fp2_fp2` | 0.4438 | 0.3739 | 0.3521 |

---

## Exp3 — Epoch Duration Sweep

Reference channel: `single:E9` for Raja, `single:FP1` for Cao2018. Center=median.

### Raja (E9)

| epoch_duration_s | det_F1 |
|-----------------|--------|
| 10 | 0.7783 |
| 20 | 0.7980 |
| **30 (default)** | **0.8084** |
| 40 | 0.8121 |
| 50 | 0.7900 |
| 60 | 0.8103 |
| 120 | 0.8135 |

### Cao2018 (FP1)

| epoch_duration_s | det_F1 |
|-----------------|--------|
| 10 | 0.6868 |
| 20 | 0.7105 |
| **30 (default)** | **0.7434** |
| 40 | 0.7463 |
| 50 | 0.7515 |
| 60 | 0.7748 |
| 120 | 0.7721 |

---

## Exp4 — IoU / Boundary Tolerance

Reference channel: `single:E9` for Raja, `single:FP1` for Cao2018. Center=median.

### Raja (E9)

| iou_threshold | det_F1 |
|--------------|--------|
| 0.0 | 0.8693 |
| **0.1 (default)** | **0.8103** |
| 0.2 | 0.7634 |
| 0.3 | 0.6718 |
| 0.5 | 0.3263 |

### Cao2018 (FP1)

| iou_threshold | det_F1 |
|--------------|--------|
| 0.0 | 0.8625 |
| **0.1 (default)** | **0.7748** |
| 0.2 | 0.7282 |
| 0.3 | 0.5647 |
| 0.5 | 0.1345 |

---

## Exp5 — Min Flagged Epochs

Reference channel: `single:E9` for Raja, `single:FP1` for Cao2018. Center=median.

### Raja (E9)

| min_flagged_epochs | det_F1 |
|-------------------|--------|
| **1 (default)** | **0.8084** |
| 2 | 0.8223 |
| 3 | 0.8343 |
| 5 | 0.8415 |

### Cao2018 (FP1)

| min_flagged_epochs | det_F1 |
|-------------------|--------|
| **1 (default)** | **0.7434** |
| 2 | 0.7434 |
| 3 | 0.7447 |
| 5 | 0.7512 |

---

## Exp6 — Std Threshold

Reference channel: `single:E9` for Raja, `single:FP1` for Cao2018. Center=median.

### Raja (E9)

| std_threshold | det_F1 |
|--------------|--------|
| 2.5 | 0.8463 |
| 3.0 | 0.8337 |
| **3.5 (default)** | **0.8084** |
| 4.0 | 0.7668 |

### Cao2018 (FP1)

| std_threshold | det_F1 |
|--------------|--------|
| 2.5 | 0.7804 |
| 3.0 | 0.7765 |
| **3.5 (default)** | **0.7434** |
| 4.0 | 0.6875 |

---

## Exp7 — Epoch Health Filter

Reference channel: `single:E9` for Raja, `single:FP1` for Cao2018. Center=median.

### Raja (E9)

| use_epoch_health | det_F1 |
|-----------------|--------|
| **False (default)** | **0.8084** |
| True | 0.8036 |

### Cao2018 (FP1)

| use_epoch_health | det_F1 |
|-----------------|--------|
| **False (default)** | **0.7434** |
| True | **0.8643** |

**Note:** Epoch health filter has negligible effect on Raja but shows significant improvement on Cao2018 (+12.1pp for FP1). Worth investigating further.

---

## Exp8 — Blink Category Analysis

Reference: `single:E9` (Raja), `single:FP1` (Cao2018).

### Raja (E9)

| blink_category | det_P | det_R | det_F1 |
|---------------|-------|-------|--------|
| all | 0.8990 | 0.7884 | **0.8084** |
| normal | 0.8838 | 0.8032 | **0.8071** |
| long (≥ 400 ms) | 0.4551 | 0.6726 | **0.4914** |

### Raja (E22)

| blink_category | det_P | det_R | det_F1 |
|---------------|-------|-------|--------|
| all | 0.9007 | 0.7908 | **0.8099** |
| normal | 0.8861 | 0.8072 | **0.8109** |
| long (≥ 400 ms) | 0.4352 | 0.6791 | **0.4779** |

### Cao2018 (FP1)

| blink_category | det_P | det_R | det_F1 |
|---------------|-------|-------|--------|
| all | 0.7957 | 0.7548 | **0.7434** |
| normal | 0.7693 | 0.7464 | **0.7240** |
| long (≥ 400 ms) | 0.3662 | 0.7995 | **0.4472** |

### Cao2018 (FP2)

| blink_category | det_P | det_R | det_F1 |
|---------------|-------|-------|--------|
| all | 0.7936 | 0.7105 | **0.7131** |
| normal | 0.7673 | 0.7022 | **0.6944** |
| long (≥ 400 ms) | 0.3698 | 0.7687 | **0.4356** |

**Note:** Long blinks (≥ 400 ms) are systematically harder — F1 drops ~31pp on Raja, ~29pp on Cao2018. Detection of long blinks has high recall (~0.67–0.80) but poor precision (~0.37–0.46), suggesting the algorithm undersegments extended eye closures.

---

## Summary: Key Findings

1. **Proposed-Med wins on periorbital channels** (E9/E22 for Raja, FP1/FP2 for Cao2018) by +6 to +10pp F1 over BLINKER-concat.
2. **Inversions on lateral frontal channels** (F3/F4/F7/F8 for Cao2018, E3/E23 for Raja single-channel) are expected — weak blink signal, autoreject cannot learn a reliable threshold.
3. **Optimal epoch duration:** 30–40 s for Raja, 50–60 s for Cao2018.
4. **Std threshold:** Tighter threshold (2.5–3.0) improves F1 on both datasets vs default 3.5.
5. **Min flagged epochs:** Increasing from 1 to 5 adds up to +3.3pp F1 (Raja), negligible for Cao2018.
6. **Epoch health filter:** No benefit for Raja; +12.1pp for Cao2018 FP1 (needs investigation).
7. **Long blinks:** Systematic weakness — consider a separate detector tuned for long blink duration.
