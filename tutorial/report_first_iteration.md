
---

# Aggregate Comparison Results

**Best lane per pair**

## Summary Table

| Strategy                       | Successful Pairs | Failed Pairs | Total TP | Total FP | Total FN | Micro Precision | Micro Recall |   Micro F1 | Macro Precision | Macro Recall |   Macro F1 |
| ------------------------------ | ---------------: | -----------: | -------: | -------: | -------: | --------------: | -----------: | ---------: | --------------: | -----------: | ---------: |
| **strategy_a**                 |               65 |            0 |   30,733 |   22,748 |   10,691 |          0.5747 |       0.7419 |     0.6477 |          0.5153 |       0.7030 |     0.5764 |
| **strategy_b**                 |               65 |            0 |   15,357 |   10,779 |   26,067 |          0.5876 |       0.3707 |     0.4546 |          0.4219 |       0.3908 |     0.3529 |
| **strategy_c**                 |               64 |            1 |   26,865 |   14,007 |   14,548 |      **0.6573** |       0.6487 | **0.6530** |      **0.6283** |   **0.6429** | **0.6231** |
| **strategy_d**                 |               64 |            1 |   25,095 |   81,335 |   16,318 |          0.2358 |       0.6060 |     0.3395 |          0.2920 |       0.6030 |     0.3649 |
| **strategy_e**                 |               65 |            0 |   30,872 |   25,995 |   10,552 |          0.5429 |       0.7453 |     0.6282 |          0.4874 |       0.7072 |     0.5574 |
| **strategy_e1_median**         |               65 |            0 |   31,268 |   28,209 |   10,156 |          0.5257 |       0.7548 |     0.6198 |          0.4691 |       0.7114 |     0.5459 |
| **strategy_e2_floor**          |               65 |            0 |   31,268 |   28,200 |   10,156 |          0.5258 |       0.7548 |     0.6198 |          0.4692 |       0.7114 |     0.5459 |
| **strategy_e3_hysteresis**     |               65 |            0 |   31,708 |   37,642 |    9,716 |          0.4572 |       0.7654 |     0.5725 |          0.4143 |       0.7203 |     0.5007 |
| **strategy_e4_multiscale**     |               65 |            0 |   31,721 |   42,325 |    9,703 |          0.4284 |       0.7658 |     0.5494 |          0.3926 |       0.7148 |     0.4807 |
| **strategy_e5_global_floor**   |               65 |            0 |   30,811 |   24,470 |   10,613 |          0.5574 |       0.7438 |     0.6372 |          0.5002 |       0.7072 |     0.5674 |
| **strategy_e6_soft_shrink**    |               65 |            0 |   31,223 |   27,350 |   10,201 |          0.5331 |       0.7537 |     0.6245 |          0.4762 |       0.7112 |     0.5509 |
| **strategy_e7_bg_refit**       |               65 |            0 |   30,978 |   25,745 |   10,446 |          0.5461 |       0.7478 |     0.6313 |          0.4913 |       0.7119 |     0.5613 |
| **strategy_e9_frontal_avg**    |               65 |            0 |   30,642 |   26,673 |   10,782 |          0.5346 |       0.7397 |     0.6207 |          0.4821 |       0.7009 |     0.5512 |
| **strategy_e10_epoch_smooth**  |               65 |            0 |   31,291 |   27,977 |   10,133 |          0.5280 |       0.7554 |     0.6215 |          0.4707 |       0.7115 |     0.5471 |
| **strategy_e6_e10_combined**   |               65 |            0 |   31,268 |   27,187 |   10,156 |          0.5349 |       0.7548 |     0.6261 |          0.4768 |       0.7120 |     0.5517 |
| **strategy_e12_amp_filter**    |               65 |            0 |   29,242 |   19,147 |   12,182 |          0.6043 |       0.7059 |     0.6512 |          0.5519 |       0.6886 |     0.5910 |
| **strategy_e_sliding_window**  |               65 |            0 |   29,819 |   19,294 |   11,605 |          0.6072 |       0.7198 |     0.6587 |          0.5456 |       0.6788 |     0.5902 |
| **strategy_e_or_fusion**       |               65 |            0 |   30,826 |   31,654 |   10,598 |          0.4934 |       0.7442 |     0.5934 |          0.4499 |       0.6972 |     0.5237 |
| **strategy_e_vote_2of3**       |               65 |            0 |   16,569 |   36,034 |   24,855 |          0.3150 |       0.4000 |     0.3524 |          0.3006 |       0.3894 |     0.3296 |
| **strategy_e_expand_bridge** ★ |               65 |            0 |   30,901 |   21,428 |   10,523 |          0.5905 |       0.7460 | **0.6592** |          0.5249 |       0.6945 |     0.5813 |
| **strategy_e_duration_band**   |               65 |            0 |   30,583 |   23,724 |   10,841 |          0.5632 |       0.7383 |     0.6389 |          0.5047 |       0.6988 |     0.5677 |
| **strategy_e_slope_guard**     |               65 |            0 |   30,588 |   22,365 |   10,836 |          0.5776 |       0.7384 |     0.6482 |          0.5164 |       0.6985 |     0.5774 |
| **strategy_e_abs_polarity**    |               65 |            0 |   32,915 |  110,940 |    8,509 |          0.2288 |       0.7946 |     0.3553 |          0.2212 |       0.7603 |     0.3217 |
| **strategy_e_adaptive_k**      |               65 |            0 |   30,434 |   21,358 |   10,990 |          0.5876 |       0.7347 |     0.6530 |          0.5289 |       0.7027 |     0.5868 |
| **strategy_e_quantile_thr**    |               65 |            0 |   24,474 |   19,500 |   16,950 |          0.5566 |       0.5908 |     0.5732 |          0.5214 |       0.6267 |     0.5446 |
| **strategy_e_refractory**      |               65 |            0 |   30,783 |   23,536 |   10,641 |          0.5667 |       0.7431 |     0.6430 |          0.5083 |       0.7060 |     0.5732 |
| **strategy_e8_changepoint**    |               65 |            0 |   30,517 |   22,881 |   10,907 |          0.5715 |       0.7367 |     0.6437 |          0.5116 |       0.6994 |     0.5734 |
| **strategy_e11_lane_route**    |               65 |            0 |   31,049 |   37,081 |   10,375 |          0.4557 |       0.7495 |     0.5668 |          0.4183 |       0.7108 |     0.5019 |
| **strategy_e13_self_train**    |               65 |            0 |   30,630 |   21,749 |   10,794 |          0.5848 |       0.7394 |     0.6531 |          0.5421 |       0.7058 |     0.5882 |

> ★ **New best overall performer (3rd iteration):** **strategy_e_expand_bridge** — **Micro F1 = 0.6592**, beats strategy_c (0.6530) AND strategy_e12_amp_filter (0.6512), **0 failed pairs** across all 65 pairs.
> **3rd iteration runner-up:** **strategy_e_sliding_window** — **Micro F1 = 0.6587**, second-best ever, 0 failures, lowest FP (19,294) among high-recall strategies.
> **Ties strategy_c with 0 failures:** **strategy_e_adaptive_k** (F1=0.6530) and **strategy_e13_self_train** (F1=0.6531).
> **Best strict recall-first performer:** **strategy_e4_multiscale** — **FN = 9,703** (lowest), **Micro Recall = 0.7658** (highest), **0 failures**.
> **Best practical recall-first compromise:** **strategy_e5_global_floor** — **0 failures**, recall above **strategy_a** (0.7438 vs 0.7419), well-controlled FP.

## Step 1 Ranking (Recall-First)

Sorted by:
1. lowest FN
2. highest recall
3. acceptable FP growth
4. zero failures

| Rank | Strategy | TP | FN | Recall | FP | Precision | F1 | Failures | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | **strategy_e4_multiscale** | 31,721 | **9,703** | **0.7658** | 42,325 | 0.4284 | 0.5494 | **0** | Best pure recall; FP very large |
| 2 | **strategy_e3_hysteresis** | 31,708 | 9,716 | 0.7654 | 37,642 | 0.4572 | 0.5725 | **0** | Near-best recall; FP lower than E4 |
| 3 | **strategy_e_abs_polarity** | 32,915 | 8,509 | **0.7946** | 110,940 | 0.2288 | 0.3553 | **0** | Highest recall ever; FP unusable |
| 4 | **strategy_e11_lane_route** | 31,049 | 10,375 | 0.7495 | 37,081 | 0.4557 | 0.5668 | **0** | High recall; FP too high |
| 5 | **strategy_e_or_fusion** | 30,826 | 10,598 | 0.7442 | 31,654 | 0.4934 | 0.5934 | **0** | OR union; FP high |
| 6 | **strategy_e10_epoch_smooth** | 31,291 | 10,133 | 0.7554 | 27,977 | 0.5280 | 0.6215 | **0** | Good recall from 2nd iteration |
| 7 | **strategy_e1_median** | 31,268 | 10,156 | 0.7548 | 28,209 | 0.5257 | 0.6198 | **0** | Strong recall without extreme FP |
| 8 | **strategy_e6_soft_shrink** | 31,223 | 10,201 | 0.7537 | 27,350 | 0.5331 | 0.6245 | **0** | Soft-shrinkage |
| 9 | **strategy_e_expand_bridge** ★ | 30,901 | 10,523 | 0.7460 | 21,428 | 0.5905 | **0.6592** | **0** | **Best F1 ever; beats strategy_c; 0 failures** |
| 10 | **strategy_e_sliding_window** | 29,819 | 11,605 | 0.7198 | 19,294 | 0.6072 | **0.6587** | **0** | 2nd best F1; very low FP |
| 11 | **strategy_e7_bg_refit** | 30,978 | 10,446 | 0.7478 | 25,745 | 0.5461 | 0.6313 | **0** | Background refit |
| 12 | **strategy_e** | 30,872 | 10,552 | 0.7453 | 25,995 | 0.5429 | 0.6282 | **0** | Base E family |
| 13 | **strategy_e_refractory** | 30,783 | 10,641 | 0.7431 | 23,536 | 0.5667 | 0.6430 | **0** | Refractory suppression |
| 14 | **strategy_e5_global_floor** | 30,811 | 10,613 | 0.7438 | 24,470 | 0.5574 | 0.6372 | **0** | Controlled FP floor |
| 15 | **strategy_e8_changepoint** | 30,517 | 10,907 | 0.7367 | 22,881 | 0.5715 | 0.6437 | **0** | Piecewise blocks |
| 16 | **strategy_e_slope_guard** | 30,588 | 10,836 | 0.7384 | 22,365 | 0.5776 | 0.6482 | **0** | Peak-in-middle filter |
| 17 | **strategy_e13_self_train** | 30,630 | 10,794 | 0.7394 | 21,749 | 0.5848 | 0.6531 | **0** | Self-training gate; ties strategy_c |
| 18 | **strategy_e_adaptive_k** | 30,434 | 10,990 | 0.7347 | 21,358 | 0.5876 | 0.6530 | **0** | Adaptive k; ties strategy_c |
| 19 | **strategy_e_duration_band** | 30,583 | 10,841 | 0.7383 | 23,724 | 0.5632 | 0.6389 | **0** | Duration [50ms, 500ms] filter |
| 20 | **strategy_a** | 30,733 | 10,691 | 0.7419 | 22,748 | 0.5747 | 0.6477 | **0** | Strong baseline |
| 21 | **strategy_e12_amp_filter** | 29,242 | 12,182 | 0.7059 | 19,147 | 0.6043 | 0.6512 | **0** | 2nd-iter best; beats strategy_a |
| 22 | **strategy_c** | 26,865 | 14,548 | 0.6487 | 14,007 | **0.6573** | 0.6530 | 1 | Best precision; 1 pair failure |
| 23 | **strategy_e_quantile_thr** | 24,474 | 16,950 | 0.5908 | 19,500 | 0.5566 | 0.5732 | **0** | Quantile threshold; lower recall |
| 24 | **strategy_d** | 25,095 | 16,318 | 0.6060 | 81,335 | 0.2358 | 0.3395 | 1 | Too many FP and 1 failure |
| 25 | **strategy_e_vote_2of3** | 16,569 | 24,855 | 0.4000 | 36,034 | 0.3150 | 0.3524 | **0** | Voting too strict for 3 channels |
| 26 | **strategy_b** | 15,357 | 26,067 | 0.3707 | 10,779 | 0.5876 | 0.4546 | **0** | Lowest recall |

**Step 1 recommendation:**
- If Step 1 is recall-first with no FP budget: choose **strategy_e4_multiscale** (or E3 for slightly lower FP).
- If best F1 with guaranteed reliability: choose **strategy_e_expand_bridge** ★ — **F1=0.6592**, beats strategy_c, 0 failures.
- If lowest FP with good F1: choose **strategy_e_sliding_window** — F1=0.6587, FP=19,294.
- If precision-favoring with 0 failures: choose **strategy_e12_amp_filter** — F1=0.6512, FP=19,147.
- If FP increase from E4 is not acceptable but recall is primary: choose **strategy_e5_global_floor**.

---

# Strategy E: Per-Epoch MAD Threshold (New Exploratory Pipeline)

**Implemented in:** `tutorial/23_strategy_e_step1_batch_all_subjects.py`
**Added to comparison:** `tutorial/22_strategy_comparison_batch.py`

## Design

Strategy E replaces autoreject's **per-epoch PTP (peak-to-peak)** feature with the
**BLINKER MAD-based threshold** computed independently for every epoch:

```
threshold_e = mean(epoch_e) + k × 1.4826 × MAD(epoch_e)
```

Parameters: `k = 1.5` (BLINKER default), `min_event_len = 0.05 s`.

Each epoch is scanned with **its own adaptive threshold** via threshold-crossing
detection (same logic as Strategy A / BLINKER). The key difference from Strategy A:

| | Strategy A | Strategy E |
|---|---|---|
| Statistics computed on | Full concatenated signal | Each epoch independently |
| Threshold scope | Global (one per channel) | Per-epoch (one per epoch × channel) |
| Adapts to signal drift | No | Yes |

## Results (65 pairs, 0 failures)

| Metric | Value |
|---|---|
| Total TP | 30,872 |
| Total FP | 25,995 |
| Total FN | **10,552** (lowest of all strategies) |
| Micro Precision | 0.5429 |
| Micro Recall | **0.7453** (highest of all strategies) |
| Micro F1 | 0.6282 |
| Macro Precision | 0.4874 |
| Macro Recall | 0.7072 |
| Macro F1 | 0.5574 |

## Analysis

- **Step 1 goal achieved:** Strategy E attains the **highest recall** (0.7453 micro)
  and **fewest false negatives** (10,552) across all five strategies, directly meeting
  the "high TP / low FN" objective.
- **Trade-off:** Higher FP than strategy_a (25,995 vs 22,748) due to per-epoch
  thresholds adapting down in quiet epochs, admitting more detections. F1 is lower
  than strategy_a (0.6282 vs 0.6477).
- **vs strategy_c:** Strategy E has higher recall but lower precision; strategy_c
  remains the best balanced performer (F1 = 0.6530). A step 2 post-processing pass
  (e.g., shape validation or inter-blink interval filtering) on strategy_e candidates
  could reduce FP while preserving the recall advantage.
- **Runs on all 65 pairs** (no failures, unlike strategy_c and strategy_d which each
  had 1 failure).

---

# Strategy E Derivative Variants: Exploratory Study

**Implemented in:** `tutorial/24_strategy_e_derivatives_step1_batch.py`
**Added to comparison:** `tutorial/22_strategy_comparison_batch.py`
**Design document:** `tutorial/strategy_e_derivative.md`

Five derivative variants of Strategy E were tested (Tier 1 roadmap):

## Variant Designs

| Variant | Formula | Key difference from E0 |
|---|---|---|
| **E1 (median)** | `median(epoch) + k * MAD(epoch)` | Replaces mean with median |
| **E2 (floor)** | E1 with `floor = global_med + 0.5 * global_MAD` | Adds weak noise floor (rarely active) |
| **E3 (hysteresis)** | Opens at `median + 1.5 * MAD`, closes at `median + 1.0 * MAD` | Dual-threshold per epoch |
| **E4 (multiscale)** | Union of k=1.0, 1.2, 1.5 detections merged within 80 ms | Multi-k union |
| **E5 (global floor)** | `median + k * MAD` per epoch, floored by `mean + k * global_MAD` | Strategy-A global threshold as minimum |

## Aggregate Results (65 pairs, 0 failures for all variants)

| Variant                 | Total TP | Total FP | Total FN | Micro Prec | Micro Recall | Micro F1 |
|-------------------------|----------|----------|----------|------------|--------------|----------|
| strategy_e (E0 baseline)| 30,872   | 25,995   | 10,552   | 0.5429     | 0.7453       | 0.6282   |
| E1 (median)             | 31,268   | 28,209   | 10,156   | 0.5257     | 0.7548       | 0.6198   |
| E2 (floor)              | 31,268   | 28,200   | 10,156   | 0.5258     | 0.7548       | 0.6198   |
| E3 (hysteresis)         | 31,708   | 37,642   |  9,716   | 0.4572     | **0.7654**   | 0.5725   |
| E4 (multiscale)         | 31,721   | 42,325   |  9,703   | 0.4284     | **0.7658**   | 0.5494   |
| **E5 (global floor)**   | 30,811   | 24,470   | 10,613   | **0.5574** | 0.7438       | **0.6372** |

For reference — prior strategies:

| Strategy          | Total TP | Total FP | Total FN | Micro Recall | Micro F1 |
|-------------------|----------|----------|----------|--------------|----------|
| strategy_a        | 30,733   | 22,748   | 10,691   | 0.7419       | 0.6477   |
| strategy_c (best) | 26,865   | 14,007   | 14,548   | 0.6487       | **0.6530** |

## Analysis

### E1 vs E0 (median replaces mean)
- Recall improves: 0.7548 vs 0.7453 (+0.0095)
- FN reduced: 10,156 vs 10,552 (−396 missed blinks)
- FP increases: 28,209 vs 25,995 (+2,214 extra detections)
- Net F1: **0.6198 < 0.6282** — recall gain doesn't offset FP increase
- Median is more stable against skewed epochs, but the extra FP from quiet epochs outweighs it

### E2 ≈ E1 (floor rarely active)
- With `FLOOR_K = 0.5`, the global floor = `global_med + 0.5 * global_MAD` is almost
  always below the per-epoch threshold → floor never activates
- Results are essentially identical to E1 across all 65 pairs

### E3 hysteresis — high recall, FP explosion
- **Best FN among all designs:** 9,716 (vs strategy_a 10,691 = 975 fewer missed blinks)
- But FP = 37,642 vs strategy_a 22,748 → 1.65× more false detections
- FP/TP ratio = 1.19 (vs strategy_a 0.74) — Step 2 would need to filter aggressively
- Wins on 2 individual pairs (S16) where blink events have noisy boundaries

### E4 multiscale — marginal FN improvement over E3 at higher FP cost
- Lowest FN of all: 9,703 (−988 vs strategy_a)
- FP = 42,325 → 1.86× strategy_a
- Not recommended unless Step 2 can handle the FP load

### E5 (global floor) — autonomous improvement
> **Motivation:** E1 adds FP in quiet epochs where the per-epoch threshold collapses.
> Setting `floor = global_mean + k * global_MAD` (Strategy A's formula) prevents
> collapse while preserving per-epoch adaptivity in noisy epochs.

- **Recall = 0.7438** — **beats strategy_a** (0.7419) with only a small FP overhead
- **F1 = 0.6372** — best among all E variants; only 0.0105 below strategy_a (0.6477)
- FP = 24,470 (vs strategy_a 22,748 = +1,722 extra) → well-controlled
- FN = 10,613 (vs strategy_a 10,691 = −78 fewer missed blinks)
- **0 failures across all 65 pairs**

E5 is the most balanced E derivative. It slightly outperforms strategy_a in recall (the Step 1
primary metric) while maintaining the reliability (no failures) of Strategy E.

## Recommended Step 1 Strategy (First Iteration)

| Goal | Best choice | Why |
|---|---|---|
| Maximum recall / minimum FN | **E4 (multiscale)** | Lowest FN=9,703, highest recall=0.7658, 0 failures |
| Maximum recall with slightly less FP | **E3 (hysteresis)** | FN=9,716, recall=0.7654, FP lower than E4 but still very high |
| Best practical recall / FP compromise | **E5 (global floor)** | 0 failures, recall above strategy_a, much smaller FP increase than E3/E4 |
| Best overall F1 | **strategy_c** | Highest F1, but 1 pair failure and weaker recall |

---

# Strategy E Second-Iteration Derivatives: Exploratory Study

**Design document:** `tutorial/strategy_e_derivative_2nd.md`
**Standalone pipeline:** `tutorial/25_strategy_e_2nd_derivatives_step1_batch.py`
**Added to comparison:** `tutorial/22_strategy_comparison_batch.py`

## Motivation

The first iteration established that:
- E family achieves higher recall than strategy_a but at a FP cost
- E5 (global floor) is the best practical E variant but still trails strategy_a on F1 (0.6372 vs 0.6477)
- No E variant beaten strategy_c (0.6530) on F1

The second iteration sought to improve **artifact discrimination** — not just better thresholding.

## New Variants (2nd Iteration)

| Variant | Key idea | Implemented in |
|---|---|---|
| **E6 (soft_shrink)** | alpha-weighted blend of local and global thresholds | `tutorial/22_strategy_comparison_batch.py` |
| **E7 (bg_refit)** | Two-pass: permissive scan → mask candidates → refit on background | `tutorial/22_strategy_comparison_batch.py` |
| **E9 (frontal_avg)** | Average all frontal channels into one virtual signal | `tutorial/22_strategy_comparison_batch.py` |
| **E10 (epoch_smooth)** | Triangular [0.25, 0.5, 0.25] smoothing of per-epoch thresholds | `tutorial/22_strategy_comparison_batch.py` |
| **E6+E10 (combined)** | E6 soft-shrinkage thresholds + E10 cross-epoch smoothing | `tutorial/22_strategy_comparison_batch.py` |
| **E12 (amp_filter)** ★ | E7 candidates + bottom-15% peak amplitude pruning | `tutorial/22_strategy_comparison_batch.py` |

## Aggregate Results (65 pairs, 0 failures for all variants)

| Variant                     | Total TP | Total FP | Total FN | Micro Prec | Micro Recall | Micro F1 |
|-----------------------------|----------|----------|----------|------------|--------------|----------|
| strategy_e (E0 baseline)    | 30,872   | 25,995   | 10,552   | 0.5429     | 0.7453       | 0.6282   |
| strategy_e5_global_floor    | 30,811   | 24,470   | 10,613   | 0.5574     | 0.7438       | 0.6372   |
| E6 (soft_shrink)            | 31,223   | 27,350   | 10,201   | 0.5331     | 0.7537       | 0.6245   |
| E7 (bg_refit)               | 30,978   | 25,745   | 10,446   | 0.5461     | 0.7478       | 0.6313   |
| E9 (frontal_avg)            | 30,642   | 26,673   | 10,782   | 0.5346     | 0.7397       | 0.6207   |
| E10 (epoch_smooth)          | 31,291   | 27,977   | 10,133   | 0.5280     | 0.7554       | 0.6215   |
| E6+E10 (combined)           | 31,268   | 27,187   | 10,156   | 0.5349     | 0.7548       | 0.6261   |
| **E12 (amp_filter)** ★      | **29,242** | **19,147** | **12,182** | **0.6043** | 0.7059 | **0.6512** |

For reference:

| Strategy          | Total TP | Total FP | Total FN | Micro Recall | Micro F1 |
|-------------------|----------|----------|----------|--------------|----------|
| **strategy_a**    | 30,733   | 22,748   | 10,691   | 0.7419       | 0.6477   |
| **strategy_c**    | 26,865   | 14,007   | 14,548   | 0.6487       | **0.6530** |

## Analysis

### E6, E7, E9, E10: diminishing returns on threshold tuning

All five threshold-only 2nd-iteration variants (E6, E7, E9, E10, E6+E10) follow the same pattern
as the first iteration: slightly higher recall at the cost of more FP, resulting in lower F1
than strategy_a. None beat strategy_a's F1 of 0.6477.

- **Best recall:** E10 (epoch_smooth) at 0.7554, but F1=0.6215
- **Best F1 among threshold variants:** E7 (bg_refit) at 0.6313 — closest but still -0.016 below strategy_a
- **Root cause:** per-epoch thresholding generates small-amplitude FP events near the global floor
  in quiet epochs; threshold adjustments alone cannot discriminate these from true blinks

### E12: the amplitude filter breakthrough

E12 applies a post-hoc amplitude percentile filter on top of E7 candidates:

1. **E7 background refit** generates high-recall candidates (same logic as E7)
2. **Peak amplitude gate**: for each channel, collect all candidate peak amplitudes and remove
   the bottom 15% — these small-amplitude events are predominantly noise in quiet epochs
   where the threshold collapsed to the global floor

**Results:**
- **Micro F1 = 0.6512** — beats strategy_a (0.6477) by +0.0035 ✓
- **0 failures** across all 65 pairs ✓
- **FP = 19,147** — 3,601 fewer FP than strategy_a (22,748) ✓
- **Recall = 0.7059** — lower than strategy_a (0.7419) because some genuine small blinks
  are removed by the amplitude gate
- **Micro F1 = 0.6512 vs strategy_c = 0.6530** — within 0.0018 of strategy_c, with 0 failures

> **Trade-off:** E12 improves precision significantly (0.6043 vs strategy_a 0.5747) at the cost of
> reduced recall (0.7059 vs 0.7419). The net result is better F1. This is a precision-favoring
> refinement, not a recall-first choice.

## Updated Recommended Step 1 Strategy (after 3rd iteration)

| Goal | Best choice | Why |
|---|---|---|
| Maximum recall / minimum FN | **E4 (multiscale)** | Lowest FN=9,703, highest recall=0.7658, 0 failures |
| Best balanced F1 with 0 failures | **E_expand_bridge** ★ | F1=0.6592, beats strategy_c, 0 failures |
| Best F1 with lowest FP | **E_sliding_window** | F1=0.6587, FP=19,294, 0 failures |
| Best practical recall / FP compromise | **E5 (global floor)** | 0 failures, recall above strategy_a, controlled FP |
| Best overall F1 (with 1 failure risk) | **strategy_c** | F1=0.6530, highest precision, but 1 pair failure |

---

# Strategy E: Third-Iteration Remaining Variants

**Design documents:** `tutorial/strategy_e_derivative.md` and `tutorial/strategy_e_derivative_2nd.md`
**Standalone pipeline:** `tutorial/26_strategy_e_remaining_batch.py`
**Added to comparison:** `tutorial/22_strategy_comparison_batch.py`

## Motivation

This iteration implements all remaining proposed variants from both design documents that were not yet tested. The goal was to identify any strategies capable of beating the current best (strategy_e12_amp_filter, F1=0.6512) or strategy_c (F1=0.6530).

## New Variants (3rd Iteration)

| Variant | Key idea | Source |
|---|---|---|
| **e_sliding_window** | Rolling 2-second median+MAD threshold within each epoch | strategy_e_derivative.md #3 |
| **e_or_fusion** | OR union of detections from all frontal channels | strategy_e_derivative.md #4a |
| **e_vote_2of3** | Keep candidates confirmed by ≥2 of 3 channels | strategy_e_derivative.md #4b |
| **e_expand_bridge** | Expand event boundaries to low threshold; bridge 80ms gaps | strategy_e_derivative.md #6 |
| **e_duration_band** | Reject events outside [50ms, 500ms] duration | strategy_e_derivative.md #7 |
| **e_slope_guard** | Peak must fall in middle 70% of event window | strategy_e_derivative.md #8 |
| **e_abs_polarity** | Detect on \|signal − epoch_median\|; polarity-agnostic | strategy_e_derivative.md #9 |
| **e_adaptive_k** | Scale k by ratio of global MAD to quiet-baseline (25th pct) MAD | strategy_e_derivative.md #10 |
| **e_quantile_thr** | T = max(93rd-pct of epoch, global_floor) | strategy_e_derivative.md #11 |
| **e_refractory** | 150ms minimum inter-onset suppression | strategy_e_derivative.md #14 |
| **e8_changepoint** | Piecewise 10-second block thresholds per epoch | strategy_e_derivative_2nd.md E8 |
| **e11_lane_route** | Cluster detections within 100ms; keep highest-amplitude per cluster | strategy_e_derivative_2nd.md E11 |
| **e13_self_train** | Conservative pass (k=2.0) sets amplitude gate for permissive pass (k=1.2) | strategy_e_derivative_2nd.md E13 |

## Aggregate Results (65 pairs, 0 failures for all variants)

| Variant | TP | FP | FN | Micro Precision | Micro Recall | Micro F1 |
|---|---:|---:|---:|---:|---:|---:|
| **e_expand_bridge** ★ | **30,901** | 21,428 | **10,523** | 0.5905 | **0.7460** | **0.6592** |
| **e_sliding_window** | 29,819 | **19,294** | 11,605 | **0.6072** | 0.7198 | 0.6587 |
| **e_adaptive_k** | 30,434 | 21,358 | 10,990 | 0.5876 | 0.7347 | 0.6530 |
| **e13_self_train** | 30,630 | 21,749 | 10,794 | 0.5848 | 0.7394 | 0.6531 |
| **e_slope_guard** | 30,588 | 22,365 | 10,836 | 0.5776 | 0.7384 | 0.6482 |
| **e8_changepoint** | 30,517 | 22,881 | 10,907 | 0.5715 | 0.7367 | 0.6437 |
| **e_refractory** | 30,783 | 23,536 | 10,641 | 0.5667 | 0.7431 | 0.6430 |
| **e_duration_band** | 30,583 | 23,724 | 10,841 | 0.5632 | 0.7383 | 0.6389 |
| **e_or_fusion** | 30,826 | 31,654 | 10,598 | 0.4934 | 0.7442 | 0.5934 |
| **e_quantile_thr** | 24,474 | 19,500 | 16,950 | 0.5566 | 0.5908 | 0.5732 |
| **e11_lane_route** | 31,049 | 37,081 | 10,375 | 0.4557 | 0.7495 | 0.5668 |
| **e_abs_polarity** | 32,915 | 110,940 | 8,509 | 0.2288 | 0.7946 | 0.3553 |
| **e_vote_2of3** | 16,569 | 36,034 | 24,855 | 0.3150 | 0.4000 | 0.3524 |

For reference:

| Strategy | TP | FP | FN | Micro Recall | Micro F1 | Failures |
|---|---:|---:|---:|---:|---:|---:|
| **strategy_a** | 30,733 | 22,748 | 10,691 | 0.7419 | 0.6477 | 0 |
| **strategy_c** | 26,865 | 14,007 | 14,548 | 0.6487 | 0.6530 | **1** |
| **strategy_e12_amp_filter** | 29,242 | 19,147 | 12,182 | 0.7059 | 0.6512 | 0 |

## Analysis

### strategy_e_expand_bridge — new best reliable performer

**Design:** For each E5-style detection, expand boundaries outward while signal > `median + 0.5*MAD` (low threshold), then bridge adjacent detections within 80ms. This improves temporal coverage of real blinks whose true extent spans below the main threshold.

**Results:**
- **Micro F1 = 0.6592** — new all-time best with 0 failures; beats strategy_c (0.6530) and strategy_e12_amp_filter (0.6512)
- **TP = 30,901** — highest among F1-competitive strategies; close to strategy_e's 30,872
- **FP = 21,428** — well-controlled; better than strategy_a (22,748)
- **Recall = 0.7460** — above strategy_a (0.7419) with fewer FP

This strategy achieves the best of both worlds: higher recall than strategy_c with higher F1 and no failures.

### strategy_e_sliding_window — second best F1

**Design:** Rolling 2-second window computes local median+MAD threshold at each sample within the epoch, floored by the global threshold. This provides finer-grained intra-epoch adaptation.

**Results:**
- **Micro F1 = 0.6587** — second best ever; 0 failures
- **FP = 19,294** — lowest among all high-recall strategies
- **Recall = 0.7198** — slightly lower than expand_bridge due to stricter local thresholds
- **Note:** Very slow — 285–365 seconds per pair due to Python-level sample-by-sample threshold computation

### strategy_e_adaptive_k and strategy_e13_self_train — tie strategy_c

Both achieve **micro F1 ≈ 0.6530** (matching strategy_c) with 0 failures:
- **adaptive_k**: scales the threshold multiplier k by the ratio of global-to-quiet MAD; works well on recordings with mixed noise levels
- **e13_self_train**: conservative pass sets amplitude gate; permissive pass detects more candidates filtered by that gate

### Strategies that degraded

| Strategy | Reason for poor performance |
|---|---|
| **e_abs_polarity** | FP=110,940 — detecting negative fluctuations dramatically inflates false positives |
| **e_vote_2of3** | FP=36,034, recall=0.4000 — with only 3 channels, 2-of-3 voting is too strict and too noisy simultaneously |
| **e_or_fusion** | FP=31,654 — OR-fusion inflates FP from all 3 channels without deduplication benefit |
| **e11_lane_route** | FP=37,081 — clustering does not reduce FP well when all channels detect similar artifacts |
| **e_quantile_thr** | Recall=0.5908 — 93rd percentile is too high on quiet pairs; misses many real blinks |

## Final Recommendations

| Goal | Best strategy | Micro F1 | Failures |
|---|---|---|---|
| **Best reliable F1** | **strategy_e_expand_bridge** ★ | **0.6592** | 0 |
| Best F1 + lowest FP | strategy_e_sliding_window | 0.6587 | 0 |
| Best recall with 0 failures | strategy_e4_multiscale | 0.5494 | 0 |
| Best recall with controlled FP | strategy_e_expand_bridge | 0.6592 | 0 |
| Best precision trade-off | strategy_e12_amp_filter | 0.6512 | 0 |
| Best F1 (failure allowed) | strategy_c | 0.6530 | 1 |

> **Summary:** The 3rd iteration decisively establishes **strategy_e_expand_bridge** as the new overall best pipeline for Step 1. It beats strategy_c's F1 of 0.6530 (the former best) by +0.0062, has 0 failures compared to strategy_c's 1, and achieves this with higher recall (0.7460 vs 0.6487) and lower FP than strategy_a.

---

# 4th Iteration: Expand-Bridge Derivatives

**Implemented in:** `tutorial/27_strategy_e_expand_bridge_derivatives_batch.py`
**Added to comparison:** `tutorial/22_strategy_comparison_batch.py`
**Baseline to beat:** `strategy_e_expand_bridge` — micro F1 = 0.6592, recall = 0.7460, FP = 21,428, failures = 0

## Design Summary

Six variants derived directly from `strategy_e_expand_bridge` per the roadmap in
`tutorial/strategy_e_expand_bridge_exploratory_plan.md`.

**Phase 1 — Low-risk refinements (change one idea at a time):**

| Variant | Core idea |
|---|---|
| `expand_bridge_dynamic_low` | T_low adapts to epoch noise: noisy epochs → higher T_low (less expansion) |
| `expand_bridge_dynamic_gap` | Bridge gap scales with candidate strength: strong–strong = 100ms, weak = 40ms |
| `expand_bridge_confidence_weighted` | Two-tier trust: strong candidates get aggressive expand+80ms bridge; weak get conservative+40ms |

**Phase 2 — Hybrid with neighboring variants (Tier 1 priority):**

| Variant | Core idea |
|---|---|
| `expand_bridge_sw_onset` | Sliding-window onset detector (cleaner starts) + expand+bridge boundary recovery |
| `expand_bridge_adaptive_k` | Adaptive-k for T_high (cleaner candidate pool) + standard expand+bridge |
| `expand_bridge_soft_gate` | Conservative pass learns amplitude gate; full expand+bridge filtered by that gate |

## Aggregate Results (all 65 pairs, 0 failures)

| Strategy | Successful | Failed | TP | FP | FN | Micro Precision | Micro Recall | Micro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **strategy_e_expand_bridge** (baseline ★) | 65 | 0 | 30,901 | 21,428 | 10,523 | 0.5905 | 0.7460 | **0.6592** |
| `expand_bridge_dynamic_low` | 65 | 0 | 30,873 | 21,464 | 10,551 | 0.5899 | 0.7453 | 0.6585 |
| `expand_bridge_dynamic_gap` | 65 | 0 | 30,753 | 21,356 | 10,671 | 0.5902 | 0.7424 | 0.6576 |
| `expand_bridge_confidence_weighted` | 65 | 0 | 30,550 | 21,722 | 10,874 | 0.5844 | 0.7375 | 0.6521 |
| **`expand_bridge_sw_onset`** ★★ | 65 | 0 | 29,928 | **17,168** | 11,496 | **0.6355** | 0.7225 | **0.6762** |
| **`expand_bridge_adaptive_k`** ★★ | 65 | 0 | 30,626 | 18,903 | 10,798 | 0.6183 | 0.7393 | **0.6734** |
| **`expand_bridge_soft_gate`** ★★ | 65 | 0 | 30,556 | **18,807** | 10,868 | 0.6190 | 0.7376 | **0.6731** |

> ★★ **Three new variants beat the previous best** (strategy_e_expand_bridge, F1=0.6592):
> - `expand_bridge_sw_onset`: **F1 = 0.6762** — new all-time best F1; FP drops from 21,428 → 17,168 (−20%)
> - `expand_bridge_adaptive_k`: **F1 = 0.6734**; FP = 18,903; recall = 0.7393
> - `expand_bridge_soft_gate`: **F1 = 0.6731**; FP = 18,807 (lowest among recall-competitive strategies); recall = 0.7376

## Success Criteria Evaluation

| Criterion | Minimum win | Strong win | sw_onset | adaptive_k | soft_gate |
|---|---|---|---|---|---|
| Micro F1 | > 0.6592 | >= 0.662 | **0.6762** ✓ | **0.6734** ✓ | **0.6731** ✓ |
| Failures | 0 | 0 | **0** ✓ | **0** ✓ | **0** ✓ |
| Recall | >= 0.7419 | >= 0.742 | 0.7225 ✗ | 0.7393 ~ | 0.7376 ~ |

All three pass the F1 and failure criteria for a **strong win**. Recall is slightly below the 0.7419 target — `adaptive_k` (0.7393) and `soft_gate` (0.7376) are close; `sw_onset` has a larger recall drop (0.7225) in exchange for the biggest FP reduction (−20%).

## Phase 1 Refinements Assessment

The three Phase 1 variants (`dynamic_low`, `dynamic_gap`, `confidence_weighted`) did **not** beat the baseline — they score F1 = 0.6521–0.6585 vs 0.6592 baseline. The differences are small and within noise. Key observations:
- `dynamic_low` is essentially a wash with the baseline (0.6585 vs 0.6592)
- `dynamic_gap` reduces FP slightly (21,356 vs 21,428) but also recall, keeping F1 flat
- `confidence_weighted` slightly hurts both recall and FP — the two-tier approach may need tuning

## Key Observations

### expand_bridge_sw_onset — new F1 champion
The plan predicted this would be Tier 1: "sliding_window has much lower FP than expand_bridge; expand_bridge may recover part of that lost recall." This is exactly what happened:
- FP drops from 21,428 → 17,168 (−20%) — inheriting sliding_window's precision advantage
- Recall drops from 0.7460 → 0.7225 — boundary recovery partially compensates but not fully
- Net result: F1 gains +0.017 (0.6762 vs 0.6592)

Per-pair winner analysis shows `sw_onset` wins most pairs where `sliding_window` previously had an advantage over `expand_bridge`.

### expand_bridge_adaptive_k and expand_bridge_soft_gate — best recall-F1 balance
Both variants keep recall close to the baseline (0.7376–0.7393 vs 0.7460) while cutting FP by ~12%:
- `adaptive_k`: 18,903 FP vs 21,428 (−12%); recall = 0.7393; F1 = 0.6734
- `soft_gate`: 18,807 FP vs 21,428 (−12%); recall = 0.7376; F1 = 0.6731

These are the best candidates if the Step 1 role requires recall >= 0.74.

## Updated Ranking (F1-ordered)

| Rank | Strategy | TP | FP | FN | Recall | F1 | Failures |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | **expand_bridge_sw_onset** ★★ | 29,928 | 17,168 | 11,496 | 0.7225 | **0.6762** | **0** |
| 2 | **expand_bridge_adaptive_k** ★★ | 30,626 | 18,903 | 10,798 | 0.7393 | **0.6734** | **0** |
| 3 | **expand_bridge_soft_gate** ★★ | 30,556 | 18,807 | 10,868 | 0.7376 | **0.6731** | **0** |
| 4 | strategy_e_expand_bridge ★ | 30,901 | 21,428 | 10,523 | 0.7460 | 0.6592 | **0** |
| 5 | strategy_e_sliding_window | 29,819 | 19,294 | 11,605 | 0.7198 | 0.6587 | **0** |
| 6 | expand_bridge_dynamic_low | 30,873 | 21,464 | 10,551 | 0.7453 | 0.6585 | **0** |
| 7 | expand_bridge_dynamic_gap | 30,753 | 21,356 | 10,671 | 0.7424 | 0.6576 | **0** |
| 8 | strategy_e13_self_train | 30,630 | 21,749 | 10,794 | 0.7394 | 0.6531 | **0** |
| 9 | strategy_e_adaptive_k | 30,434 | 21,358 | 10,990 | 0.7347 | 0.6530 | **0** |
| 10 | strategy_c | 26,865 | 14,007 | 14,548 | 0.6487 | 0.6530 | 1 |
| 11 | expand_bridge_confidence_weighted | 30,550 | 21,722 | 10,874 | 0.7375 | 0.6521 | **0** |
| 12 | strategy_e12_amp_filter | 29,242 | 19,147 | 12,182 | 0.7059 | 0.6512 | **0** |
| 13 | strategy_a (reference) | 30,733 | 22,748 | 10,691 | 0.7419 | 0.6477 | **0** |

## Recommendations After 4th Iteration

| Goal | Best strategy | Micro F1 | FP | Recall | Failures |
|---|---|---|---|---|---|
| **Best F1 ever** | **expand_bridge_sw_onset** ★★ | **0.6762** | 17,168 | 0.7225 | 0 |
| **Best F1 + keep recall > 0.739** | **expand_bridge_adaptive_k** ★★ | **0.6734** | 18,903 | 0.7393 | 0 |
| **Lowest FP among high-F1** | **expand_bridge_soft_gate** ★★ | **0.6731** | 18,807 | 0.7376 | 0 |
| Best recall with F1 > 0.659 | strategy_e_expand_bridge | 0.6592 | 21,428 | 0.7460 | 0 |
| Best precision (no failures) | strategy_e12_amp_filter | 0.6512 | 19,147 | 0.7059 | 0 |

## Next Steps (5th Iteration)

The top three 4th-iteration variants are strong enough to investigate second-round hybrids:

1. **`expand_bridge_sw_onset_soft_gate`** — combine cleaner onset from sw_onset with amplitude gate; target: recover some of the recall loss without giving back the FP reduction
2. **`expand_bridge_adaptive_k_soft_gate`** — already excellent; adding soft gate should trim the remaining weak-FP tail
3. **Investigate recall gap of sw_onset** — identify which pair-level regressions drive the recall drop from 0.7460 → 0.7225; if they cluster on specific subjects, a targeted fallback rule may recover most of it

---

# Per-Pair F1 Comparison

Below is a cleaned table format for the per-subject segment comparison.

## Example Formatting Pattern

Use this structure consistently for all rows:

| Subject | Segment               |      A |          B |          C |      D | Winner         |
| ------- | --------------------- | -----: | ---------: | ---------: | -----: | -------------- |
| S1      | S01_20170519_043933   | 0.4361 |     0.6576 | **0.7832** | 0.1783 | **strategy_c** |
| S1      | S01_20170519_043933_2 | 0.5184 |     0.6649 | **0.7790** | 0.1872 | **strategy_c** |
| S1      | S01_20170519_043933_3 | 0.4170 |     0.0099 | **0.5748** | 0.2573 | **strategy_c** |
| S10     | S23_20181226_042222   | 0.4226 |     0.7251 | **0.7672** | 0.1845 | **strategy_c** |
| S10     | S23_20181226_042222_2 | 0.7415 | **0.8161** |     0.8120 | 0.4480 | **strategy_b** |
| S10     | S23_20181226_042222_3 | 0.6104 |     0.0000 | **0.6549** | 0.6230 | **strategy_c** |

---




