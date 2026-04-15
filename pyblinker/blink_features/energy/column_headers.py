"""Energy feature column header helpers."""

from __future__ import annotations

from typing import Dict, List, Set

from ..utils.column_headers_common import (
    build_output_columns as build_common_output_columns,
    make_stat_column as make_common_stat_column,
)

FEATURE_GROUP = "energy"
STATS = ("mean", "std", "cv")
METRICS = (
    "blink_signal_energy",
    "teager_kaiser_energy",
    "blink_line_length",
    "blink_velocity_integral",
)


def metrics_for_style(style: str) -> List[str]:
    """Return energy metrics for a segmentation style."""

    _ = style
    return list(METRICS)


def channel_label(channel_name: str, modality: str) -> str:
    """Return output-channel label for feature columns by modality."""

    return channel_name if modality == "eog" else channel_name.upper()


def make_stat_column(
    *, modality: str, style: str, metric: str, stat: str, channel: str
) -> str:
    """Build an energy stat column header."""

    return make_common_stat_column(
        modality=modality,
        style=style,
        feature_group=FEATURE_GROUP,
        metric=metric,
        stat=stat,
        channel=channel,
    )


def build_output_columns(
    modality_by_channel: Dict[str, str],
    styles_by_modality: Dict[str, Set[str]],
) -> List[str]:
    """Generate ordered output columns for modality/style/metric/stat combinations."""

    modality_channels: Dict[str, List[str]] = {}
    for channel, modality in modality_by_channel.items():
        modality_channels.setdefault(modality, []).append(channel)

    columns = build_common_output_columns(
        modality_channels=modality_channels,
        styles_by_modality=styles_by_modality,
        feature_group=FEATURE_GROUP,
        metrics_for_style=metrics_for_style,
        stats=STATS,
        channel_label=lambda ch, mod: channel_label(ch, mod),
    )

    ordered_columns: List[str] = []
    for channel, modality in modality_by_channel.items():
        for style in sorted(styles_by_modality.get(modality, set())):
            for metric in METRICS:
                for stat in STATS:
                    col = make_stat_column(
                        modality=modality,
                        style=style,
                        metric=metric,
                        stat=stat,
                        channel=channel_label(channel, modality),
                    )
                    if col in columns:
                        ordered_columns.append(col)
    return ordered_columns


def add_legacy_alias_columns(df):
    """Return energy frame unchanged (no legacy aliases)."""

    return df
