"""Shared fixtures for the Rune Arc test harness."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterator

import pytest

TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
CHALLENGE_DIR = TESTS_DIR / "challenge"
PLUGIN_DIR = TESTS_DIR.parent / "plugins" / "rune"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def challenge_dir() -> Path:
    return CHALLENGE_DIR


@pytest.fixture
def plugin_dir() -> Path:
    return PLUGIN_DIR


@pytest.fixture
def sample_checkpoint_v4(fixtures_dir: Path) -> dict:
    return json.loads((fixtures_dir / "checkpoint_v4.json").read_text())


@pytest.fixture
def sample_tome(fixtures_dir: Path) -> str:
    return (fixtures_dir / "tome_sample.md").read_text()


@pytest.fixture
def isolated_claude_config() -> Iterator[Path]:
    """Set up ~/.claude-rune-plugin-test/ with auth preserved.

    Wipes and recreates the fixed config directory with:
    - Auth files copied from ~/.claude/ (settings.json, settings.local.json)
    - Empty state directories (teams/, tasks/, projects/, agent-memory/)

    Cleaned up after the test.
    """
    from helpers.claude_runner import ClaudeRunner

    config_dir = ClaudeRunner.default_config_dir()
    if config_dir.exists():
        shutil.rmtree(config_dir)
    config_dir.mkdir()

    real_config = Path.home() / ".claude"
    for auth_file in ("settings.json", "settings.local.json"):
        src = real_config / auth_file
        if src.exists():
            shutil.copy2(src, config_dir / auth_file)

    for state_dir in ("teams", "tasks", "projects", "agent-memory"):
        (config_dir / state_dir).mkdir()

    yield config_dir

    shutil.rmtree(config_dir, ignore_errors=True)
