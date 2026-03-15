from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Any

from .backend.base import BaseImageBackend, ImageGenerationRequest, ReferenceImage
from .backend.loader import load_backend


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


def _select_mode(subject, backend: BaseImageBackend) -> str:
    wants_img2img = bool(subject.lifecycle.image_current)
    if wants_img2img and backend.capabilities.get("img2img", False):
        return "img2img"
    return "txt2img"


def _normalize_reference_images(subject) -> list[ReferenceImage]:
    collector = getattr(subject, "collect_reference_images", None)
    if collector is None:
        return []

    max_references = int(getattr(subject, "max_reference_images", 4))
    raw_references = collector() or []
    selected: list[ReferenceImage] = []

    for raw in raw_references:
        if isinstance(raw, ReferenceImage):
            selected.append(raw)
            continue

        if not raw.get("notable", True):
            continue

        selected.append(
            ReferenceImage(
                path=raw["path"],
                role=raw.get("role", "context"),
                weight=raw.get("weight", 1.0),
                caption=raw.get("caption"),
            )
        )

    selected.sort(key=lambda item: item.weight, reverse=True)
    return selected[:max_references]


def _reference_text(references: list[ReferenceImage]) -> str:
    labels = [ref.caption or ref.role for ref in references]
    return "Reference context: " + ", ".join(labels)


def _build_request(subject, backend: BaseImageBackend) -> tuple[ImageGenerationRequest, bool]:
    references = _normalize_reference_images(subject)
    supports_multi_reference = backend.capabilities.get("multi_reference", False)
    prompt = subject.build_prompt()
    reference_fallback_used = False

    if references and not supports_multi_reference:
        prompt = f"{prompt}\n{_reference_text(references)}"
        references = []
        reference_fallback_used = True

    request = ImageGenerationRequest(
        subject_type=subject.subject_type,
        subject_key=subject.subject_key,
        prompt=prompt,
        mode=_select_mode(subject, backend),
        reference_images=references,
    )
    return request, reference_fallback_used


def process_generation_job(
    subject,
    backend: BaseImageBackend | None = None,
    backend_config: dict[str, Any] | None = None,
) -> dict:
    """Generate an image for a subject-like object with lifecycle methods.

    If no backend instance is provided, one is loaded using `backend_config`.
    """
    backend_instance = backend or load_backend(backend_config)
    request, reference_fallback_used = _build_request(subject, backend_instance)
    result = backend_instance.generate(request)
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
        "reference_count": len(request.reference_images),
        "reference_fallback_used": reference_fallback_used,
    }
    subject.lifecycle.set_ready(image_record)
    return image_record
