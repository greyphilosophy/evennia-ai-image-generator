from __future__ import annotations

from dataclasses import dataclass

from evennia_ai_image_generator.context import collect_subject_context
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia_ai_image_generator.prompts import build_prompt, compute_prompt_fingerprint, compute_state_fingerprint


@dataclass
class PromptSubject(SceneImageMixin):
    description: str = "A quiet observatory"


def test_build_prompt_uses_description() -> None:
    prompt = build_prompt(
        {
            "subject_type": "room",
            "description": "A quiet observatory",
        }
    )

    assert prompt == "A quiet observatory"


def test_build_prompt_falls_back_to_subject_type() -> None:
    prompt = build_prompt(
        {
            "subject_type": "object",
            "description": "",
        }
    )

    assert prompt == "A object in a text MUD"


def test_compute_prompt_fingerprint_normalizes_whitespace() -> None:
    fp1 = compute_prompt_fingerprint("A quiet observatory")
    fp2 = compute_prompt_fingerprint("A   quiet   observatory")

    assert fp1 == fp2


def test_compute_state_fingerprint_matches_prompt_fingerprint() -> None:
    prompt = "A quiet observatory"

    assert compute_state_fingerprint(prompt) == compute_prompt_fingerprint(prompt)
