"""Shared blink waveform analytics used by per-blink feature functions."""

from __future__ import annotations

from typing import Dict

import numpy as np

from pyblinker.blink_features._blink_metrics_shared import (
    ALL_METHODS,
    CANONICAL_METRIC_STEMS,
    METHODS_BY_MODALITY,
    _method_keys,
    core_nan_dict,
    logger,
)
from pyblinker.blink_features.kinematics.core_metrics import (
    compute_blink_kinematic_metrics,
)
from pyblinker.blink_features.morphology.core_metrics import (
    compute_blink_morphology_metrics,
)


def compute_blink_core(
    segment: np.ndarray,
    sfreq: float,
    *,
    start_end_method: str,
    modality: str,
    include_second_derivative: bool = True,
    use_abs_for_thresholds_and_areas: bool = True,
    dx1: np.ndarray | None = None,
    dx2: np.ndarray | None = None,
) -> Dict[str, float]:
    """Compute canonical per-blink metrics for a segmented waveform.

    Parameters
    ----------
    segment
        One-dimensional signal segment spanning a single blink according to the
        requested ``start_end_method``. The array is converted to ``float`` and
        flattened internally.
    sfreq
        Sampling frequency in Hertz.
    start_end_method
        Segmentation strategy name (``"base"``, ``"zero"``, ``"tent"``,
        ``"half_base"``, or ``"half_zero"``).
    modality
        Recording modality. ``"eeg"``/``"eog"`` retain zero-crossing metrics
        whereas ``"ear"`` (Eye Aspect Ratio) omits them and returns ``NaN``.
    include_second_derivative
        If ``True`` (default) velocity and acceleration statistics are
        reported. When ``False`` the acceleration metrics are set to ``NaN``.
    use_abs_for_thresholds_and_areas
        When ``True`` the magnitude used for rise/fall thresholds and area
        calculations is based on ``abs(segment)`` for EEG/EOG data. EAR blinks
        always rely on the dip magnitude relative to their local baseline and
        ignore this flag.

    Returns
    -------
    dict
        Mapping of metric names (with method suffix) to numeric values. If the
        segmentation method is not supported for the modality or the segment is
        invalid, the returned values are ``NaN``.
    """

    method = start_end_method
    modality_key = modality.lower()
    if modality_key not in METHODS_BY_MODALITY:
        raise ValueError(f"Unsupported modality '{modality}'")

    keys = _method_keys(method, CANONICAL_METRIC_STEMS)
    if method in ALL_METHODS and method not in METHODS_BY_MODALITY[modality_key]:
        return core_nan_dict(keys)

    if sfreq <= 0:
        logger.warning("Non-positive sampling frequency %s; returning NaNs", sfreq)
        return core_nan_dict(keys)

    seg = np.asarray(segment, dtype=float).reshape(-1)
    if seg.size == 0:
        logger.debug("Empty blink segment provided for method '%s'", method)
        return core_nan_dict(keys)

    metrics = {}
    metrics.update(
        compute_blink_morphology_metrics(
            seg,
            sfreq,
            start_end_method=method,
            modality=modality_key,
            use_abs_for_thresholds_and_areas=use_abs_for_thresholds_and_areas,
        )
    )
    metrics.update(
        compute_blink_kinematic_metrics(
            seg,
            sfreq,
            start_end_method=method,
            modality=modality_key,
            include_second_derivative=include_second_derivative,
            dx1=dx1,
            dx2=dx2,
        )
    )

    return metrics


__all__ = [
    "CANONICAL_METRIC_STEMS",
    "METHODS_BY_MODALITY",
    "ALL_METHODS",
    "compute_blink_core",
    "core_nan_dict",
]
