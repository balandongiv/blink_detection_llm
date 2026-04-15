"""EEG/EOG blink boundary utilities."""

from __future__ import annotations

from typing import List, Sequence, Tuple


def compute_outer_bounds(peaks: Sequence[int], n_samples: int) -> List[Tuple[int, int]]:
    """Compute search windows around consecutive blink peaks.

    Each blink peak is assigned an ``outer_start`` and ``outer_end`` index such
    that windows do not overlap and cover the entire signal. The first blink's
    window begins at sample ``0`` and extends up to the next peak. The last
    blink's window ends at ``n_samples - 1``. All intermediate blinks span from
    the previous peak to the next peak.
    """

    bounds: List[Tuple[int, int]] = []
    for i, max_blink in enumerate(peaks):
        outer_start = 0 if i == 0 else peaks[i - 1]
        outer_end = (n_samples - 1) if i == len(peaks) - 1 else peaks[i + 1]
        bounds.append((outer_start, outer_end))
    return bounds


__all__ = ["compute_outer_bounds"]
