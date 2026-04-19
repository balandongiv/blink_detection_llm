from __future__ import annotations

import sys
from pathlib import Path

import mne
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.blinker.pyblinker import BlinkDetector
from src.blinker.get_blink_positions import get_blink_position
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import prepare_epoch_detection_input
from src.common.validation import match_blink_tables
from src.utils.peak_overlap_metric import (
    calculate_interval_overlap_ratio,
    is_peak_overlap_match,
)

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


def load_brain_region_channels(yaml_path: Path) -> list[str]:
    with yaml_path.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    channels: list[str] = []
    for region_channels in config["eeg_regions"].values():
        channels.extend(region_channels)
    return channels


def load_raw_with_brain_channels(
    fif_path: Path,
    brain_channels: list[str],
) -> mne.io.BaseRaw:
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    available = [ch for ch in brain_channels if ch in raw.ch_names]
    raw.pick(available)
    return raw


def make_fixed_epochs(raw: mne.io.BaseRaw, duration: float = EPOCH_DURATION_S) -> mne.Epochs:
    return mne.make_fixed_length_epochs(raw, duration=duration, preload=True, verbose="ERROR")


def load_annotation_as_reference(
    csv_path: Path,
    epoch_duration: float = EPOCH_DURATION_S,
) -> pd.DataFrame:
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    rows: list[dict] = []
    for _, row in df.iterrows():
        onset_abs = float(row["onset"])
        duration = float(row["duration"])
        epoch_index = int(onset_abs // epoch_duration)
        rows.append(
            {
                "epoch_index": epoch_index,
                "blink_onset": onset_abs - epoch_index * epoch_duration,
                "blink_duration": duration,
            }
        )
    return pd.DataFrame(rows, columns=["epoch_index", "blink_onset", "blink_duration"])


def enrich_absolute_times(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    out["absolute_onset_s"] = (
        out["epoch_index"].astype(float) * float(EPOCH_DURATION_S)
        + out["blink_onset"].astype(float)
    )
    out["absolute_offset_s"] = out["absolute_onset_s"] + out["blink_duration"].astype(float)
    return out


def nearest_row(table: pd.DataFrame, epoch_index: int, onset: float, duration: float) -> pd.Series | None:
    if table.empty:
        return None
    epoch_rows = table[table["epoch_index"] == epoch_index].copy()
    if epoch_rows.empty:
        return None
    epoch_rows["distance"] = (
        (epoch_rows["blink_onset"] - onset).abs()
        + (epoch_rows["blink_duration"] - duration).abs()
    )
    return epoch_rows.sort_values("distance").iloc[0]


def run_get_blink_position_per_channel(
    prepared,
    valid_epoch_indices: list[int],
) -> list[dict]:
    """Mirror Tutorial 19 strategy_a step 1 candidate generation."""

    params = BlinkDetector._build_detector_params(None, {})
    params["sfreq"] = float(prepared.sfreq)

    epoch_boundaries = [
        (
            idx * prepared.epoch_length_samples,
            (idx + 1) * prepared.epoch_length_samples,
        )
        for idx in range(len(valid_epoch_indices))
    ]

    results = []
    for channel_index, channel_name in enumerate(prepared.channel_names):
        concatenated_signal = prepared.data[valid_epoch_indices, channel_index, :].reshape(-1)

        df_positions = get_blink_position(
            params,
            blink_component=concatenated_signal,
            ch=channel_name,
            progress_bar=False,
        )

        mapped_positions = map_concatenated_blinks_to_epochs(
            df_positions,
            channel=channel_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )

        signal_by_epoch = {
            epoch_index: prepared.data[epoch_index, channel_index, :].astype(float)
            for epoch_index in range(prepared.data.shape[0])
        }

        results.append(
            {
                "channel": channel_name,
                "df_positions": df_positions,
                "mapped_candidates": mapped_positions,
                "signal_by_epoch": signal_by_epoch,
            }
        )
    return results


def main() -> None:
    print("Peak-overlap metric usage tutorial")
    print("Prediction source: strategy_a step 1")
    print(f"FIF: {FIF_PATH}")
    print(f"CSV: {CSV_PATH}")
    print(f"Peak side tolerance: {PEAK_SIDE_TOLERANCE_S:.2f}s")

    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(
        FIF_PATH,
        brain_channels,
    )
    epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )

    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = run_get_blink_position_per_channel(prepared, valid_epoch_indices)

    reference = enrich_absolute_times(load_annotation_as_reference(CSV_PATH, epoch_duration=EPOCH_DURATION_S))

    lane_rows = []
    best_result = None
    best_metrics = None
    for channel_result in channel_results:
        predicted = enrich_absolute_times(channel_result["mapped_candidates"])
        metrics = match_blink_tables(
            predicted,
            reference,
            n_epochs=len(epochs),
            signal_by_epoch=channel_result["signal_by_epoch"],
            sfreq=float(prepared.sfreq),
            peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
        )
        lane_rows.append(
            {
                "channel": channel_result["channel"],
                "raw_candidate_count": int(len(channel_result["df_positions"])),
                "mapped_candidate_count": int(len(channel_result["mapped_candidates"])),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )
        if best_metrics is None or (
            metrics.f1,
            metrics.true_positives,
            -metrics.false_positives,
            channel_result["channel"],
        ) > (
            best_metrics.f1,
            best_metrics.true_positives,
            -best_metrics.false_positives,
            best_result["channel"],
        ):
            best_result = channel_result
            best_metrics = metrics

    lane_summary = pd.DataFrame(lane_rows).sort_values(
        ["f1", "tp", "fp", "channel"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    signal_channel = best_result["channel"]
    signal_by_epoch = best_result["signal_by_epoch"]
    predicted = enrich_absolute_times(best_result["mapped_candidates"])
    metrics = best_metrics

    example_ref = reference.iloc[0]
    example_pred = nearest_row(
        predicted,
        int(example_ref["epoch_index"]),
        float(example_ref["blink_onset"]),
        float(example_ref["blink_duration"]),
    )

    print()
    print("Strategy A Step 1 Output")
    print(f"selected_channel={signal_channel}")
    print(f"predicted_blinks={len(predicted)}")
    print(f"reference_blinks={len(reference)}")
    print(f"valid_epochs={len(valid_epoch_indices)}")
    print()
    print("Top 5 lane summary")
    print(lane_summary.head(5).to_string(index=False))

    print()
    print("Metrics Against Ground Truth")
    print(f"tp={metrics.true_positives}")
    print(f"fp={metrics.false_positives}")
    print(f"fn={metrics.false_negatives}")
    print(f"precision={metrics.precision:.4f}")
    print(f"recall={metrics.recall:.4f}")
    print(f"f1={metrics.f1:.4f}")

    print()
    print("How the new definition works")
    print("1. Prediction and ground_truth must overlap in time.")
    print("2. The highest-amplitude sample in their union must lie inside the overlap.")
    print("3. The overlap must also cover about +/-0.01s around that peak.")

    if example_pred is not None:
        overlap_ratio = calculate_interval_overlap_ratio(
            float(example_pred["blink_onset"]),
            float(example_pred["blink_duration"]),
            float(example_ref["blink_onset"]),
            float(example_ref["blink_duration"]),
        )
        is_match = is_peak_overlap_match(
            example_pred,
            example_ref,
            epoch_signal=signal_by_epoch[int(example_ref["epoch_index"])],
            sfreq=float(prepared.sfreq),
            peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
        )
        print()
        print("Direct utility example")
        print(f"example_epoch={int(example_ref['epoch_index'])}")
        print(f"selected_channel_for_metric={signal_channel}")
        print(f"overlap_ratio={overlap_ratio:.4f}")
        print(f"peak_overlap_match={is_match}")

    print()
    print("Minimal API call")
    print(
        "match_blink_tables(predicted, ground_truth, n_epochs=len(epochs), "
        "signal_by_epoch=signal_by_epoch, sfreq=sfreq, peak_side_tolerance_s=0.01)"
    )
    print()
    print("Direct utility imports")
    print("from pyblinker.utils.peak_overlap_metric import is_peak_overlap_match")
    print("from pyblinker.utils.peak_overlap_metric import calculate_interval_overlap_ratio")


if __name__ == "__main__":
    main()
