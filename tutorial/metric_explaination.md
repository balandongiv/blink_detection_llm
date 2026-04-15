Here’s what **TP, FP, FN, TN** mean for **blink detection**:

---

## Confusion matrix meanings

| Term   | Meaning in blink detection                        | Example                           |
| ------ | ------------------------------------------------- | --------------------------------- |
| **TP** | **True Positive** → real blink correctly detected | actual blink detected as blink    |
| **FP** | **False Positive** → non-blink detected as blink  | noise spike marked as blink       |
| **FN** | **False Negative** → real blink missed            | actual blink not detected         |
| **TN** | **True Negative** → non-blink correctly ignored   | normal EEG segment left untouched |

---

## Simple example

Imagine 200 signal events:

* real blinks = **150**
* real non-blinks = **50**

Your detector outputs:

* TP = **135**
* FP = **30**
* FN = **15**
* TN = **20**

That means:

* **135 real blinks found**
* **30 fake blink detections**
* **15 blinks missed**
* **20 non-blinks correctly rejected**

---

## Visual layout

|                      | Predicted Blink | Predicted Non-Blink |
| -------------------- | --------------: | ------------------: |
| **Actual Blink**     |              TP |                  FN |
| **Actual Non-Blink** |              FP |                  TN |

---

## Most useful formulas

### Precision

“How many detected blinks were actually real?”

[
\text{Precision} = \frac{TP}{TP+FP}
]

\text{Precision}=\frac{TP}{TP+FP}

---

### Recall

“How many real blinks did we catch?”

[
\text{Recall} = \frac{TP}{TP+FN}
]

\text{Recall}=\frac{TP}{TP+FN}

---

### Accuracy

Overall correctness:

[
\text{Accuracy} = \frac{TP+TN}{TP+FP+FN+TN}
]

\text{Accuracy}=\frac{TP+TN}{TP+FP+FN+TN}

---

### F1 score

Best overall blink detection balance:

[
F1 = \frac{2TP}{2TP+FP+FN}
]

F1=\frac{2TP}{2TP+FP+FN}

---

For **blink detection**, usually the most important are:

* **high recall** → don’t miss blinks
* **good precision** → avoid false blink artifacts

If you give me your TP/FP/FN/TN numbers, I can calculate the exact metrics.
