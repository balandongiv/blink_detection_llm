"""Helper classes and functions for blink analysis."""

import pandas as pd

from ._runtime import configure_mne_home

__version__ = "0.4.1"

configure_mne_home()

try:
    pd.set_option("future.infer_string", False)
except Exception:
    pass


from .blinker.fit_blink import FitBlinks
from .blinker.pyblinker import BlinkDetector
from .segment_blink_properties import compute_segment_blink_properties

__all__ = [
    "__version__",

    "FitBlinks",
    "BlinkDetector",
    "compute_segment_blink_properties",
]
