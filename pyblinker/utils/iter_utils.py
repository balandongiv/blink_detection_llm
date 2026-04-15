"""Helpers for working with iterables and list-like metadata containers."""

from __future__ import annotations

from typing import Iterable, List, Sequence, TypeVar, Union, overload

import math

import numpy as np
import pandas as pd

from .string_utils import safe_literal_eval

_T = TypeVar("_T")


@overload
def ensure_list(value: Sequence[_T]) -> List[_T]: ...


@overload
def ensure_list(value: np.ndarray) -> List[Union[int, float]]: ...


@overload
def ensure_list(value: pd.Series) -> List[object]: ...


@overload
def ensure_list(value: _T) -> List[_T]: ...


def ensure_list(value):
    """Coerce ``value`` to a list.

    Strings are interpreted as Python literals when possible so that serialized
    list representations (e.g., ``"[1, 2, 3]"``) are expanded into proper Python
    lists. Non-iterable scalars are wrapped in a single-element list.
    """

    if isinstance(value, str):
        parsed = safe_literal_eval(value)
        if parsed is not value:
            value = parsed
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Series):
        return value.tolist()
    return [value]


def ensure_float_list(value: object) -> List[float]:
    """Return a list of floats, gracefully handling ``None`` and ``NaN``."""

    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, str):
        parsed = safe_literal_eval(value)
        if parsed is not value:
            value = parsed
    if isinstance(value, (list, tuple, set)):
        return [float(v) for v in list(value)]
    if isinstance(value, np.ndarray):
        return [float(v) for v in value.tolist()]
    if isinstance(value, pd.Series):
        return [float(v) for v in value.tolist()]
    return [float(value)]


def iter_chunks(iterable: Iterable[_T], size: int) -> Iterable[List[_T]]:
    """Yield fixed-size chunks from ``iterable``."""

    chunk: List[_T] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


__all__ = ["ensure_list", "ensure_float_list", "iter_chunks"]
