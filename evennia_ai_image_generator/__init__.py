"""Core package for evennia-ai-image-generator.

The package intentionally avoids importing all submodules eagerly at import-time.
This keeps Django/Evennia app loading lightweight when the package is listed in
``INSTALLED_APPS``.
"""

from importlib import import_module


_EXPORTS = {
    "BaseImageBackend": "evennia_ai_image_generator.backend.base",
    "ImageGenerationRequest": "evennia_ai_image_generator.backend.base",
    "ImageGenerationResult": "evennia_ai_image_generator.backend.base",
    "ReferenceImage": "evennia_ai_image_generator.backend.base",
    "BackendConfigurationError": "evennia_ai_image_generator.backend.loader",
    "load_backend": "evennia_ai_image_generator.backend.loader",
    "ImageGenerationError": "evennia_ai_image_generator.errors",
    "ModelLoadError": "evennia_ai_image_generator.errors",
    "DiffusersBackend": "evennia_ai_image_generator.backend.diffusers_backend",
    "PlaceholderBackend": "evennia_ai_image_generator.backend.placeholder",
    "SceneImageMixin": "evennia_ai_image_generator.mixins",
    "collect_subject_context": "evennia_ai_image_generator.context",
    "build_prompt": "evennia_ai_image_generator.prompts",
    "compute_prompt_fingerprint": "evennia_ai_image_generator.prompts",
    "compute_state_fingerprint": "evennia_ai_image_generator.prompts",
    "GenerationQueue": "evennia_ai_image_generator.queue",
    "build_generation_queue": "evennia_ai_image_generator.queue",
    "process_generation_job": "evennia_ai_image_generator.queue",
    "RuntimeServices": "evennia_ai_image_generator.config",
    "build_runtime_services": "evennia_ai_image_generator.config",
    "imagegen": "evennia_ai_image_generator.commands",
    "imageregen": "evennia_ai_image_generator.commands",
    "imageclear": "evennia_ai_image_generator.commands",
    "imageprompt": "evennia_ai_image_generator.commands",
}

__all__ = [
    "BaseImageBackend",
    "GenerationQueue",
    "build_generation_queue",
    "ImageGenerationRequest",
    "ImageGenerationResult",
    "PlaceholderBackend",
    "DiffusersBackend",
    "BackendConfigurationError",
    "ImageGenerationError",
    "ModelLoadError",
    "load_backend",
    "ReferenceImage",
    "SceneImageMixin",
    "collect_subject_context",
    "build_prompt",
    "compute_prompt_fingerprint",
    "compute_state_fingerprint",
    "process_generation_job",
    "RuntimeServices",
    "build_runtime_services",
    "imagegen",
    "imageregen",
    "imageclear",
    "imageprompt",
]


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
