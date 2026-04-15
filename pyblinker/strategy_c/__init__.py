"""Strategy C: single-channel autoreject-backed blink detection."""

from pathlib import Path

import yaml

from .single_channel_autoreject import (
    EpochDetectionStrategyCAutoreject,
    Stage1CandidateDetection,
    Stage1CandidateEvaluation,
    Stage1CandidateLane,
    Stage1ScanResult,
    StrategyCAutorejectResult,
    channel_results_strategy_c,
    epoch_detection_strategy_c_autoreject,
    get_autoreject_method_aliases,
    get_stage1_scan_threshold_scale,
    get_stage1_threshold_scope_aliases,
    normalize_autoreject_method,
    normalize_stage1_threshold_scope,
)

_CONFIG_PATH = Path(__file__).with_name("autoreject_config.yaml")
with _CONFIG_PATH.open("r", encoding="utf-8") as handle:
    _CONFIG = yaml.safe_load(handle)

_AUTOREJECT_METHODS = _CONFIG["autoreject_methods"]
_THRESHOLD_SCOPES = _CONFIG["threshold_scopes"]
_THRESHOLD_SCALES = _CONFIG["stage1_threshold_scales"]
_CHANNELS = _CONFIG["channels"]

AUTOREJECT_BAYESIAN_OPTIMIZATION = str(_AUTOREJECT_METHODS["bayesian_optimization"])
AUTOREJECT_METHOD_ALIASES = get_autoreject_method_aliases()
AUTOREJECT_RANDOM_SEARCH = str(_AUTOREJECT_METHODS["random_search"])
CONSENSUS_CHANNEL_NAME = str(_CHANNELS["consensus_name"])
DEFAULT_AUTOREJECT_METHOD = str(_AUTOREJECT_METHODS["default"])
DEFAULT_STAGE1_THRESHOLD_SCOPE = str(_THRESHOLD_SCOPES["default"])
DEFAULT_STRATEGY_C_CHANNELS = tuple(_CHANNELS["default_strategy_c"])
SEED_RESCUE_CHANNEL = str(_CHANNELS["seed_rescue"])
STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE = float(_THRESHOLD_SCALES["bayesian"])
STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE = float(_THRESHOLD_SCALES["global"])
STAGE1_RANDOM_SCAN_THRESHOLD_SCALE = float(_THRESHOLD_SCALES["random"])
STAGE1_THRESHOLD_SCOPE_ALIASES = get_stage1_threshold_scope_aliases()
SUPPORTED_AUTOREJECT_METHODS = (
    str(_AUTOREJECT_METHODS["random_search"]),
    str(_AUTOREJECT_METHODS["bayesian_optimization"]),
)
SUPPORTED_STAGE1_THRESHOLD_SCOPES = (
    str(_THRESHOLD_SCOPES["per_channel"]),
    str(_THRESHOLD_SCOPES["global"]),
)
THRESHOLD_SCOPE_GLOBAL = str(_THRESHOLD_SCOPES["global"])
THRESHOLD_SCOPE_PER_CHANNEL = str(_THRESHOLD_SCOPES["per_channel"])


__all__ = [
    "EpochDetectionStrategyCAutoreject",
    "Stage1CandidateDetection",
    "Stage1CandidateEvaluation",
    "Stage1CandidateLane",
    "Stage1ScanResult",
    "StrategyCAutorejectResult",
    "channel_results_strategy_c",
    "epoch_detection_strategy_c_autoreject",
    "get_autoreject_method_aliases",
    "get_stage1_scan_threshold_scale",
    "get_stage1_threshold_scope_aliases",
    "normalize_autoreject_method",
    "normalize_stage1_threshold_scope",
    "AUTOREJECT_BAYESIAN_OPTIMIZATION",
    "AUTOREJECT_METHOD_ALIASES",
    "AUTOREJECT_RANDOM_SEARCH",
    "CONSENSUS_CHANNEL_NAME",
    "DEFAULT_AUTOREJECT_METHOD",
    "DEFAULT_STAGE1_THRESHOLD_SCOPE",
    "DEFAULT_STRATEGY_C_CHANNELS",
    "SEED_RESCUE_CHANNEL",
    "STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE",
    "STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE",
    "STAGE1_RANDOM_SCAN_THRESHOLD_SCALE",
    "STAGE1_THRESHOLD_SCOPE_ALIASES",
    "SUPPORTED_AUTOREJECT_METHODS",
    "SUPPORTED_STAGE1_THRESHOLD_SCOPES",
    "THRESHOLD_SCOPE_GLOBAL",
    "THRESHOLD_SCOPE_PER_CHANNEL",
]
