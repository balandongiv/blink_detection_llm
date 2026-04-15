"""Shared scanning primitives for all Strategy E variants.

All E variants share the same threshold-crossing detection core.  Centralising
here prevents duplicate implementations across the E submodules.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ── Threshold-crossing detectors ──────────────────────────────────────────────

def scan_threshold_crossings(
    signal: np.ndarray,
    threshold: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Vectorised threshold-crossing scan.

    Returns ``(onset_sample, offset_sample)`` pairs where the signal exceeds
    ``threshold`` for at least ``min_blink_frames`` consecutive samples.
    """
    above = signal > threshold
    if not above.any():
        return []
    padded = np.concatenate([[False], above, [False]])
    diff = np.diff(padded.astype(np.int8))
    onsets = np.where(diff == 1)[0]
    offsets = np.where(diff == -1)[0]
    return [
        (int(on), int(off))
        for on, off in zip(onsets, offsets)
        if (off - on) > min_blink_frames
    ]


def scan_hysteresis_crossings(
    signal: np.ndarray,
    t_high: float,
    t_low: float,
    min_blink_frames: float,
) -> list[tuple[int, int]]:
    """Hysteresis threshold crossing.

    Event opens when ``signal > t_high``; closes when ``signal < t_low``.
    ``min_blink_frames`` is enforced on the final event length.
    """
    blinks: list[tuple[int, int]] = []
    in_event = False
    start = 0
    n = len(signal)
    for i in range(n):
        val = signal[i]
        if not in_event:
            if val > t_high:
                in_event = True
                start = i
        else:
            if val < t_low:
                if (i - start) > min_blink_frames:
                    blinks.append((start, i))
                in_event = False
    if in_event and (n - start) > min_blink_frames:
        blinks.append((start, n))
    return blinks


# ── Interval helpers ───────────────────────────────────────────────────────────

def merge_intervals(
    intervals: list[tuple[int, int]],
    gap_frames: int,
) -> list[tuple[int, int]]:
    """Merge overlapping or close intervals within ``gap_frames`` samples."""
    if not intervals:
        return []
    sorted_ivs = sorted(intervals)
    merged: list[list[int]] = [[sorted_ivs[0][0], sorted_ivs[0][1]]]
    for start, end in sorted_ivs[1:]:
        if start <= merged[-1][1] + gap_frames:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


# ── DataFrame builder ──────────────────────────────────────────────────────────

def make_candidates_df(
    cand_rows: list[dict],
    channel_name: str,
) -> pd.DataFrame:
    """Convert a list of candidate dicts to a sorted, typed DataFrame."""
    if cand_rows:
        return (
            pd.DataFrame(cand_rows)
            .sort_values(["epoch_index", "blink_onset"])
            .reset_index(drop=True)
        )
    return pd.DataFrame(
        columns=["epoch_index", "channel", "blink_onset", "blink_duration"]
    )


__all__ = [
    "make_candidates_df",
    "merge_intervals",
    "scan_hysteresis_crossings",
    "scan_threshold_crossings",
]
