from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from threading import Event, Lock
from time import perf_counter
from typing import Any

from .base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult


class DiffusersBackendDependencyError(ImportError):
    """Raised when diffusers backend dependencies are unavailable."""


@dataclass
class _PipelineBundle:
    pipeline: Any
    device: str


class DiffusersBackend(BaseImageBackend):
    """Stable Diffusion backend powered by Hugging Face diffusers.

    Notes:
    - Uses lazy initialization so importing the package doesn't require torch/diffusers.
    - Currently supports txt2img generation.
    - For tests/dev, `dry_run=True` returns deterministic URLs without loading a model.
    """

    capabilities = {
        "txt2img": True,
        "img2img": False,
        "multi_reference": False,
        "inpainting": False,
    }

    _shared_bundle_cache: dict[tuple[str, str, str, str | None, bool], _PipelineBundle] = {}
    _inflight_loads: dict[tuple[str, str, str, str | None, bool], Event] = {}
    _cache_lock = Lock()

    @classmethod
    def clear_shared_cache(cls) -> int:
        """Clear cached pipeline bundles and return number of removed entries."""
        with cls._cache_lock:
            removed = len(cls._shared_bundle_cache)
            cls._shared_bundle_cache.clear()
            cls._inflight_loads.clear()
            return removed

    @classmethod
    def shared_cache_size(cls) -> int:
        """Return number of cached pipeline bundles."""
        with cls._cache_lock:
            return len(cls._shared_bundle_cache)

    def __init__(
        self,
        model_id: str = "runwayml/stable-diffusion-v1-5",
        revision: str | None = None,
        device: str = "cpu",
        torch_dtype: str = "float32",
        media_url_base: str = "https://game.test/media/generated",
        output_dir: str = "generated",
        use_safetensors: bool = True,
        dry_run: bool = False,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 20,
    ) -> None:
        self.model_id = model_id
        self.revision = revision
        self.device = device
        self.torch_dtype = torch_dtype
        self.media_url_base = media_url_base.rstrip("/")
        self.output_dir = output_dir.strip("/") or "generated"
        self.use_safetensors = use_safetensors
        self.dry_run = dry_run
        self.guidance_scale = guidance_scale
        self.num_inference_steps = num_inference_steps
        self._bundle: _PipelineBundle | None = None

    def _cache_key(self) -> tuple[str, str, str, str | None, bool]:
        return (
            self.model_id,
            self.device,
            self.torch_dtype,
            self.revision,
            self.use_safetensors,
        )

    def _load_bundle(self) -> _PipelineBundle:
        if self._bundle is not None:
            return self._bundle

        cache_key = self._cache_key()
        waiter: Event | None = None
        is_loader = False

        with self._cache_lock:
            cached_bundle = self._shared_bundle_cache.get(cache_key)
            if cached_bundle is not None:
                self._bundle = cached_bundle
                return cached_bundle

            waiter = self._inflight_loads.get(cache_key)
            if waiter is None:
                waiter = Event()
                self._inflight_loads[cache_key] = waiter
                is_loader = True

        if not is_loader:
            waiter.wait()
            with self._cache_lock:
                cached_bundle = self._shared_bundle_cache.get(cache_key)
                if cached_bundle is not None:
                    self._bundle = cached_bundle
                    return cached_bundle
            raise RuntimeError("Backend model initialization did not produce a cached pipeline")

        try:
            try:
                import torch
                from diffusers import StableDiffusionPipeline
            except Exception as err:  # pragma: no cover - depends on environment
                raise DiffusersBackendDependencyError(
                    "Diffusers backend requires `diffusers` and `torch` to be installed"
                ) from err

            dtype = getattr(torch, self.torch_dtype, None)
            if dtype is None:
                raise ValueError(f"Unknown torch dtype: {self.torch_dtype}")

            kwargs = {
                "pretrained_model_name_or_path": self.model_id,
                "torch_dtype": dtype,
                "use_safetensors": self.use_safetensors,
            }
            if self.revision:
                kwargs["revision"] = self.revision

            pipeline = StableDiffusionPipeline.from_pretrained(**kwargs)
            pipeline = pipeline.to(self.device)
            bundle = _PipelineBundle(pipeline=pipeline, device=self.device)

            with self._cache_lock:
                existing = self._shared_bundle_cache.get(cache_key)
                if existing is not None:
                    self._bundle = existing
                    return existing

                self._shared_bundle_cache[cache_key] = bundle
                self._bundle = bundle
                return bundle
        finally:
            with self._cache_lock:
                inflight = self._inflight_loads.pop(cache_key, None)
                if inflight is not None:
                    inflight.set()

    def _build_paths(self, request: ImageGenerationRequest) -> tuple[str, str]:
        digest_input = (
            f"{self.model_id}:{request.subject_type}:{request.subject_key}:"
            f"{request.mode}:{request.prompt}:{request.negative_prompt}"
        )
        digest = sha1(digest_input.encode("utf-8")).hexdigest()[:12]
        filename = f"{request.subject_type}_{request.subject_key}_{digest}.png"
        return f"{self.output_dir}/{filename}", f"{self.media_url_base}/{filename}"

    def _deterministic_result(self, request: ImageGenerationRequest, started: float) -> ImageGenerationResult:
        image_path, image_url = self._build_paths(request)
        return ImageGenerationResult(
            image_path=image_path,
            image_url=image_url,
            seed=request.seed,
            model_name=self.model_id,
            generation_time=perf_counter() - started,
            metadata={
                "mode": request.mode,
                "dry_run": True,
                "device": self.device,
                "num_inference_steps": self.num_inference_steps,
            },
        )

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        started = perf_counter()

        if self.dry_run:
            return self._deterministic_result(request, started)

        if request.mode != "txt2img":
            raise ValueError(
                f"DiffusersBackend currently supports txt2img only; got mode={request.mode!r}"
            )

        bundle = self._load_bundle()

        kwargs: dict[str, Any] = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt or None,
            "num_inference_steps": self.num_inference_steps,
            "guidance_scale": request.guidance_scale if request.guidance_scale is not None else self.guidance_scale,
            "width": request.width,
            "height": request.height,
        }
        if request.seed is not None:
            try:
                import torch
            except Exception as err:  # pragma: no cover - depends on environment
                raise DiffusersBackendDependencyError(
                    "Diffusers backend requires `torch` to apply request seeds"
                ) from err
            kwargs["generator"] = torch.Generator(device=bundle.device).manual_seed(request.seed)

        output = bundle.pipeline(**kwargs)
        image = output.images[0]
        image_path, image_url = self._build_paths(request)

        disk_path = Path(image_path)
        disk_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(disk_path)

        return ImageGenerationResult(
            image_path=image_path,
            image_url=image_url,
            seed=request.seed,
            model_name=self.model_id,
            generation_time=perf_counter() - started,
            metadata={
                "mode": request.mode,
                "device": bundle.device,
                "size": [image.width, image.height],
                "num_inference_steps": self.num_inference_steps,
                "guidance_scale": kwargs["guidance_scale"],
            },
        )
