"""Shared fixtures for the Rune Arc test harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator

# Ensure tests/ is in sys.path so `from helpers.x import Y` works regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

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
    """Validate ~/.claude-rune-plugin-test/ exists for isolated E2E testing.

    This fixture expects the isolated config directory to be set up manually
    before running E2E tests. It never reads from or touches ~/.claude/.

    Manual setup:
        mkdir -p ~/.claude-rune-plugin-test
        # Copy any needed settings into it manually

    The harness uses CLAUDE_CONFIG_DIR=~/.claude-rune-plugin-test to redirect
    all Claude Code state (teams, tasks, memory) to this directory.
    """
    from helpers.claude_runner import ClaudeRunner

    config_dir = ClaudeRunner.default_config_dir()
    if not config_dir.exists():
        pytest.skip(
            f"Isolated config dir not found: {config_dir}\n"
            f"Create it manually: mkdir -p {config_dir}"
        )

    # Ensure state subdirs exist (non-destructive)
    for state_dir in ("teams", "tasks", "projects", "agent-memory"):
        (config_dir / state_dir).mkdir(exist_ok=True)

    yield config_dir
