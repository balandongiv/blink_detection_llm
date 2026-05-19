"""Strategy C configuration defaults, aliases, and normalization."""

from __future__ import annotations

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "strategy_c" / "autoreject_config.yaml"
with _CONFIG_PATH.open("r", encoding="utf-8") as handle:
    _CONFIG = yaml.safe_load(handle)

_AUTOREJECT_METHODS = _CONFIG["autoreject_methods"]
_THRESHOLD_SCOPES = _CONFIG["threshold_scopes"]
_THRESHOLD_SCALES = _CONFIG["stage1_threshold_scales"]

AUTOREJECT_RANDOM_SEARCH = str(_AUTOREJECT_METHODS["random_search"])
AUTOREJECT_BAYESIAN_OPTIMIZATION = str(_AUTOREJECT_METHODS["bayesian_optimization"])
DEFAULT_AUTOREJECT_METHOD = str(_AUTOREJECT_METHODS["default"])

THRESHOLD_SCOPE_PER_CHANNEL = str(_THRESHOLD_SCOPES["per_channel"])
THRESHOLD_SCOPE_GLOBAL = str(_THRESHOLD_SCOPES["global"])
DEFAULT_STAGE1_THRESHOLD_SCOPE = str(_THRESHOLD_SCOPES["default"])

AUTOREJECT_METHOD_ALIASES = {
    AUTOREJECT_RANDOM_SEARCH: AUTOREJECT_RANDOM_SEARCH,
    AUTOREJECT_BAYESIAN_OPTIMIZATION: AUTOREJECT_BAYESIAN_OPTIMIZATION,
    **{str(key): str(value) for key, value in _AUTOREJECT_METHODS.get("aliases", {}).items()},
}
STAGE1_THRESHOLD_SCOPE_ALIASES = {
    THRESHOLD_SCOPE_PER_CHANNEL: THRESHOLD_SCOPE_PER_CHANNEL,
    THRESHOLD_SCOPE_GLOBAL: THRESHOLD_SCOPE_GLOBAL,
    **{str(key): str(value) for key, value in _THRESHOLD_SCOPES.get("aliases", {}).items()},
}

SUPPORTED_AUTOREJECT_METHODS = (
    AUTOREJECT_RANDOM_SEARCH,
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
)
SUPPORTED_STAGE1_THRESHOLD_SCOPES = (
    THRESHOLD_SCOPE_PER_CHANNEL,
    THRESHOLD_SCOPE_GLOBAL,
)

STAGE1_RANDOM_SCAN_THRESHOLD_SCALE = float(_THRESHOLD_SCALES["random"])
STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE = float(_THRESHOLD_SCALES["bayesian"])
STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE = float(_THRESHOLD_SCALES["global"])


def get_autoreject_method_aliases() -> dict[str, str]:
    return dict(AUTOREJECT_METHOD_ALIASES)


def get_stage1_threshold_scope_aliases() -> dict[str, str]:
    return dict(STAGE1_THRESHOLD_SCOPE_ALIASES)


def normalize_autoreject_method(autoreject_method: str | None) -> str:
    if autoreject_method is None:
        return DEFAULT_AUTOREJECT_METHOD

    key = str(autoreject_method).strip().lower()
    if key not in AUTOREJECT_METHOD_ALIASES:
        supported = ", ".join(sorted(AUTOREJECT_METHOD_ALIASES))
        raise ValueError(
            f"Unsupported autoreject_method={autoreject_method!r}. Use one of: {supported}."
        )
    return AUTOREJECT_METHOD_ALIASES[key]


def normalize_stage1_threshold_scope(stage1_threshold_scope: str | None) -> str:
    if stage1_threshold_scope is None:
        return DEFAULT_STAGE1_THRESHOLD_SCOPE

    key = str(stage1_threshold_scope).strip().lower()
    if key not in STAGE1_THRESHOLD_SCOPE_ALIASES:
        supported = ", ".join(sorted(STAGE1_THRESHOLD_SCOPE_ALIASES))
        raise ValueError(
            "Unsupported threshold_scope="
            f"{stage1_threshold_scope!r}. Use one of: {supported}."
        )
    return STAGE1_THRESHOLD_SCOPE_ALIASES[key]


def validate_strategy_c_options(
    *,
    autoreject_method: str | None,
    stage1_threshold_scope: str | None,
) -> tuple[str, str]:
    return (
        normalize_autoreject_method(autoreject_method),
        normalize_stage1_threshold_scope(stage1_threshold_scope),
    )


__all__ = [
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
    "get_autoreject_method_aliases",
    "get_stage1_threshold_scope_aliases",
    "normalize_autoreject_method",
    "normalize_stage1_threshold_scope",
    "validate_strategy_c_options",
]
