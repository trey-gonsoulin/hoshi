"""Shared utilities for hoshi."""

from __future__ import annotations

from collections.abc import Mapping


def fuzzy_match(query: str, candidates: Mapping[str, object]) -> object | None:
    """Return the best fuzzy match for *query* among *candidates*, or None."""
    q = query.lower().replace(" ", "")
    for key, item in candidates.items():
        if key.lower().replace(" ", "") == q:
            return item
    for item in candidates.values():
        for alias in getattr(item, "aliases", []):
            if alias.lower().replace(" ", "") == q:
                return item
    for key, item in candidates.items():
        if key.lower().startswith(query.lower()):
            return item
    for item in candidates.values():
        for alias in getattr(item, "aliases", []):
            if alias.lower().startswith(query.lower()):
                return item
    return None
