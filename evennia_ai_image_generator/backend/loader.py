from __future__ import annotations

from importlib import import_module
from typing import Any

from .base import BaseImageBackend
from .placeholder import PlaceholderBackend


class BackendConfigurationError(ValueError):
    """Raised when backend settings are invalid or the backend cannot be loaded."""


def load_backend(config: dict[str, Any] | None = None) -> BaseImageBackend:
    """Load and instantiate an image backend from lightweight config.

    Supported configuration patterns:

    - None / {}: returns PlaceholderBackend()
    - {"backend": "placeholder", "options": {...}}
    - {"backend": "pkg.module:ClassName", "options": {...}}
    """

    if config is None:
        config = {}
    elif not isinstance(config, dict):
        raise BackendConfigurationError("Backend configuration must be a dictionary")

    backend_name = config.get("backend", "placeholder")
    options = config.get("options", {})

    if not isinstance(backend_name, str):
        raise BackendConfigurationError("Backend name must be a string")

    if options is None:
        options = {}

    if not isinstance(options, dict):
        raise BackendConfigurationError("Backend options must be a dictionary")

    if backend_name == "placeholder":
        return PlaceholderBackend(**options)

    if ":" not in backend_name:
        raise BackendConfigurationError(
            "Unknown backend. Use 'placeholder' or a 'module.path:ClassName' backend path"
        )

    module_name, class_name = backend_name.split(":", 1)
    if not module_name or not class_name:
        raise BackendConfigurationError(
            "Backend path must include both module and class name, e.g. 'pkg.module:BackendClass'"
        )

    try:
        module = import_module(module_name)
    except Exception as err:  # pragma: no cover - exercised by tests, kept broad for import errors
        raise BackendConfigurationError(f"Could not import backend module '{module_name}': {err}") from err

    try:
        backend_cls = getattr(module, class_name)
    except AttributeError as err:
        raise BackendConfigurationError(
            f"Backend class '{class_name}' was not found in module '{module_name}'"
        ) from err

    if not isinstance(backend_cls, type) or not issubclass(backend_cls, BaseImageBackend):
        raise BackendConfigurationError(
            f"Configured backend '{backend_name}' is not a BaseImageBackend subclass"
        )

    try:
        return backend_cls(**options)
    except Exception as err:  # pragma: no cover - construction failures are configuration errors
        raise BackendConfigurationError(
            f"Could not initialize backend '{backend_name}' with provided options: {err}"
        ) from err
