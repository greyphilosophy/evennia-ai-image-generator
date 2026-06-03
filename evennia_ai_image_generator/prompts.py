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

    return base


def compute_prompt_fingerprint(prompt: str) -> str:
    normalized = " ".join(prompt.split())
    return sha1(normalized.encode("utf-8")).hexdigest()


def compute_state_fingerprint(prompt: str) -> str:
    """Compute a state fingerprint from normalized visual prompt input.

    Current implementation aliases prompt fingerprinting until a richer
    structured-state fingerprint pipeline is introduced.
    """
    return compute_prompt_fingerprint(prompt)
