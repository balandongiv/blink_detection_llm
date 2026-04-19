"""MATLAB-style helper functions ported to Python."""

from .forking import (
    corr,
    get_intersection,
    polyfit,
    polyval,
    weighted_corr,
    mad,
)
from .ear_crossing import (
    CrossingPoint,
    ThresholdCrossingError,
    ThresholdCrossingResult,
    compute_threshold_slopes,
    find_threshold_crossing_triplet,
    linear_interpolated_crossing,
)

__all__ = [
    "corr",
    "get_intersection",
    "polyfit",
    "polyval",
    "weighted_corr",
    "mad",
    "lines_intersection",
    "CrossingPoint",
    "ThresholdCrossingError",
    "ThresholdCrossingResult",
    "compute_threshold_slopes",
    "find_threshold_crossing_triplet",
    "linear_interpolated_crossing",
]


def __getattr__(name: str):
    if name == "lines_intersection":
        from .line_intersection import lines_intersection

        return lines_intersection
    raise AttributeError(f"module 'pyblinker.fitutils' has no attribute {name!r}")
