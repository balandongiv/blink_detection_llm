"""Morphology feature column header helpers."""

from __future__ import annotations

from typing import Dict, List, Set

import pandas as pd

from .._blink_metrics_shared import ALL_METHODS
from ..constants import cast_columns_to_object
from ..utils.column_headers_common import (
    build_output_columns as build_common_output_columns,
    make_stat_column as make_common_stat_column,
)
from .core_metrics import MORPHOLOGY_METRIC_STEMS

FEATURE_GROUP = "morphology"
STATS = ("mean", "std", "cv")
LEGACY_MORPHOLOGY_METRICS = (
    "duration_base",
    "duration_zero",
    "duration_tent",
    "peak_time_blink",
    "peak_max_blink",
    "peak_time_tent",
    "peak_max_tent",
    "duration_half_base",
    "duration_half_zero",
    "time_shut_base",
    "time_shut_tent",
    "closing_time_tent",
    "reopening_time_tent",
    "closing_time_zero",
    "reopening_time_zero",
    "time_shut_zero",
    "inter_blink_max_amp",
)
LEGACY_METRIC_STYLE_MAP = {
    "duration_base": "base",
    "duration_zero": "zero",
    "duration_tent": "tent",
    "peak_time_blink": "peak",
    "peak_max_blink": "peak",
    "peak_time_tent": "peak",
    "peak_max_tent": "peak",
    "duration_half_base": "half",
    "duration_half_zero": "half",
    "time_shut_base": "base",
    "time_shut_tent": "tent",
    "closing_time_tent": "tent",
    "reopening_time_tent": "tent",
    "closing_time_zero": "zero",
    "reopening_time_zero": "zero",
    "time_shut_zero": "zero",
    "inter_blink_max_amp": "inter_blink",
}
DURATION_STYLE_MAP = {
    "base": "duration_base",
    "zero": "duration_zero",
    "tent": "duration_tent",
    "half": "duration_half_base",
    "half_base": "duration_half_base",
    "half_zero": "duration_half_zero",
}
REQUIRED_LEGACY_MORPHOLOGY_METRICS = frozenset(LEGACY_METRIC_STYLE_MAP)


def rename_metric_column_name(
    modality: str,
    metric: str,
    stat_name: str,
    channel_name: str,
) -> str:
    """Map legacy morphology metric names to historical column tokens."""

    landmark = LEGACY_METRIC_STYLE_MAP[metric]
    return f"{modality}__{landmark}__morphology__{metric}_{stat_name}__{channel_name}"


def metric_method_for_style(style: str) -> str:
    """Map metadata style names to waveform metric methods."""

    return style if style in ALL_METHODS else "base"


def metrics_for_style(style: str) -> List[str]:
    """Return list of metrics for a given style (including duration)."""

    metric_suffix = style if style in ALL_METHODS else "base"
    metric_names = [f"{stem}_{metric_suffix}" for stem in MORPHOLOGY_METRIC_STEMS]
    metric_names.append("duration")
    return metric_names


def make_stat_column(
    *, modality: str, style: str, metric: str, stat: str, channel: str
) -> str:
    """Build a morphology stat column header."""

    return make_common_stat_column(
        modality=modality,
        style=style,
        feature_group=FEATURE_GROUP,
        metric=metric,
        stat=stat,
        channel=channel,
    )


def build_output_columns(
    modality_channels: Dict[str, List[str]],
    styles_by_modality: Dict[str, Set[str]],
) -> List[str]:
    """Build sorted output columns including legacy EEG morphology aliases."""

    def _legacy_columns(modality: str, channels: List[str]) -> List[str]:
        if not channels or modality not in {"eeg", "eog"}:
            return []
        primary_channel = channels[0]
        out: List[str] = []
        for legacy_metric in LEGACY_MORPHOLOGY_METRICS:
            for stat_name in STATS:
                out.append(
                    rename_metric_column_name(
                        modality=modality,
                        metric=legacy_metric,
                        stat_name=stat_name,
                        channel_name=primary_channel,
                    )
                )
        return out

    return build_common_output_columns(
        modality_channels=modality_channels,
        styles_by_modality=styles_by_modality,
        feature_group=FEATURE_GROUP,
        metrics_for_style=metrics_for_style,
        stats=STATS,
        extra_columns=_legacy_columns,
    )


def add_legacy_alias_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Expose uppercase EAR channel aliases used by historical tests."""

    if df.empty:
        return cast_columns_to_object(df)

    alias_updates: Dict[str, pd.Series] = {}
    for col in df.columns:
        if not col.startswith("ear__"):
            continue
        if "__" not in col:
            continue
        head, channel = col.rsplit("__", 1)
        alias_channel = channel.upper()
        if alias_channel == channel:
            continue
        alias_col = f"{head}__{alias_channel}"
        alias_updates[alias_col] = df[col]

    if not alias_updates:
        return cast_columns_to_object(df)
    return cast_columns_to_object(df).assign(**alias_updates)
