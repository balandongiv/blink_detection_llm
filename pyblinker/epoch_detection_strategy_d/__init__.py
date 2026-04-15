"""Strategy D: autoreject Bayesian-optimised PTP threshold + MNE peak_finder."""

from .core import learn_bayesian_thresholds, peaks_to_candidates
from .runner import blink_position_strategy_d, run_strategy_d

__all__ = [
    "blink_position_strategy_d",
    "learn_bayesian_thresholds",
    "peaks_to_candidates",
    "run_strategy_d",
]
