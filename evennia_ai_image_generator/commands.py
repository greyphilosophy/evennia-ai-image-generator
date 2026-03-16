from __future__ import annotations

from .queue import GenerationQueue


def _queue_subject(subject, queue: GenerationQueue | None = None, *, reason: str = "builder") -> bool:
    """Queue lifecycle and optional global queue entry, with deduplication."""
    if queue is not None and not queue.queue_image_generation(subject.subject_key):
        if subject.image_state != "pending":
            subject.lifecycle.mark_pending(reason=reason)
        return False

    subject.lifecycle.mark_pending(reason=reason)
    return True


def imagegen(subject, queue: GenerationQueue | None = None) -> str:
    """Queue generation/evaluation for a subject when possible."""
    if not getattr(subject, "image_enabled", True):
        return "Image generation is disabled for this subject."

    if subject.image_state == "ready":
        subject.mark_image_stale(reason="builder_gen")

    queued = _queue_subject(subject, queue=queue, reason="builder_gen")
    if queued:
        return f"Queued image generation for {subject.subject_key}."
    return f"Image generation already pending for {subject.subject_key}."


def imageregen(subject, queue: GenerationQueue | None = None) -> str:
    """Mark the subject stale and queue regeneration."""
    if not getattr(subject, "image_enabled", True):
        return "Image generation is disabled for this subject."

    subject.mark_image_stale(reason="builder_regen")
    queued = _queue_subject(subject, queue=queue, reason="builder_regen")
    if queued:
        return f"Queued image regeneration for {subject.subject_key}."
    return f"Image generation already pending for {subject.subject_key}."


def imageclear(subject) -> str:
    """Clear current image while preserving history for optional reuse."""
    subject.lifecycle.clear_current(reason="builder_clear")
    return f"Cleared current image for {subject.subject_key}."


def imageprompt(subject) -> str:
    """Show effective prompt (or last prompt when available)."""
    current = getattr(subject.lifecycle, "image_current", None) or {}
    return current.get("prompt") or subject.build_prompt()
