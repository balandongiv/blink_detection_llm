from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from time import perf_counter

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.common.validation import (
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    AUTOREJECT_RANDOM_SEARCH,
    DEFAULT_STAGE1_THRESHOLD_SCOPE,
    THRESHOLD_SCOPE_GLOBAL,
    epoch_detection_strategy_c_autoreject,
)


DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"
# stage1_channels=None means use all available EEG channels.
CHANNELS = None

TARGET_EPOCH_INDEX = 0
VISUALIZE = False
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
N_JOBS = 1
USE_MULTIPROCESSING = False
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT = False


@dataclass
class DebugRunResult:
    method: str
    elapsed_s: float
    detector: object
    prepared: object
    annotations: mne.Annotations
    channel: str
    n_good_blinks: int
    blink_table: pd.DataFrame
    selected_channel: pd.DataFrame
    metrics: object


def load_first_5_epochs() -> mne.Epochs:
    epochs = mne.read_epochs(str(DATA_PATH), preload=True, verbose="ERROR")
    return epochs[:5].copy()


def build_detector(
    epochs: mne.Epochs,
    *,
    autoreject_method: str,
    stage1_threshold_scope: str = DEFAULT_STAGE1_THRESHOLD_SCOPE,
    stage1_rescale_threshold: bool = True,
):
    return epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=VISUALIZE,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        n_jobs=N_JOBS,
        use_multiprocessing=USE_MULTIPROCESSING,
        stage1_threshold_scope=stage1_threshold_scope,
        stage1_rescale_threshold=stage1_rescale_threshold,
        autoreject_random_state=AUTOREJECT_RANDOM_STATE,
        autoreject_method=autoreject_method,
        autoreject_augment=AUTOREJECT_AUGMENT,
    )


def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        existing = [column for column in columns if column in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


def run_debug_benchmark(
    *,
    epochs: mne.Epochs,
    reference: pd.DataFrame,
    autoreject_method: str,
    stage1_threshold_scope: str = DEFAULT_STAGE1_THRESHOLD_SCOPE,
    stage1_rescale_threshold: bool = True,
) -> DebugRunResult:
    started = perf_counter()
    detector = build_detector(
        epochs,
        autoreject_method=autoreject_method,
        stage1_threshold_scope=stage1_threshold_scope,
        stage1_rescale_threshold=stage1_rescale_threshold,
    )
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    annotations, channel, n_good_blinks, blink_table, _fig_data, selected_channel, _epochs = (
        detector.get_blink()
    )
    elapsed_s = perf_counter() - started
    metrics = match_blink_tables(
        blink_table,
        reference,
        n_epochs=len(epochs),
    )
    return DebugRunResult(
        method=autoreject_method,
        elapsed_s=elapsed_s,
        detector=detector,
        prepared=prepared,
        annotations=annotations,
        channel=channel,
        n_good_blinks=n_good_blinks,
        blink_table=blink_table,
        selected_channel=selected_channel,
        metrics=metrics,
    )


def print_run_configuration(
    *,
    script_name: str,
    method: str,
    stage1_threshold_scope: str,
    stage1_rescale_threshold: bool,
) -> None:
    print(f"script={script_name}")
    print(f"data_path={DATA_PATH}")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"target_epoch_index={TARGET_EPOCH_INDEX}")
    print(f"filter_low={FILTER_LOW}")
    print(f"filter_high={FILTER_HIGH}")
    print(f"resample_rate={RESAMPLE_RATE}")
    print(f"strategy_c_channels={CHANNELS}")
    print(f"stage1_threshold_scope={stage1_threshold_scope}")
    print(f"stage1_rescale_threshold={stage1_rescale_threshold}")
    print(f"autoreject_method={method}")
    print(f"autoreject_random_state={AUTOREJECT_RANDOM_STATE}")
    print(f"autoreject_augment={AUTOREJECT_AUGMENT}")


def print_prepared_summary(result: DebugRunResult) -> None:
    prepared = result.prepared
    print("\n=== Prepared Epoch Data ===")
    print(f"prepared_shape={prepared.data.shape}")
    print(f"prepared_channel_names={prepared.channel_names}")
    print(f"prepared_sfreq={prepared.sfreq}")
    print(f"epoch_length_samples={prepared.epoch_length_samples}")
    print(f"valid_epoch_indices={result.detector.last_result.valid_epoch_indices}")


def print_autoreject_api_usage(result: DebugRunResult) -> None:
    detector = result.detector
    valid_epoch_count = len(detector.last_result.valid_epoch_indices)
    channel_count = len(detector.stage1_channel_names_)
    sample_count = int(result.prepared.epoch_length_samples)
    print("\n=== Autoreject API Usage ===")
    print(f"stage1_threshold_scope={detector.stage1_threshold_scope_}")
    print(f"stage1_threshold_learning_api={detector.stage1_threshold_learning_api_}")
    if detector.stage1_threshold_scope_ == THRESHOLD_SCOPE_GLOBAL:
        print("Strategy C uses `autoreject.get_rejection_threshold(...)` to learn one")
        print("shared EEG rejection threshold for the selected Stage 1 slice.")
        print(
            "The configured `autoreject_method` value is retained only for constructor "
            "compatibility in this mode."
        )
        print("Exact call shape:")
        print("get_rejection_threshold(")
        print("    stage1_epochs,")
        print(f"    random_state={detector.autoreject_random_state},")
        print("    ch_types='eeg',")
        print(f"    cv={min(5, valid_epoch_count)},")
        print("    verbose=False,")
        print(")")
        print(
            f"learned_global_threshold={detector.stage1_global_threshold_}"
        )
        print(
            "That shared rejection threshold is reused for every eligible EEG lane, "
            "and the Stage 1 detector applies a fixed sample-scan scale on top of it."
        )
    else:
        print("Strategy C uses `autoreject.compute_thresholds(...)` as a per-channel threshold learner.")
        print("Exact call shape:")
        print("compute_thresholds(")
        print("    stage1_epochs,")
        print(f"    method={detector.autoreject_method!r},")
        print(f"    random_state={detector.autoreject_random_state},")
        print(f"    augment={detector.autoreject_augment},")
        print("    verbose=False,")
        print(")")
        print("One rejection threshold is learned for each eligible EEG channel.")
        print(
            "Those learned thresholds are reused directly as Stage 1 scan thresholds "
            "after applying the detector's fixed scan-threshold scale."
        )
    print(
        f"stage1_scan_threshold_scale={detector._get_stage1_scan_threshold_scale()}"
    )
    print(f"stage1_rescale_threshold={detector.stage1_rescale_threshold}")
    print(
        "stage1_epochs is an `mne.EpochsArray` built from "
        f"{valid_epoch_count} valid epochs, {channel_count} eligible EEG channels, "
        f"and {sample_count} samples per epoch."
    )
    if detector.stage1_backbone_channels_:
        print(
            "An optional weighted-median backbone lane is also built from the configured "
            f"frontal subset: {detector.stage1_backbone_channels_}"
        )
    else:
        print("No frontal backbone lane was built for this run.")


def print_execution_flow_chart(result: DebugRunResult) -> None:
    print("\n=== Execution Flow Chart ===")
    threshold_step = (
        "  -> get_rejection_threshold(...)"
        if result.detector.stage1_threshold_scope_ == THRESHOLD_SCOPE_GLOBAL
        else "  -> compute_thresholds(...)"
    )
    threshold_detail = (
        "     -> learn one shared EEG PTP threshold"
        if result.detector.stage1_threshold_scope_ == THRESHOLD_SCOPE_GLOBAL
        else "     -> learn one PTP threshold per eligible EEG channel"
    )
    print(
        "\n".join(
            [
                "load dev_epo.fif",
                "  -> keep first 5 epochs",
                "  -> instantiate EpochDetectionStrategyCAutoreject",
                "  -> prepare_epoch_detection_input(...)",
                "     -> pick EEG channels",
                "     -> band-pass filter data",
                "     -> optionally resample",
                "  -> get_valid_epoch_indices(...)",
                "  -> resolve eligible EEG Stage 1 channels",
                "  -> optionally resolve the configured frontal subset for the backbone lane",
                "  -> build stage1_epochs as mne.EpochsArray",
                threshold_step,
                threshold_detail,
                "  -> convert rejection thresholds into Stage 1 sample scan thresholds",
                "  -> detect Stage 1 candidates on every eligible EEG lane",
                "  -> optionally detect the weighted frontal backbone lane",
                "  -> compute lane-level blink statistics",
                "  -> shortlist the best 3 representative lanes",
                "  -> union Stage 1 candidates across those representative lanes",
                "  -> if a representative lane includes the backbone, run the F7 rescue lane",
                "  -> FitBlinks(...) on the chosen representative lane using the merged intervals",
                "  -> attach downstream quality flags",
                "  -> map candidates back into epoch-local blink rows",
                "  -> build final annotations, blink table, and selected-channel summary",
            ]
        )
    )


def print_candidate_channel_explanation(result: DebugRunResult) -> None:
    print("\n=== Selected Lane ===")
    selected_summary = result.selected_channel.copy()
    candidate_source = (
        selected_summary.loc[0, "strategy_c_candidate_source"]
        if not selected_summary.empty and "strategy_c_candidate_source" in selected_summary.columns
        else "channel_threshold"
    )
    if candidate_source == "weighted_median_backbone":
        print(
            f"`{result.channel}` is the optional weighted frontal backbone lane chosen "
            "after multi-lane Stage 1 scoring."
        )
        print("Backbone formula:")
        if result.detector.stage1_threshold_scope_ == THRESHOLD_SCOPE_GLOBAL:
            print("s(t) = median_c(x_c(t) / tau)")
        else:
            print("s(t) = median_c(x_c(t) / tau_c)")
    else:
        print(
            f"`{result.channel}` is the representative EEG lane selected after evaluating "
            "all Stage 1 candidate lanes."
        )
    if not selected_summary.empty and "strategy_c_representative_channels" in selected_summary.columns:
        print(
            "Representative Stage 1 lanes: "
            f"{selected_summary.loc[0, 'strategy_c_representative_channels']}"
        )


def print_rescue_lane_explanation() -> None:
    print("\n=== Selective Rescue Lane ===")
    print("The rescue lane is a fallback detection path, not a second threshold-learning pass.")
    print(
        "It is only activated when the shortlisted representative lanes include the "
        "optional weighted frontal backbone."
    )
    print("Current Strategy C rescue-lane steps:")
    print("1. Look only at `EEG F7 - Pz`.")
    print("2. Run a loose seed detector to find short local events.")
    print("3. Keep only two-event clusters with a narrow spacing pattern.")
    print("4. Ignore clusters already covered by the representative Stage 1 candidates.")
    print("5. Open a small local time window around the cluster center.")
    print("6. Rerun a stricter detector inside that local window.")
    print("7. Keep only blink-shaped rescue candidates and union them with the representative output.")
    print("So the rescue lane remains a narrow F7-only fallback lane for blind-spot recovery.")


def print_debug_run(
    result: DebugRunResult,
    *,
    reference: pd.DataFrame,
) -> None:
    detector = result.detector
    metrics = result.metrics
    print("\n=== Run Result ===")
    print(f"elapsed_s={result.elapsed_s:.6f}")
    print(f"selected_channel={result.channel}")
    print(f"n_good_blinks={result.n_good_blinks}")
    print(f"annotation_count={len(result.annotations)}")
    print(f"stage1_threshold_scope={detector.stage1_threshold_scope_}")
    print(f"stage1_threshold_learning_api={detector.stage1_threshold_learning_api_}")
    print(f"stage1_autoreject_method={detector.stage1_autoreject_method_}")
    print(f"stage1_global_threshold={detector.stage1_global_threshold_}")
    print(f"stage1_channels={detector.stage1_channel_names_}")
    print(f"stage1_backbone_channels={detector.stage1_backbone_channels_}")
    print(f"stage1_thresholds={detector.stage1_thresholds_}")
    print(f"stage1_scan_threshold_scale={detector._get_stage1_scan_threshold_scale()}")
    print(f"stage1_candidate_count={len(detector.stage1_candidates_)}")
    print(f"stage1_rescue_candidate_count={len(detector.stage1_rescue_candidates_)}")
    print_frame("Representative Stage 1 Lanes", detector.stage1_representative_channels_)
    print_frame("Selected Channel Summary", result.selected_channel)
    print_frame(
        f"Predicted Blinks For Epoch {TARGET_EPOCH_INDEX}",
        result.blink_table[result.blink_table["epoch_index"] == TARGET_EPOCH_INDEX].copy(),
        ["epoch_index", "channel", "blink_onset", "blink_duration", "epoch_selection"],
    )
    print_frame(
        f"Reference Blinks For Epoch {TARGET_EPOCH_INDEX}",
        reference[reference["epoch_index"] == TARGET_EPOCH_INDEX].copy(),
        ["epoch_index", "blink_onset", "blink_duration"],
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


def run_single_method_debug(
    *,
    method: str,
    script_name: str,
    stage1_threshold_scope: str = DEFAULT_STAGE1_THRESHOLD_SCOPE,
    stage1_rescale_threshold: bool = True,
) -> DebugRunResult:
    print_run_configuration(
        script_name=script_name,
        method=method,
        stage1_threshold_scope=stage1_threshold_scope,
        stage1_rescale_threshold=stage1_rescale_threshold,
    )
    epochs = load_first_5_epochs()
    reference = load_reference_blink_table(REFERENCE_PATH)
    result = run_debug_benchmark(
        epochs=epochs,
        reference=reference,
        autoreject_method=method,
        stage1_threshold_scope=stage1_threshold_scope,
        stage1_rescale_threshold=stage1_rescale_threshold,
    )
    print_prepared_summary(result)
    print_autoreject_api_usage(result)
    print_execution_flow_chart(result)
    print_candidate_channel_explanation(result)
    print_rescue_lane_explanation()
    print_debug_run(result, reference=reference)
    return result


def print_method_alias_note() -> None:
    print(
        "The tutorial filename keeps the requested `bayasian` spelling, but the actual "
        f"autoreject method string remains `{AUTOREJECT_BAYESIAN_OPTIMIZATION}`."
    )


__all__ = [
    "AUTOREJECT_BAYESIAN_OPTIMIZATION",
    "AUTOREJECT_RANDOM_SEARCH",
    "THRESHOLD_SCOPE_GLOBAL",
    "run_single_method_debug",
    "print_method_alias_note",
]
