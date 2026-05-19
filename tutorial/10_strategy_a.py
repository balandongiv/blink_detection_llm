"""Strategy A — Step 1 inspection tutorial.

This tutorial runs Strategy A **Step 1 only**: blink candidate detection via
``get_blink_position`` concatenated across valid epochs, followed by per-channel
lane scoring against a human-annotated ground truth.

Evaluation is performed with the ``blink_evaluation`` library using IoU-based
event matching (``iou_threshold=0.1``).
"""

from __future__ import annotations

from pathlib import Path
import sys

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_annotations
from blink_evaluation.io import dataframe_to_annotations

from src.common.bad_epochs import get_valid_epoch_indices
from src.strategy_a.kleifges_blinker_2017 import kleifges_strategy_a
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference

FIF_PATH = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif"
)
CSV_PATH = Path(
    r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg\S1\S01_20170519_043933\ear_eog.csv"
)
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
IOU_THRESHOLD = 0.1
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Set to a positive integer to process only the first N epochs (useful for quick inspection).
N_EPOCHS: int | None = None


def main() -> None:
    print("\n=== Blinking Strategy A ===")
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )

    print(f"Total epochs: {len(epochs)}")

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)

    # Find the blink candidates
    channel_results = kleifges_strategy_a(prepared, valid_epoch_indices)

    ground_truth_df = enrich_absolute_times(
        load_annotation_as_reference(CSV_PATH, EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )
    gt_annotations = dataframe_to_annotations(ground_truth_df)

    lane_rows: list[dict] = []
    best_channel: str | None = None
    best_eval_result = None

    for cr in channel_results:
        predicted_df = enrich_absolute_times(cr["mapped_candidates"], EPOCH_DURATION_S)
        pred_annotations = dataframe_to_annotations(predicted_df)

        result = evaluate_annotations(
            gt_annotations,
            pred_annotations,
            target_label="blink",
            iou_threshold=IOU_THRESHOLD,
        )

        em = result.event_metrics
        lane_rows.append(
            {
                "channel": cr["channel"],
                "raw_candidate_count": int(len(cr["df_positions"])),
                "mapped_candidate_count": int(len(cr["mapped_candidates"])),
                "tp": em.tp,
                "fp": em.fp,
                "fn": em.fn,
                "precision": em.precision,
                "recall": em.recall,
                "f1": em.f1,
            }
        )

        if best_eval_result is None or (
            em.f1,
            em.tp,
            -em.fp,
            cr["channel"],
        ) > (
            best_eval_result.event_metrics.f1,
            best_eval_result.event_metrics.tp,
            -best_eval_result.event_metrics.fp,
            best_channel,
        ):
            best_channel = cr["channel"]
            best_eval_result = result

    lane_summary = (
        pd.DataFrame(lane_rows)
        .sort_values(["f1", "tp", "fp", "channel"], ascending=[False, False, True, True])
        .reset_index(drop=True)
    )

    m = best_eval_result.event_metrics
    print(f"\nbest_channel={best_channel}")
    print(f"tp={m.tp}  fp={m.fp}  fn={m.fn}")
    print(f"precision={m.precision:.4f}  recall={m.recall:.4f}  f1={m.f1:.4f}")
    print(f"\n=== Lane Summary (top 10) ===")
    print(lane_summary.head(10).to_string(index=False))
    print(f"\n=== Best Channel Predicted Blinks (first 20) ===")


if __name__ == "__main__":
    main()
