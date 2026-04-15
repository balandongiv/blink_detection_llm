"""Strategy C: single-channel autoreject-backed blink detection."""

from .single_channel_autoreject import (
    EpochDetectionStrategyCAutoreject,
    Stage1CandidateDetection,
    Stage1CandidateEvaluation,
    Stage1CandidateLane,
    Stage1ScanResult,
    StrategyCAutorejectResult,
    channel_results_strategy_c,
    compare_with_reference_benchmark,
    epoch_detection_strategy_c_autoreject,
    get_autoreject_method_aliases,
    get_default_autoreject_method,
    get_default_stage1_threshold_scope,
    get_default_strategy_c_channels,
    get_ignored_template_args,
    get_reference_benchmark,
    get_stage1_scan_threshold_scale,
    get_stage1_threshold_scope_aliases,
    load_strategy_c_config,
    normalize_autoreject_method,
    normalize_stage1_threshold_scope,
    summarize_stage1_detections,
)


def __getattr__(name: str):
    config = load_strategy_c_config()
    autoreject_methods = config["autoreject_methods"]
    threshold_scopes = config["threshold_scopes"]
    threshold_scales = config["stage1_threshold_scales"]
    channels = config["channels"]

    dynamic_values = {
        "AUTOREJECT_BAYESIAN_OPTIMIZATION": str(autoreject_methods["bayesian_optimization"]),
        "AUTOREJECT_METHOD_ALIASES": get_autoreject_method_aliases(),
        "AUTOREJECT_RANDOM_SEARCH": str(autoreject_methods["random_search"]),
        "CONSENSUS_CHANNEL_NAME": str(channels["consensus_name"]),
        "DEFAULT_AUTOREJECT_METHOD": get_default_autoreject_method(),
        "DEFAULT_STAGE1_THRESHOLD_SCOPE": get_default_stage1_threshold_scope(),
        "DEFAULT_STRATEGY_C_CHANNELS": get_default_strategy_c_channels(),
        "IGNORED_TEMPLATE_ARGS": get_ignored_template_args(),
        "REFERENCE_BENCHMARK": get_reference_benchmark(),
        "SEED_RESCUE_CHANNEL": str(channels["seed_rescue"]),
        "STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE": float(threshold_scales["bayesian"]),
        "STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE": float(threshold_scales["global"]),
        "STAGE1_RANDOM_SCAN_THRESHOLD_SCALE": float(threshold_scales["random"]),
        "STAGE1_THRESHOLD_SCOPE_ALIASES": get_stage1_threshold_scope_aliases(),
        "SUPPORTED_AUTOREJECT_METHODS": (
            str(autoreject_methods["random_search"]),
            str(autoreject_methods["bayesian_optimization"]),
        ),
        "SUPPORTED_STAGE1_THRESHOLD_SCOPES": (
            str(threshold_scopes["per_channel"]),
            str(threshold_scopes["global"]),
        ),
        "THRESHOLD_SCOPE_GLOBAL": str(threshold_scopes["global"]),
        "THRESHOLD_SCOPE_PER_CHANNEL": str(threshold_scopes["per_channel"]),
    }
    if name in dynamic_values:
        return dynamic_values[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "EpochDetectionStrategyCAutoreject",
    "Stage1CandidateDetection",
    "Stage1CandidateEvaluation",
    "Stage1CandidateLane",
    "Stage1ScanResult",
    "StrategyCAutorejectResult",
    "channel_results_strategy_c",
    "compare_with_reference_benchmark",
    "epoch_detection_strategy_c_autoreject",
    "get_autoreject_method_aliases",
    "get_default_autoreject_method",
    "get_default_stage1_threshold_scope",
    "get_default_strategy_c_channels",
    "get_ignored_template_args",
    "get_reference_benchmark",
    "get_stage1_scan_threshold_scale",
    "get_stage1_threshold_scope_aliases",
    "load_strategy_c_config",
    "normalize_autoreject_method",
    "normalize_stage1_threshold_scope",
    "summarize_stage1_detections",
    "AUTOREJECT_BAYESIAN_OPTIMIZATION",
    "AUTOREJECT_METHOD_ALIASES",
    "AUTOREJECT_RANDOM_SEARCH",
    "CONSENSUS_CHANNEL_NAME",
    "DEFAULT_AUTOREJECT_METHOD",
    "DEFAULT_STAGE1_THRESHOLD_SCOPE",
    "DEFAULT_STRATEGY_C_CHANNELS",
    "IGNORED_TEMPLATE_ARGS",
    "REFERENCE_BENCHMARK",
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
