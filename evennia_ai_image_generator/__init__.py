"""Core package for evennia-ai-image-generator."""

from .backend.base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult, ReferenceImage
from .backend.loader import BackendConfigurationError, load_backend
from .backend.diffusers_backend import DiffusersBackend
from .backend.placeholder import PlaceholderBackend
from .mixins import SceneImageMixin
from .context import collect_subject_context
from .prompts import build_prompt, compute_prompt_fingerprint
from .queue import GenerationQueue, process_generation_job
from .commands import imagegen, imageregen, imageclear, imageprompt

__all__ = [
    "BaseImageBackend",
    "GenerationQueue",
    "ImageGenerationRequest",
    "ImageGenerationResult",
    "PlaceholderBackend",
    "DiffusersBackend",
    "BackendConfigurationError",
    "load_backend",
    "ReferenceImage",
    "SceneImageMixin",
    "collect_subject_context",
    "build_prompt",
    "compute_prompt_fingerprint",
    "process_generation_job",
    "imagegen",
    "imageregen",
    "imageclear",
    "imageprompt",
]
