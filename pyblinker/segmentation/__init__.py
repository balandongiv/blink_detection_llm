"""Segmentation and refinement utilities for pyblinker."""

from .refinement import slice_raw_into_mne_epochs_refine_annot
from .refinement.eeg import refine_blinks_from_epochs, refine_local_maximum_stub

__all__ = [
    "refine_blinks_from_epochs",
    "refine_local_maximum_stub",
    "slice_raw_into_mne_epochs_refine_annot",
]
