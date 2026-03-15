from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from .backend.base import BaseImageBackend, ImageGenerationRequest


@dataclass
class GenerationQueue:
    pending: set[str]

    def __init__(self) -> None:
        self.pending = set()

    def queue_image_generation(self, subject_key: str) -> bool:
        """Return True when queued, False if duplicate."""
        if subject_key in self.pending:
            return False
        self.pending.add(subject_key)
        return True

    def mark_complete(self, subject_key: str) -> None:
        self.pending.discard(subject_key)


def process_generation_job(subject, backend: BaseImageBackend) -> dict:
    """Generate an image for a subject-like object with lifecycle methods."""
    request = ImageGenerationRequest(
        subject_type=subject.subject_type,
        subject_key=subject.subject_key,
        prompt=subject.build_prompt(),
        mode="img2img" if subject.lifecycle.image_current else "txt2img",
    )
    result = backend.generate(request)
    fingerprint = sha1(request.prompt.encode("utf-8")).hexdigest()
    revision = len(subject.lifecycle.image_history) + 1
    image_record = {
        "image_id": f"{subject.subject_type}_{subject.subject_key}_{revision:04d}",
        "path": result.image_path,
        "url": result.image_url,
        "revision": revision,
        "state_fingerprint": fingerprint,
        "prompt": request.prompt,
        "model_name": result.model_name,
        "mode": request.mode,
    }
    subject.lifecycle.set_ready(image_record)
    return image_record
