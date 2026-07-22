"""Experiment 2: Four-condition strategy comparison (the main comparison).

Naive Epoch Concatenation vs Epoch-Aware Pipeline (Sec. 3.3.1-3.3.3).
Tests whether BLINKER-concat and MNE-annot are outperformed by the proposed
three-stage pipeline (Proposed-Mean, Proposed-Med), primarily through improved f1 score.

Threshold Estimator at Stage B (Sec. 3.3.4).
Tests whether the robust MAD-based (median) estimator outperforms the mean-based
estimator, especially for sessions with extreme outlier amplitudes.

Conditions
----------
BLINKER-concat  — naive concatenation with BLINKER threshold.
MNE-annot       — MNE annotate_amplitude routine.
Proposed-Mean   — three-stage pipeline with mean + std threshold at Stage B.
Proposed-Med    — three-stage pipeline, robust MAD-based (median) estimator at Stage B (primary).

Datasets
--------
Drowsy Driving Raja corpus and Cao2018 dataset.

Statistical tests
-----------------
Pairwise Wilcoxon signed-rank tests on matched session-level F1 scores
(src/stat/wilcoxon.py). Proposed vs baselines: one-tailed (alternative="greater").
Proposed-Mean vs Proposed-Med: two-tailed.
Bonferroni correction: n_pairs = C(4, 2) = 6.

Epoch-health filtering (USE_EPOCH_HEALTH / --use-epoch-health)
----------------------------------------------------------------
Defaults to OFF, matching exp1_channel_selection_*.py's default of
``use_epoch_health=False`` — every epoch is scored. Turning this on makes
exp2 non-comparable to exp1 unless exp1 is also re-run with
--use-epoch-health (see src/utils/experiment_utils.valid_epoch_indices_for_pair).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels
from src.common.epoch_input import prepare_epoch_detection_input
from experiment_script.channel_group_config import apply_stage_a_channel_group
from pyblinker.strategies import kleifges_strategy
from src.strategy_nathanael_mne.runner import blink_position_strategy_nathanael
from pyblinker.double_thresholding import blink_position_strategy_dbo
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from src.stat.wilcoxon import run_wilcoxon_tests
from src.utils.dataset_discovery import discover_cao_pairs, discover_raja_pairs
from src.utils.experiment_utils import (
    load_gt_annotations_for_pair,
    make_dataset_loaders,
    setup_tutorial_logging,
    valid_epoch_indices_for_pair,
    write_csv as _write_csv,
)
from src.utils.strategy_comparison_report import (
    print_per_session_table,
    print_summary_table,
    summary_rows,
)

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp2_strategy_comparison.yaml")
_RAJA    = get_raja_paths()
_CAO     = get_cao_paths()

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True
USE_EPOCH_HEALTH: bool = bool(_EXP_CFG.get("use_epoch_health", False))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAJA_REGION_YAML     = _RAJA["brain_region_yaml"]
CAO_REGION_YAML      = _CAO["brain_region_yaml"]
RAJA_ANNOTATION_BASE = _RAJA["annotation_base"]
RAJA_PROCESSED_BASE  = _RAJA["processed_base"]
CAO_DATASET_ROOT     = _CAO["dataset_root"]

# ---------------------------------------------------------------------------
# Shared parameters (experiment_script/setup/exp2_strategy_comparison.yaml)
# ---------------------------------------------------------------------------
EPOCH_DURATION_S       = float(_EXP_CFG.get("epoch_duration_s", 30.0))
FILTER_LOW             = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH            = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE          = int(_EXP_CFG.get("resample_rate", 100))
N_EPOCHS: int | None   = None  # positive int → limit epochs per session for quick runs

# Strategy nathanael_mne (MNE-annot) parameters
MNE_HALF_WINDOW_S = float(_EXP_CFG.get("mne_half_window_s", 0.10))
MNE_LOW_FREQ      = float(_EXP_CFG.get("mne_low_freq", 1.0))
MNE_HIGH_FREQ     = float(_EXP_CFG.get("mne_high_freq", 20.0))
MNE_THRESH        = _EXP_CFG.get("mne_thresh", None)

# Strategy Proposed-Med (double-thresholding) parameters
AUTOREJECT_RANDOM_STATE = int(_EXP_CFG.get("autoreject_random_state", 42))
MIN_FLAGGED_EPOCHS      = int(_EXP_CFG.get("min_flagged_epochs", 1))
STD_THRESHOLD           = float(_EXP_CFG.get("std_threshold", 3.0))

CONDITIONS = [
    "BLINKER-concat",
    # "MNE-annot",
    # "Proposed-Mean",
    # "Proposed-Med",
]

# Conditions that are hypothesised to outperform baselines → one-tailed Wilcoxon
_PROPOSED = frozenset({"Proposed-Mean", "Proposed-Med"})
_BASELINES = frozenset({"BLINKER-concat", "MNE-annot"})


# ---------------------------------------------------------------------------
# Per-condition runners — return standard channel_results list
# ---------------------------------------------------------------------------

def _run_blinker_concat(prepared, valid_epoch_indices):
    return kleifges_strategy(prepared, valid_epoch_indices)


def _run_mne_annot(prepared, valid_epoch_indices):
    return blink_position_strategy_nathanael(
        prepared,
        valid_epoch_indices,
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )


def _run_proposed_mean(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":     STD_THRESHOLD,
        "center_method":     "mean",
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":           VERBOSE,
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


def _run_proposed_med(prepared, valid_epoch_indices):
    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":     STD_THRESHOLD,
        "center_method":     "median",
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":           VERBOSE,
    }
    return blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)


_CONDITION_RUNNERS = {
    "BLINKER-concat": _run_blinker_concat,
    "MNE-annot":      _run_mne_annot,
    "Proposed-Mean":  _run_proposed_mean,
    "Proposed-Med":   _run_proposed_med,
}


