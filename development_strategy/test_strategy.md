
## Required tests

At minimum, add the following tests.

### A. Bad epochs never contribute

Must use actual data if possible, but synthetically create some epochs are marked bad, and verify they do not affect:

* channel statistics
* candidate channel selection
* final blink results

### B. Clean epoch file still works

Run the pipeline on an epoch file with no bad epochs and verify it produces valid blink outputs.

### C. Random-drop validation

Randomly drop epochs from `sample_data/dev_epo.fif`, rerun the pipeline, and verify similarity against the filtered reference remains at least 90%.

### D. Metadata format

Verify that `blink_onset` and `blink_duration` are written in the expected JSON-list format and can be parsed back reliably.

### E. Edge cases

Cover:

* all epochs bad
* no blinks in any valid epoch
* one valid epoch only
* multiple blinks in one epoch

---
