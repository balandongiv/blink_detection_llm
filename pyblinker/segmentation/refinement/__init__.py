"""Blink refinement utilities shared across pipelines."""

from __future__ import annotations

from .ear import (
    EARRefinementConfig,
    EARThresholdBlinkRefiner,
    refine_annotations_for_threshold,
)
from .eeg import (
    compute_outer_bounds,
    refine_blinks_from_epochs,
    refine_local_maximum_stub,
)
from .epochs import slice_raw_into_mne_epochs_refine_annot
from .prep import EpochPreparationResult

__all__ = [
    "EARRefinementConfig",
    "EARThresholdBlinkRefiner",
    "EpochPreparationResult",
    "compute_outer_bounds",
    "refine_annotations_for_threshold",
    "refine_blinks_from_epochs",
    "refine_local_maximum_stub",
    "slice_raw_into_mne_epochs_refine_annot",
]
