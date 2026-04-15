from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from time import perf_counter

import mne
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.blinker.get_blink_positions import get_blink_position
from pyblinker.blinker.pyblinker import BlinkDetector
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_channel import map_concatenated_blinks_to_epochs
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.common.validation import (
    BlinkValidationMetrics,
    filter_reference_to_valid_epochs,
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.epoch_detection_strategy_b.nathanael_mne import find_eog_candidate_regions

DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"

N_EPOCHS = 5
TARGET_CHANNEL = "EEG X1 - Pz"
FRONTAL_MEDIAN_CHANNELS = (
    "EEG Fp1 - Pz",
    "EEG Fp2 - Pz",
    "EEG F7 - Pz",
    "EEG F8 - Pz",
    "EEG F3 - Pz",
    "EEG Fz - Pz",
    "EEG F4 - Pz",
)
SEED_CHANNEL = "EEG F7 - Pz"

REFERENCE_BENCHMARK = {
    "strategy_a_step1": {"TP": 133, "FP": 32, "FN": 0, "precision": 0.80, "recall": 1.0, "f1": 0.89},
    "strategy_b_step1": {"TP": 131, "FP": 14, "FN": 2, "precision": 0.903, "recall": 0.98, "f1": 0.94},
}


@dataclass
class PreparedSlice:
    epochs: mne.Epochs
    prepared: object
    valid_epoch_indices: list[int]
    epoch_boundaries: list[tuple[int, int]]
    reference: pd.DataFrame
    params: dict


def _load_slice(channels: list[str] | tuple[str, ...]) -> PreparedSlice:
    epochs = mne.read_epochs(str(DATA_PATH), preload=True, verbose="ERROR")[:N_EPOCHS].copy()
    epochs.pick(list(channels))
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=1.0,
        filter_high=20.0,
        resample_rate=None,
    )
    params = BlinkDetector._build_detector_params(None, {})
    params["sfreq"] = float(prepared.sfreq)
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    epoch_boundaries = [
        (
            index * prepared.epoch_length_samples,
            (index + 1) * prepared.epoch_length_samples,
        )
        for index in range(len(valid_epoch_indices))
    ]
    reference = filter_reference_to_valid_epochs(
        load_reference_blink_table(REFERENCE_PATH),
        valid_epoch_indices,
    )
    return PreparedSlice(
        epochs=epochs,
        prepared=prepared,
        valid_epoch_indices=valid_epoch_indices,
        epoch_boundaries=epoch_boundaries,
        reference=reference,
        params=params,
    )


def _metric_dict(metrics: BlinkValidationMetrics) -> dict[str, float | int]:
    return {
        "TP": metrics.true_positives,
        "FP": metrics.false_positives,
        "FN": metrics.false_negatives,
        "precision": round(metrics.precision, 6),
        "recall": round(metrics.recall, 6),
        "f1": round(metrics.f1, 6),
    }


def _evaluate(
    mapped: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    n_epochs: int,
) -> BlinkValidationMetrics:
    return match_blink_tables(mapped, reference, n_epochs=n_epochs)


def _detect_legacy_candidates(
    signal: np.ndarray,
    *,
    params: dict,
    channel: str,
) -> pd.DataFrame:
    return get_blink_position(
        params,
        blink_component=signal,
        ch=channel,
        progress_bar=False,
    )


def _map_candidates(
    blink_df: pd.DataFrame,
    *,
    channel: str,
    prepared_slice: PreparedSlice,
) -> pd.DataFrame:
    return map_concatenated_blinks_to_epochs(
        blink_df,
        channel=channel,
        valid_epoch_indices=prepared_slice.valid_epoch_indices,
        epoch_boundaries=prepared_slice.epoch_boundaries,
        sfreq=prepared_slice.prepared.sfreq,
    )


def _interval_overlap_ratio(
    pred_onset: float,
    pred_duration: float,
    ref_onset: float,
    ref_duration: float,
) -> float:
    pred_end = pred_onset + max(pred_duration, 0.0)
    ref_end = ref_onset + max(ref_duration, 0.0)
    overlap = max(0.0, min(pred_end, ref_end) - max(pred_onset, ref_onset))
    denom = max(min(pred_end - pred_onset, ref_end - ref_onset), 1e-12)
    return overlap / denom


def _events_match(
    row_a: pd.Series,
    row_b: pd.Series,
    *,
    onset_tolerance_s: float = 0.1,
    duration_tolerance_s: float = 0.1,
    overlap_threshold: float = 0.5,
) -> bool:
    onset_diff = abs(float(row_a["blink_onset"]) - float(row_b["blink_onset"]))
    duration_diff = abs(float(row_a["blink_duration"]) - float(row_b["blink_duration"]))
    overlap = _interval_overlap_ratio(
        float(row_a["blink_onset"]),
        float(row_a["blink_duration"]),
        float(row_b["blink_onset"]),
        float(row_b["blink_duration"]),
    )
    return onset_diff <= onset_tolerance_s and (
        duration_diff <= duration_tolerance_s or overlap >= overlap_threshold
    )


def _dedup_union(*tables: pd.DataFrame) -> pd.DataFrame:
    frames = [table.copy() for table in tables if table is not None and not table.empty]
    if not frames:
        return pd.DataFrame(
            columns=[
                "epoch_index",
                "channel",
                "blink_onset",
                "blink_duration",
                "start_blink",
                "end_blink",
            ]
        )

    concatenated = pd.concat(frames, ignore_index=True, sort=False)
    concatenated = concatenated.sort_values(
        ["epoch_index", "blink_onset", "blink_duration"]
    ).reset_index(drop=True)

    kept_rows: list[pd.Series] = []
    for _, row in concatenated.iterrows():
        duplicate = any(
            int(existing["epoch_index"]) == int(row["epoch_index"])
            and _events_match(row, existing)
            for existing in kept_rows
        )
        if not duplicate:
            kept_rows.append(row)

    return pd.DataFrame(kept_rows).reset_index(drop=True)


def _cluster_seed_events(seed_mapped: pd.DataFrame) -> list[tuple[int, list[pd.Series]]]:
    clusters: list[tuple[int, list[pd.Series]]] = []
    if seed_mapped.empty:
        return clusters

    for epoch_index, group in seed_mapped.groupby("epoch_index"):
        group = group.sort_values("blink_onset").reset_index(drop=True)
        current_cluster = [group.iloc[0]]
        for row_index in range(1, len(group)):
            row = group.iloc[row_index]
            prev = current_cluster[-1]
            if float(row["blink_onset"]) - float(prev["blink_onset"]) <= 0.15:
                current_cluster.append(row)
            else:
                if len(current_cluster) >= 2:
                    clusters.append((int(epoch_index), current_cluster))
                current_cluster = [row]
        if len(current_cluster) >= 2:
            clusters.append((int(epoch_index), current_cluster))
    return clusters


def _is_cluster_already_covered(
    epoch_index: int,
    cluster: list[pd.Series],
    baseline: pd.DataFrame,
) -> bool:
    baseline_epoch = baseline[baseline["epoch_index"] == epoch_index]
    if baseline_epoch.empty:
        return False
    for seed_row in cluster:
        for _, baseline_row in baseline_epoch.iterrows():
            if abs(float(seed_row["blink_onset"]) - float(baseline_row["blink_onset"])) <= 0.15:
                return True
    return False


def _build_selective_rescue_lane(prepared_slice: PreparedSlice, baseline: pd.DataFrame) -> pd.DataFrame:
    prepared = prepared_slice.prepared
    f7_index = prepared.channel_names.index(SEED_CHANNEL)
    epoch_signals = prepared.data[prepared_slice.valid_epoch_indices, f7_index, :]
    f7_signal = epoch_signals.reshape(-1)

    seed_params = prepared_slice.params.copy()
    seed_params["std_threshold"] = 1.3
    seed_params["min_event_len"] = 0.0
    seed_params["min_event_sep"] = 0.0
    seed_df = _detect_legacy_candidates(
        f7_signal,
        params=seed_params,
        channel=SEED_CHANNEL,
    )
    seed_mapped = _map_candidates(
        seed_df,
        channel=SEED_CHANNEL,
        prepared_slice=prepared_slice,
    )

    rescue_rows: list[pd.Series] = []
    for epoch_index, cluster in _cluster_seed_events(seed_mapped):
        if len(cluster) != 2:
            continue
        seed_span_s = float(cluster[-1]["blink_onset"]) - float(cluster[0]["blink_onset"])
        max_seed_duration_s = max(float(row["blink_duration"]) for row in cluster)
        if not (0.08 <= seed_span_s <= 0.15):
            continue
        if max_seed_duration_s >= 0.03:
            continue
        if _is_cluster_already_covered(epoch_index, cluster, baseline):
            continue

        cluster_center_s = float(
            np.mean(
                [
                    float(row["blink_onset"]) + float(row["blink_duration"]) / 2.0
                    for row in cluster
                ]
            )
        )
        local_start_s = max(0.0, cluster_center_s - 0.35)
        local_stop_s = min(
            prepared.epoch_length_samples / prepared.sfreq,
            cluster_center_s + 0.35,
        )
        epoch_offset = prepared_slice.valid_epoch_indices.index(epoch_index)
        epoch_signal = epoch_signals[epoch_offset]
        local_start_sample = int(round(local_start_s * prepared.sfreq))
        local_stop_sample = int(round(local_stop_s * prepared.sfreq))
        local_signal = epoch_signal[local_start_sample:local_stop_sample]
        if local_signal.size == 0:
            continue

        rescue_params = prepared_slice.params.copy()
        rescue_params["std_threshold"] = 0.4
        rescue_params["min_event_len"] = 0.03
        rescue_params["min_event_sep"] = 0.05
        local_df = _detect_legacy_candidates(
            local_signal,
            params=rescue_params,
            channel=SEED_CHANNEL,
        )
        if local_df.empty:
            continue

        local_df = local_df.copy()
        global_epoch_offset = epoch_index * prepared.epoch_length_samples
        local_df["start_blink"] += global_epoch_offset + local_start_sample
        local_df["end_blink"] += global_epoch_offset + local_start_sample
        local_mapped = _map_candidates(
            local_df.loc[:, ["start_blink", "end_blink"]],
            channel=SEED_CHANNEL,
            prepared_slice=prepared_slice,
        )
        if local_mapped.empty:
            continue

        for _, row in local_mapped.iterrows():
            duration_s = float(row["blink_duration"])
            center_delta_s = abs(
                (float(row["blink_onset"]) + duration_s / 2.0) - cluster_center_s
            )
            if 0.15 <= duration_s <= 0.60 and center_delta_s <= 0.20:
                rescue_rows.append(row)

    if not rescue_rows:
        return pd.DataFrame(
            columns=[
                "epoch_index",
                "channel",
                "blink_onset",
                "blink_duration",
                "start_blink",
                "end_blink",
            ]
        )

    return pd.DataFrame(rescue_rows).reset_index(drop=True)


def _print_result(title: str, result: dict[str, object]) -> None:
    print(f"\n=== {title} ===")
    for key, value in result.items():
        print(f"{key}: {value}")


def main() -> None:
    wall_start = perf_counter()

    x1_slice = _load_slice([TARGET_CHANNEL])
    frontal_slice = _load_slice(FRONTAL_MEDIAN_CHANNELS)

    x1_signal = x1_slice.prepared.data[
        x1_slice.valid_epoch_indices,
        x1_slice.prepared.channel_names.index(TARGET_CHANNEL),
        :,
    ].reshape(-1)

    baseline_a_start = perf_counter()
    legacy_a_df = _detect_legacy_candidates(
        x1_signal,
        params=x1_slice.params,
        channel=TARGET_CHANNEL,
    )
    legacy_a_mapped = _map_candidates(
        legacy_a_df,
        channel=TARGET_CHANNEL,
        prepared_slice=x1_slice,
    )
    legacy_a_metrics = _evaluate(
        legacy_a_mapped,
        x1_slice.reference,
        n_epochs=len(x1_slice.epochs),
    )
    baseline_a_runtime = perf_counter() - baseline_a_start

    baseline_b_start = perf_counter()
    legacy_b_df = find_eog_candidate_regions(
        x1_signal,
        channel=TARGET_CHANNEL,
        sfreq=float(x1_slice.prepared.sfreq),
        half_window_s=0.10,
        l_freq=1.0,
        h_freq=20.0,
        thresh=None,
    )
    legacy_b_mapped = _map_candidates(
        legacy_b_df,
        channel=TARGET_CHANNEL,
        prepared_slice=x1_slice,
    )
    legacy_b_metrics = _evaluate(
        legacy_b_mapped,
        x1_slice.reference,
        n_epochs=len(x1_slice.epochs),
    )
    baseline_b_runtime = perf_counter() - baseline_b_start

    median_start = perf_counter()
    frontal_signal = np.median(
        frontal_slice.prepared.data[frontal_slice.valid_epoch_indices, :, :],
        axis=1,
    ).reshape(-1)
    frontal_median_df = _detect_legacy_candidates(
        frontal_signal,
        params=frontal_slice.params,
        channel="front7_median",
    )
    frontal_median_mapped = _map_candidates(
        frontal_median_df,
        channel="front7_median",
        prepared_slice=frontal_slice,
    )
    frontal_median_metrics = _evaluate(
        frontal_median_mapped,
        frontal_slice.reference,
        n_epochs=len(frontal_slice.epochs),
    )
    frontal_median_runtime = perf_counter() - median_start

    rescue_start = perf_counter()
    rescue_lane = _build_selective_rescue_lane(frontal_slice, frontal_median_mapped)
    recovered_union = _dedup_union(frontal_median_mapped, rescue_lane)
    recovered_metrics = _evaluate(
        recovered_union,
        frontal_slice.reference,
        n_epochs=len(frontal_slice.epochs),
    )
    rescue_runtime = perf_counter() - rescue_start

    recovered_rows = []
    for _, row in rescue_lane.iterrows():
        recovered_rows.append(
            {
                "epoch_index": int(row["epoch_index"]),
                "blink_onset": round(float(row["blink_onset"]), 6),
                "blink_duration": round(float(row["blink_duration"]), 6),
            }
        )

    _print_result(
        "Reference Benchmark Targets",
        REFERENCE_BENCHMARK,
    )
    _print_result(
        "Local Baseline Rerun - Strategy A Step 1",
        {
            "metrics": _metric_dict(legacy_a_metrics),
            "candidate_count": len(legacy_a_mapped),
            "runtime_s": round(baseline_a_runtime, 6),
        },
    )
    _print_result(
        "Local Baseline Rerun - Strategy B Step 1",
        {
            "metrics": _metric_dict(legacy_b_metrics),
            "candidate_count": len(legacy_b_mapped),
            "runtime_s": round(baseline_b_runtime, 6),
        },
    )
    _print_result(
        "Exploratory Strategy C - 7 Channel Frontal Median",
        {
            "metrics": _metric_dict(frontal_median_metrics),
            "candidate_count": len(frontal_median_mapped),
            "runtime_s": round(frontal_median_runtime, 6),
        },
    )
    _print_result(
        "Exploratory Strategy C - 7 Channel Frontal Median + Selective F7 Rescue",
        {
            "metrics": _metric_dict(recovered_metrics),
            "candidate_count": len(recovered_union),
            "rescue_candidate_count": len(rescue_lane),
            "rescued_rows": recovered_rows,
            "runtime_s": round(rescue_runtime, 6),
        },
    )
    _print_result(
        "Comparison To Reference Strategy A Benchmark",
        {
            "delta_TP": recovered_metrics.true_positives - REFERENCE_BENCHMARK["strategy_a_step1"]["TP"],
            "delta_FP": recovered_metrics.false_positives - REFERENCE_BENCHMARK["strategy_a_step1"]["FP"],
            "delta_FN": recovered_metrics.false_negatives - REFERENCE_BENCHMARK["strategy_a_step1"]["FN"],
        },
    )
    _print_result(
        "Comparison To Reference Strategy B Benchmark",
        {
            "delta_TP": recovered_metrics.true_positives - REFERENCE_BENCHMARK["strategy_b_step1"]["TP"],
            "delta_FP": recovered_metrics.false_positives - REFERENCE_BENCHMARK["strategy_b_step1"]["FP"],
            "delta_FN": recovered_metrics.false_negatives - REFERENCE_BENCHMARK["strategy_b_step1"]["FN"],
        },
    )
    _print_result(
        "Run Metadata",
        {
            "data_path": str(DATA_PATH),
            "reference_path": str(REFERENCE_PATH),
            "n_reference_blinks": len(frontal_slice.reference),
            "n_epochs": len(frontal_slice.epochs),
            "wall_time_s": round(perf_counter() - wall_start, 6),
        },
    )


if __name__ == "__main__":
    main()
