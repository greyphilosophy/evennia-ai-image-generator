import pytest

from evennia_ai_image_generator import build_runtime_services
from evennia_ai_image_generator.backend.diffusers_backend import DiffusersBackend
from evennia_ai_image_generator.backend.placeholder import PlaceholderBackend


def test_build_runtime_services_defaults() -> None:
    services = build_runtime_services()

    assert isinstance(services.backend, PlaceholderBackend)
    assert services.queue.max_pending is None
    assert services.max_image_history is None


def test_build_runtime_services_applies_performance_options() -> None:
    services = build_runtime_services(
        {
            "backend": {
                "backend": "diffusers",
                "options": {
                    "dry_run": True,
                    "shared_model_cache": False,
                },
            },
            "queue": {"max_pending": 3},
            "max_image_history": 5,
        }
    )

    assert isinstance(services.backend, DiffusersBackend)
    assert services.backend.shared_model_cache is False
    assert services.queue.max_pending == 3
    assert services.max_image_history == 5


@pytest.mark.parametrize("invalid", [[], (), "config", 3])
def test_build_runtime_services_rejects_non_mapping_config(invalid) -> None:
    with pytest.raises(ValueError, match="Runtime configuration"):
        build_runtime_services(invalid)


def test_build_runtime_services_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match="Unknown runtime option"):
        build_runtime_services({"unknown": True})


@pytest.mark.parametrize("invalid", [True, -1, 2.5, "10"])
def test_build_runtime_services_rejects_invalid_max_image_history(invalid) -> None:
    with pytest.raises(ValueError, match="max_image_history"):
        build_runtime_services({"max_image_history": invalid})


@pytest.mark.parametrize("invalid", [[], (), "backend", 4])
def test_build_runtime_services_rejects_invalid_backend_shape(invalid) -> None:
    with pytest.raises(ValueError, match="Runtime option 'backend'"):
        build_runtime_services({"backend": invalid})


@pytest.mark.parametrize("invalid", [[], (), "queue", 7])
def test_build_runtime_services_rejects_invalid_queue_shape(invalid) -> None:
    with pytest.raises(ValueError, match="Runtime option 'queue'"):
        build_runtime_services({"queue": invalid})
