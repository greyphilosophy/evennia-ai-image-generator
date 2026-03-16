from __future__ import annotations

from dataclasses import dataclass, field

from evennia_ai_image_generator.context import collect_subject_context
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia_ai_image_generator.prompts import build_prompt, compute_prompt_fingerprint


@dataclass
class PromptSubject(SceneImageMixin):
    description: str = "A quiet observatory"
    style_tags: list[str] = field(default_factory=lambda: [" painterly ", "noir", "noir"])
    mood_tags: list[str] = field(default_factory=lambda: ["mysterious"])


def test_collect_subject_context_normalizes_tags() -> None:
    subject = PromptSubject(subject_type="room", subject_key="obs")

    context = collect_subject_context(subject)

    assert context["subject_type"] == "room"
    assert context["subject_key"] == "obs"
    assert context["description"] == "A quiet observatory"
    assert context["style_tags"] == ["painterly", "noir"]
    assert context["mood_tags"] == ["mysterious"]


def test_build_prompt_includes_context_fragments() -> None:
    prompt = build_prompt(
        {
            "subject_type": "room",
            "description": "A quiet observatory",
            "style_tags": ["painterly", "noir"],
            "mood_tags": ["mysterious"],
        }
    )

    assert prompt == "A quiet observatory\nstyle: painterly, noir\nmood: mysterious"


def test_compute_prompt_fingerprint_normalizes_whitespace() -> None:
    fp1 = compute_prompt_fingerprint("A quiet observatory\nstyle: noir")
    fp2 = compute_prompt_fingerprint("A   quiet observatory style: noir")

    assert fp1 == fp2


def test_scene_image_mixin_uses_prompt_pipeline() -> None:
    subject = PromptSubject(subject_type="room", subject_key="obs")

    prompt = subject.build_prompt()

    assert prompt == "A quiet observatory\nstyle: painterly, noir\nmood: mysterious"


def test_collect_subject_context_accepts_string_tags() -> None:
    subject = PromptSubject(subject_type="room", subject_key="obs")
    subject.style_tags = " watercolor "
    subject.mood_tags = "brooding"

    context = collect_subject_context(subject)

    assert context["style_tags"] == ["watercolor"]
    assert context["mood_tags"] == ["brooding"]
