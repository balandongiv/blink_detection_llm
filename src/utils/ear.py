"""EAR-specific utility functions."""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["select_auto_threshold"]


def select_auto_threshold(features: pd.DataFrame) -> float:
    """Choose a threshold favoring minimal fallback/extension and valid slopes."""

    if "threshold_value" not in features.columns or features.empty:
        raise ValueError(
            "Features must include 'threshold_value' to select an automatic threshold."
        )

    candidates = []
    for theta, group in features.groupby("threshold_value"):
        fallback_rate = pd.to_numeric(
            group["refinement_fallback_to_coarse"], errors="coerce"
        ).mean()
        extension_rate = pd.to_numeric(
            group["refinement_used_outward_extension"], errors="coerce"
        ).mean()

        slopes = pd.to_numeric(group["ear_threshold_closing_slope"], errors="coerce")
        slope_valid_rate = (
            float(np.isfinite(slopes).mean()) if not slopes.empty else 0.0
        )
        candidates.append(
            (
                float(theta),
                float(fallback_rate),
                float(extension_rate),
                slope_valid_rate,
            )
        )

    candidates.sort(key=lambda item: (item[1], item[2], -item[3], item[0]))
    return candidates[0][0]
