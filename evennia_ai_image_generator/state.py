from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

ImageState = Literal["none", "pending", "ready", "failed", "stale"]

ALLOWED_TRANSITIONS: dict[ImageState, set[ImageState]] = {
    "none": {"pending"},
    "pending": {"ready", "failed"},
    "ready": {"stale"},
    "failed": {"pending"},
    "stale": {"pending"},
}


@dataclass
class ImageLifecycle:
    """Tracks image state and lightweight metadata for a subject."""

    state: ImageState = "none"
    image_current: dict | None = None
    image_history: list[dict] = field(default_factory=list)
    image_index: dict[str, dict] = field(default_factory=dict)
    image_generation: dict = field(default_factory=dict)

    def transition(self, new_state: ImageState) -> None:
        if new_state == self.state:
            return
        allowed = ALLOWED_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise ValueError(f"Invalid image state transition: {self.state} -> {new_state}")
        self.state = new_state

    def mark_pending(self, reason: str = "look") -> None:
        if self.state in {"none", "failed", "stale"}:
            self.transition("pending")
        self.image_generation.update(
            {
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "status": "pending",
            }
        )

    def set_ready(self, image_record: dict) -> None:
        if self.state != "pending":
            raise ValueError("Can only set ready from pending state")
        self.transition("ready")
        self.image_current = image_record
        self.image_history.append(image_record)
        fingerprint = image_record.get("state_fingerprint")
        if fingerprint:
            self.image_index[fingerprint] = {
                "image_id": image_record.get("image_id"),
                "path": image_record.get("path"),
                "revision": image_record.get("revision"),
                "url": image_record.get("url"),
            }
        self.image_generation.update({"status": "ready", "error": None})

    def set_failed(self, error: str) -> None:
        if self.state != "pending":
            raise ValueError("Can only set failed from pending state")
        self.transition("failed")
        self.image_generation.update({"status": "failed", "error": error})

    def mark_stale(self, reason: str = "manual") -> None:
        if self.state == "ready":
            self.transition("stale")
        self.image_generation.update({"reason": reason})
