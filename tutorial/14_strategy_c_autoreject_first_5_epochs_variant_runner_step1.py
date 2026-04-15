"""Run one Strategy C Step 1 variant and stop before any FitBlinks pass.

This runner evaluates the direct Stage 1 output only:

- learn thresholds
- build candidate lanes
- detect raw candidate intervals
- map each lane's candidates back to epoch-local blink rows
- compare each lane's mapped candidates against the 5-epoch ground_truth

It intentionally does not call the downstream representative-lane
``FitBlinks(...)`` refinement.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from time import perf_counter

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_validation import (
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.epoch_detection_strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    # AUTOREJECT_RANDOM_SEARCH,
    DEFAULT_STRATEGY_C_CHANNELS,
    THRESHOLD_SCOPE_GLOBAL,
    THRESHOLD_SCOPE_PER_CHANNEL,
    epoch_detection_strategy_c_autoreject,
)
from tutorial.strategy_c_autoreject_first_5_epochs_common import (
    REFERENCE_PATH,
    load_first_5_epochs,
)


DISABLE_BACKBONE_CHANNELS = ("__NO_BACKBONE__",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one Strategy C Step 1 variant on the first 5 epochs and print "
            "lane-level mapped-candidate metrics before any FitBlinks pass."
        ),
        epilog=(
            "Example: python tutorial/14_strategy_c_autoreject_first_5_epochs_variant_runner_step1.py "
            "--method bayesian_optimization --scope per_channel"
        ),
    )
    parser.add_argument(
        "--method",
        default=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        choices=[
                # AUTOREJECT_RANDOM_SEARCH,
                 AUTOREJECT_BAYESIAN_OPTIMIZATION],
        help="Autoreject threshold search method.",
    )
    parser.add_argument(
        "--scope",
        default=THRESHOLD_SCOPE_PER_CHANNEL,
        choices=[THRESHOLD_SCOPE_PER_CHANNEL, THRESHOLD_SCOPE_GLOBAL],
        help="Stage 1 threshold scope.",
    )
    parser.add_argument(
        "--with-backbone",
        dest="with_backbone",
        action="store_true",
        help="Enable the weighted frontal backbone. By default the runner disables it.",
    )
    parser.add_argument(
        "--no-backbone",
        dest="with_backbone",
        action="store_false",
        help="Disable the weighted frontal backbone explicitly.",
    )
    parser.set_defaults(with_backbone=False)
    parser.add_argument(
        "--show-candidates",
        action="store_true",
        help="Print the full mapped Stage 1 candidate table.",
    )
    parser.add_argument(
        "--disable-threshold-rescale",
        action="store_true",
        help=(
            "Use the raw threshold learned by autoreject for Stage 1 lane scanning "
            "instead of multiplying by the fixed scan-threshold scale."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Python logging level for the runner and Strategy C detector.",
    )
    return parser.parse_args()


def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        existing = [column for column in columns if column in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


def configure_logging(log_level: str) -> None:
    """Configure console logging for manual tutorial runs."""

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(levelname)s: %(name)s: %(message)s",
        force=True,
    )


def load_reference() -> pd.DataFrame:
    return load_reference_blink_table(REFERENCE_PATH)


def build_step1_summary(
    detections: list[object],
    *,
    reference: pd.DataFrame,
    n_epochs: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for detection in detections:
        metrics = match_blink_tables(
            detection.mapped_candidates,
            reference,
            n_epochs=n_epochs,
        )
        rows.append(
            {
                "channel": detection.channel,
                "candidate_source": detection.candidate_source,
                "threshold": float(detection.threshold),
                "raw_candidate_count": int(len(detection.positions)),
                "mapped_candidate_count": int(len(detection.mapped_candidates)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["f1", "tp", "fp", "channel"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)


def get_detection_by_channel(detections: list[object], channel: str):
    for detection in detections:
        if detection.channel == channel:
            return detection
    return None


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    stage1_channels = (
        DEFAULT_STRATEGY_C_CHANNELS if args.with_backbone else DISABLE_BACKBONE_CHANNELS
    )

    print(f"script={Path(__file__).name}")
    print("dataset=sample_data/dev_epo.fif")
    print("epochs=first 5 only")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"autoreject_method={args.method}")
    print(f"stage1_threshold_scope={args.scope}")
    print(f"stage1_rescale_threshold={not args.disable_threshold_rescale}")
    print(f"stage1_channels={stage1_channels}")
    print(f"weighted_frontal_backbone_enabled={args.with_backbone}")
    print(f"log_level={args.log_level}")

    started = perf_counter()
    epochs: mne.Epochs = load_first_5_epochs()
    reference = load_reference()

    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=1.0,
        filter_high=20.0,
        resample_rate=None,
        n_jobs=1,
        use_multiprocessing=False,
        stage1_channels=stage1_channels,
        stage1_threshold_scope=args.scope,
        stage1_rescale_threshold=not args.disable_threshold_rescale,
        autoreject_random_state=42,
        autoreject_method=args.method,
        autoreject_augment=False,
    )

    prepared = detector.prepare_epoch_data()
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    stage1 = detector.run_stage1_candidate_scan(
        prepared=prepared,
        valid_epoch_indices=valid_epoch_indices,
    )
    elapsed_s = perf_counter() - started
    summary = build_step1_summary(
        stage1.detections,
        reference=reference,
        n_epochs=len(epochs),
    )


    print("\n=== Run Result ===")
    print(f"elapsed_s={elapsed_s:.6f}")
    print(f"valid_epoch_indices={valid_epoch_indices}")
    print(f"stage1_threshold_scope={detector.stage1_threshold_scope}")
    print(f"stage1_threshold_learning_api={stage1.threshold_learning_api}")
    print(f"stage1_autoreject_method={detector.autoreject_method}")
    print(f"stage1_rescale_threshold={detector.stage1_rescale_threshold}")
    print(f"stage1_eeg_channels={stage1.channel_names}")
    print(f"stage1_backbone_built={stage1.backbone_signal is not None}")
    print(f"stage1_backbone_channels={detector.stage1_backbone_channels_}")
    print(f"stage1_global_threshold={stage1.global_threshold}")
    print(f"stage1_scan_threshold_scale={detector._get_stage1_scan_threshold_scale()}")
    print(f"candidate_lane_count={len(stage1.candidate_lanes)}")

    print_frame("Stage 1 Lane Summary", summary)

    if args.show_candidates:
        if summary.empty:
            print_frame("Best Lane Mapped Candidates", pd.DataFrame())
        else:
            best_channel = str(summary.loc[0, "channel"])
            best_detection = get_detection_by_channel(stage1.detections, best_channel)
            best_candidates = (
                best_detection.mapped_candidates
                if best_detection is not None
                else pd.DataFrame()
            )
            print_frame(
                "Best Lane Mapped Candidates",
                best_candidates,
                ["epoch_index", "channel", "blink_onset", "blink_duration", "candidate_source"],
            )


if __name__ == "__main__":
    main()
