"""Core package for evennia-ai-image-generator."""

from .backend.base import BaseImageBackend, ImageGenerationRequest, ImageGenerationResult, ReferenceImage
from .backend.loader import BackendConfigurationError, load_backend
from .backend.diffusers_backend import DiffusersBackend
from .backend.placeholder import PlaceholderBackend
from .mixins import SceneImageMixin
from .queue import GenerationQueue, process_generation_job

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
    "process_generation_job",
]
