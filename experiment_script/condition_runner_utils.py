"""Shared helpers for analyses that re-run the five exp2 detector conditions.

Both ``exp7_epoch_health_effect`` and ``exp8_long_blink_analysis`` need to run the
same five conditions used in the main comparison — BLINKER-concat, MNE-annot, DBO,
Proposed-Mean, Proposed-Med — on a session, but under different epoch sets or
against different ground-truth subsets.  To guarantee identical detector
configuration, the condition runners are imported directly from
``exp2_strategy_comparison`` rather than re-declared.
"""

from __future__ import annotations

from pathlib import Path

import mne

from blink_evaluation import (
    enrich_absolute_times,
    evaluate_channels,
    load_annotation_as_reference,
)
from blink_evaluation.io import dataframe_to_annotations
from src.common.epoch_input import prepare_epoch_detection_input
from experiment_script.channel_group_config import apply_stage_a_channel_group
from tutorial.tutorial_utils import (
    DEFAULT_CAO_REGION_YAML,
    DEFAULT_RAJA_REGION_YAML,
    make_dataset_loaders,
)

# Reuse the exact condition runners + ordering from the main comparison.
from experiment_script.exp2_strategy_comparison import CONDITIONS, _CONDITION_RUNNERS

__all__ = [
    "CONDITIONS",
    "prepare_session",
    "reference_dataframe",
    "annotations_from_reference",
    "run_condition",
]


def prepare_session(
    pair: dict,
    epoch_duration_s: float,
    *,
    raja_region_yaml: Path = DEFAULT_RAJA_REGION_YAML,
    cao_region_yaml: Path = DEFAULT_CAO_REGION_YAML,
    n_epochs: int | None = None,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
):
    """Load + epoch + prepare one session; return ``(epochs, prepared)``."""
    loaders = make_dataset_loaders(
        raja_region_yaml=raja_region_yaml, cao_region_yaml=cao_region_yaml
    )
    raw = loaders[pair["dataset"]](pair["fif"])
    epochs = mne.make_fixed_length_epochs(
        raw, duration=epoch_duration_s, preload=True, verbose="ERROR"
    )
    if n_epochs is not None:
        epochs = epochs[:n_epochs]
    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=filter_low, filter_high=filter_high, resample_rate=100,
    )
    prepared = apply_stage_a_channel_group(prepared, pair["dataset"])
    return epochs, prepared


def reference_dataframe(pair: dict, epoch_duration_s: float):
    """Return the per-blink ground-truth reference DataFrame (epoch_index, …)."""
    return load_annotation_as_reference(pair["csv"], epoch_duration_s)


def annotations_from_reference(ref_df, epoch_duration_s: float):
    """Convert a (possibly filtered) reference DataFrame to mne.Annotations."""
    if ref_df is None or len(ref_df) == 0:
        return mne.Annotations(onset=[], duration=[], description=[])
    return dataframe_to_annotations(enrich_absolute_times(ref_df.reset_index(drop=True), epoch_duration_s))


def run_condition(prepared, valid_epoch_indices, gt_annotations, condition, epoch_duration_s):
    """Run one condition; evaluate against *gt_annotations*; return a metrics dict."""
    channel_results = _CONDITION_RUNNERS[condition](prepared, valid_epoch_indices)
    scored = evaluate_channels(
        channel_results, gt_annotations, epoch_duration=epoch_duration_s
    )
    em = scored.best_eval_result.event_metrics
    return {
        "best_channel": scored.best_channel,
        "tp": em.tp, "fp": em.fp, "fn": em.fn,
        "precision": em.precision, "recall": em.recall, "f1": em.f1,
    }, channel_results, scored
