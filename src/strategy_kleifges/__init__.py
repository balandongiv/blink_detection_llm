"""Strategy A: Kleifges/BLINKER-based blink position detection."""

from src.common.bad_epochs import get_valid_epoch_indices, simulate_bad_epochs
from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input

from .kleifges_blinker_2017 import kleifges_strategy
from .runner import channel_results_strategy_a, run_strategy_a

__all__ = [
    "PreparedEpochDetectionInput",
    "kleifges_strategy",
    "channel_results_strategy_a",
    "get_valid_epoch_indices",
    "prepare_epoch_detection_input",
    "run_strategy_a",
    "simulate_bad_epochs",
]
