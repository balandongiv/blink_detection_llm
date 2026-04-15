"""EAR blink refinement package."""

from .epoch import (
    _append_ear_refinements,
    _append_outer_bounds_from_peaks,
    _empty_interpolated_thresholds,
    _locate_trough,
    _refine_ear_blinks_for_epoch,
    _select_seg_type,
)
from .threshold import (
    EARRefinementConfig,
    EARThresholdBlinkRefiner,
    refine_annotations_for_threshold,
)

__all__ = [
    "EARRefinementConfig",
    "EARThresholdBlinkRefiner",
    "refine_annotations_for_threshold",
    "_append_ear_refinements",
    "_append_outer_bounds_from_peaks",
    "_empty_interpolated_thresholds",
    "_locate_trough",
    "_refine_ear_blinks_for_epoch",
    "_select_seg_type",
]
