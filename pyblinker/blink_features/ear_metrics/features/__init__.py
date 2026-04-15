"""EAR baseline and extrema features."""

from .ear_before_blink import ear_before_blink_avg_epoch
from .ear_extrema import ear_extrema_epoch

__all__ = [
    "ear_before_blink_avg_epoch",
    "ear_extrema_epoch",
]
