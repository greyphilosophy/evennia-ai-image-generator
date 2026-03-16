from __future__ import annotations

from collections.abc import Iterable

from .queue import EnqueueStatus, GenerationQueue


PERMISSION_DENIED_MESSAGE = "Only builders can use image management commands."


def _coerce_builder_flag(value) -> bool:
    """Normalize direct/callable builder flags to a strict boolean."""
    if callable(value):
        value = value()
    return bool(value)


def _iter_permissions(permissions) -> Iterable[str]:
    """Yield permission labels from common permission container shapes."""
    if permissions is None:
        return ()

    if isinstance(permissions, str):
        return (permissions,)

    if hasattr(permissions, "all") and callable(permissions.all):
        return permissions.all()

    return permissions


def _actor_is_builder(actor) -> bool:
    """Return ``True`` when the optional actor has builder privileges."""
    if actor is None:
        return True

    if _coerce_builder_flag(getattr(actor, "is_builder", False)):
        return True

    permissions = _iter_permissions(getattr(actor, "permissions", None))
    return any(str(permission).lower() == "builder" for permission in permissions)


def _queue_subject(
    subject,
    queue: GenerationQueue | None = None,
    *,
    reason: str = "builder",
) -> EnqueueStatus:
    """Queue lifecycle and optional global queue entry, with explicit outcomes."""
    if queue is not None:
        status = queue.enqueue_with_status(subject.subject_key)
        if status == "queued":
            subject.lifecycle.mark_pending(reason=reason)
        elif status == "duplicate" and subject.image_state != "pending":
            # Keep subject lifecycle aligned with queue dedupe state.
            subject.lifecycle.mark_pending(reason=reason)
        return status

    subject.lifecycle.mark_pending(reason=reason)
    return "queued"


def imagegen(subject, queue: GenerationQueue | None = None, *, actor=None) -> str:
    """Queue generation/evaluation for a subject when possible."""
    if not _actor_is_builder(actor):
        return PERMISSION_DENIED_MESSAGE

    if not getattr(subject, "image_enabled", True):
        return "Image generation is disabled for this subject."

    if subject.image_state == "ready":
        subject.mark_image_stale(reason="builder_gen")

    queue_status = _queue_subject(subject, queue=queue, reason="builder_gen")
    if queue_status == "queued":
        return f"Queued image generation for {subject.subject_key}."
    if queue_status == "full":
        return "Image generation queue is full. Please try again shortly."
    return f"Image generation already pending for {subject.subject_key}."


def imageregen(subject, queue: GenerationQueue | None = None, *, actor=None) -> str:
    """Mark the subject stale and queue regeneration."""
    if not _actor_is_builder(actor):
        return PERMISSION_DENIED_MESSAGE

    if not getattr(subject, "image_enabled", True):
        return "Image generation is disabled for this subject."

    subject.mark_image_stale(reason="builder_regen")
    queue_status = _queue_subject(subject, queue=queue, reason="builder_regen")
    if queue_status == "queued":
        return f"Queued image regeneration for {subject.subject_key}."
    if queue_status == "full":
        return "Image generation queue is full. Please try again shortly."
    return f"Image generation already pending for {subject.subject_key}."


def imageclear(subject, *, actor=None) -> str:
    """Clear current image while preserving history for optional reuse."""
    if not _actor_is_builder(actor):
        return PERMISSION_DENIED_MESSAGE

    subject.lifecycle.clear_current(reason="builder_clear")
    return f"Cleared current image for {subject.subject_key}."


def imageprompt(subject, *, actor=None) -> str:
    """Show effective prompt (or last prompt when available)."""
    if not _actor_is_builder(actor):
        return PERMISSION_DENIED_MESSAGE

    current = getattr(subject.lifecycle, "image_current", None) or {}
    return current.get("prompt") or subject.build_prompt()
