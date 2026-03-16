from __future__ import annotations


class ImageGenerationError(RuntimeError):
    """Raised when a generation job fails during request execution."""


class ModelLoadError(ImageGenerationError):
    """Raised when a backend model cannot be loaded/initialized."""
