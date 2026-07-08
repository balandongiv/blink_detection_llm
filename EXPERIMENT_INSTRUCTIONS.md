# Experiment Pipeline: Instructions for Fresh Run

## Overview

This document describes how to reproduce the full Exp1–8 blink detection ablation study from scratch.
It is intended as a reference for both human operators and LLM coding agents tasked with re-running or refactoring the pipeline.

---

## Environment

- **Conda env:** `double_threshold_algo`
- **Python:** `C:\Users\balan\anaconda3\envs\double_threshold_algo\python.exe`
- **N_JOBS:** 16 (i7-13700F, 24 logical threads — leave 8 for OS)
- **OVERWRITE:** `False` (resume support — completed session CSVs are cached and skipped on restart)
- **Working directory:** `C:\Users\balan\IdeaProjects\blink_detection_llm`

Run each script as:
```
python experiment_script\run_expN_<dataset>.py
```

---

## Naming Convention

All results use the format:

```
proposed_<center>_<selection>_<channel>
```

Examples:
- `proposed_median_single_e9` — Proposed algorithm, median centre, channel E9 used alone
- `proposed_median_frontal_e9` — Proposed algorithm, median centre, channel E9 evaluated within the frontal group
- `proposed_median_frontal_fp1` — Proposed algorithm, median centre, FP1 within the frontal group (Cao2018)
- `proposed_mean_all_e22` — Proposed algorithm, mean centre, E22 within the full-channel group

Baselines use:
- `blinker_concat_<selection>_<channel>`
- `mne_annot_<selection>_<channel>`

---

## Step 1 — Run Experiment 1 (Channel Selection Ablation)

**Scripts:**
```
python experiment_script\run_exp1_raja.py
python experiment_script\run_exp1_cao2018.py
```

**Output directories:**
- `runs/exp1_channel_raja/`
- `runs/exp1_channel_cao/`

**What it does:** Runs the full Proposed pipeline (Stage A autoreject → Stage B threshold → Stage C detection) for every brain-region channel group AND every individual frontal channel, across all sessions in each dataset. Reports `det_precision`, `det_recall`, `det_f1` per channel.

### After Exp1: Automatic Channel Selection

Run the channel selection script to pick the top 4 individual channels and top 4 regional groups for each dataset:

```
python experiment_script\exp1_get_best_region_channel.py
```

This script reads both Exp1 summaries and writes:
- `runs/channel_selection/selected_channels.json` — machine-readable selection
- `runs/channel_selection/selected_channels_report.md` — human-readable report

The selected channels become the `GROUPS_TO_RUN` filter for Exp2–8. Edit each script's `RAJA_SELECTION_ORDER` / `CAO_SELECTION_ORDER` list if you want a different subset.

**Current best channels (from this run):**

| Rank | Raja (EGI-128) | F1 | Cao2018 (10-20) | F1 |
|------|---------------|-----|----------------|-----|
| 1 | `single:E9` | 0.808 | `single:FP1` | 0.743 |
| 2 | `single:E22` | 0.810 | `single:FP2` | 0.713 |
| 3 | `single:E3` | 0.672 | `single:F7` | 0.451 |
| 4 | `single:E23` | 0.604 | `single:F8` | 0.438 |

| Rank | Raja regional | Best-ch F1 | Cao2018 regional | Best-ch F1 |
|------|--------------|------------|-----------------|------------|
| 1 | `all` (E9) | 0.854 | `all` (FP1) | 0.780 |
| 2 | `frontal_left` (E22) | 0.831 | `frontal` (FP1) | 0.769 |
| 3 | `frontal` (E9) | 0.830 | `frontal_left` (FP1) | 0.747 |
| 4 | `frontal_right` (E9) | 0.815 | `frontal_right` (FP2) | 0.742 |

---

## Step 2 — Run Experiment 2 (Strategy Comparison)

**Scripts:**
```
python experiment_script\run_exp2_raja.py
python experiment_script\run_exp2_cao2018.py
```

Compares: `Proposed-Med`, `Proposed-Mean`, `BLINKER-concat`, `MNE-annot`
Per channel within each selection group.

---

## Step 3 — Run Experiment 3 (Epoch Duration)

**Scripts:**
```
python experiment_script\run_exp3_raja.py
python experiment_script\run_exp3_cao2018.py
```

Sweeps epoch duration: 10, 20, 30, 40, 50, 60, 120 seconds.
Reference epoch: 30 s (default).

---

## Step 4 — Run Experiment 4 (IoU / Boundary Tolerance)

**Scripts:**
```
python experiment_script\run_exp4_raja.py
python experiment_script\run_exp4_cao2018.py
```

Sweeps IoU overlap threshold: 0.0, 0.1, 0.2, 0.3, 0.5.
Reference: 0.1 (default).

---

## Step 5 — Run Experiment 5 (Min Flagged Epochs)

**Scripts:**
```
python experiment_script\run_exp5_raja.py
python experiment_script\run_exp5_cao2018.py
```

Sweeps `min_flagged_epochs`: 1, 2, 3, 5.
Reference: 1 (default).

---

## Step 6 — Run Experiment 6 (Std Threshold)

**Scripts:**
```
python experiment_script\run_exp6_raja.py
python experiment_script\run_exp6_cao2018.py
```

Sweeps `std_threshold`: 2.5, 3.0, 3.5, 4.0.
Reference: 3.5 (default).

---

## Step 7 — Run Experiment 7 (Epoch Health Filter)

**Scripts:**
```
python experiment_script\run_exp7_raja.py
python experiment_script\run_exp7_cao2018.py
```

Compares `use_epoch_health=False` vs `True`.
Reference: False (default).

---

## Step 8 — Run Experiment 8 (Blink Category Analysis)

**Scripts:**
```
python experiment_script\run_exp8_raja.py
python experiment_script\run_exp8_cao2018.py
```

Breaks down performance by blink category: `all`, `normal`, `long` (>= 400 ms threshold).

---

## Reporting Rules (CRITICAL)

- **NEVER** mention Stage A, Stage B, Stage C, `stageA_*` metrics in any report, Telegram, or LaTeX output
- **ONLY** report: `det_precision`, `det_recall`, `det_f1`
- Telegram token: read from `bot_telegram.md` at runtime — NEVER print, log, or hardcode
- Telegram chat ID: `7784180158`

---

## Sequential Run Order (Recommended)

Run Exp1 Raja and Exp1 Cao2018 first (they take the longest).
Then run the channel selection script.
Then run Exp2–8 for both datasets sequentially (N_JOBS=16).

Approximate runtimes (i7-13700F, N_JOBS=16, OVERWRITE=False for resumption):
- Exp1 Raja: ~60 min (46 sessions × many groups)
- Exp1 Cao: ~70 min (58 sessions × many groups)
- Exp2: ~10 min per dataset (cached from Exp1 for Proposed; baselines run fresh)
- Exp3: ~60 min per dataset (7 epoch durations × all sessions)
- Exp4–7: ~10–25 min per dataset
- Exp8: ~5 min per dataset
