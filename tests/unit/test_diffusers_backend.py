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
