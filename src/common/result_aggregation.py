"""Channel aggregation and candidate selection for epoch-mode detection."""

from __future__ import annotations

import pandas as pd

from pyblinker.blinker.get_representative_channel import channel_selection


def aggregate_channel_results(results) -> pd.DataFrame:
    """Build a channel summary frame from per-channel worker outputs."""

    rows: list[dict[str, object]] = []
    for result in results:
        row = dict(result.stats)
        row["valid_epoch_count"] = result.n_valid_epochs
        row["epochs_with_detections"] = result.n_epochs_with_detections
        row["detection_epoch_fraction"] = (
            float(result.n_epochs_with_detections) / float(result.n_valid_epochs)
            if result.n_valid_epochs > 0
            else 0.0
        )
        row["pavr_passed_events"] = result.n_pavr_passed
        rows.append(row)
    return pd.DataFrame(rows)


def select_candidate_channel_from_results(results, params: dict) -> pd.DataFrame:
    """Reuse the legacy channel-ranking logic on epoch-mode summaries."""

    summary = aggregate_channel_results(results)
    if summary.empty:
        return pd.DataFrame()
    selected = channel_selection(summary.copy(), params)
    selected.reset_index(drop=True, inplace=True)
    return selected


def get_selected_channel_result(results, selected: pd.DataFrame):
    """Return the worker result corresponding to the chosen channel."""

    if selected.empty or "ch" not in selected.columns:
        return None
    channel = selected.loc[0, "ch"]
    for result in results:
        if result.channel == channel:
            return result
    return None


__all__ = [
    "aggregate_channel_results",
    "get_selected_channel_result",
    "select_candidate_channel_from_results",
]
