"""EEG/EOG blink refinement package."""

from .bounds import compute_outer_bounds
from .refinement import (
    _append_peak_refinements,
    refine_blinks_from_epochs,
    refine_local_maximum_stub,
)

__all__ = [
    "compute_outer_bounds",
    "_append_peak_refinements",
    "refine_blinks_from_epochs",
    "refine_local_maximum_stub",
]
