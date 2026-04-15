
## 7. Validation strategy

The new approach is considered correct if, after randomly dropping epochs and rerunning the epoch-aware pipeline, the resulting blink detections on the remaining valid epochs remain highly similar to the reference annotations in `sample_data/dev_epo_annotations.csv`.

### Validation procedure

1. Load `sample_data/dev_epo.fif`
2. Randomly mark or simulate a subset of epochs as bad
3. Run the new epoch-aware pipeline
4. Filter `sample_data/dev_epo_annotations.csv` to the same retained epoch set
5. Compare predicted blink events against the filtered reference
6. Repeat across multiple random seeds and drop ratios

### Suggested drop ratios

* 10%
* 20%
* 30%
* 40%

### Suggested seeds

* at least 10 fixed seeds

### Event matching rule

A predicted blink matches a reference blink if:

* it belongs to the same `epoch_index`
* onset difference is within 50 to 100 ms
* duration difference is within 50 to 100 ms, or temporal overlap is sufficiently high

### Metrics

Compute:

* precision
* recall
* F1 score
* epoch-level blink/no-blink agreement
* blink-count agreement per epoch

### Acceptance target

* **Primary target: F1 >= 0.90**

Because candidate channel selection may shift slightly after dropping epochs, exact event identity is not required. High event-level similarity is the target.

---