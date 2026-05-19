# Blink Detection Metrics

This document explains what **TP**, **FP**, **FN**, and **TN** mean for blink
detection, then shows the most useful evaluation formulas.

---

## Confusion Matrix Terms

| Term   | Full name      | Meaning in blink detection       | Example                           |
| ------ | -------------- | -------------------------------- | --------------------------------- |
| **TP** | True positive  | Real blink correctly detected    | Actual blink detected as blink    |
| **FP** | False positive | Non-blink detected as blink      | Noise spike marked as blink       |
| **FN** | False negative | Real blink missed                | Actual blink not detected         |
| **TN** | True negative  | Non-blink correctly ignored      | Normal EEG segment left untouched |

---

## Simple Example

Imagine 200 signal events:

- real blinks = **150**
- real non-blinks = **50**

Your detector outputs:

- TP = **135**
- FP = **30**
- FN = **15**
- TN = **20**

That means:

- **135 real blinks found**
- **30 false blink detections**
- **15 blinks missed**
- **20 non-blinks correctly rejected**

---

## Confusion Matrix Layout

|                      | Predicted Blink | Predicted Non-Blink |
| -------------------- | --------------: | ------------------: |
| **Actual Blink**     |              TP |                  FN |
| **Actual Non-Blink** |              FP |                  TN |

---

## Metric Formulas

### Precision

Precision answers: how many detected blinks were actually real?

```math
\text{Precision} = \frac{TP}{TP + FP}
```

With the example values:

```math
\text{Precision} = \frac{135}{135 + 30} = 0.8182
```

---

### Recall

Recall answers: how many real blinks did the detector catch?

```math
\text{Recall} = \frac{TP}{TP + FN}
```

With the example values:

```math
\text{Recall} = \frac{135}{135 + 15} = 0.9000
```

---

### Accuracy

Accuracy measures overall correctness across blink and non-blink events.

```math
\text{Accuracy} = \frac{TP + TN}{TP + FP + FN + TN}
```

With the example values:

```math
\text{Accuracy} = \frac{135 + 20}{135 + 30 + 15 + 20} = 0.7750
```

---

### F1 Score

F1 score balances precision and recall.

```math
F1 = \frac{2TP}{2TP + FP + FN}
```

With the example values:

```math
F1 = \frac{2 \cdot 135}{2 \cdot 135 + 30 + 15} = 0.8571
```

---

## Practical Priority For Blink Detection

For blink detection, the most important metrics are usually:

- **high recall**: avoid missing real blinks
- **good precision**: avoid false blink artifacts

Use recall when Step 1 is meant to be a candidate generator. Use precision and
F1 when comparing final cleaned detector outputs.
