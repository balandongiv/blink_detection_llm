"""Strategy C: single-channel autoreject-backed blink detection."""

from src.config.strategy_c_defaults import (
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
    validate_strategy_c_options,
)

from .runner import (
    blink_position_strategy_c,
    channel_results_strategy_c,
    epoch_detection_strategy_c_autoreject,
    run_strategy_c,
)
from .single_channel_autoreject import (
    learn_strategy_c_thresholds,
)


__all__ = [
    "blink_position_strategy_c",
    "channel_results_strategy_c",
    "epoch_detection_strategy_c_autoreject",
    "get_autoreject_method_aliases",
    "get_stage1_threshold_scope_aliases",
    "learn_strategy_c_thresholds",
    "normalize_autoreject_method",
    "normalize_stage1_threshold_scope",
    "run_strategy_c",
    "validate_strategy_c_options",
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
