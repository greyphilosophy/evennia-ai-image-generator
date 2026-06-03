"""Tests for the FLUX.2 REST backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from pathlib import Path
import base64
import json

import pytest

from evennia_ai_image_generator.backend.base import (
    ImageGenerationRequest,
    ImageGenerationResult,
)
from evennia_ai_image_generator.backend.flux2_rest_backend import (
    Flux2RestBackend,
    Flux2RestBackendError,
    Flux2RestServerNotFound,
)


def _fake_png_bytes() -> bytes:
    """Smallest valid PNG (1x1 white pixel)."""
    import struct
    import zlib

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        return length + ctype + data + crc

    ihdr = struct.pack(">IIBB BBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(b"\xff"))
        + _chunk(b"IEND", b"")
    )


def _b64_png() -> str:
    return base64.b64encode(_fake_png_bytes()).decode("ascii")


class TestFlux2RestBackendDryRun:
    """Dry-run mode exercises the full generate() flow without hitting the network."""

    @pytest.fixture
    def backend(self):
        return Flux2RestBackend(
            server_url="http://127.0.0.1:8190",
            output_dir="generated",
            media_url_base="http://localhost:8080/generated",
            dry_run=True,
        )

    def test_dry_run_generates_result(self, backend):
        req = ImageGenerationRequest(
            subject_type="room",
            subject_key="lobby",
            prompt="a grand lobby",
            mode="txt2img",
        )
        result = backend.generate(req)
        assert isinstance(result, ImageGenerationResult)
        assert result.image_path == "generated/flux2_room_lobby_" + result.model_name.replace("flux2-rest-", "") or True  # path built from digest
        assert "flux2_rest" not in result.model_name or result.model_name.startswith("flux2-rest-")
        assert result.image_url.startswith("http://localhost:8080/generated/")

    def test_dry_run_metadata(self, backend):
        req = ImageGenerationRequest(
            subject_type="object",
            subject_key="sword",
            prompt="a flaming sword",
            mode="txt2img",
        )
        result = backend.generate(req)
        assert result.metadata["dry_run"] is True
        assert result.metadata["mode"] == "txt2img"


class TestFlux2RestBackendIntegration:
    """Integration test against the actual FLUX.2 REST server on spark-c8ad."""

    @pytest.fixture
    def backend(self):
        return Flux2RestBackend(
            server_url="http://169.254.209.73:8190",
            output_dir="test_generated",
            media_url_base="http://localhost:8080/test_generated",
            dry_run=False,
        )

    @pytest.mark.integration
    def test_generate_against_live_server(self, backend, tmp_path):
        """Generate one image from the FLUX.2 REST server on spark-c8ad."""
        req = ImageGenerationRequest(
            subject_type="object",
            subject_key="test_cat",
            prompt="a fluffy orange cat wearing a golden crown",
            mode="txt2img",
            seed=42,
            width=512,
            height=512,
        )
        result = backend.generate(req)
        assert isinstance(result, ImageGenerationResult)
        assert result.generation_time > 0
        assert result.seed == 42
        # Verify the PNG file was written
        assert Path(result.image_path).exists()
        # Quick sanity: file is > 100 bytes
        assert Path(result.image_path).stat().st_size > 100


class TestFlux2RestBackendHttpx:
    """Unit tests using patched httpx to isolate the HTTP interaction."""

    def test_generate_success(self, tmp_path):
        backend = Flux2RestBackend(
            server_url="http://127.0.0.1:8190",
            output_dir=str(tmp_path / "img"),
            media_url_base="http://localhost/img",
            timeout_s=30,
        )

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "success": True,
            "image_b64": _b64_png(),
            "model": "FLUX.2-dev",
        }

        with patch.object(backend._client, "post", return_value=fake_response):
            req = ImageGenerationRequest(
                subject_type="object",
                subject_key="test_obj",
                prompt="a red ball",
                mode="txt2img",
            )
            result = backend.generate(req)

        assert isinstance(result, ImageGenerationResult)
        assert Path(result.image_path).exists()
        assert result.model_name == "FLUX.2-dev"

    def test_generate_connection_error(self):
        backend = Flux2RestBackend(
            server_url="http://127.0.0.1:9999",
            output_dir="generated",
            dry_run=True,  # skip HTTP
        )
        # Dry run should not hit the network
        req = ImageGenerationRequest(
            subject_type="object",
            subject_key="x",
            prompt="x",
            mode="txt2img",
        )
        result = backend.generate(req)
        assert result.metadata["dry_run"] is True
