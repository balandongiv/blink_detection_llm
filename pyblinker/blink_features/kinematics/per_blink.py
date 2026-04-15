"""Per-blink kinematic metrics delegated to the shared blink core."""

from __future__ import annotations

from typing import Dict, Mapping

import numpy as np

from .._core_blink import METHODS_BY_MODALITY
from .core_metrics import KINEMATIC_METRICS_NO_STYLE, compute_blink_kinematic_metrics


def compute_segment_kinematics(
    segment: np.ndarray | Mapping[str, np.ndarray],
    sfreq: float,
    *,
    method: str | None = None,
    modality: str = "eeg",
    include_second_derivative: bool = True,
    use_abs_for_thresholds_and_areas: bool = True,
) -> Dict[str, float]:
    """Compute blink kinematic metrics for a single segmentation method.

    Parameters
    ----------
    segment
        Either a one-dimensional array representing the blink waveform or a
        mapping of ``{method: segment}``. When a single array is provided the
        function defaults to the first supported method for the modality (base
        for EEG/EOG, base for EAR). Passing a mapping allows callers to provide
        distinct start/end windows for multiple methods in a single call.
    sfreq
        Sampling frequency of the provided segments.
    method
        Name of the segmentation style/method associated with the provided
        segment. Defaults to the first allowed method for the modality when
        not supplied.
    modality
        Recording modality. ``"eeg"`` (default) enables zero-based metrics
        whereas ``"ear"`` (Eye Aspect Ratio) suppresses them.
    include_second_derivative
        Forwarded to :func:`pyblinker.blink_features.kinematics.core_metrics.
        compute_blink_kinematic_metrics`.
    use_abs_for_thresholds_and_areas
        Retained for backward compatibility with prior APIs; ignored by
        kinematic-only calculations.

    Returns
    -------
    dict
        Mapping of metric names with method suffixes to floating point values.
    """

    _ = use_abs_for_thresholds_and_areas

    if isinstance(segment, Mapping) and set(segment.keys()) >= {"raw"}:
        raw_seg = np.asarray(segment["raw"], dtype=float).reshape(-1)
        dx1 = (
            np.asarray(segment.get("dx1"), dtype=float).reshape(-1)
            if "dx1" in segment
            else None
        )
        dx2 = (
            np.asarray(segment.get("dx2"), dtype=float).reshape(-1)
            if "dx2" in segment
            else None
        )
    else:
        raw_seg = np.asarray(segment, dtype=float).reshape(-1)
        dx1 = None
        dx2 = None

    modality_key = modality.lower()
    if method is None:
        method = METHODS_BY_MODALITY.get(modality_key, ("base",))[0]

    metrics = compute_blink_kinematic_metrics(
        raw_seg,
        sfreq,
        start_end_method=method,
        modality=modality_key,
        include_second_derivative=include_second_derivative,
        dx1=dx1,
        dx2=dx2,
    )
    for metric in KINEMATIC_METRICS_NO_STYLE:
        key_with_suffix = f"{metric}_{method}"
        if key_with_suffix in metrics and metric not in metrics:
            metrics[metric] = metrics[key_with_suffix]
    return metrics
