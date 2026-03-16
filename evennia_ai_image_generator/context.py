from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _normalize_items(items: Any) -> list[str]:
    if items is None:
        return []

    if isinstance(items, str):
        candidates = [items]
    elif isinstance(items, Iterable):
        candidates = list(items)
    else:
        candidates = [items]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def collect_subject_context(subject) -> dict:
    """Collect deterministic prompt context from a subject-like object."""
    return {
        "subject_type": getattr(subject, "subject_type", "subject"),
        "subject_key": getattr(subject, "subject_key", "unknown"),
        "description": (getattr(subject, "description", "") or "").strip(),
        "style_tags": _normalize_items(getattr(subject, "style_tags", None)),
        "mood_tags": _normalize_items(getattr(subject, "mood_tags", None)),
    }
