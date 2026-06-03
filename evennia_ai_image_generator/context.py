from __future__ import annotations


def collect_subject_context(subject) -> dict:
    """Collect deterministic prompt context from a subject-like object."""
    return {
        "subject_type": getattr(subject, "subject_type", "subject"),
        "subject_key": getattr(subject, "subject_key", "unknown"),
        "description": (getattr(subject, "description", "") or "").strip(),
    }
