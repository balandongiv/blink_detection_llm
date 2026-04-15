"""Pure helper functions for the Strategy C autoreject detector.

All functions here are side-effect-free and can be imported and tested
independently of the main EpochDetectionStrategyCAutoreject class.

Cross-strategy utilities (_empty_annotations, finalize_blink_table,
build_epoch_boundaries) live in pyblinker.common.pipeline_utils.
"""

from __future__ import annotations

import mne
import numpy as np
import pandas as pd

from pyblinker.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.common.epoch_io import normalize_blink_table
from pyblinker.common.pipeline_utils import (
    build_epoch_boundaries,
    empty_annotations,
    finalize_blink_table,
)

from .autoreject_constants import (
    AUTOREJECT_METHOD_ALIASES,
    REFERENCE_BENCHMARK,
    STAGE1_THRESHOLD_SCOPE_ALIASES,
    SUPPORTED_AUTOREJECT_METHODS,
    SUPPORTED_STAGE1_THRESHOLD_SCOPES,
)


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

def normalize_autoreject_method(autoreject_method: str) -> str:
    """Return a canonical autoreject search method or raise a clear error."""

    key = str(autoreject_method).strip().lower()
    try:
        return AUTOREJECT_METHOD_ALIASES[key]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_AUTOREJECT_METHODS)
        raise ValueError(
            f"Unsupported autoreject_method={autoreject_method!r}. "
            f"Use one of: {supported}."
        ) from exc


def normalize_stage1_threshold_scope(stage1_threshold_scope: str) -> str:
    """Return a canonical Stage 1 threshold scope or raise a clear error."""

    key = str(stage1_threshold_scope).strip().lower()
    try:
        return STAGE1_THRESHOLD_SCOPE_ALIASES[key]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_STAGE1_THRESHOLD_SCOPES)
        raise ValueError(
            f"Unsupported stage1_threshold_scope={stage1_threshold_scope!r}. "
            f"Use one of: {supported}."
        ) from exc


# ---------------------------------------------------------------------------
# Benchmark comparison
# ---------------------------------------------------------------------------

def compare_with_reference_benchmark(metrics) -> dict[str, dict[str, float | int]]:
    """Return delta-to-benchmark summaries for the documented Step 1 baselines."""

    return {
        "vs_strategy_a_step1": {
            "delta_tp": int(metrics.true_positives - REFERENCE_BENCHMARK["strategy_a_step1"]["TP"]),
            "delta_fp": int(metrics.false_positives - REFERENCE_BENCHMARK["strategy_a_step1"]["FP"]),
            "delta_fn": int(metrics.false_negatives - REFERENCE_BENCHMARK["strategy_a_step1"]["FN"]),
        },
        "vs_strategy_b_step1": {
            "delta_tp": int(metrics.true_positives - REFERENCE_BENCHMARK["strategy_b_step1"]["TP"]),
            "delta_fp": int(metrics.false_positives - REFERENCE_BENCHMARK["strategy_b_step1"]["FP"]),
            "delta_fn": int(metrics.false_negatives - REFERENCE_BENCHMARK["strategy_b_step1"]["FN"]),
        },
    }


# ---------------------------------------------------------------------------
# Empty-frame factories
# ---------------------------------------------------------------------------

def _empty_candidate_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "epoch_index",
            "channel",
            "blink_onset",
            "blink_duration",
            "start_blink",
            "end_blink",
            "candidate_source",
        ]
    )


# ---------------------------------------------------------------------------
# Event overlap and deduplication
# ---------------------------------------------------------------------------

def _interval_overlap_ratio(
    pred_onset: float,
    pred_duration: float,
    ref_onset: float,
    ref_duration: float,
) -> float:
    pred_end = pred_onset + max(pred_duration, 0.0)
    ref_end = ref_onset + max(ref_duration, 0.0)
    overlap = max(0.0, min(pred_end, ref_end) - max(pred_onset, ref_onset))
    denom = max(min(pred_end - pred_onset, ref_end - ref_onset), 1e-12)
    return overlap / denom


def _events_match(
    row_a: pd.Series,
    row_b: pd.Series,
    *,
    onset_tolerance_s: float = 0.1,
    duration_tolerance_s: float = 0.1,
    overlap_threshold: float = 0.5,
) -> bool:
    onset_diff = abs(float(row_a["blink_onset"]) - float(row_b["blink_onset"]))
    duration_diff = abs(float(row_a["blink_duration"]) - float(row_b["blink_duration"]))
    overlap = _interval_overlap_ratio(
        float(row_a["blink_onset"]),
        float(row_a["blink_duration"]),
        float(row_b["blink_onset"]),
        float(row_b["blink_duration"]),
    )
    return onset_diff <= onset_tolerance_s and (
        duration_diff <= duration_tolerance_s or overlap >= overlap_threshold
    )


def _dedup_union(*tables: pd.DataFrame) -> pd.DataFrame:
    frames = [table.copy() for table in tables if table is not None and not table.empty]
    if not frames:
        return pd.DataFrame(
            columns=[
                "epoch_index",
                "channel",
                "blink_onset",
                "blink_duration",
                "start_blink",
                "end_blink",
                "candidate_source",
            ]
        )

    concatenated = pd.concat(frames, ignore_index=True, sort=False)
    concatenated = concatenated.sort_values(
        ["epoch_index", "blink_onset", "blink_duration"]
    ).reset_index(drop=True)

    kept_rows: list[pd.Series] = []
    for _, row in concatenated.iterrows():
        duplicate = any(
            int(existing["epoch_index"]) == int(row["epoch_index"])
            and _events_match(row, existing)
            for existing in kept_rows
        )
        if not duplicate:
            kept_rows.append(row)

    return pd.DataFrame(kept_rows).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Rescue lane helpers
# ---------------------------------------------------------------------------

def _cluster_seed_events(seed_mapped: pd.DataFrame) -> list[tuple[int, list[pd.Series]]]:
    clusters: list[tuple[int, list[pd.Series]]] = []
    if seed_mapped.empty:
        return clusters

    for epoch_index, group in seed_mapped.groupby("epoch_index"):
        group = group.sort_values("blink_onset").reset_index(drop=True)
        current_cluster = [group.iloc[0]]
        for row_index in range(1, len(group)):
            row = group.iloc[row_index]
            prev = current_cluster[-1]
            if float(row["blink_onset"]) - float(prev["blink_onset"]) <= 0.15:
                current_cluster.append(row)
            else:
                if len(current_cluster) >= 2:
                    clusters.append((int(epoch_index), current_cluster))
                current_cluster = [row]
        if len(current_cluster) >= 2:
            clusters.append((int(epoch_index), current_cluster))
    return clusters


def _is_cluster_already_covered(
    epoch_index: int,
    cluster: list[pd.Series],
    baseline: pd.DataFrame,
) -> bool:
    baseline_epoch = baseline[baseline["epoch_index"] == epoch_index]
    if baseline_epoch.empty:
        return False
    for seed_row in cluster:
        for _, baseline_row in baseline_epoch.iterrows():
            if abs(float(seed_row["blink_onset"]) - float(baseline_row["blink_onset"])) <= 0.15:
                return True
    return False


__all__ = [
    "build_epoch_boundaries",
    "compare_with_reference_benchmark",
    "empty_annotations",
    "finalize_blink_table",
    "normalize_autoreject_method",
    "normalize_stage1_threshold_scope",
    "_cluster_seed_events",
    "_dedup_union",
    "_empty_candidate_table",
    "_events_match",
    "_interval_overlap_ratio",
    "_is_cluster_already_covered",
]
