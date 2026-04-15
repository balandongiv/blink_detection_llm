"""Internal helpers used by kinematic epoch feature extraction."""

from __future__ import annotations

from typing import List

import pandas as pd


def coerce_numeric_list(value: object, ensure_list_func) -> List[float]:
    values = ensure_list_func(value) if value is not None else []
    out: List[float] = []
    for item in values:
        if item is None or pd.isna(item):
            out.append(float("nan"))
        else:
            out.append(float(item))
    return out


def pad(values: List[float], length: int) -> List[float]:
    if len(values) >= length:
        return values[:length]
    return values + [float("nan")] * (length - len(values))
