"""Kleifges approach inspection tutorial for a single FIF file.

This tutorial runs the Kleifges approach **Step 1 only** on a single FIF file:
blink candidate detection via ``get_blink_position`` concatenated across valid
epochs, followed by per-channel lane scoring against a human-annotated ground
truth.

It intentionally stops after ``evaluate_channel_lanes`` and prints a compact
summary to stdout.  The downstream refinement steps (MAD-based epoch filtering,
multi-channel voting, blink-table normalization, and annotation export) are not
exercised here — see ``tutorial/32_strategy_a_step1_peak_overlap_fn_report.py``
for a full FN analysis report that continues from the same scoring point.
"""

from __future__ import annotations

import pickle
from pathlib import Path
import sys

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import (
    build_annotations_from_events,
    build_events_masterlist_df,
    evaluate_channels,
    load_ground_truth_annotations,
    save_scored_annotations_csv,
)
from blink_evaluation.blink_epoch_report import create_blink_epoch_report
from src.common.bad_epochs import get_valid_epoch_indices
from src.strategy_kleifges.kleifges_blinker_2017 import (
    kleifges_strategy,
)
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels

FIF_PATH = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif"
)
CSV_PATH = Path(
    r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg\S1\S01_20170519_043933\ear_eog.csv"
)
PICKLE_DIR = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\annotation_prediction"
)
ANNOTATION_CSV = PICKLE_DIR / "ear_eog_predicted_kleifges.csv"
MASTERLIST_CSV = PICKLE_DIR / "blink_events_masterlist_kleifges.csv"
REPORT_PATH = PICKLE_DIR / "blink_epoch_report_kleifges.html"
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 30.0
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None

# Set to a positive integer to process only the first N epochs from this single FIF file
# (useful for quick inspection).
N_EPOCHS: int | None = None


def main() -> None:
    print("\n=== Blinking Kleifges Approach ===")
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    brain_channels=["E3"]
    raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    predicted_annotations = kleifges_strategy(prepared, valid_epoch_indices)
    gt_annotations = load_ground_truth_annotations(CSV_PATH, EPOCH_DURATION_S)

    # -- Save inputs for blink_evaluation development -------------------------
    # PICKLE_DIR.mkdir(parents=True, exist_ok=True)
    # eval_inputs = {
    #     "channel_results": predicted_annotations,
    #     "gt_annotations": gt_annotations,
    #     "epoch_duration": EPOCH_DURATION_S,
    #     "peak_required": True,
    #     "peak_tolerance": 0.1,
    #     "fif_path": str(FIF_PATH),
    # }
    # pickle_path = PICKLE_DIR / "kleifges_eval_inputs.pkl"
    # with open(pickle_path, "wb") as f:
    #     pickle.dump(eval_inputs, f)
    # print(f"Eval inputs pickled: {pickle_path}")
    # -------------------------------------------------------------------------

    scored = evaluate_channels(
        predicted_annotations,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
        peak_required=True,
        peak_tolerance=0.1,
    )

    em = scored.best_eval_result.event_metrics
    print(f"\nbest_channel={scored.best_channel}")
    print(f"tp={em.tp}  fp={em.fp}  fn={em.fn}")
    print(f"precision={em.precision:.4f}  recall={em.recall:.4f}  f1={em.f1:.4f}")
    print(f"\n=== Lane Summary (top 10) ===")
    print(scored.lane_summary.head(10).to_string(index=False))
    print(f"\n=== Best Channel Predicted Blinks (first 20) ===")
    print(scored.best_predicted.head(20).to_string(index=False))

    # -- build output from tp/fp/fn events ------------------------------------
    result = scored.best_eval_result
    tp_events = result.true_positives
    fp_events = result.false_positives
    fn_events = result.false_negatives

    # masterlist CSV: one row per event with full timing on both sides
    df_masterlist = build_events_masterlist_df(tp_events, fp_events, fn_events)
    df_masterlist["onset"] = df_masterlist.apply(
        lambda row: (
            (row["onset_gt"] + row["onset_pred"]) / 2.0
            if pd.notna(row["onset_gt"]) and pd.notna(row["onset_pred"])
            else float(row["onset_gt"]) if pd.notna(row["onset_gt"])
            else float(row["onset_pred"]) if pd.notna(row["onset_pred"])
            else 0.0
        ),
        axis=1,
    )
    df_masterlist = df_masterlist.sort_values("onset").reset_index(drop=True)

    df_masterlist.to_csv(MASTERLIST_CSV, index=False)
    print(f"\nMasterlist CSV saved: {MASTERLIST_CSV}")
    print(df_masterlist.to_string(index=False))

    # annotation CSV: tp/fp/fn windows for visual replay on the raw signal
    scored_ann = build_annotations_from_events(tp_events, fp_events, fn_events)
    csv_out = save_scored_annotations_csv(scored_ann, ANNOTATION_CSV)
    print(f"\nScored annotation CSV saved: {csv_out}")

    # -- Per-epoch blink HTML report ------------------------------------------
    saved_reports = create_blink_epoch_report(
        scored,
        df_masterlist,
        epoch_duration=EPOCH_DURATION_S,
        output_path=REPORT_PATH,
        pad_s=0.5,
        csv_path=CSV_PATH,
        sync_offset_s=0.0,
    )
    for p in saved_reports:
        print(f"Blink epoch report saved: {p}")


if __name__ == "__main__":
    main()
