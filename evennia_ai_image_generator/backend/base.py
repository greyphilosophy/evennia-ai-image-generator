from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ReferenceImage:
    path: str
    role: str
    weight: float = 1.0
    caption: str | None = None


@dataclass
class ImageGenerationRequest:
    subject_type: Literal["room", "object"]
    subject_key: str
    prompt: str
    negative_prompt: str = ""
    mode: Literal["txt2img", "img2img", "refine", "compose"] = "txt2img"
    reference_images: list[ReferenceImage] = field(default_factory=list)
    seed: int | None = None
    width: int = 1024
    height: int = 1024
    strength: float | None = None
    guidance_scale: float | None = None
    style: str | None = None


@dataclass
class ImageGenerationResult:
    image_path: str
    image_url: str
    seed: int | None
    model_name: str
    generation_time: float
    metadata: dict = field(default_factory=dict)


class BaseImageBackend:
    capabilities = {
        "txt2img": True,
        "img2img": False,
        "multi_reference": False,
        "inpainting": False,
    }

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        raise NotImplementedError
