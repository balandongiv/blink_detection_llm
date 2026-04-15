"""Per-blink morphology metrics delegated to the shared blink core.
All feature calculations rely only on blink onset and blink duration stored in the metadata.
This design intentionally decouples feature extraction from how blink boundaries are defined.

As a result, users should have full flexibility to define blink onset and duration according to their needs.
See pyblinker/segmentation/refinement.py

"""

from __future__ import annotations

from typing import Dict, Iterable, Mapping

import numpy as np

from .._core_blink import METHODS_BY_MODALITY
from .core_metrics import compute_blink_morphology_metrics


def _normalize_methods(modality: str, methods: Iterable[str] | None) -> tuple[str, ...]:
    modality_key = modality.lower()
    allowed = METHODS_BY_MODALITY.get(modality_key, ("base",))
    if methods is None:
        return (allowed[0],)
    ordered: list[str] = []
    for method in methods:
        if method not in ordered:
            ordered.append(method)
    return tuple(ordered) if ordered else (allowed[0],)


def compute_blink_waveform_metrics(
    segment: np.ndarray | Mapping[str, np.ndarray],
    sfreq: float,
    *,
    method: Iterable[str] | None = None,
    modality: str = "eeg",
    include_second_derivative: bool = True,
    use_abs_for_thresholds_and_areas: bool = True,
) -> Dict[str, float]:
    """Compute morphology-oriented blink metrics for selected methods.

    The signature mirrors :func:`pyblinker.blink_features.kinematics.per_blink.
    compute_segment_kinematics` so callers can interchange the two depending on
    their feature subset needs. The returned key space is identical to the
    kinematic helper and all signal analytics are delegated to
    :func:`pyblinker.blink_features.morphology.core_metrics.
    compute_blink_morphology_metrics`.
    """

    _ = include_second_derivative

    if isinstance(segment, Mapping) and set(segment.keys()) >= {"raw"}:
        raw_seg = np.asarray(segment["raw"], dtype=float).reshape(-1)
    else:
        raw_seg = np.asarray(segment, dtype=float).reshape(-1)

    modality_key = modality.lower()
    if method is None:
        method = METHODS_BY_MODALITY.get(modality_key, ("base",))[0]

    metrics = compute_blink_morphology_metrics(
        raw_seg,
        sfreq,
        start_end_method=method,
        modality=modality_key,
        use_abs_for_thresholds_and_areas=use_abs_for_thresholds_and_areas,
    )
    return metrics
