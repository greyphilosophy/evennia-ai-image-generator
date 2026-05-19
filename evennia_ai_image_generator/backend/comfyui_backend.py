from __future__ import annotations

"""ComfyUI-backed image generation engine for evennia-ai-image-generator.

Talks to a local ComfyUI server via its REST API. Build and sends a
minimal txt2img workflow (CLIP → encode → KSampler → VAE decode → save)
using whatever checkpoint ComfyUI reports.
"""

import hashlib
import json
import os
import random
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult


# ---- Exceptions ----

class ComfyUIBackendError(Exception):
    """Raised when the ComfyUI backend encounters an irrecoverable error."""


class ComfyUIServerNotFound(ComfyUIBackendError):
    """Raised when the ComfyUI server is not reachable."""


class ComfyUIWorkflowError(ComfyUIBackendError):
    """Raised when ComfyUI reports a workflow execution error."""


# ---- Backend ----

class ComfyUIBackend(BaseImageBackend):
    """ComfyUI backend for txt2img generation.

    Configuration options:

    - **server_url**: ComfyUI API endpoint (default ``http://127.0.0.1:8188``)
    - **checkpoint**: Exact filename of the checkpoint in ComfyUI's checkpoints
      folder.  Falls back to first available ``.safetensors`` / ``.ckpt`` file.
    - **scheduler**: Sampler scheduler name (default ``euler``)
    - **sampler_name**: Sampler name (default ``euler``)
    - **default_steps**: Default inference steps (default 20)
    - **default_cfg**: Default guidance scale (default 7.5)
    - **output_dir**: Local directory for saving outputs (default ``generated``)
    - **media_url_base**: URL base for served images
    - **timeout_s**: HTTP timeout per request in seconds (default 120)
    - **max_wait_s**: Max wait for a single generation (default 600)
    - **dry_run**: If True, return a deterministic placeholder result
    """

    capabilities = {
        "txt2img": True,
        "img2img": False,
        "multi_reference": False,
        "inpainting": False,
    }

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8188",
        checkpoint: str | None = None,
        scheduler: str = "karras",
        sampler_name: str = "euler",
        default_steps: int = 20,
        default_cfg: float = 7.5,
        output_dir: str = "generated",
        media_url_base: str = "https://game.test/media/generated",
        timeout_s: float = 120.0,
        max_wait_s: float = 600.0,
        dry_run: bool = False,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.checkpoint = checkpoint
        self.scheduler = scheduler
        self.sampler_name = sampler_name
        self.default_steps = default_steps
        self.default_cfg = default_cfg
        self.output_dir = output_dir.strip("/") or "generated"
        self.media_url_base = media_url_base.rstrip("/")
        self.timeout_s = timeout_s
        self.max_wait_s = max_wait_s
        self.dry_run = dry_run
        self._client = httpx.Client(timeout=self.timeout_s)
        self._checkpoint_cache: str | None = None

    # ---- public API ---------------------------------------------------------

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        started = time.perf_counter()

        if self.dry_run:
            return self._dry_result(request, started)

        if request.mode not in ("txt2img",):
            raise ValueError(
                f"ComfyUIBackend supports txt2img only; got mode={request.mode!r}"
            )

        # Resolve checkpoint once at startup
        if self._checkpoint_cache is None:
            self._checkpoint_cache = self._resolve_checkpoint()

        # Build & submit workflow
        seed = request.seed if request.seed is not None else random.randint(0, 2**32 - 1)
        workflow = self._build_workflow(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "",
            width=request.width,
            height=request.height,
            steps=self.default_steps,
            cfg=self.default_cfg,
            seed=seed,
            checkpoint=self._checkpoint_cache,
        )

        prompt_id = self._submit_prompt(workflow)

        # Wait for completion
        raw_images = self._wait_for_prompt(prompt_id)

        # Save locally
        filename = self._build_filename(request)
        image_path = f"{self.output_dir}/{filename}"
        disk_path = Path(image_path)
        disk_path.parent.mkdir(parents=True, exist_ok=True)

        if raw_images:
            self._save_image(raw_images[0], disk_path)
        else:
            self._create_placeholder(disk_path)

        image_url = f"{self.media_url_base}/{filename}"

        return ImageGenerationResult(
            image_path=image_path,
            image_url=image_url,
            seed=request.seed,
            model_name=self._checkpoint_cache,
            generation_time=time.perf_counter() - started,
            metadata={
                "mode": request.mode,
                "server": self.server_url,
                "checkpoint": self._checkpoint_cache,
            },
        )

    # ---- workflow construction ----------------------------------------------

    def _build_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg: float,
        seed: int,
        checkpoint: str,
    ) -> dict[str, Any]:
        """Build a minimal txt2img workflow dict for ComfyUI."""
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 1],
                },
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["1", 1],
                },
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1,
                },
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": self.sampler_name,
                    "scheduler": self.scheduler,
                    "denoise": 1.0,
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2],
                },
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["6", 0],
                    "filename_prefix": "comfyimg",
                },
            },
        }

    # ---- ComfyUI client -------------------------------------------------------

    def _resolve_checkpoint(self) -> str:
        """Fetch available checkpoints from the server and return one."""
        try:
            r = self._client.get(f"{self.server_url}/api/models/checkpoints")
            if r.status_code == 200:
                models = r.json()
                ckpt_list = [
                    m if isinstance(m, str) else m.get("name", "")
                    for m in models
                ]
                ckpt_list = [c for c in ckpt_list if c]
                # Pick actual checkpoint files first (no embedded / path)
                actual_ckpts = [
                    c for c in ckpt_list
                    if c.endswith((".safetensors", ".ckpt")) and "/" not in c
                ]
                candidates = actual_ckpts or ckpt_list
                if self.checkpoint and self.checkpoint in candidates:
                    return self.checkpoint
                if candidates:
                    return candidates[0]
        except httpx.ConnectError as exc:
            raise ComfyUIServerNotFound(
                f"Cannot connect to ComfyUI server at"
                f" {self.server_url}: {exc}"
            ) from exc

        raise ComfyUIServerNotFound(
            "No checkpoints found on ComfyUI server. "
            "Download one to models/checkpoints/ and restart the server."
        )

    def _submit_prompt(self, workflow: dict[str, Any]) -> str:
        payload = {"prompt": workflow}
        r = self._client.post(
            f"{self.server_url}/prompt",
            headers={"Content-Type": "application/json"},
            content=json.dumps(payload),
        )
        if r.status_code != 200:
            raise ComfyUIWorkflowError(
                f"ComfyUI /prompt returned {r.status_code}: {r.text[:500]}"
            )
        data = r.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ComfyUIWorkflowError(f"No prompt_id in response: {data}")
        return prompt_id

    def _wait_for_prompt(self, prompt_id: str) -> list[dict[str, Any]]:
        """Poll history until the prompt finishes; return image metadata."""
        deadline = time.monotonic() + self.max_wait_s
        while time.monotonic() < deadline:
            r = self._client.get(f"{self.server_url}/history/{prompt_id}")
            if r.status_code == 200:
                history = r.json()
                prompt_data = history.get(prompt_id)
                if prompt_data and "outputs" in prompt_data:
                    outputs = prompt_data["outputs"]
                    for node_id, node_out in outputs.items():
                        if "images" in node_out:
                            return node_out["images"]
                    break
            time.sleep(0.5)

        raise TimeoutError(
            f"Timed out waiting for ComfyUI prompt {prompt_id}"
            f" after {self.max_wait_s}s"
        )

    def _download_image(self, image_info: dict[str, Any]) -> bytes:
        filename = image_info.get("filename", "")
        subfolder = image_info.get("subfolder", "")
        query = {
            "filename": f"{subfolder}/{filename}" if subfolder else filename,
            "subfolder": str(subfolder),
            "type": "output",
        }
        url = f"{self.server_url}/view?{urllib.parse.urlencode(query)}"
        r = self._client.get(url)
        if r.status_code != 200:
            raise ComfyUIWorkflowError(
                f"Failed to download image {filename}: {r.status_code}"
            )
        return r.content

    # ---- helpers ------------------------------------------------------------

    def _build_filename(self, request: ImageGenerationRequest) -> str:
        digest_input = (
            f"{request.subject_type}:{request.subject_key}:"
            f"{request.mode}:{request.prompt}:{request.negative_prompt}"
        )
        digest = hashlib.sha1(digest_input.encode("utf-8")).hexdigest()[:12]
        return f"{request.subject_type}_{request.subject_key}_{digest}.png"

    def _save_image(self, image_info: dict[str, Any], path: Path) -> None:
        path.write_bytes(self._download_image(image_info))

    def _create_placeholder(self, path: Path) -> None:
        """Write a minimal 1×1 grey PNG so downstream code doesn't crash."""
        import struct
        import zlib

        def _chunk(ctype: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
            return length + ctype + data + crc

        ihdr = struct.pack(">IIBB BBB", 1, 1, 8, 2, 0, 0, 0)
        png = (
            b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(b"\xaa"))
            + _chunk(b"IEND", b"")
        )
        path.write_bytes(png)

    def _dry_result(
        self, request: ImageGenerationRequest, started: float
    ) -> ImageGenerationResult:
        filename = self._build_filename(request)
        return ImageGenerationResult(
            image_path=f"{self.output_dir}/{filename}",
            image_url=f"{self.media_url_base}/{filename}",
            seed=request.seed,
            model_name=self.checkpoint or "comfyui-dry-run",
            generation_time=time.perf_counter() - started,
            metadata={"mode": request.mode, "dry_run": True},
        )

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
