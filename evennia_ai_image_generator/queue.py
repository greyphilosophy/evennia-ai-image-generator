from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Literal

from .backend.base import BaseImageBackend, ImageGenerationRequest, ReferenceImage
from .backend.loader import load_backend
from .prompts import compute_prompt_fingerprint



EnqueueStatus = Literal["queued", "duplicate", "full"]


@dataclass
class GenerationQueue:
    pending: set[str]
    max_pending: int | None

    def __init__(self, max_pending: int | None = None) -> None:
        if max_pending is not None and max_pending < 1:
            raise ValueError("max_pending must be at least 1 when provided")
        self.pending = set()
        self.max_pending = max_pending
        self._lock = Lock()

    def enqueue_with_status(self, subject_key: str) -> EnqueueStatus:
        """Attempt to enqueue a job key and return outcome status."""
        with self._lock:
            if subject_key in self.pending:
                return "duplicate"
            if self.max_pending is not None and len(self.pending) >= self.max_pending:
                return "full"
            self.pending.add(subject_key)
            return "queued"

    def queue_image_generation(self, subject_key: str) -> bool:
        """Return ``True`` when queued, else ``False`` for duplicate or full queue."""
        return self.enqueue_with_status(subject_key) == "queued"

    def mark_complete(self, subject_key: str) -> None:
        with self._lock:
            self.pending.discard(subject_key)

    def is_queued(self, subject_key: str) -> bool:
        with self._lock:
            return subject_key in self.pending

    def pending_count(self) -> int:
        with self._lock:
            return len(self.pending)


@dataclass(frozen=True)
class RequestBuildResult:
    request: ImageGenerationRequest
    reference_fallback_used: bool
    continuity_fallback_used: bool


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

        if not isinstance(raw, dict):
            continue

        if not raw.get("notable", True):
            continue

        path = raw.get("path")
        if not path:
            continue

        selected.append(
            ReferenceImage(
                path=path,
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


def _continuity_text(subject) -> str:
    current = getattr(subject.lifecycle, "image_current", None) or {}
    previous_prompt = current.get("prompt")
    if previous_prompt:
        return f"Continuity/style hint from prior scene: {previous_prompt}"
    return "Continuity/style hint: keep composition and palette consistent with prior version."


def _build_request(subject, backend: BaseImageBackend) -> RequestBuildResult:
    references = _normalize_reference_images(subject)
    supports_multi_reference = backend.capabilities.get("multi_reference", False)
    supports_img2img = backend.capabilities.get("img2img", False)
    has_prior_image = bool(getattr(subject.lifecycle, "image_current", None))
    prompt = subject.build_prompt()
    reference_fallback_used = False
    continuity_fallback_used = False

    if references and not supports_multi_reference:
        prompt = f"{prompt}\n{_reference_text(references)}"
        references = []
        reference_fallback_used = True

    if has_prior_image and not supports_img2img:
        prompt = f"{prompt}\n{_continuity_text(subject)}"
        continuity_fallback_used = True

    request = ImageGenerationRequest(
        subject_type=subject.subject_type,
        subject_key=subject.subject_key,
        prompt=prompt,
        mode=_select_mode(subject, backend),
        reference_images=references,
    )
    return RequestBuildResult(
        request=request,
        reference_fallback_used=reference_fallback_used,
        continuity_fallback_used=continuity_fallback_used,
    )


def process_generation_job(
    subject,
    backend: BaseImageBackend | None = None,
    backend_config: dict[str, Any] | None = None,
) -> dict:
    """Generate an image for a subject-like object with lifecycle methods.

    If no backend instance is provided, one is loaded using `backend_config`.
    """
    backend_instance = backend or load_backend(backend_config)
    build = _build_request(subject, backend_instance)
    result = backend_instance.generate(build.request)
    fingerprint = compute_prompt_fingerprint(build.request.prompt)
    revision = len(subject.lifecycle.image_history) + 1
    image_record = {
        "image_id": f"{subject.subject_type}_{subject.subject_key}_{revision:04d}",
        "path": result.image_path,
        "url": result.image_url,
        "revision": revision,
        "state_fingerprint": fingerprint,
        "prompt": build.request.prompt,
        "model_name": result.model_name,
        "mode": build.request.mode,
        "reference_count": len(build.request.reference_images),
        "reference_fallback_used": build.reference_fallback_used,
        "continuity_fallback_used": build.continuity_fallback_used,
    }
    subject.lifecycle.set_ready(image_record)
    return image_record
