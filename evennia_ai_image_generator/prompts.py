from __future__ import annotations

from hashlib import sha1


def build_prompt(context: dict) -> str:
    """Build a deterministic prompt from normalized context."""
    subject_type = context.get("subject_type", "subject")
    description = (context.get("description") or "").strip()

    if description:
        base = description
    else:
        base = f"A {subject_type} in a text MUD"

    style_tags = context.get("style_tags") or []
    mood_tags = context.get("mood_tags") or []

    fragments = []
    if style_tags:
        fragments.append("style: " + ", ".join(style_tags))
    if mood_tags:
        fragments.append("mood: " + ", ".join(mood_tags))

    if fragments:
        return f"{base}\n" + "\n".join(fragments)
    return base


def compute_prompt_fingerprint(prompt: str) -> str:
    normalized = " ".join(prompt.split())
    return sha1(normalized.encode("utf-8")).hexdigest()
