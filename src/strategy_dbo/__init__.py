"""Strategy C: single-channel autoreject-backed blink detection."""

from src.config.strategy_dbo_defaults import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    AUTOREJECT_METHOD_ALIASES,
    AUTOREJECT_RANDOM_SEARCH,
    DEFAULT_AUTOREJECT_METHOD,
    DEFAULT_STAGE1_THRESHOLD_SCOPE,
    STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE,
    STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE,
    STAGE1_RANDOM_SCAN_THRESHOLD_SCALE,
    STAGE1_THRESHOLD_SCOPE_ALIASES,
    SUPPORTED_AUTOREJECT_METHODS,
    SUPPORTED_STAGE1_THRESHOLD_SCOPES,
    THRESHOLD_SCOPE_GLOBAL,
    THRESHOLD_SCOPE_PER_CHANNEL,
    get_autoreject_method_aliases,
    get_stage1_threshold_scope_aliases,
    normalize_autoreject_method,
    normalize_stage1_threshold_scope,
    validate_strategy_dbo_options,
)

from .runner import (
    blink_position_strategy_dbo,
    channel_results_strategy_dbo,
    epoch_detection_strategy_dbo_autoreject,
    run_strategy_dbo,
)
from .single_channel_autoreject import (
    learn_strategy_dbo_thresholds,
)


__all__ = [
    "blink_position_strategy_dbo",
    "channel_results_strategy_dbo",
    "epoch_detection_strategy_dbo_autoreject",
    "get_autoreject_method_aliases",
    "get_stage1_threshold_scope_aliases",
    "learn_strategy_dbo_thresholds",
    "normalize_autoreject_method",
    "normalize_stage1_threshold_scope",
    "run_strategy_dbo",
    "validate_strategy_dbo_options",
    "AUTOREJECT_BAYESIAN_OPTIMIZATION",
    "AUTOREJECT_METHOD_ALIASES",
    "AUTOREJECT_RANDOM_SEARCH",
    "DEFAULT_AUTOREJECT_METHOD",
    "DEFAULT_STAGE1_THRESHOLD_SCOPE",
    "STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE",
    "STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE",
    "STAGE1_RANDOM_SCAN_THRESHOLD_SCALE",
    "STAGE1_THRESHOLD_SCOPE_ALIASES",
    "SUPPORTED_AUTOREJECT_METHODS",
    "SUPPORTED_STAGE1_THRESHOLD_SCOPES",
    "THRESHOLD_SCOPE_GLOBAL",
    "THRESHOLD_SCOPE_PER_CHANNEL",
]
