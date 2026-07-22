"""Exp2 condition runners — detector implementations only; callers own configuration.

Conditions
----------
BLINKER-concat  — naive concatenation with BLINKER threshold.
MNE-annot       — MNE annotate_amplitude routine.
Proposed-Mean   — three-stage pipeline with mean + std threshold at Stage B.
Proposed-Med    — three-stage pipeline, robust MAD-based (median) estimator at Stage B (primary).

This module holds no configuration of its own. Every parameter is passed in by
the caller via a ``settings`` dict, keyed by the same names used in
experiment_script/setup/exp2_strategy_comparison.yaml:
  mne_half_window_s, mne_low_freq, mne_high_freq, mne_thresh,
  autoreject_random_state, std_threshold, min_flagged_epochs, verbose

The caller (not this module) is the single source of truth for those values:
  - experiment_script/exp2_a_strategy_comparison_cao2018.py / _raja.py, via
    src/exp/exp2_channel_group_sweep.py
  - src/utils/condition_runner_utils.py (exp7/exp8 analyses)
  - experiment_script/paper_blink_type_recall.py (dynamic module load)
"""

from __future__ import annotations

from pyblinker.strategies import kleifges_strategy
from src.strategy_nathanael_mne.runner import blink_position_strategy_nathanael
from pyblinker.double_thresholding import blink_position_strategy_dbo


# ---------------------------------------------------------------------------
# Per-condition runners — return standard channel_results list
# ---------------------------------------------------------------------------

def _run_blinker_concat(prepared, valid_epoch_indices, settings):
    return kleifges_strategy(prepared, valid_epoch_indices)


def _run_mne_annot(prepared, valid_epoch_indices, settings):
    return blink_position_strategy_nathanael(
        prepared,
        valid_epoch_indices,
        half_window_s=settings["mne_half_window_s"],
        l_freq=settings["mne_low_freq"],
        h_freq=settings["mne_high_freq"],
        thresh=settings["mne_thresh"],
    )


def _run_proposed_mean(prepared, valid_epoch_indices, settings):
    setting = {
        "autoreject_random_state": settings["autoreject_random_state"],
        "std_threshold":     settings["std_threshold"],
        "center_method":     "mean",
        "min_flagged_epochs": settings["min_flagged_epochs"],
        "verbose":           settings["verbose"],
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


def _run_proposed_med(prepared, valid_epoch_indices, settings):
    setting = {
        "autoreject_random_state": settings["autoreject_random_state"],
        "std_threshold":     settings["std_threshold"],
        "center_method":     "median",
        "min_flagged_epochs": settings["min_flagged_epochs"],
        "verbose":           settings["verbose"],
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


_CONDITION_RUNNERS = {
    "BLINKER-concat": _run_blinker_concat,
    "MNE-annot":      _run_mne_annot,
    "Proposed-Mean":  _run_proposed_mean,
    "Proposed-Med":   _run_proposed_med,
}
