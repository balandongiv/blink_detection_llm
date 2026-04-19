"""Utilities for working with feature summary data frames.

The helpers defined here support the tutorials and analysis workflows that
operate on aggregated per-epoch features.  They expose a consistent pandas
indexing scheme that downstream consumers can rely on without reimplementing
the conversion logic.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd

__all__ = ["to_epoch_indexed"]


def _coerce_epoch_labels(
    values: Iterable[pd.Series | pd.Index | pd.ArrayLike],
) -> list[pd.Index]:
    """Return the epoch labels as integer valued :class:`~pandas.Index` objects."""

    coerced: list[pd.Index] = []
    for value in values:
        idx = pd.Index(value)
        if idx.empty:
            coerced.append(idx.astype(int, copy=False))
            continue

        try:
            coerced.append(pd.Index(pd.to_numeric(idx, errors="raise")).astype(int))
        except Exception:  # pragma: no cover - best effort fallback
            coerced.append(idx)
    return coerced


def to_epoch_indexed(
    df: pd.DataFrame,
    *,
    epoch_column: str = "epoch",
    subject_column: str | None = "subject",
    sort_index: bool = True,
) -> pd.DataFrame:
    """Return ``df`` with an index suitable for epoch level operations.

    Parameters
    ----------
    df
        Input dataframe that contains at least an ``epoch`` column.
    epoch_column
        Name of the column that stores the per epoch identifier.  The values
        are coerced to integers when possible.
    subject_column
        Optional column name describing the subject identifier.  When present
        the returned dataframe uses a ``(subject, epoch)`` multi index.  When
        the column is missing the result only indexes by epoch.
    sort_index
        When ``True`` the resulting index is lexicographically sorted.

    Returns
    -------
    :class:`~pandas.DataFrame`
        A copy of ``df`` indexed by epoch (and optionally by subject).

    Raises
    ------
    KeyError
        If ``epoch_column`` is not present either as a column or index level.
    TypeError
        If ``df`` is not a :class:`~pandas.DataFrame` instance.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    if isinstance(df.index, pd.MultiIndex):
        index_names = [name for name in df.index.names if name is not None]
        expected_names: list[str] = []
        if subject_column:
            expected_names.append(subject_column)
        expected_names.append(epoch_column)

        if all(name in index_names for name in expected_names):
            result = df.copy()
            if sort_index:
                result = result.sort_index()
            return result

    if df.index.name == epoch_column and subject_column is None:
        result = df.copy()
        if sort_index:
            result = result.sort_index()
        return result

    working = df.copy()

    if epoch_column in working.columns:
        working[epoch_column] = _coerce_epoch_labels([working[epoch_column]])[0]
        epoch_source = working[epoch_column]
    elif working.index.name == epoch_column:
        epoch_source = working.index
    else:
        raise KeyError(f"'{epoch_column}' column not found in dataframe")

    index_levels: list[pd.Index] = []
    index_names: list[str] = []

    if subject_column and subject_column in working.columns:
        index_levels.append(pd.Index(working[subject_column], name=subject_column))
        index_names.append(subject_column)
        working = working.drop(columns=[subject_column])

    index_levels.append(pd.Index(epoch_source, name=epoch_column))
    index_names.append(epoch_column)

    # Remove the column we just used for the index. ``set_index`` would drop it
    # implicitly, but handling the removal explicitly keeps the logic clear and
    # works even when the values originate from the index.
    if epoch_column in working.columns:
        working = working.drop(columns=[epoch_column])

    if len(index_levels) == 1:
        result = working.set_index(index_levels[0])
    else:
        multi_index = pd.MultiIndex.from_arrays(index_levels, names=index_names)
        result = working.set_index(multi_index)

    if sort_index:
        result = result.sort_index()

    return result
