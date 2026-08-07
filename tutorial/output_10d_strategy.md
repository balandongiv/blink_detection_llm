## Strategy Results: `dbo_drop`

**Centering method:** `median`  
**Total epochs analysed:** 59

---

### Stage A — Epoch Screening

Autoreject was applied using Bayesian optimization.

- **Valid epochs screened:** 59
- **Epochs exceeding the peak-to-peak threshold:** 19 / 59 (**32.2%**)

<details>
<summary>Flagged epoch indices</summary>

`[0, 34, 37, 38, 40, 41, 42, 43, 44, 45, 47, 49, 50, 52, 53, 54, 55, 56, 57]`

</details>

---

### Stage B — Threshold Estimation

Thresholds were estimated using the **19 flagged epochs only**.

**Threshold formula**

\[
\text{Threshold} = \text{Median} + 3.5 \times (1.4826 \times \text{MAD})
\]

| Channel | Threshold | Center | Dispersion |
|:--|--:|--:|--:|
| E23 | 0.000020 | -0.000000 | 0.000006 |
| E24 | 0.000019 | -0.000000 | 0.000005 |
| E33 | 0.000017 | -0.000000 | 0.000005 |
| **E22** | **0.000029** | -0.000000 | **0.000008** |

> **Region-level blink threshold:** `0.000029`  
> Derived from the channel with the highest estimated threshold: **E22**

---

## Best Detection Channel

### **E22**

| True Positives | False Positives | False Negatives |
|--:|--:|--:|
| 134 | 15 | 4 |

| Precision | Recall | F1-score |
|--:|--:|--:|
| 0.8993 | **0.9710** | **0.9338** |

> E22 achieved very high recall, missing only **4 of 138** reference blink events, while maintaining strong precision.

---

## Channel-Level Performance

| Rank | Channel | Raw Candidates | Mapped Candidates | TP | FP | FN | Precision | Recall | F1-score |
|--:|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | **E22** | 149 | 149 | 134 | 15 | 4 | 0.8993 | **0.9710** | **0.9338** |
| 2 | E23 | 122 | 122 | 97 | 25 | 41 | 0.7951 | 0.7029 | 0.7462 |
| 3 | E24 | 44 | 44 | 34 | 10 | 104 | 0.7727 | 0.2464 | 0.3736 |
| 4 | E33 | 81 | 81 | 0 | 81 | 138 | 0.0000 | 0.0000 | 0.0000 |

---

## Key Interpretation

- **E22 is the clearly dominant blink-detection channel**, achieving an F1-score of **0.9338**.
- The method has **excellent sensitivity** at E22, with a recall of **97.10%**.
- **E23 provides moderate backup performance**, but its recall is substantially lower than E22.
- **E24 detects relatively few true blinks**, leading to poor recall.
- **E33 is not suitable for blink detection** in this recording, as all 81 detections were false positives.