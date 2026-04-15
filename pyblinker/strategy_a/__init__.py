"""Strategy A: Kleifges/BLINKER-based blink position detection."""

from pyblinker.common.bad_epochs import get_valid_epoch_indices, simulate_bad_epochs
from pyblinker.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input

from .kleifges_blinker_2017 import blink_position_strategy_a
from .runner import channel_results_strategy_a, run_strategy_a

__all__ = [
    "PreparedEpochDetectionInput",
    "blink_position_strategy_a",
    "channel_results_strategy_a",
    "get_valid_epoch_indices",
    "prepare_epoch_detection_input",
    "run_strategy_a",
    "simulate_bad_epochs",
]
