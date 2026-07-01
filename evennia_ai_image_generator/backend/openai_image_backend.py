from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from time import perf_counter

from .base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult

logger = logging.getLogger(__name__)


class OpenAIImageBackendError(Exception):
    """Raised when the OpenAI image backend encounters an error."""


# dall-e-3 supported sizes
_DALLE3_SIZES = ["1024x1024", "1024x1792", "1792x1024"]


@dataclass
class OpenAIImageBackend(BaseImageBackend):
    """OpenAI image generation backend using the Images API.

    Uses the OpenAI Python SDK to generate images. Supports dall-e-3 only
    (the only model with stable size guarantees and URL response format).

    Configuration:

    - **api_key**: OpenAI API key. If empty, falls back to the
      ``OPENAI_API_KEY`` environment variable.
    - **model**: Model name (default ``dall-e-3``)
    - **output_dir**: Local directory for saving outputs
    - **media_url_base**: URL base for served images

    Only supports ``txt2img`` mode. Other modes raise ``ValueError``.
    """

    capabilities = {
        "txt2img": True,
        "img2img": False,
        "multi_reference": False,
        "inpainting": False,
    }

    api_key: str = ""
    model: str = "dall-e-3"
    output_dir: str = "generated"
    media_url_base: str = "https://game.test/media/generated"

    def __post_init__(self) -> None:
        self.output_dir = self.output_dir.strip("/") or "generated"
        self.media_url_base = self.media_url_base.rstrip("/")

    def _pick_size(self, width: int, height: int) -> str:
        """Pick the closest valid dall-e-3 size for the request."""
        target_ratio = width / max(height, 1)
        best: str = _DALLE3_SIZES[0]
        best_diff = 999.0
        for sz in _DALLE3_SIZES:
            sw, sh = (int(x) for x in sz.split("x"))
            diff = abs(sw / max(sh, 1) - target_ratio)
            if diff < best_diff:
                best_diff = diff
                best = sz
        return best

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        if request.mode not in ("txt2img",):
            raise ValueError(
                "OpenAIImageBackend supports txt2img mode only; "
                f"got mode={request.mode!r}"
            )

        started = perf_counter()

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OpenAIImageBackendError(
                "The `openai` package is needed but not installed: "
                "pip install openai"
            ) from exc

        api_key = self.api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise OpenAIImageBackendError(
                "No OpenAI API key found. Set OPENAI_API_KEY or pass api_key=..."
            )

        client = OpenAI(api_key=api_key)

        width = request.width or 1024
        height = request.height or 1024
        size_str = self._pick_size(width, height)

        try:
            response = client.images.generate(
                model=self.model,
                prompt=request.prompt,
                size=size_str,
                n=1,
                response_format="url",
            )
        except Exception as exc:
            logger.warning("OpenAI image generation failed: %s", exc)
            raise OpenAIImageBackendError(
                f"OpenAI image generation failed: {exc}"
            ) from exc

        # Download and save the image
        image_url_from_api = response.data[0].url
        image_path, image_url = self._build_paths(request)
        self._download_and_save(image_url_from_api, Path(image_path))

        elapsed = perf_counter() - started

        return ImageGenerationResult(
            image_path=image_path,
            image_url=image_url,
            seed=None,
            model_name=self.model,
            generation_time=elapsed,
            metadata={
                "mode": "txt2img",
                "model": self.model,
                "size": size_str,
            },
        )

    def _build_paths(self, request: ImageGenerationRequest) -> tuple[str, str]:
        digest = sha1(
            f"openai:{request.subject_type}:{request.subject_key}:"
            f"{request.mode}:{request.prompt}:{request.negative_prompt}"
            .encode("utf-8")
        ).hexdigest()[:12]
        safe_key = request.subject_key.replace(" ", "-")
        filename = f"openai_{request.subject_type}_{safe_key}_{digest}.png"
        return (
            f"{self.output_dir}/{filename}",
            f"{self.media_url_base}/{filename}",
        )

    def _download_and_save(self, url: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        import httpx

        r = httpx.get(url, timeout=60.0)
        r.raise_for_status()
        path.write_bytes(r.content)
