from __future__ import annotations

from hashlib import sha1
from time import perf_counter

from .base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult


class PlaceholderBackend(BaseImageBackend):
    """Deterministic backend for local/dev use while AI backend is unavailable."""

    capabilities = {
        "txt2img": True,
        "img2img": True,
        "multi_reference": False,
        "inpainting": False,
    }

    def __init__(self, media_url_base: str = "https://game.test/media/generated") -> None:
        self.media_url_base = media_url_base.rstrip("/")

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        started = perf_counter()
        digest = sha1(f"{request.subject_type}:{request.subject_key}:{request.prompt}".encode("utf-8")).hexdigest()[:12]
        filename = f"{request.subject_type}_{request.subject_key}_{digest}.png"
        image_path = f"generated/{filename}"
        image_url = f"{self.media_url_base}/{filename}"
        return ImageGenerationResult(
            image_path=image_path,
            image_url=image_url,
            seed=request.seed,
            model_name="placeholder-v1",
            generation_time=perf_counter() - started,
            metadata={"mode": request.mode, "placeholder": True},
        )
