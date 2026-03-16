from __future__ import annotations

from .queue import EnqueueStatus, GenerationQueue


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


def imagegen(subject, queue: GenerationQueue | None = None) -> str:
    """Queue generation/evaluation for a subject when possible."""
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


def imageregen(subject, queue: GenerationQueue | None = None) -> str:
    """Mark the subject stale and queue regeneration."""
    if not getattr(subject, "image_enabled", True):
        return "Image generation is disabled for this subject."

    subject.mark_image_stale(reason="builder_regen")
    queue_status = _queue_subject(subject, queue=queue, reason="builder_regen")
    if queue_status == "queued":
        return f"Queued image regeneration for {subject.subject_key}."
    if queue_status == "full":
        return "Image generation queue is full. Please try again shortly."
    return f"Image generation already pending for {subject.subject_key}."


def imageclear(subject) -> str:
    """Clear current image while preserving history for optional reuse."""
    subject.lifecycle.clear_current(reason="builder_clear")
    return f"Cleared current image for {subject.subject_key}."


def imageprompt(subject) -> str:
    """Show effective prompt (or last prompt when available)."""
    current = getattr(subject.lifecycle, "image_current", None) or {}
    return current.get("prompt") or subject.build_prompt()
