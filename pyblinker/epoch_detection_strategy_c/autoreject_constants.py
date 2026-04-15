"""Load autoreject configuration from autoreject_config.yaml and expose module constants."""

from __future__ import annotations

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).with_name("autoreject_config.yaml")


def _load_config() -> dict:
    with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


_cfg = _load_config()

# --- Channels ---
DEFAULT_STRATEGY_C_CHANNELS: tuple[str, ...] = tuple(_cfg["channels"]["default_strategy_c"])
SEED_RESCUE_CHANNEL: str = _cfg["channels"]["seed_rescue"]
CONSENSUS_CHANNEL_NAME: str = _cfg["channels"]["consensus_name"]

# --- Autoreject methods ---
AUTOREJECT_RANDOM_SEARCH: str = _cfg["autoreject_methods"]["random_search"]
AUTOREJECT_BAYESIAN_OPTIMIZATION: str = _cfg["autoreject_methods"]["bayesian_optimization"]
DEFAULT_AUTOREJECT_METHOD: str = _cfg["autoreject_methods"]["default"]
AUTOREJECT_METHOD_ALIASES: dict[str, str] = {
    AUTOREJECT_RANDOM_SEARCH: AUTOREJECT_RANDOM_SEARCH,
    AUTOREJECT_BAYESIAN_OPTIMIZATION: AUTOREJECT_BAYESIAN_OPTIMIZATION,
    **_cfg["autoreject_methods"]["aliases"],
}
SUPPORTED_AUTOREJECT_METHODS: tuple[str, ...] = (
    AUTOREJECT_RANDOM_SEARCH,
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
)

# --- Threshold scopes ---
THRESHOLD_SCOPE_PER_CHANNEL: str = _cfg["threshold_scopes"]["per_channel"]
THRESHOLD_SCOPE_GLOBAL: str = _cfg["threshold_scopes"]["global"]
DEFAULT_STAGE1_THRESHOLD_SCOPE: str = _cfg["threshold_scopes"]["default"]
STAGE1_THRESHOLD_SCOPE_ALIASES: dict[str, str] = {
    THRESHOLD_SCOPE_PER_CHANNEL: THRESHOLD_SCOPE_PER_CHANNEL,
    THRESHOLD_SCOPE_GLOBAL: THRESHOLD_SCOPE_GLOBAL,
    **_cfg["threshold_scopes"]["aliases"],
}
SUPPORTED_STAGE1_THRESHOLD_SCOPES: tuple[str, ...] = (
    THRESHOLD_SCOPE_PER_CHANNEL,
    THRESHOLD_SCOPE_GLOBAL,
)

# --- Stage 1 threshold scales ---
STAGE1_RANDOM_SCAN_THRESHOLD_SCALE: float = float(_cfg["stage1_threshold_scales"]["random"])
STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE: float = float(_cfg["stage1_threshold_scales"]["bayesian"])
STAGE1_GLOBAL_SCAN_THRESHOLD_SCALE: float = float(_cfg["stage1_threshold_scales"]["global"])

# --- Benchmark and ignored args ---
REFERENCE_BENCHMARK: dict = _cfg["reference_benchmark"]
IGNORED_TEMPLATE_ARGS: tuple[str, ...] = tuple(_cfg["ignored_template_args"])


__all__ = [
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
