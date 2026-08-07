"""Shared helpers for analyses that re-run the exp2 detector conditions.

Both ``exp7_epoch_health_effect`` and ``exp8_long_blink_analysis`` need to run the
same conditions used in the main comparison — BLINKER-concat, MNE-annot,
Proposed-Med — on a session, but under different epoch sets or against
different ground-truth subsets.  The condition *runners* (the actual detector
implementations) are imported from ``src.exp.exp2_strategy_conditions`` so the
analyses reuse the exact same code, but this module is the authority for the
active condition list and detector parameters — read once here from
experiment_script/setup/exp2_strategy_comparison.yaml, the same yaml
experiment_script/exp2_a_strategy_comparison_cao2018.py / _raja.py read for
the main comparison.
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
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from src.utils.experiment_utils import make_dataset_loaders

# Reuse the exact condition runner implementations from the main comparison.
from src.exp.exp2_strategy_conditions import _CONDITION_RUNNERS

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp2_strategy_comparison.yaml")

CONDITIONS = _EXP_CFG["conditions"]
_DETECTOR_SETTINGS = {
    "mne_half_window_s":      float(_EXP_CFG["mne_half_window_s"]),
    "mne_low_freq":           float(_EXP_CFG["mne_low_freq"]),
    "mne_high_freq":          float(_EXP_CFG["mne_high_freq"]),
    "mne_thresh":             _EXP_CFG["mne_thresh"],
    "autoreject_random_state": int(_EXP_CFG["autoreject_random_state"]),
    "std_threshold":          float(_EXP_CFG["std_threshold"]),
    "min_flagged_epochs":     int(_EXP_CFG["min_flagged_epochs"]),
    "verbose":                bool(_EXP_CFG["verbose"]),
}

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
    raja_region_yaml: Path | None = None,
    cao_region_yaml: Path | None = None,
    n_epochs: int | None = None,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
):
    """Load + epoch + prepare one session; return ``(epochs, prepared)``."""
    loaders = make_dataset_loaders(
        raja_region_yaml=raja_region_yaml or get_raja_paths()["brain_region_yaml"],
        cao_region_yaml=cao_region_yaml or get_cao_paths()["brain_region_yaml"],
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
    channel_results = _CONDITION_RUNNERS[condition](prepared, valid_epoch_indices, _DETECTOR_SETTINGS)
    scored = evaluate_channels(
        channel_results, gt_annotations, epoch_duration=epoch_duration_s
    )
    em = scored.best_eval_result.event_metrics
    return {
        "best_channel": scored.best_channel,
        "tp": em.tp, "fp": em.fp, "fn": em.fn,
        "precision": em.precision, "recall": em.recall, "f1": em.f1,
    }, channel_results, scored
