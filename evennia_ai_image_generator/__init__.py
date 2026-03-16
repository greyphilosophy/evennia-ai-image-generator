"""Core package for evennia-ai-image-generator."""

from .backend.base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult, ReferenceImage
from .backend.loader import BackendConfigurationError, load_backend
from .backend.diffusers_backend import DiffusersBackend
from .backend.placeholder import PlaceholderBackend
from .mixins import SceneImageMixin
from .context import collect_subject_context
from .prompts import build_prompt, compute_prompt_fingerprint
from .queue import GenerationQueue, build_generation_queue, process_generation_job
from .config import RuntimeServices, build_runtime_services
from .commands import imagegen, imageregen, imageclear, imageprompt

__all__ = [
    "BaseImageBackend",
    "GenerationQueue",
    "build_generation_queue",
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
    "RuntimeServices",
    "build_runtime_services",
    "imagegen",
    "imageregen",
    "imageclear",
    "imageprompt",
]
