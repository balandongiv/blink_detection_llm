"""Utilities for aligning and comparing blink events between detected and ground truth sets.

All comparisons and tolerance checks in this module are performed in sample index
units (1-based). Callers may convert results to time units (seconds) using the
sampling rate if desired. Reporting helpers in ``pyblinker.utils.evaluation.reporting``
provide such conversions automatically for readability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("start_blink", "end_blink")

DEFAULT_TOLERANCE_SAMPLES = 1
DEFAULT_AMPLITUDE_RTOL = 1e-6
DEFAULT_AMPLITUDE_ATOL = 1e-12
DEFAULT_REQUIRE_BOTH_CONDITIONS = True


@dataclass(slots=True)
class Alignment:
    """Represents one greedy alignment between detected and ground truth blink events."""

    ground_truth_idx: Optional[int]
    detected_idx: Optional[int]
    start_diff: Optional[float]
    end_diff: Optional[float]
    overlap_samples: int = 0
    conditions_satisfied: bool = False

    def is_match(self, tolerance_samples: int) -> bool:  # noqa: ARG002 - signature retained for compatibility
        """Return ``True`` when amplitude and overlap conditions were satisfied."""

        return bool(self.conditions_satisfied)


def coerce_to_one_based(df_or_array_like: Iterable) -> pd.DataFrame:
    """Return a defensive copy of blink events with 1-based integer sample indices.

    Parameters
    ----------
    df_or_array_like
        Either a :class:`pandas.DataFrame` with ``start_blink`` and ``end_blink`` columns
        or any array-like object with shape ``(n_events, 2)`` representing start and end
        samples. Values are coerced to integers. If any sample index is 0-based (i.e.,
        contains a 0), the entire table is shifted by +1.

    Returns
    -------
    pandas.DataFrame
        A new DataFrame with ``start_blink`` and ``end_blink`` columns using 1-based
        integer indices.

    Raises
    ------
    ValueError
        If values are missing, non-finite, or negative after coercion.
    """

    if isinstance(df_or_array_like, pd.DataFrame):
        if not set(REQUIRED_COLUMNS).issubset(df_or_array_like.columns):
            raise ValueError(
                "DataFrame must contain 'start_blink' and 'end_blink' columns to coerce."
            )
        df = df_or_array_like.loc[:, REQUIRED_COLUMNS].copy()
    else:
        array = np.asarray(df_or_array_like)
        if array.ndim != 2 or array.shape[1] != 2:
            raise ValueError("Array-like input must have shape (n_events, 2).")
        df = pd.DataFrame(array, columns=REQUIRED_COLUMNS)

    for col in REQUIRED_COLUMNS:
        if not np.isfinite(df[col]).all():
            raise ValueError(f"Column '{col}' contains non-finite values.")
        df[col] = df[col].astype(int)

    if (df[REQUIRED_COLUMNS] < 0).any().any():
        raise ValueError("Blink sample indices must be non-negative before coercion.")

    if (df[REQUIRED_COLUMNS] == 0).any().any():
        df[REQUIRED_COLUMNS] = df[REQUIRED_COLUMNS] + 1

    if (df["start_blink"] > df["end_blink"]).any():
        raise ValueError("Each blink event must satisfy start_blink <= end_blink.")

    return df


def validate_event_table(df: pd.DataFrame) -> None:
    """Validate the structure and ordering of a blink event table.

    This function ensures that required columns are present, values are 1-based
    integers, and each event satisfies ``start_blink <= end_blink``. Comparisons are
    always performed in sample index units (1-based).
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Blink events must be provided as a pandas DataFrame.")

    if not set(REQUIRED_COLUMNS).issubset(df.columns):
        raise ValueError(
            "Blink event table must contain 'start_blink' and 'end_blink' columns."
        )

    for col in REQUIRED_COLUMNS:
        if not np.issubdtype(df[col].dtype, np.integer):
            if not np.isfinite(df[col]).all():
                raise ValueError(f"Column '{col}' contains non-finite values.")
            df[col] = df[col].astype(int)
        if (df[col] < 1).any():
            raise ValueError(f"Column '{col}' must use 1-based positive indices.")

    if (df["start_blink"] > df["end_blink"]).any():
        raise ValueError("Each blink event must satisfy start_blink <= end_blink.")

    if not df["start_blink"].is_monotonic_increasing:
        raise ValueError(
            "Blink events must be sorted by start_blink in ascending order."
        )


@dataclass(slots=True)
class _CandidateMatch:
    """Container for ranking admissible detected/ground-truth pairs."""

    sort_key: tuple[float, int, float, int, int]
    detected_idx: int
    ground_truth_idx: int
    overlap_length: int
    amplitude_similar: bool
    has_overlap: bool
    conditions_satisfied: bool


def _expanded_interval(start: int, end: int, tolerance: int) -> tuple[int, int]:
    """Return a tolerance-expanded interval inclusive of both endpoints."""

    expanded_start = int(start) - tolerance
    expanded_end = int(end) + tolerance
    if expanded_start > expanded_end:
        expanded_start, expanded_end = expanded_end, expanded_start
    return expanded_start, expanded_end


def _overlap_length(
    detected_start: int,
    detected_end: int,
    ground_truth_start: int,
    ground_truth_end: int,
    tolerance_samples: int,
) -> int:
    """Return the number of samples of overlap after tolerance expansion."""

    det_start_exp, det_end_exp = _expanded_interval(
        detected_start, detected_end, tolerance_samples
    )
    gt_start_exp, gt_end_exp = _expanded_interval(
        ground_truth_start, ground_truth_end, tolerance_samples
    )

    overlap_start = max(det_start_exp, gt_start_exp)
    overlap_end = min(det_end_exp, gt_end_exp)
    if overlap_end < overlap_start:
        return 0
    return int(overlap_end - overlap_start + 1)


def _amplitudes_are_similar(
    detected_value: float,
    ground_truth_value: float,
    *,
    rtol: float,
    atol: float,
) -> bool:
    """Return ``True`` when both amplitudes are finite and ``numpy.isclose``."""

    if not (np.isfinite(detected_value) and np.isfinite(ground_truth_value)):
        return False
    return bool(np.isclose(detected_value, ground_truth_value, rtol=rtol, atol=atol))


def _build_candidate_matches(
    detected_start: np.ndarray,
    detected_end: np.ndarray,
    ground_truth_start: np.ndarray,
    ground_truth_end: np.ndarray,
    detected_amplitude: Optional[np.ndarray],
    ground_truth_amplitude: Optional[np.ndarray],
    *,
    tolerance_samples: int,
    amplitude_rtol: float,
    amplitude_atol: float,
    require_both_conditions: bool,
) -> list[_CandidateMatch]:
    """Return all admissible candidate matches obeying configured criteria."""

    candidates: list[_CandidateMatch] = []

    amplitude_available = (
        detected_amplitude is not None and ground_truth_amplitude is not None
    )

    for det_idx in range(detected_start.size):
        det_s = int(detected_start[det_idx])
        det_e = int(detected_end[det_idx])
        det_amp = (
            float(detected_amplitude[det_idx])
            if detected_amplitude is not None
            else None
        )

        for gt_idx in range(ground_truth_start.size):
            gt_s = int(ground_truth_start[gt_idx])
            gt_e = int(ground_truth_end[gt_idx])
            gt_amp = (
                float(ground_truth_amplitude[gt_idx])
                if ground_truth_amplitude is not None
                else None
            )

            overlap = _overlap_length(det_s, det_e, gt_s, gt_e, tolerance_samples)
            has_overlap = overlap > 0

            amplitude_similar = True
            amplitude_diff = 0.0
            if amplitude_available:
                amplitude_similar = False
                amplitude_diff = float("inf")
                if det_amp is not None and gt_amp is not None:
                    amplitude_similar = _amplitudes_are_similar(
                        det_amp,
                        gt_amp,
                        rtol=amplitude_rtol,
                        atol=amplitude_atol,
                    )
                    if amplitude_similar:
                        amplitude_diff = abs(det_amp - gt_amp)

            # Candidate admissibility is driven by tolerance-expanded overlap so we can
            # still pair near-matching events even when amplitude similarity fails. The
            # stricter `require_both_conditions` flag is preserved in
            # `conditions_satisfied`, which reporting later turns into either
            # `share_within_tolerance` or `matches_within_tolerance`.
            if not has_overlap:
                continue

            if require_both_conditions:
                meets_criteria = amplitude_similar and has_overlap
            else:
                meets_criteria = amplitude_similar or has_overlap

            boundary_diff = abs(det_s - gt_s) + abs(det_e - gt_e)
            amplitude_diff_value = float(amplitude_diff)

            sort_key = (
                -float(overlap),
                int(boundary_diff),
                amplitude_diff_value,
                int(det_idx),
                int(gt_idx),
            )

            candidates.append(
                _CandidateMatch(
                    sort_key=sort_key,
                    detected_idx=int(det_idx),
                    ground_truth_idx=int(gt_idx),
                    overlap_length=int(overlap),
                    amplitude_similar=bool(amplitude_similar),
                    has_overlap=bool(has_overlap),
                    conditions_satisfied=bool(meets_criteria),
                )
            )

    return candidates


def align_events(
    detected_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    tolerance_samples: int,
    *,
    amplitude_rtol: float = DEFAULT_AMPLITUDE_RTOL,
    amplitude_atol: float = DEFAULT_AMPLITUDE_ATOL,
    require_both_conditions: bool = DEFAULT_REQUIRE_BOTH_CONDITIONS,
) -> list[Alignment]:
    """Align detected and ground truth blink events using overlap and amplitude.

    The procedure enumerates all detected/ground-truth combinations whose
    tolerance-expanded intervals overlap and, when amplitude information is
    available, whose ``max_amplitude`` values are similar within the configured
    tolerances. Candidate pairs are greedily selected using deterministic
    tie-breaking (largest overlap, then smallest boundary difference, then
    smallest amplitude difference) to ensure a one-to-one mapping.
    """

    if tolerance_samples < 0:
        raise ValueError("tolerance_samples must be non-negative.")

    validate_event_table(detected_df)
    validate_event_table(ground_truth_df)

    det_start = detected_df["start_blink"].to_numpy(dtype=int)
    det_end = detected_df["end_blink"].to_numpy(dtype=int)
    gt_start = ground_truth_df["start_blink"].to_numpy(dtype=int)
    gt_end = ground_truth_df["end_blink"].to_numpy(dtype=int)

    det_amp_series = detected_df.get("max_amplitude")
    gt_amp_series = ground_truth_df.get("max_amplitude")

    det_amp = None
    gt_amp = None
    if det_amp_series is not None and gt_amp_series is not None:
        det_amp = det_amp_series.to_numpy(dtype=np.float64)
        gt_amp = gt_amp_series.to_numpy(dtype=np.float64)

    candidates = _build_candidate_matches(
        det_start,
        det_end,
        gt_start,
        gt_end,
        det_amp,
        gt_amp,
        tolerance_samples=tolerance_samples,
        amplitude_rtol=amplitude_rtol,
        amplitude_atol=amplitude_atol,
        require_both_conditions=require_both_conditions,
    )

    matches: dict[int, int] = {}
    matched_detections: set[int] = set()
    selected_candidates: dict[tuple[int, int], _CandidateMatch] = {}

    for candidate in sorted(candidates, key=lambda c: c.sort_key):
        gt_idx = candidate.ground_truth_idx
        det_idx = candidate.detected_idx
        if gt_idx in matches or det_idx in matched_detections:
            continue
        matches[gt_idx] = det_idx
        matched_detections.add(det_idx)
        selected_candidates[(gt_idx, det_idx)] = candidate

    alignments: list[Alignment] = []
    for gt_idx in range(gt_start.size):
        det_idx = matches.get(gt_idx)
        if det_idx is None:
            alignments.append(
                Alignment(
                    ground_truth_idx=gt_idx,
                    detected_idx=None,
                    start_diff=None,
                    end_diff=None,
                    overlap_samples=0,
                    conditions_satisfied=False,
                )
            )
            continue

        candidate = selected_candidates.get((gt_idx, det_idx))
        overlap_samples = candidate.overlap_length if candidate else 0
        conditions_satisfied = candidate.conditions_satisfied if candidate else False

        alignments.append(
            Alignment(
                ground_truth_idx=gt_idx,
                detected_idx=det_idx,
                start_diff=float(int(det_start[det_idx]) - int(gt_start[gt_idx])),
                end_diff=float(int(det_end[det_idx]) - int(gt_end[gt_idx])),
                overlap_samples=int(overlap_samples),
                conditions_satisfied=bool(conditions_satisfied),
            )
        )

    for det_idx in range(det_start.size):
        if det_idx in matched_detections:
            continue
        alignments.append(
            Alignment(
                ground_truth_idx=None,
                detected_idx=det_idx,
                start_diff=None,
                end_diff=None,
                overlap_samples=0,
                conditions_satisfied=False,
            )
        )

    return alignments


def compute_alignment_metrics(diff_table: pd.DataFrame) -> dict[str, float]:
    """Compute summary metrics describing alignment quality.

    Metrics are derived directly from ``diff_table`` (typically produced by
    :func:`pyblinker.utils.evaluation.reporting.make_diff_table`) and include:

    ``total_ground_truth``
        Number of ground truth events.
    ``total_detected``
        Number of detected events.
    ``ground_truth_only``
        Ground truth events without a detected counterpart.
    ``detected_only``
        Detected events without a ground truth counterpart.
    ``share_within_tolerance``
        Count of unique events (detected plus ground truth) participating in
        amplitude- and overlap-satisfying pairs.
    ``matches_within_tolerance``
        Count of unique events belonging to pairs that met the tolerance window
        but failed at least one amplitude/overlap requirement.
    ``pairs_outside_tolerance``
        Count of unique events in pairs whose boundaries exceeded the tolerance
        window regardless of amplitude/overlap success.
    ``share_within_tolerance_percent``
        Percentage of unique events that participate in amplitude- and overlap-
        satisfying pairs.

    ``diff_table`` must include ``match_category`` and ``within_tolerance``
    columns describing how each paired event was classified:

    ``"share_within_tolerance"``
        Assigned when both amplitude and overlap conditions are satisfied for a
        detected/ground-truth pair. ``within_tolerance`` may be either ``True``
        or ``False`` depending on whether the start/end boundaries also fall
        within the tolerance window.
    ``"matches_within_tolerance"``
        Assigned to pairs whose start and end indices fall within the tolerance
        window but fail at least one amplitude/overlap requirement. These pairs
        are within the boundary window (``within_tolerance=True``) yet are not
        counted toward ``share_within_tolerance`` because the quality checks did
        not pass.
    ``"pairs_outside_tolerance"``
        Assigned when a paired event violates the tolerance window
        (``within_tolerance=False``), even if amplitude/overlap conditions are
        otherwise satisfied.

    The ``within_tolerance`` column is a boolean flag indicating whether both
    start and end differences for a paired event fall within the configured
    tolerance. Rows without a detected/ground-truth pairing use ``NaN`` for both
    ``match_category`` and ``within_tolerance``.

    Example
    -------
    Imagine ``tolerance_samples`` is ``1`` with three ground truth blinks
    (``G1``-``G3``) and three detected blinks (``D1``-``D3``). Suppose ``G1``
    and ``D1`` overlap and have similar amplitudes, so they receive
    ``match_category="share_within_tolerance"`` with ``within_tolerance=True``.
    ``G2`` and ``D2`` overlap but the detected start is two samples early, so
    they receive ``match_category="pairs_outside_tolerance"`` with
    ``within_tolerance=False`` even though amplitude checks pass. ``G3`` and
    ``D3`` align within the tolerance window but the amplitudes differ, leading
    to ``match_category="matches_within_tolerance"`` with
    ``within_tolerance=True``. The resulting metrics would be:

    * ``total_ground_truth`` = 3 and ``total_detected`` = 3.
    * ``ground_truth_only`` = 0 and ``detected_only`` = 0 because all events are
      paired.
    * ``share_within_tolerance`` = 2 because only ``G1`` and ``D1`` satisfy both
      amplitude and overlap checks; ``share_within_tolerance_percent`` is
      therefore ``2 / 6 * 100`` when measured against the six unique events.
    * ``matches_within_tolerance`` = 2 for the ``G3``/``D3`` pair whose
      amplitudes differ despite boundary agreement.
    * ``pairs_outside_tolerance`` = 2 for the ``G2``/``D2`` pair whose boundaries
      violate the tolerance window.
    """

    if not isinstance(diff_table, pd.DataFrame):
        raise TypeError("diff_table must be a pandas DataFrame.")

    total_ground_truth = diff_table["ground_truth_idx"].notna().sum()
    total_detected = diff_table["detected_idx"].notna().sum()

    match_category = diff_table.get("match_category")
    if match_category is None:
        raise KeyError("diff_table must include a 'match_category' column.")

    if "within_tolerance" not in diff_table.columns:
        raise KeyError("diff_table must include a 'within_tolerance' column.")

    paired_mask = (
        diff_table["ground_truth_idx"].notna() & diff_table["detected_idx"].notna()
    )
    share_pairs_mask = match_category == "share_within_tolerance"
    matches_pairs_mask = match_category == "matches_within_tolerance"
    outside_pairs_mask = match_category == "pairs_outside_tolerance"

    share_pairs = int((share_pairs_mask & paired_mask).sum())
    matches_pairs = int((matches_pairs_mask & paired_mask).sum())
    outside_pairs = int((outside_pairs_mask & paired_mask).sum())

    share_count = 2 * share_pairs
    matches_count = 2 * matches_pairs
    outside_count = 2 * outside_pairs
    ground_truth_only = int(
        (
            diff_table["ground_truth_idx"].notna() & diff_table["detected_idx"].isna()
        ).sum()
    )
    detected_only = int(
        (
            diff_table["detected_idx"].notna() & diff_table["ground_truth_idx"].isna()
        ).sum()
    )
    unique_total = int(total_ground_truth + total_detected)

    def _pct(n: int, d: int) -> float:
        return (n / d) * 100.0 if d else float("nan")

    return {
        "unique_total": float(unique_total),
        "total_ground_truth": float(total_ground_truth),
        "total_detected": float(total_detected),
        "ground_truth_only": float(ground_truth_only),
        "detected_only": float(detected_only),
        "share_within_tolerance": float(share_count),
        "matches_within_tolerance": float(matches_count),
        "pairs_outside_tolerance": float(outside_count),
        "share_within_tolerance_percent": _pct(share_count, unique_total),
    }


def compute_pairwise_differences(
    detected_df: pd.DataFrame, ground_truth_df: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """Return absolute start/end sample differences for overlapping events.

    Parameters are validated using :func:`validate_event_table`. Differences are
    computed only for overlapping index positions (``min(len(detected), len(ground_truth))``),
    always in sample index units (1-based).
    """

    validate_event_table(detected_df)
    validate_event_table(ground_truth_df)

    n = min(len(detected_df), len(ground_truth_df))
    if n == 0:
        return np.array([], dtype=int), np.array([], dtype=int)

    det_start = detected_df["start_blink"].to_numpy(dtype=int)
    det_end = detected_df["end_blink"].to_numpy(dtype=int)
    gt_start = ground_truth_df["start_blink"].to_numpy(dtype=int)
    gt_end = ground_truth_df["end_blink"].to_numpy(dtype=int)

    return np.abs(det_start[:n] - gt_start[:n]), np.abs(det_end[:n] - gt_end[:n])
