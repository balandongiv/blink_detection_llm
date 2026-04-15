"""Strategy C: autoreject-backed blink epoch detection."""

from .autoreject_constants import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    AUTOREJECT_METHOD_ALIASES,
    AUTOREJECT_RANDOM_SEARCH,
    CONSENSUS_CHANNEL_NAME,
    DEFAULT_AUTOREJECT_METHOD,
    DEFAULT_STAGE1_THRESHOLD_SCOPE,
    DEFAULT_STRATEGY_C_CHANNELS,
    IGNORED_TEMPLATE_ARGS,
    REFERENCE_BENCHMARK,
    SEED_RESCUE_CHANNEL,
    STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE,
    STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE,
    STAGE1_RANDOM_SCAN_THRESHOLD_SCALE,
    STAGE1_THRESHOLD_SCOPE_ALIASES,
    SUPPORTED_AUTOREJECT_METHODS,
    SUPPORTED_STAGE1_THRESHOLD_SCOPES,
    THRESHOLD_SCOPE_GLOBAL,
    THRESHOLD_SCOPE_PER_CHANNEL,
)
from .autoreject_types import (
    Stage1CandidateDetection,
    Stage1CandidateEvaluation,
    Stage1CandidateLane,
    Stage1ScanResult,
    StrategyCAutorejectResult,
)
from .autoreject_utils import (
    compare_with_reference_benchmark,
    normalize_autoreject_method,
    normalize_stage1_threshold_scope,
)
from .epoch_detection_strategy_c_autoreject import (
    EpochDetectionStrategyCAutoreject,
    epoch_detection_strategy_c_autoreject,
)
from .strategy_c_config import DEFAULT_FRONTAL_CHANNEL_PATTERNS, StrategyCConfig

__all__ = [
    "AUTOREJECT_BAYESIAN_OPTIMIZATION",
    "AUTOREJECT_METHOD_ALIASES",
    "AUTOREJECT_RANDOM_SEARCH",
    "CONSENSUS_CHANNEL_NAME",
    "DEFAULT_AUTOREJECT_METHOD",
    "DEFAULT_FRONTAL_CHANNEL_PATTERNS",
    "DEFAULT_STAGE1_THRESHOLD_SCOPE",
    "DEFAULT_STRATEGY_C_CHANNELS",
    "EpochDetectionStrategyCAutoreject",
    "IGNORED_TEMPLATE_ARGS",
    "REFERENCE_BENCHMARK",
    "SEED_RESCUE_CHANNEL",
    "STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE",
    "STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE",
    "STAGE1_RANDOM_SCAN_THRESHOLD_SCALE",
    "STAGE1_THRESHOLD_SCOPE_ALIASES",
    "Stage1CandidateDetection",
    "Stage1CandidateEvaluation",
    "Stage1CandidateLane",
    "Stage1ScanResult",
    "StrategyCAutorejectResult",
    "StrategyCConfig",
    "SUPPORTED_AUTOREJECT_METHODS",
    "SUPPORTED_STAGE1_THRESHOLD_SCOPES",
    "THRESHOLD_SCOPE_GLOBAL",
    "THRESHOLD_SCOPE_PER_CHANNEL",
    "compare_with_reference_benchmark",
    "epoch_detection_strategy_c_autoreject",
    "normalize_autoreject_method",
    "normalize_stage1_threshold_scope",
]
