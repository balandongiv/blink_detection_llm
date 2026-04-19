"""Strategy E: per-epoch MAD-based threshold scanning and derivative variants."""

from .core import run_e_base_channel, run_e_base_all_channels
from .runner import ALL_E_VARIANTS, channel_results_strategy_e, run_strategy_e
from .soft_shrink import run_e6_soft_shrink_channel

__all__ = [
    "ALL_E_VARIANTS",
    "channel_results_strategy_e",
    "run_e6_soft_shrink_channel",
    "run_e_base_all_channels",
    "run_e_base_channel",
    "run_strategy_e",
]
