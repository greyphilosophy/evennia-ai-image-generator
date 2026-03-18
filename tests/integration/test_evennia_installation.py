from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest


EVENNIA_CLI = shutil.which("evennia")
HAS_EVENNIA = importlib.util.find_spec("evennia") is not None and EVENNIA_CLI is not None


@pytest.mark.skipif(not HAS_EVENNIA, reason="Evennia is not installed in this environment")
def test_evennia_init_and_migrate_with_plugin_app(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    game_name = "integration_game"
    game_dir = tmp_path / game_name

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{repo_root}:{existing_pythonpath}" if existing_pythonpath else str(repo_root)

    init = subprocess.run(
        [EVENNIA_CLI, "--init", game_name],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    assert init.returncode == 0, init.stderr

    settings_path = game_dir / "server" / "conf" / "settings.py"
    assert settings_path.exists()
    with settings_path.open("a", encoding="utf-8") as handle:
        handle.write('\nINSTALLED_APPS += ["evennia_ai_image_generator"]\n')

    migrate = subprocess.run(
        [EVENNIA_CLI, "migrate", "--noinput"],
        cwd=game_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=300,
    )
    assert migrate.returncode == 0, migrate.stderr
