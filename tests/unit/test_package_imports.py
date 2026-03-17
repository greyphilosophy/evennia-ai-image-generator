from __future__ import annotations

import importlib.util
import json
import subprocess
import sys

import pytest


def _run_python(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        capture_output=True,
        check=False,
    )


def test_package_import_is_lazy() -> None:
    result = _run_python(
        """
import json
import sys
import evennia_ai_image_generator

print(json.dumps({
    "diffusers_loaded": "evennia_ai_image_generator.backend.diffusers_backend" in sys.modules,
    "commands_loaded": "evennia_ai_image_generator.commands" in sys.modules,
    "config_loaded": "evennia_ai_image_generator.config" in sys.modules,
}))
"""
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())

    assert payload["diffusers_loaded"] is False
    assert payload["commands_loaded"] is False
    assert payload["config_loaded"] is False


def test_public_exports_still_resolve_lazily() -> None:
    result = _run_python(
        """
import json
import sys
import evennia_ai_image_generator as pkg

services_builder = pkg.build_runtime_services

print(json.dumps({
    "callable": callable(services_builder),
    "config_loaded": "evennia_ai_image_generator.config" in sys.modules,
}))
"""
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())

    assert payload["callable"] is True
    assert payload["config_loaded"] is True


@pytest.mark.skipif(importlib.util.find_spec("django") is None, reason="django is not installed")
def test_django_can_populate_installed_apps_with_package() -> None:
    result = _run_python(
        """
from django.conf import settings
import django

settings.configure(
    SECRET_KEY="tests",
    INSTALLED_APPS=["evennia_ai_image_generator"],
)

django.setup()
print("ok")
"""
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
