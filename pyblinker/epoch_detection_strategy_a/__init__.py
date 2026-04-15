"""Epoch-aware blink detection built on the legacy six-step pipeline."""

from .bad_epoch_utils import get_valid_epoch_indices, simulate_bad_epochs
from .epoch_blink_pipeline import (
    BlinkDetectorEpoch,
    PreparedEpochDetectionInput,
    prepare_epoch_detection_input,
    run_epoch_blink_pipeline,
)

__all__ = [
    "BlinkDetectorEpoch",
    "PreparedEpochDetectionInput",
    "get_valid_epoch_indices",
    "prepare_epoch_detection_input",
    "run_epoch_blink_pipeline",
    "simulate_bad_epochs",
]
