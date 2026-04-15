"""Strategy B (Nathanael MNE): MNE EOG-event-based blink candidate detection."""

from pyblinker.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input

from .nathanael_mne import (
    DEFAULT_STRATEGY_B_CHANNELS,
    find_eog_candidate_regions,
    summarize_candidate_regions,
)
from .runner import blink_position_strategy_b, run_strategy_b

__all__ = [
    "DEFAULT_STRATEGY_B_CHANNELS",
    "PreparedEpochDetectionInput",
    "blink_position_strategy_b",
    "find_eog_candidate_regions",
    "prepare_epoch_detection_input",
    "run_strategy_b",
    "summarize_candidate_regions",
]
