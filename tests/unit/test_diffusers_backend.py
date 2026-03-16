import sys
import threading
import time
import types

from evennia_ai_image_generator.backend.base import ImageGenerationRequest
from evennia_ai_image_generator.backend.diffusers_backend import DiffusersBackend


def _request(mode: str = "txt2img") -> ImageGenerationRequest:
    return ImageGenerationRequest(
        subject_type="room",
        subject_key="tavern",
        prompt="A warm tavern",
        mode=mode,
    )


def test_diffusers_backend_dry_run_returns_deterministic_output() -> None:
    backend = DiffusersBackend(dry_run=True, output_dir="generated", media_url_base="https://game.test/media/generated")

    first = backend.generate(_request())
    second = backend.generate(_request())

    assert first.image_path == second.image_path
    assert first.image_url == second.image_url
    assert first.metadata.get("dry_run") is True


def test_diffusers_backend_declares_txt2img_only_for_now() -> None:
    backend = DiffusersBackend(dry_run=True)

    assert backend.capabilities["txt2img"] is True
    assert backend.capabilities["img2img"] is False


def test_diffusers_backend_defaults_to_sd15_model() -> None:
    backend = DiffusersBackend(dry_run=True)

    assert backend.model_id == "runwayml/stable-diffusion-v1-5"


def test_diffusers_backend_reuses_shared_pipeline_bundle(monkeypatch) -> None:
    class _FakePipeline:
        def to(self, device):
            return self

    class _FakeStableDiffusionPipeline:
        load_calls = 0

        @classmethod
        def from_pretrained(cls, **kwargs):
            cls.load_calls += 1
            return _FakePipeline()

    fake_torch = types.SimpleNamespace(float32="float32")
    fake_diffusers = types.SimpleNamespace(StableDiffusionPipeline=_FakeStableDiffusionPipeline)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "diffusers", fake_diffusers)

    DiffusersBackend._shared_bundle_cache.clear()
    backend_one = DiffusersBackend(dry_run=False)
    backend_two = DiffusersBackend(dry_run=False)

    bundle_one = backend_one._load_bundle()
    bundle_two = backend_two._load_bundle()

    assert bundle_one is bundle_two
    assert _FakeStableDiffusionPipeline.load_calls == 1


def test_diffusers_backend_threadsafe_singleflight_bundle_load(monkeypatch) -> None:
    class _FakePipeline:
        def to(self, device):
            return self

    class _FakeStableDiffusionPipeline:
        load_calls = 0

        @classmethod
        def from_pretrained(cls, **kwargs):
            time.sleep(0.05)
            cls.load_calls += 1
            return _FakePipeline()

    fake_torch = types.SimpleNamespace(float32="float32")
    fake_diffusers = types.SimpleNamespace(StableDiffusionPipeline=_FakeStableDiffusionPipeline)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "diffusers", fake_diffusers)

    DiffusersBackend._shared_bundle_cache.clear()
    DiffusersBackend._inflight_loads.clear()
    backend_one = DiffusersBackend(dry_run=False)
    backend_two = DiffusersBackend(dry_run=False)
    results = []

    def _load(backend):
        results.append(backend._load_bundle())

    first = threading.Thread(target=_load, args=(backend_one,))
    second = threading.Thread(target=_load, args=(backend_two,))
    first.start()
    second.start()
    first.join(timeout=3)
    second.join(timeout=3)

    assert len(results) == 2
    assert results[0] is results[1]
    assert _FakeStableDiffusionPipeline.load_calls == 1
