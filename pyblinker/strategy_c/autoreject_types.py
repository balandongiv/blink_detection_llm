"""Dataclasses for Strategy C autoreject detector inputs and outputs."""

from __future__ import annotations

from dataclasses import dataclass

import mne
import numpy as np
import pandas as pd


@dataclass
class StrategyCAutorejectResult:
    """Structured output retained by the detector after ``get_blink()``."""

    annotations: mne.Annotations
    channel: str
    n_good_blinks: int
    blink_table: pd.DataFrame
    fig_data: list[object]
    selected_channel: pd.DataFrame
    epochs: mne.Epochs
    valid_epoch_indices: list[int]


@dataclass
class Stage1CandidateLane:
    """Stage 1 detection lane built from one raw or derived signal."""

    channel: str
    signal: np.ndarray
    threshold: float
    candidate_source: str


@dataclass
class Stage1CandidateDetection:
    """Stage 1 candidate detections for one lane before downstream fitting."""

    channel: str
    signal: np.ndarray
    threshold: float
    candidate_source: str
    positions: pd.DataFrame
    mapped_candidates: pd.DataFrame


@dataclass
class Stage1CandidateEvaluation(Stage1CandidateDetection):
    """Stage 1 lane plus downstream fit/statistics used for lane selection."""

    fitted_df: pd.DataFrame
    stats: dict[str, float | str]


@dataclass
class Stage1ScanResult:
    """Shared Stage 1 scan output reused by tutorials and the main detector."""

    epoch_boundaries: list[tuple[int, int]]
    backbone_signal: np.ndarray | None
    thresholds: dict[str, float]
    channel_names: tuple[str, ...]
    global_threshold: float | None
    threshold_learning_api: str
    candidate_lanes: list[Stage1CandidateLane]
    detections: list[Stage1CandidateDetection]


__all__ = [
    "Stage1CandidateDetection",
    "Stage1CandidateEvaluation",
    "Stage1CandidateLane",
    "Stage1ScanResult",
    "StrategyCAutorejectResult",
]
