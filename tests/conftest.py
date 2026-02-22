"""Shared fixtures for the Rune Arc test harness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Iterator

# Ensure tests/ is in sys.path so `from helpers.x import Y` works regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
CHALLENGE_DIR = TESTS_DIR / "challenge"
PLUGIN_DIR = TESTS_DIR.parent / "plugins" / "rune"
SCRIPTS_DIR = PLUGIN_DIR / "scripts"


# ---------------------------------------------------------------------------
# Custom markers
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_jq: test requires jq binary")
    config.addinivalue_line("markers", "security: security-critical test")
    config.addinivalue_line("markers", "session_isolation: cross-session safety test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def has_jq() -> bool:
    """Check if jq is available on PATH."""
    try:
        subprocess.run(["jq", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_jq = pytest.mark.skipif(not has_jq(), reason="jq not installed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def scripts_dir() -> Path:
    return SCRIPTS_DIR


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


@pytest.fixture
def project_env() -> Iterator[tuple[Path, Path]]:
    """Create an isolated project root + CLAUDE_CONFIG_DIR pair for hook tests.

    Yields (project_dir, config_dir) with the standard Rune directory layout.
    Both directories are cleaned up after the test.
    """
    import os
    import tempfile

    with tempfile.TemporaryDirectory(prefix="rune-project-") as project_dir:
        with tempfile.TemporaryDirectory(prefix="rune-config-") as config_dir:
            project = Path(project_dir)
            config = Path(config_dir)
            (project / "tmp").mkdir()
            (project / ".claude").mkdir()
            (project / ".claude" / "arc").mkdir()
            (config / "teams").mkdir()
            (config / "tasks").mkdir()
            yield project, config


@pytest.fixture
def hook_runner(project_env: tuple[Path, Path]):
    """Factory fixture for running hook scripts with proper environment isolation."""
    import os

    project, config = project_env

    def _run(
        script: Path,
        input_json: dict | str,
        *,
        env_override: dict[str, str] | None = None,
        timeout: int = 15,
    ) -> subprocess.CompletedProcess[str]:
        if isinstance(input_json, dict):
            # Inject cwd if not already provided
            if "cwd" not in input_json:
                input_json["cwd"] = str(project)
            stdin_text = json.dumps(input_json)
        else:
            stdin_text = input_json

        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        env["PPID"] = str(os.getpid())  # Use test process PID
        if env_override:
            env.update(env_override)

        return subprocess.run(
            ["bash", str(script)],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(project),
        )

    return _run
