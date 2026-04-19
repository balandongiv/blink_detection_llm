"""EAR threshold-crossing utilities with linear interpolation.

This module provides reusable helpers to locate downward/upward threshold
crossings around a blink-like dip in an EAR (Eye Aspect Ratio) time series.
Crossings are bracketed using sign changes relative to a threshold ``theta``
and refined with linear interpolation. A deterministic plateau policy is used
whenever a crossing segment is flat to avoid divide-by-zero errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence, Tuple

import numpy as np

PlateauPolicy = Literal["midpoint", "left", "right"]


class ThresholdCrossingError(RuntimeError):
    """Raised when an event-consistent crossing triple cannot be found."""


@dataclass
class CrossingPoint:
    """Container for a single threshold crossing."""

    index: int
    time: float
    value: float
    bracket: Tuple[int, int]


@dataclass
class ThresholdCrossingResult:
    """Threshold-crossing triple surrounding a blink-like event."""

    left: CrossingPoint
    right: CrossingPoint
    minimum_index: int
    minimum_time: float
    minimum_value: float
    window: Tuple[int, int]
    found_by: Literal["window", "expanded"]
    status: Literal["ok"] = "ok"


def linear_interpolated_crossing(
    t0: float,
    y0: float,
    t1: float,
    y1: float,
    theta: float,
    *,
    plateau_policy: PlateauPolicy = "midpoint",
) -> float:
    """Return the interpolated crossing time with ``y = theta``.

    When ``y1 == y0`` (a flat segment), the interpolation defaults to the
    midpoint of the segment unless overridden by ``plateau_policy``.
    """

    if y1 == y0:
        if plateau_policy == "left":
            return float(t0)
        if plateau_policy == "right":
            return float(t1)
        return float(0.5 * (t0 + t1))

    alpha = (theta - y0) / (y1 - y0)
    return float(t0 + alpha * (t1 - t0))


def _crossing_candidates(
    d: np.ndarray, start: int, end: int, direction: Literal["down", "up"]
) -> np.ndarray:
    if direction == "down":
        raw = np.nonzero((d[:-1] > 0) & (d[1:] <= 0))[0]
    else:
        raw = np.nonzero((d[:-1] < 0) & (d[1:] >= 0))[0]

    valid = (raw >= start) & (raw < end)
    return raw[valid]


def _find_crossings_in_window(
    ear: np.ndarray,
    t: np.ndarray,
    theta: float,
    window_start: int,
    window_end: int,
    *,
    plateau_policy: PlateauPolicy,
) -> ThresholdCrossingResult | None:
    """Return the first downward crossing, subsequent min, and first upward crossing."""

    if window_end - window_start < 1:
        return None

    d = ear - theta
    downward = _crossing_candidates(d, window_start, window_end, direction="down")
    if downward.size == 0:
        return None

    left_idx = int(downward[0])
    search_start = left_idx + 1
    if search_start > window_end:
        return None

    min_offset = int(np.argmin(ear[search_start : window_end + 1]))
    min_idx = search_start + min_offset

    upward = _crossing_candidates(
        d, max(min_idx, window_start), window_end, direction="up"
    )
    upward = upward[upward > min_idx - 1]
    if upward.size == 0:
        return None

    right_idx = int(upward[0])

    left_time = linear_interpolated_crossing(
        t[left_idx],
        ear[left_idx],
        t[left_idx + 1],
        ear[left_idx + 1],
        theta,
        plateau_policy=plateau_policy,
    )
    right_time = linear_interpolated_crossing(
        t[right_idx],
        ear[right_idx],
        t[right_idx + 1],
        ear[right_idx + 1],
        theta,
        plateau_policy=plateau_policy,
    )

    min_time = float(t[min_idx])
    min_value = float(ear[min_idx])

    left = CrossingPoint(
        index=left_idx,
        time=float(left_time),
        value=float(theta),
        bracket=(left_idx, left_idx + 1),
    )
    right = CrossingPoint(
        index=right_idx,
        time=float(right_time),
        value=float(theta),
        bracket=(right_idx, right_idx + 1),
    )

    return ThresholdCrossingResult(
        left=left,
        right=right,
        minimum_index=int(min_idx),
        minimum_time=min_time,
        minimum_value=min_value,
        window=(int(window_start), int(window_end)),
        found_by="window",
    )


def find_threshold_crossing_triplet(
    ear: Sequence[float] | np.ndarray,
    theta: float,
    *,
    t: Sequence[float] | np.ndarray | None = None,
    window: tuple[int, int] | None = None,
    max_expansion: int = 0,
    expansion_step: int = 1,
    plateau_policy: PlateauPolicy = "midpoint",
) -> ThresholdCrossingResult:
    """Locate event-consistent threshold crossings and the intervening minimum.

    Parameters
    ----------
    ear : Sequence[float]
        1D EAR samples.
    theta : float
        Threshold to intersect.
    t : Sequence[float], optional
        Timebase aligned with ``ear``. Defaults to sample indices.
    window : tuple[int, int], optional
        Inclusive start/end indices limiting the search.
    max_expansion : int, default=0
        Maximum number of samples by which the window may be expanded in either
        direction when crossings are missing.
    expansion_step : int, default=1
        Number of samples added per outward expansion attempt.
    plateau_policy : {"midpoint", "left", "right"}
        Policy for flat segments encountered during interpolation.
    """

    ear_arr = np.asarray(ear, dtype=float)
    if ear_arr.ndim != 1:
        raise ThresholdCrossingError("EAR input must be 1D")

    if ear_arr.size < 2:
        raise ThresholdCrossingError("EAR input must contain at least two samples")

    if t is None:
        t_arr = np.arange(ear_arr.size, dtype=float)
    else:
        t_arr = np.asarray(t, dtype=float)
        if t_arr.shape != ear_arr.shape:
            raise ThresholdCrossingError(
                "Timebase and EAR arrays must share the same shape"
            )

    base_start, base_end = window if window is not None else (0, ear_arr.size - 1)
    if base_start < 0 or base_end >= ear_arr.size:
        raise ThresholdCrossingError("Window bounds are outside the EAR array")
    if base_start >= base_end:
        raise ThresholdCrossingError("Window start must be strictly before window end")

    if expansion_step <= 0:
        raise ThresholdCrossingError("Expansion step must be positive")
    if max_expansion < 0:
        raise ThresholdCrossingError("Max expansion must be non-negative")

    expansions = range(0, max_expansion + 1, expansion_step)
    last_error: ThresholdCrossingError | None = None

    for expansion in expansions:
        start = max(0, base_start - expansion)
        end = min(ear_arr.size - 1, base_end + expansion)
        if start >= end:
            last_error = ThresholdCrossingError(
                "Expanded window is too small for crossing search"
            )
            continue

        candidate = _find_crossings_in_window(
            ear_arr,
            t_arr,
            theta,
            window_start=start,
            window_end=end,
            plateau_policy=plateau_policy,
        )
        if candidate is None:
            continue

        found_by = "window" if expansion == 0 else "expanded"
        candidate.found_by = found_by
        candidate.window = (start, end)

        if not (t_arr[start] <= candidate.left.time <= t_arr[end]):
            raise ThresholdCrossingError(
                "Left crossing time lies outside the search window"
            )
        if not (t_arr[start] <= candidate.right.time <= t_arr[end]):
            raise ThresholdCrossingError(
                "Right crossing time lies outside the search window"
            )
        if not (
            candidate.left.index < candidate.minimum_index < candidate.right.index + 1
        ):
            raise ThresholdCrossingError(
                "Minimum is not bracketed by threshold crossings"
            )

        return candidate

    if last_error is not None:
        raise last_error
    raise ThresholdCrossingError("No threshold crossings found within search bounds")


def compute_threshold_slopes(
    result: ThresholdCrossingResult, theta: float
) -> tuple[float, float]:
    """Compute closing and opening slopes for a crossing triple.

    Returns
    -------
    tuple
        ``(closing_slope, opening_slope)`` with the sign conventions:
        closing_slope < 0, opening_slope > 0 when times are ordered correctly.
        ``nan`` is returned when the denominators are zero.
    """

    denom_close = result.minimum_time - result.left.time
    denom_open = result.right.time - result.minimum_time

    closing = (
        (result.minimum_value - theta) / denom_close if denom_close != 0 else np.nan
    )
    opening = (theta - result.minimum_value) / denom_open if denom_open != 0 else np.nan

    return float(closing), float(opening)
