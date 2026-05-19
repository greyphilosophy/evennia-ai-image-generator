import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from evennia_ai_image_generator.backend.base import ImageGenerationRequest
from evennia_ai_image_generator.backend.comfyui_backend import (
    ComfyUIBackend,
    ComfyUIBackendError,
    ComfyUIServerNotFound,
    ComfyUIWorkflowError,
)


def _request(mode: str = "txt2img") -> ImageGenerationRequest:
    return ImageGenerationRequest(
        subject_type="room",
        subject_key="tavern",
        prompt="A warm tavern interior",
        negative_prompt="ugly, blurry",
        mode=mode,
        seed=42,
    )


# ---- dry-run tests (no server needed) ----


def test_comfyui_backend_dry_run_returns_deterministic_output() -> None:
    backend = ComfyUIBackend(
        dry_run=True,
        output_dir="generated",
        media_url_base="https://game.test/media/generated",
    )

    first = backend.generate(_request())
    second = backend.generate(_request())

    assert first.image_path == second.image_path
    assert first.image_url == second.image_url
    assert first.metadata.get("dry_run") is True
    assert first.model_name == "comfyui-dry-run"  # dry run placeholder name


def test_comfyui_backend_declares_capabilities() -> None:
    backend = ComfyUIBackend(dry_run=True)

    assert backend.capabilities["txt2img"] is True
    assert backend.capabilities["img2img"] is False
    assert backend.capabilities["multi_reference"] is False
    assert backend.capabilities["inpainting"] is False


def test_comfyui_backend_rejects_unsupported_modes() -> None:
    # Must use dry_run=False so the mode check gate is reached
    backend = ComfyUIBackend(dry_run=False)
    try:
        img2img_req = ImageGenerationRequest(
            subject_type="room",
            subject_key="tavern",
            prompt="A warm tavern interior",
            negative_prompt="ugly, blurry",
            mode="img2img",
            seed=42,
        )
        backend.generate(img2img_req)
    except ValueError as err:
        assert "txt2img" in str(err)
    else:
        raise AssertionError("Expected ValueError for unsupported mode")


def test_comfyui_backend_default_options() -> None:
    backend = ComfyUIBackend(
        dry_run=True,
        checkpoint="v1-5.safetensors",
        scheduler="karras",
        sampler_name="euler",
        default_steps=20,
        default_cfg=7.5,
    )

    assert backend.server_url == "http://127.0.0.1:8188"
    assert backend.checkpoint == "v1-5.safetensors"
    assert backend.scheduler == "karras"
    assert backend.sampler_name == "euler"
    assert backend.default_steps == 20
    assert backend.default_cfg == 7.5


# ---- workflow building tests ----


def test_build_workflow_contains_correct_nodes() -> None:
    backend = ComfyUIBackend(dry_run=True)
    workflow = backend._build_workflow(
        prompt="a tavern",
        negative_prompt="blurry",
        width=512,
        height=512,
        steps=20,
        cfg=7.5,
        seed=42,
        checkpoint="v1-5.safetensors",
    )

    # Should have nodes 1-7
    assert set(workflow.keys()) == {"1", "2", "3", "4", "5", "6", "7"}

    # Node 1: CheckpointLoaderSimple
    assert workflow["1"]["class_type"] == "CheckpointLoaderSimple"
    assert workflow["1"]["inputs"]["ckpt_name"] == "v1-5.safetensors"

    # Node 2: positive prompt encode
    assert workflow["2"]["class_type"] == "CLIPTextEncode"
    assert workflow["2"]["inputs"]["text"] == "a tavern"
    assert workflow["2"]["inputs"]["clip"] == ["1", 1]

    # Node 3: negative prompt encode
    assert workflow["3"]["class_type"] == "CLIPTextEncode"
    assert workflow["3"]["inputs"]["text"] == "blurry"
    assert workflow["3"]["inputs"]["clip"] == ["1", 1]

    # Node 4: EmptyLatentImage
    assert workflow["4"]["class_type"] == "EmptyLatentImage"
    assert workflow["4"]["inputs"]["width"] == 512
    assert workflow["4"]["inputs"]["height"] == 512
    assert workflow["4"]["inputs"]["batch_size"] == 1

    # Node 5: KSampler with proper input wiring
    assert workflow["5"]["class_type"] == "KSampler"
    sampler_inputs = workflow["5"]["inputs"]
    assert sampler_inputs["model"] == ["1", 0]
    assert sampler_inputs["positive"] == ["2", 0]
    assert sampler_inputs["negative"] == ["3", 0]
    assert sampler_inputs["latent_image"] == ["4", 0]
    assert sampler_inputs["seed"] == 42
    assert sampler_inputs["steps"] == 20
    assert sampler_inputs["cfg"] == 7.5
    assert sampler_inputs["sampler_name"] == "euler"
    assert sampler_inputs["scheduler"] == "karras"
    assert sampler_inputs["denoise"] == 1.0

    # Node 6: VAEDecode
    assert workflow["6"]["class_type"] == "VAEDecode"
    assert workflow["6"]["inputs"]["samples"] == ["5", 0]
    assert workflow["6"]["inputs"]["vae"] == ["1", 2]

    # Node 7: SaveImage
    assert workflow["7"]["class_type"] == "SaveImage"
    assert workflow["7"]["inputs"]["images"] == ["6", 0]


def test_build_workflow_respects_custom_dimensions() -> None:
    backend = ComfyUIBackend(dry_run=True)
    workflow = backend._build_workflow(
        prompt="test",
        negative_prompt="bad",
        width=768,
        height=1024,
        steps=30,
        cfg=8.0,
        seed=123,
        checkpoint="some.ckpt",
    )

    assert workflow["4"]["inputs"]["width"] == 768
    assert workflow["4"]["inputs"]["height"] == 1024
    assert workflow["5"]["inputs"]["steps"] == 30
    assert workflow["5"]["inputs"]["cfg"] == 8.0
    assert workflow["5"]["inputs"]["seed"] == 123
    assert workflow["1"]["inputs"]["ckpt_name"] == "some.ckpt"


# ---- server resolution tests ----


def test_resolve_checkpoint_from_api() -> None:
    backend = ComfyUIBackend(dry_run=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        "v1-5-pruned-emaonly.safetensors",
        "sdxl-base.safetensors",
    ]
    backend._client.get = MagicMock(return_value=mock_response)

    result = backend._resolve_checkpoint()
    assert result == "v1-5-pruned-emaonly.safetensors"


def test_resolve_checkpoint_prefers_requested() -> None:
    backend = ComfyUIBackend(
        checkpoint="sdxl-base.safetensors",
        dry_run=False,
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        "v1-5-pruned-emaonly.safetensors",
        "sdxl-base.safetensors",
    ]
    backend._client.get = MagicMock(return_value=mock_response)

    result = backend._resolve_checkpoint()
    assert result == "sdxl-base.safetensors"


def test_resolve_checkpoint_filters_subdirectory_entries() -> None:
    backend = ComfyUIBackend(dry_run=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        "vae/something.safetensors",
        "diffusion_pytorch.safetensors",
    ]
    backend._client.get = MagicMock(return_value=mock_response)

    result = backend._resolve_checkpoint()
    assert result == "diffusion_pytorch.safetensors"


def test_resolve_checkpoint_raises_on_connect_error() -> None:
    import httpx
    backend = ComfyUIBackend(dry_run=False)
    backend._client.get = MagicMock(side_effect=httpx.ConnectError("refused"))

    try:
        backend._resolve_checkpoint()
    except ComfyUIServerNotFound as err:
        assert "Cannot connect" in str(err)
    else:
        raise AssertionError("Expected ComfyUIServerNotFound")


def test_resolve_checkpoint_raises_when_empty() -> None:
    backend = ComfyUIBackend(dry_run=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    backend._client.get = MagicMock(return_value=mock_response)

    try:
        backend._resolve_checkpoint()
    except ComfyUIServerNotFound as err:
        assert "No checkpoints found" in str(err)
    else:
        raise AssertionError("Expected ComfyUIServerNotFound")


def test_resolve_checkpoint_handles_dict_model_entries() -> None:
    backend = ComfyUIBackend(dry_run=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"name": "v1-5.safetensors"},
        {"name": "sdxl.safetensors"},
    ]
    backend._client.get = MagicMock(return_value=mock_response)

    result = backend._resolve_checkpoint()
    assert result == "v1-5.safetensors"


# ---- workflow submission tests ----


def test_submit_prompt_returns_prompt_id() -> None:
    backend = ComfyUIBackend(dry_run=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"prompt_id": "abc123"}
    backend._client.post = MagicMock(return_value=mock_response)

    workflow = backend._build_workflow(
        prompt="test", negative_prompt="", width=512, height=512,
        steps=20, cfg=7.5, seed=0, checkpoint="v1-5.safetensors",
    )
    pid = backend._submit_prompt(workflow)
    assert pid == "abc123"


def test_submit_prompt_raises_on_400() -> None:
    backend = ComfyUIBackend(dry_run=False)
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"error": {"type": "invalid"}}'
    backend._client.post = MagicMock(return_value=mock_response)

    workflow = backend._build_workflow(
        prompt="test", negative_prompt="", width=512, height=512,
        steps=20, cfg=7.5, seed=0, checkpoint="v1-5.safetensors",
    )
    try:
        backend._submit_prompt(workflow)
    except ComfyUIWorkflowError as err:
        assert "400" in str(err)
    else:
        raise AssertionError("Expected ComfyUIWorkflowError")


def test_submit_prompt_raises_when_no_prompt_id() -> None:
    backend = ComfyUIBackend(dry_run=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    backend._client.post = MagicMock(return_value=mock_response)

    workflow = backend._build_workflow(
        prompt="test", negative_prompt="", width=512, height=512,
        steps=20, cfg=7.5, seed=0, checkpoint="v1-5.safetensors",
    )
    try:
        backend._submit_prompt(workflow)
    except ComfyUIWorkflowError as err:
        assert "No prompt_id" in str(err)
    else:
        raise AssertionError("Expected ComfyUIWorkflowError")


# ---- helper tests ----


def test_build_filename_is_deterministic() -> None:
    backend = ComfyUIBackend(dry_run=True)
    req1 = _request()
    req2 = _request()
    assert backend._build_filename(req1) == backend._build_filename(req2)
    assert req1.subject_key in backend._build_filename(req1)


def test_build_filename_is_subject_specific() -> None:
    backend = ComfyUIBackend(dry_run=True)
    req1 = _request()
    req2 = ImageGenerationRequest(
        subject_type="object",
        subject_key="sword",
        prompt="A shiny sword",
        mode="txt2img",
    )
    assert backend._build_filename(req1) != backend._build_filename(req2)


def test_create_placeholder_writes_valid_png(tmp_path) -> None:
    backend = ComfyUIBackend(dry_run=True)
    placeholder_path = tmp_path / "placeholder.png"
    backend._create_placeholder(placeholder_path)

    assert placeholder_path.exists()
    # Valid PNG magic bytes
    assert placeholder_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_comfyui_backend_respects_scheduler_and_sampler() -> None:
    backend = ComfyUIBackend(
        dry_run=True,
        scheduler="sgm_uniform",
        sampler_name="dpmpp_2m",
    )
    workflow = backend._build_workflow(
        prompt="test", negative_prompt="", width=512, height=512,
        steps=20, cfg=7.5, seed=0, checkpoint="v1-5.safetensors",
    )
    assert workflow["5"]["inputs"]["scheduler"] == "sgm_uniform"
    assert workflow["5"]["inputs"]["sampler_name"] == "dpmpp_2m"


def test_comfyui_backend_server_url_strips_trailing_slash() -> None:
    backend = ComfyUIBackend(dry_run=True, server_url="http://127.0.0.1:8188/")
    assert backend.server_url == "http://127.0.0.1:8188"


def test_comfyui_backend_output_dir_strips_leading_slash() -> None:
    backend = ComfyUIBackend(dry_run=True, output_dir="/generated/images/")
    assert backend.output_dir == "generated/images"
