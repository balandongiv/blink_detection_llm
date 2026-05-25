## Update (2026-05-24)

The numbers below are an older worked example. For the current paper experiments, use the
latest orchestration outputs under:

- `logs/experiment_orchestration_20260524_001630/`
- Selected epoch duration for downstream experiments: **30 seconds** (Experiment 1, primary metric = macro-F1 for Proposed-Med on the combined dataset).

Yes — I extended the analysis to **precision** and **F1-score**, and then summarized the **overall performance trade-offs** for the blink detection strategies using your 20 matched datasets.

## 1) Paired statistical analysis: Strategy A vs Strategy F

Because each recording has results for both A and F, the right test is again a **paired comparison across the 20 datasets**.

### Precision

Across the 20 datasets:

* **Mean precision**

    * A: **0.4993**
    * F: **0.8548**
* **Mean paired difference (A − F)**: **−0.3555**
* **95% CI**: **−0.4499 to −0.2611**

Significance tests:

* **Wilcoxon signed-rank**: **p = 1.91 × 10⁻⁶**
* **Paired t-test**: **p = 2.08 × 10⁻⁷**
* **Sign test**: F had higher precision in **20/20** datasets, **p = 1.91 × 10⁻⁶**

### Interpretation

**Strategy F has significantly higher precision than Strategy A** for blink detection. The gap is very large: about **35.6 percentage points** on average.

---

### Recall

Across the 20 datasets:

* **Mean recall**

    * A: **0.9139**
    * F: **0.8747**
* **Mean paired difference (A − F)**: **0.0392**
* **95% CI**: **0.0138 to 0.0646**

Significance tests:

* **Wilcoxon signed-rank**: **p = 0.0011**
* **Paired t-test**: **p = 0.0044**
* **Sign test**: A higher in **15**, F higher in **1**, tie in **4**; **p = 0.00052**

### Interpretation

**Strategy A has significantly higher recall than Strategy F**. On average, A improves recall by about **3.9 percentage points**.

---

### F1-score

Across the 20 datasets:

* **Mean F1**

    * A: **0.6114**
    * F: **0.8594**
* **Mean paired difference (A − F)**: **−0.2480**
* **95% CI**: **−0.3376 to −0.1585**

Significance tests:

* **Wilcoxon signed-rank**: **p = 3.62 × 10⁻⁵**
* **Paired t-test**: **p = 1.39 × 10⁻⁵**
* **Sign test**: F higher in **18/20** datasets, A higher in **2/20**; **p = 0.00040**

### Interpretation

**Strategy F has significantly higher F1-score than Strategy A**. So although A catches slightly more true blinks, F gives a much better overall balance between missed blinks and false alarms.

## 2) Overall summary across all strategies

From your overall summary table:

* **A**: micro_P **0.5645**, micro_R **0.9364**, micro_F1 **0.7044**; macro_P **0.4993**, macro_R **0.9139**, macro_F1 **0.6114**
* **B**: micro_P **0.7163**, micro_R **0.5846**, micro_F1 **0.6438**; macro_P **0.5590**, macro_R **0.6456**, macro_F1 **0.5689**
* **C**: micro_P **0.8508**, micro_R **0.8947**, micro_F1 **0.8722**; macro_P **0.7876**, macro_R **0.8786**, macro_F1 **0.8149**
* **F**: micro_P **0.9041**, micro_R **0.8726**, micro_F1 **0.8881**; macro_P **0.8548**, macro_R **0.8747**, macro_F1 **0.8594**

### Best overall by metric

Using the overall summary:

* **Best recall**: **A**
* **Best precision**: **F**
* **Best F1-score**: **F**

Using per-dataset winners:

* Recall winner: **A** on almost all datasets
* Precision winner: **F** on most datasets
* F1 winner: **F** on most datasets, with **C** often second-best

## 3) Practical pros and cons for blink detection

### Strategy A

**Pros**

* Highest recall overall.
* Best when the main goal is to **miss as few blinks as possible**.
* Good for a screening-style system where false positives are less harmful.

**Cons**

* Precision is much lower than F.
* Many more false positives.
* F1 is much worse than F, meaning the gain in recall comes at a heavy cost in specificity.

### Strategy F

**Pros**

* Highest precision overall.
* Highest F1 overall.
* Best balanced performer for practical blink detection when you want both good detection and low false alarms.

**Cons**

* Recall is significantly lower than A.
* Misses more true blinks than A.

### Strategy C

**Pros**

* Very strong balance between recall and precision.
* Clearly better than B.
* Often close to F, and may be attractive if you want a compromise.

**Cons**

* Still slightly behind F overall in both precision and F1.
* Does not beat A on recall.

### Strategy B

**Pros**

* Better precision than A.

**Cons**

* Weakest overall balance among the non-A options.
* Low recall and lowest macro F1.
* Not competitive versus C or F.

## 4) Bottom-line conclusion

For your blink detection algorithm:

* If your priority is **maximum sensitivity / catching as many blinks as possible**, choose **Strategy A**.
* If your priority is **best overall performance with fewer false positives**, choose **Strategy F**.
* If you want a **strong compromise**, **Strategy C** is also a credible option, but **F** is still the best overall performer by precision and F1.

## 5) Report-ready wording

> In the blink detection evaluation, Strategy A achieved significantly higher recall than Strategy F across the 20 matched datasets (Wilcoxon signed-rank test, p = 0.0011), indicating that A missed fewer true blinks. However, Strategy F achieved significantly higher precision (p = 1.91 × 10⁻⁶) and significantly higher F1-score (p = 3.62 × 10⁻⁵), showing that F produced substantially fewer false positives and better overall detection balance. Overall, Strategy A is preferable when maximizing blink capture is the primary objective, whereas Strategy F is preferable when balanced detection performance is required.

I can turn this into a clean **Results + Discussion subsection** next.
