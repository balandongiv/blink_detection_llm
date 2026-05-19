"""Small DataFrame helpers shared across tutorials and evaluation utilities."""

from __future__ import annotations

from collections.abc import Iterable


def pick_first_match(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    """Return the first candidate present in ``columns`` (case sensitive)."""

    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None
