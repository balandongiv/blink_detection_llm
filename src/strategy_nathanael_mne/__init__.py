"""Strategy B (Nathanael MNE): MNE EOG-event-based blink candidate detection."""

from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input

from .nathanael_mne import (
    DEFAULT_STRATEGY_NATHANAEL_MNE_CHANNELS,
    find_eog_candidate_regions,
)
from .runner import blink_position_strategy_nathanael, run_strategy_nathanael_mne, summarize_candidate_regions

__all__ = [
    "DEFAULT_STRATEGY_NATHANAEL_MNE_CHANNELS",
    "PreparedEpochDetectionInput",
    "blink_position_strategy_nathanael",
    "find_eog_candidate_regions",
    "prepare_epoch_detection_input",
    "run_strategy_nathanael_mne",
    "summarize_candidate_regions",
]
