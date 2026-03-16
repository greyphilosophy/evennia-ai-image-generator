from evennia_ai_image_generator.backend.base import BaseImageBackend
from evennia_ai_image_generator.backend.loader import BackendConfigurationError, load_backend
from evennia_ai_image_generator.backend.placeholder import PlaceholderBackend


class _CustomBackend(BaseImageBackend):
    def __init__(self, marker: str = "ok") -> None:
        self.marker = marker

    def generate(self, request):  # pragma: no cover - not used in loader tests
        raise NotImplementedError


class _NotABackend:
    pass


def test_load_backend_defaults_to_placeholder() -> None:
    backend = load_backend()
    assert isinstance(backend, PlaceholderBackend)


def test_load_backend_accepts_placeholder_options() -> None:
    backend = load_backend({"backend": "placeholder", "options": {"media_url_base": "https://example.test/media"}})
    assert isinstance(backend, PlaceholderBackend)
    assert backend.media_url_base == "https://example.test/media"


def test_load_backend_imports_custom_backend_by_path() -> None:
    backend = load_backend(
        {
            "backend": "tests.unit.test_backend_loader:_CustomBackend",
            "options": {"marker": "loaded"},
        }
    )
    assert isinstance(backend, _CustomBackend)
    assert backend.marker == "loaded"


def test_load_backend_rejects_invalid_backend_name() -> None:
    try:
        load_backend({"backend": "unknown"})
    except BackendConfigurationError as err:
        assert "Unknown backend" in str(err)
    else:
        raise AssertionError("Expected BackendConfigurationError")


def test_load_backend_rejects_non_backend_class() -> None:
    try:
        load_backend({"backend": "tests.unit.test_backend_loader:_NotABackend"})
    except BackendConfigurationError as err:
        assert "not a BaseImageBackend" in str(err)
    else:
        raise AssertionError("Expected BackendConfigurationError")


def test_load_backend_requires_dict_options() -> None:
    try:
        load_backend({"backend": "placeholder", "options": ["not", "a", "dict"]})
    except BackendConfigurationError as err:
        assert "must be a dictionary" in str(err)
    else:
        raise AssertionError("Expected BackendConfigurationError")


def test_load_backend_requires_dict_config() -> None:
    try:
        load_backend("placeholder")  # type: ignore[arg-type]
    except BackendConfigurationError as err:
        assert "configuration must be a dictionary" in str(err)
    else:
        raise AssertionError("Expected BackendConfigurationError")


def test_load_backend_requires_string_backend_name() -> None:
    try:
        load_backend({"backend": 123})  # type: ignore[arg-type]
    except BackendConfigurationError as err:
        assert "name must be a string" in str(err)
    else:
        raise AssertionError("Expected BackendConfigurationError")


def test_load_backend_treats_none_options_as_empty_dict() -> None:
    backend = load_backend({"backend": "placeholder", "options": None})
    assert isinstance(backend, PlaceholderBackend)
