from __future__ import annotations

import base64
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from .base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult

logger = logging.getLogger(__name__)


class Flux2RestBackendError(Exception):
    """Raised when the FLUX.2 REST backend encounters an error."""


class Flux2RestServerNotFound(Flux2RestBackendError):
    """Raised when the FLUX.2 REST server is not reachable."""


@dataclass
class Flux2RestBackend(BaseImageBackend):
    """FLUX.2 REST API backend for txt2img generation with Turbo LoRA support.

    Talks to a FLUX.2 REST API server (e.g. the FLUX.2-dev server
    with Turbo LoRA fused, running on port 8190). The server accepts
    a JSON POST to ``/generate`` and returns base64-encoded PNG image
    data.

    The ``turbo`` flag is sent to the server, defaulting to ``True``
    so that the 8-step Turbo LoRA mode is used (~30s per image).

    Configuration options:

    - **server_url**: FLUX.2 REST API endpoint (default ``http://127.0.0.1:8190``)
    - **output_dir**: Local directory for saving outputs (default ``generated``)
    - **media_url_base**: URL base for served images
    - **timeout_s**: HTTP timeout per request (default 120)
    - **default_steps**: Default inference steps (default 28)
    - **default_guidance_scale**: Default guidance scale (default 7.0)
    - **default_seed**: Default seed (default 42)
    - **default_width**: Default image width (default 1024)
    - **default_height**: Default image height (default 1024)
    - **dry_run**: If True, return a deterministic placeholder result
    """

    capabilities = {
        "txt2img": True,
        "img2img": True,
        "multi_reference": False,
        "inpainting": False,
    }

    server_url: str = "http://127.0.0.1:8190"
    output_dir: str = "generated"
    media_url_base: str = "https://game.test/media/generated"
    timeout_s: float = 120.0
    default_steps: int = 28
    default_guidance_scale: float = 7.0
    default_seed: int = 42
    default_width: int = 1024
    default_height: int = 1024
    dry_run: bool = False

    def __post_init__(self) -> None:
        self.server_url = self.server_url.rstrip("/")
        self.output_dir = self.output_dir.rstrip("/") or "generated"
        self.media_url_base = self.media_url_base.rstrip("/")
        self._client = httpx.Client(timeout=self.timeout_s)

    # ---- public API ---------------------------------------------------------

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        started = perf_counter()

        if self.dry_run:
            return self._deterministic_result(request, started)

        if request.mode not in ("txt2img", "img2img"):
            raise ValueError(
                f"Flux2RestBackend supports txt2img/img2img; got mode={request.mode!r}"
            )

        # Build the /generate payload
        seed = request.seed if request.seed is not None else self.default_seed
        guidance = (
            request.guidance_scale
            if request.guidance_scale is not None
            else self.default_guidance_scale
        )
        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "steps": self.default_steps,
            "guidance_scale": guidance,
            "seed": seed,
            "width": request.width or self.default_width,
            "height": request.height or self.default_height,
            "turbo": True,
        }

        # Call the REST endpoint
        response = self._call_generate(payload)

        # Save the image locally
        image_path, image_url = self._build_paths(request)
        disk_path = Path(image_path)
        disk_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_image(response["image_b64"], disk_path)

        elapsed = perf_counter() - started

        return ImageGenerationResult(
            image_path=image_path,
            image_url=image_url,
            seed=seed,
            model_name=response.get("model") or self.server_url,
            generation_time=elapsed,
            metadata={
                "mode": request.mode,
                "server": self.server_url,
                "steps": self.default_steps,
                "guidance_scale": guidance,
                "width": payload["width"],
                "height": payload["height"],
            },
        )

    # ---- REST client -------------------------------------------------------

    def _call_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.server_url}/generate"
        try:
            r = self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except httpx.ConnectError as exc:
            raise Flux2RestServerNotFound(
                f"Cannot connect to FLUX.2 REST server at {self.server_url}: {exc}"
            ) from exc

        if r.status_code >= 400:
            body = (r.text or "")[:500]
            raise Flux2RestBackendError(
                f"FLUX.2 REST API returned HTTP {r.status_code}: {body}"
            )

        data = r.json()

        if not data.get("success"):
            raise Flux2RestBackendError(
                f"FLUX.2 REST API error: {data.get('error', 'unknown')}"
            )

        return data

    # ---- helpers ------------------------------------------------------------

    def _build_paths(self, request: ImageGenerationRequest) -> tuple[str, str]:
        digest_input = (
            f"flux2rest:{request.subject_type}:{request.subject_key}:"
            f"{request.mode}:{request.prompt}:{request.negative_prompt}"
        )
        digest = sha1(digest_input.encode("utf-8")).hexdigest()[:12]
        filename = f"flux2_{request.subject_type}_{request.subject_key}_{digest}.png"
        return (
            f"{self.output_dir}/{filename}",
            f"{self.media_url_base}/{filename}",
        )

    def _save_image(self, image_b64: str, path: Path) -> None:
        image_bytes = base64.b64decode(image_b64)
        path.write_bytes(image_bytes)

    def _deterministic_result(
        self, request: ImageGenerationRequest, started: float
    ) -> ImageGenerationResult:
        image_path, image_url = self._build_paths(request)
        return ImageGenerationResult(
            image_path=image_path,
            image_url=image_url,
            seed=request.seed,
            model_name=f"flux2-rest-{self.server_url}",
            generation_time=perf_counter() - started,
            metadata={
                "mode": request.mode,
                "dry_run": True,
                "server": self.server_url,
            },
        )

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
