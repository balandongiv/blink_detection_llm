from __future__ import annotations

from pathlib import Path
import sys

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.false_negative_analysis import collect_false_negatives
from src.analysis.fn_report_builder import build_false_negative_report
from src.analysis.lane_evaluation import evaluate_channel_lanes
from src.common.bad_epochs import get_valid_epoch_indices
from src.strategy_a.kleifges_blinker_2017 import (
    kleifges_strategy_a,
)
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference

FIF_PATH = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif"
)
CSV_PATH = Path(
    r"D:\dataset\drowsy_driving_raja\human_label_annotation\S1\S01_20170519_043933\ear_eog.csv"
)
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
EPOCH_DURATION_S = 60.0
PEAK_SIDE_TOLERANCE_S = 0.01
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
PAD_S = 0.75
OUTPUT_DIR = (
    REPO_ROOT
    / "tutorial"
    / "output"
    / "32_strategy_a_step1_peak_overlap_fn_report"
)


def main() -> None:
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = kleifges_strategy_a(prepared, valid_epoch_indices)
    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(CSV_PATH, EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )

    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=EPOCH_DURATION_S,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )

    false_negatives = collect_false_negatives(
        scored.best_predicted,
        ground_truth,
        signal_by_epoch=scored.best_result["signal_by_epoch"],
        sfreq=float(prepared.sfreq),
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    ).sort_values(["absolute_onset_s", "epoch_index", "blink_onset"]).reset_index(drop=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    false_negatives.to_csv(OUTPUT_DIR / "strategy_a_step1_peak_overlap_false_negatives.csv", index=False)
    scored.lane_summary.to_csv(OUTPUT_DIR / "strategy_a_step1_peak_overlap_lane_summary.csv", index=False)

    m = scored.best_metrics
    report = build_false_negative_report(
        title="Strategy A Step 1 Peak-Overlap False Negatives",
        summary_items={
            "FIF": str(FIF_PATH),
            "CSV": str(CSV_PATH),
            "Representative channel": scored.best_result["channel"],
            "Metrics": f"TP={m.true_positives}, FP={m.false_positives}, FN={m.false_negatives}, F1={m.f1:.4f}",
            "Peak side tolerance": f"{PEAK_SIDE_TOLERANCE_S:.2f}s",
            "False negative count": str(len(false_negatives)),
        },
        lane_summary=scored.lane_summary,
        false_negatives=false_negatives,
        predicted=scored.best_predicted,
        signal_by_epoch=scored.best_result["signal_by_epoch"],
        sfreq=float(prepared.sfreq),
        tags=("strategy_a_step1", scored.best_result["channel"], "false_negative"),
        pad_s=PAD_S,
    )

    output_path = OUTPUT_DIR / "strategy_a_step1_peak_overlap_false_negative_report.html"
    report.save(output_path, overwrite=True, open_browser=False)
    print(output_path)


if __name__ == "__main__":
    main()
