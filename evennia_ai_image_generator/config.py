from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .backend.base import BaseImageBackend
from .backend.loader import load_backend
from .queue import GenerationQueue, build_generation_queue
from .state import validate_max_image_history_limit


@dataclass(frozen=True)
class RuntimeServices:
    """Resolved runtime services built from package configuration."""

    backend: BaseImageBackend
    queue: GenerationQueue
    max_image_history: int | None = None


def build_runtime_services(config: dict[str, Any] | None = None) -> RuntimeServices:
    """Build backend + queue services from a lightweight configuration mapping.

    Supported top-level keys:

    - ``backend``: backend configuration consumed by :func:`load_backend`.
    - ``queue``: queue configuration consumed by :func:`build_generation_queue`.
    - ``max_image_history``: optional integer cap for per-subject image history.
    """

    if config is None:
        config = {}
    elif not isinstance(config, dict):
        raise ValueError("Runtime configuration must be a dictionary")

    unknown_options = set(config) - {"backend", "queue", "max_image_history"}
    if unknown_options:
        names = ", ".join(sorted(unknown_options))
        raise ValueError(f"Unknown runtime option(s): {names}")

    max_image_history = validate_max_image_history_limit(
        config.get("max_image_history"),
        option_name="Runtime option 'max_image_history'",
    )

    backend_config = config.get("backend")
    queue_config = config.get("queue")

    if backend_config is not None and not isinstance(backend_config, dict):
        raise ValueError("Runtime option 'backend' must be a dictionary or None")

    if queue_config is not None and not isinstance(queue_config, dict):
        raise ValueError("Runtime option 'queue' must be a dictionary or None")

    backend = load_backend(backend_config)
    queue = build_generation_queue(queue_config)
    return RuntimeServices(backend=backend, queue=queue, max_image_history=max_image_history)
