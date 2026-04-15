from __future__ import annotations

from pathlib import Path
import sys
from time import perf_counter

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.epoch_detection_strategy_a.epoch_validation import (
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.epoch_detection_strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    epoch_detection_strategy_c_autoreject,
)
from tutorial.strategy_c_autoreject_first_5_epochs_common import (
    REFERENCE_PATH,
    load_first_5_epochs,
)


DISABLE_BACKBONE_CHANNELS = ("__NO_BACKBONE__",)


def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        existing = [column for column in columns if column in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


def main() -> None:
    print(f"script={Path(__file__).name}")
    print("variant=All EEG channels + no weighted frontal backbone / Bayesian Optimization")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"stage1_channels={DISABLE_BACKBONE_CHANNELS}")
    print(f"autoreject_method={AUTOREJECT_BAYESIAN_OPTIMIZATION}")

    epochs = load_first_5_epochs()
    reference = load_reference_blink_table(REFERENCE_PATH)

    started = perf_counter()
    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=1.0,
        filter_high=20.0,
        resample_rate=None,
        n_jobs=1,
        use_multiprocessing=False,
        stage1_channels=DISABLE_BACKBONE_CHANNELS,
        stage1_threshold_scope="per_channel",
        autoreject_random_state=42,
        autoreject_method=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        autoreject_augment=False,
    )
    annotations, channel, n_good_blinks, blink_table, _fig_data, selected_channel, _epochs = (
        detector.get_blink()
    )
    elapsed_s = perf_counter() - started
    metrics = match_blink_tables(blink_table, reference, n_epochs=len(epochs))

    print("\n=== Run Result ===")
    print(f"elapsed_s={elapsed_s:.6f}")
    print(f"selected_channel={channel}")
    print(f"n_good_blinks={n_good_blinks}")
    print(f"annotation_count={len(annotations)}")
    print(f"stage1_threshold_scope={detector.stage1_threshold_scope_}")
    print(f"stage1_threshold_learning_api={detector.stage1_threshold_learning_api_}")
    print(f"stage1_autoreject_method={detector.stage1_autoreject_method_}")
    print(f"stage1_channels={detector.stage1_channel_names_}")
    print(f"stage1_backbone_built={detector.stage1_backbone_signal_ is not None}")
    print(f"stage1_backbone_channels={detector.stage1_backbone_channels_}")
    print(f"stage1_thresholds={detector.stage1_thresholds_}")
    print(f"stage1_scan_threshold_scale={detector._get_stage1_scan_threshold_scale()}")
    print(f"stage1_candidate_count={len(detector.stage1_candidates_)}")
    print(f"stage1_rescue_candidate_count={len(detector.stage1_rescue_candidates_)}")

    print_frame("Representative Stage 1 Lanes", detector.stage1_representative_channels_)
    print_frame("Selected Channel Summary", selected_channel)
    print_frame(
        "Predicted Blinks",
        blink_table,
        ["epoch_index", "channel", "blink_onset", "blink_duration", "epoch_selection"],
    )

    print("\n=== Metrics Against Reference ===")
    print(
        {
            "true_positives": metrics.true_positives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "epoch_blink_agreement": metrics.epoch_blink_agreement,
            "blink_count_agreement": metrics.blink_count_agreement,
        }
    )


if __name__ == "__main__":
    main()
