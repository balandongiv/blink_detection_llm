"""Strategy F: Two-stage autoreject + robust median/MAD blink detection.

Stage A uses AutoReject to identify suspicious (blink-heavy) epochs.
Stage B computes a per-channel sample-level threshold from those epochs
       using robust statistics (median + k * MAD).
Stage C detects blink regions via threshold crossings.
"""

from src.common.bad_epochs import get_valid_epoch_indices, simulate_bad_epochs
from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input

from .autoreject_epoch_screener import screen_epochs_with_autoreject
from .blink_threshold import compute_flagged_epoch_threshold
from .core import blink_position_strategy_dbo_drop
from .runner import channel_results_strategy_dbo_drop, run_strategy_dbo_drop

__all__ = [
    "PreparedEpochDetectionInput",
    "blink_position_strategy_dbo_drop",
    "channel_results_strategy_dbo_drop",
    "compute_flagged_epoch_threshold",
    "get_valid_epoch_indices",
    "prepare_epoch_detection_input",
    "run_strategy_dbo_drop",
    "screen_epochs_with_autoreject",
    "simulate_bad_epochs",
]
