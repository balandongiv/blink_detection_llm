"""Time and sample utilities for blink refinement."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


def _compute_epoch_blink_bounds(
    blink_onsets_sec: np.ndarray,
    blink_durs_sec: np.ndarray,
    epoch_start_sec: float,
    epoch_end_sec: float,
    sfreq: float,
    n_samp_epoch: int,
) -> Tuple[List[int], List[int]]:
    """Return coarse blink start and end samples for a given epoch."""

    blink_starts: List[int] = []
    blink_ends: List[int] = []
    for onset_sec, dur_sec in zip(blink_onsets_sec, blink_durs_sec):
        ann_start = float(onset_sec)
        ann_end = float(onset_sec + max(dur_sec, 0.0))
        if max(ann_start, epoch_start_sec) < min(ann_end, epoch_end_sec):
            start_rel = int(
                np.clip(
                    round((ann_start - epoch_start_sec) * sfreq), 0, n_samp_epoch - 1
                )
            )
            end_rel = int(
                np.clip(
                    round((ann_end - epoch_start_sec) * sfreq) - 1,
                    0,
                    n_samp_epoch - 1,
                )
            )
            if end_rel < start_rel:
                end_rel = start_rel
            blink_starts.append(start_rel)
            blink_ends.append(end_rel)

    return blink_starts, blink_ends


__all__ = ["_compute_epoch_blink_bounds"]
