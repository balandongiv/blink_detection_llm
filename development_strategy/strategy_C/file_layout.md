
## Suggested file layout
Our focus is using the autorject or its derivative as the core blink detection algorithm in Step 1, but we will need to build a custom pipeline around it for the full epoch detection strategy. Below is a suggested file layout to organize the code and tests for Strategy C development:
Under strategy C, there can be multiple sub-approaches for Step 1, so we can create separate subdirectories for each approach to keep the code organized. The `scripts` directory can contain exploratory and validation scripts, while the `test` directory can contain unit tests for each approach.
The folder structure might look like this:
for different `<sub_step1_approach>`, we can have separate directories under `pyblinker/epoch_detection_strategy_c/` to keep the code organized. Each approach can have its own pipeline, channel processor, result aggregation, metadata export, validation, and utility functions. The `scripts` directory can contain exploratory and validation scripts, while the `test` directory can contain unit tests for each approach.
The `<sub_step1_approach>` means different variations of the Step 1 algorithm, such as different windowing strategies, different local vs whole-head approaches, or different thresholding techniques. This way, we can keep the code for each approach separate and easily test and compare them.
```text
pyblinker/
   epoch_detection_strategy_c_<sub_step1_approach>/
      epoch_blink_pipeline.py
      epoch_channel_processor.py
      epoch_result_aggregation.py
      epoch_metadata_export.py
      epoch_validation.py
      bad_epoch_utils.py



test/
    epoch_detection_strategy_c_<sub_step1_approach>/
      test_bad_epochs_are_excluded.py
      test_epoch_pipeline_matches_reference.py
      test_epoch_metadata_export.py
      test_random_drop_similarity.py
      
```
# autoreject
The auroreject package is available at `autoreject/autoreject`