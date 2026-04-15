"""Kinematic feature column header helpers."""

from __future__ import annotations

from typing import Dict, List, Set

import pandas as pd

from ..constants import cast_columns_to_object
from ..utils.column_headers_common import (
    build_output_columns as build_common_output_columns,
    make_stat_column as make_common_stat_column,
)
from .core_metrics import KINEMATIC_METRIC_STEMS, KINEMATIC_METRICS_NO_STYLE

FEATURE_GROUP = "kinematic"
STATS = ("mean", "std", "cv")
EXTENDED_METRICS = (
    "aver_left_velocity",
    "aver_right_velocity",
    "neg_amp_vel_ratio_base",
    "pos_amp_vel_ratio_base",
    "neg_amp_vel_ratio_zero",
    "pos_amp_vel_ratio_zero",
    "neg_amp_vel_ratio_tent",
    "pos_amp_vel_ratio_tent",
    "inter_blink_max_vel_base",
    "inter_blink_max_vel_zero",
)


def metrics_for_style(style: str) -> List[str]:
    """Return output metric names for a segmentation style."""

    metric_suffix = style if style in {"base", "zero", "tent"} else "base"
    return [
        stem if stem in KINEMATIC_METRICS_NO_STYLE else f"{stem}_{metric_suffix}"
        for stem in KINEMATIC_METRIC_STEMS
    ]


def make_stat_column(
    *, modality: str, style: str, metric: str, stat: str, channel: str
) -> str:
    """Build a kinematic stat column header."""

    return make_common_stat_column(
        modality=modality,
        style=style,
        feature_group=FEATURE_GROUP,
        metric=metric,
        stat=stat,
        channel=channel,
    )


def _all_metrics_for_style(style: str) -> List[str]:
    names = metrics_for_style(style)
    names.extend(EXTENDED_METRICS)
    return names


def build_output_columns(
    modality_channels: Dict[str, List[str]],
    styles_by_modality: Dict[str, Set[str]],
) -> List[str]:
    """Build sorted unique kinematics output columns."""

    return build_common_output_columns(
        modality_channels=modality_channels,
        styles_by_modality=styles_by_modality,
        feature_group=FEATURE_GROUP,
        metrics_for_style=_all_metrics_for_style,
        stats=STATS,
    )


def add_legacy_alias_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Expose historical EAR interpolation column aliases used by old tests."""

    if df.empty:
        return cast_columns_to_object(df)

    alias_updates: Dict[str, pd.Series] = {}
    for col in df.columns:
        if "ear__th_interpolation__kinematic__" not in col:
            continue
        alias_col = col.replace(
            "ear__th_interpolation__", "ear__ interpolated_threshold__"
        )
        if "__" in alias_col:
            head, tail = alias_col.rsplit("__", 1)
            alias_col = f"{head}____{tail}"
        alias_updates[alias_col] = df[col]

    if not alias_updates:
        return cast_columns_to_object(df)

    return cast_columns_to_object(df).assign(**alias_updates)
