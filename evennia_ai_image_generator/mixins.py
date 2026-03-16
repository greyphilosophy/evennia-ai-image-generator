from __future__ import annotations

from dataclasses import dataclass

from .context import collect_subject_context
from .prompts import build_prompt
from .state import ImageLifecycle


@dataclass
class SceneImageMixin:
    """Framework-agnostic mixin behavior that can be embedded in Evennia typeclasses."""

    subject_type: str = "room"
    subject_key: str = "unknown"
    image_enabled: bool = True
    description: str = ""
    max_image_history: int | None = None

    def __post_init__(self) -> None:
        self.lifecycle = ImageLifecycle(max_history=self.max_image_history)

    def build_prompt(self) -> str:
        return build_prompt(collect_subject_context(self))

    def collect_reference_images(self) -> list[dict]:
        """Return optional reference images for scene generation."""
        return []

    @property
    def image_state(self) -> str:
        return self.lifecycle.state

    @property
    def image_current(self) -> dict | None:
        return self.lifecycle.image_current

    def mark_image_stale(self, reason: str = "manual") -> None:
        self.lifecycle.mark_stale(reason=reason)

    def queue_for_generation(self, reason: str = "look") -> bool:
        if not self.image_enabled:
            return False
        if self.lifecycle.state in {"none", "failed", "stale"}:
            self.lifecycle.mark_pending(reason=reason)
            return True
        return False

    def render_look(self) -> str:
        lines = [self.description or "You see nothing special."]
        if not self.image_enabled:
            return "\n".join(lines)

        if self.lifecycle.state == "ready" and self.lifecycle.image_current:
            lines.append(f"Image: {self.lifecycle.image_current['url']}")
        elif self.lifecycle.state in {"none", "pending", "stale"}:
            lines.append("Image: generating...")
        elif self.lifecycle.state == "failed" and not self.lifecycle.image_current:
            lines.append("Image: generation failed")
        return "\n".join(lines)
