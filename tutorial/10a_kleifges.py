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

from pathlib import Path
import sys

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import (
    evaluate_channels,
    export_scored_prediction_csv,
    load_ground_truth_annotations,
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
PREDICTION_CSV_TEMPLATE = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933"
    r"\annotation_prediction\ear_eog_predicted_{strategy}.csv"
)
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

    scored = evaluate_channels(
        predicted_annotations,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
    )

    em = scored.best_eval_result.event_metrics
    print(f"\nbest_channel={scored.best_channel}")
    print(f"tp={em.tp}  fp={em.fp}  fn={em.fn}")
    print(f"precision={em.precision:.4f}  recall={em.recall:.4f}  f1={em.f1:.4f}")
    print(f"\n=== Lane Summary (top 10) ===")
    print(scored.lane_summary.head(10).to_string(index=False))
    print(f"\n=== Best Channel Predicted Blinks (first 20) ===")
    print(scored.best_predicted.head(20).to_string(index=False))

    # -- Export tp/fp/fn/tn annotation CSV ------------------------------------
    recording_duration = len(epochs) * EPOCH_DURATION_S
    csv_out = export_scored_prediction_csv(
        scored,
        gt_annotations,
        strategy="kleifges",
        csv_path_template=PREDICTION_CSV_TEMPLATE,
        recording_duration=recording_duration,
    )
    print(f"\nScored annotation CSV saved: {csv_out}")

    # -- Diagnostic: show how many blinks will be plotted ----------------------
    mc = scored.best_channel_result["mapped_candidates"].reset_index(drop=True)
    sig = scored.best_channel_result["signal_by_epoch"]
    missing_ep = [int(r["epoch_index"]) for _, r in mc.iterrows() if sig.get(int(r["epoch_index"])) is None]
    tp_set = {m.pred_index for m in scored.best_eval_result.true_positives}
    fp_set = {e.index for e in scored.best_eval_result.false_positives}
    unknown = [int(p) for p in range(len(mc)) if p not in tp_set and p not in fp_set]
    print(f"\n[DIAG] mapped_candidates rows : {len(mc)}")
    print(f"[DIAG] signal_by_epoch keys   : {len(sig)},  range {min(sig)}-{max(sig)}")
    print(f"[DIAG] ep_idx missing in sig  : {len(missing_ep)}  {missing_ep[:10]}")
    print(f"[DIAG] tp_set size={len(tp_set)}  fp_set size={len(fp_set)}  unknown={len(unknown)}")
    print(f"[DIAG] FN events              : {len(scored.best_eval_result.false_negatives)}")
    print(f"[DIAG] Expected total figures : {len(mc) - len(missing_ep) + len(scored.best_eval_result.false_negatives)}")

    # -- Per-epoch blink HTML report ------------------------------------------
    report_path = csv_out.parent / "blink_epoch_report_kleifges.html"
    saved_reports = create_blink_epoch_report(
        scored,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
        output_path=report_path,
        pad_s=0.5,
    )
    for p in saved_reports:
        print(f"Blink epoch report saved: {p}")



if __name__ == "__main__":
    main()
