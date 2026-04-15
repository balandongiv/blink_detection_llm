"""Shared helpers for feature column header formatting and schema generation."""

from __future__ import annotations

from typing import Callable, Iterable, Sequence


def make_stat_column(
    *,
    modality: str,
    style: str,
    feature_group: str,
    metric: str,
    stat: str,
    channel: str,
) -> str:
    """Return canonical stat column name for blink feature outputs."""

    return f"{modality}__{style}__{feature_group}__{metric}_{stat}__{channel}"


def build_output_columns(
    *,
    modality_channels: dict[str, list[str]],
    styles_by_modality: dict[str, set[str]],
    feature_group: str,
    metrics_for_style: Callable[[str], Sequence[str]],
    stats: Sequence[str],
    channel_label: Callable[[str, str], str] | None = None,
    extra_columns: Callable[[str, list[str]], Iterable[str]] | None = None,
    default_styles: set[str] | None = None,
) -> list[str]:
    """Build sorted unique output column list using common modality/style loop."""

    channel_label = channel_label or (lambda ch, _mod: ch)
    default_styles = default_styles or {"base"}

    column_set: set[str] = set()
    for modality, channels in modality_channels.items():
        styles = sorted(styles_by_modality.get(modality) or default_styles)
        for style in styles:
            for metric in metrics_for_style(style):
                for stat in stats:
                    for channel in channels:
                        column_set.add(
                            make_stat_column(
                                modality=modality,
                                style=style,
                                feature_group=feature_group,
                                metric=metric,
                                stat=stat,
                                channel=channel_label(channel, modality),
                            )
                        )

        if extra_columns is not None:
            column_set.update(extra_columns(modality, channels))

    return sorted(column_set)
