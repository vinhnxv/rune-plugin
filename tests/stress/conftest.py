"""Stress-tier pytest fixtures.

Provides session-scoped cost tracking and per-test isolation configuration
for the stress test tier. Fixture names use the ``stress_`` prefix to avoid
shadowing root-level conftest fixtures.

Stress tests are opt-in: they require the ``--run-stress`` CLI flag and are
excluded from the default pytest run via ``addopts = -m "not stress"`` in
``pyproject.toml``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from helpers.cost_tracker import CostTracker


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def stress_cost_tracker() -> CostTracker:
    """Session-scoped CostTracker instance for stress tests.

    Shared across all stress tests in a single pytest session.  Budget is
    read from ``RUNE_TEST_MAX_BUDGET`` (default $20 per session).  Individual
    stress tests are capped at $2.00 each.

    Returns:
        A fresh CostTracker initialised from the environment.
    """
    return CostTracker()


# ---------------------------------------------------------------------------
# Function-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stress_config(tmp_path: Path) -> Path:
    """Isolated CLAUDE_CONFIG_DIR for a single stress test.

    Creates a temporary directory pre-populated with the standard Rune state
    sub-directories (``teams``, ``tasks``, ``projects``, ``agent-memory``).
    The directory is removed automatically after the test.

    Args:
        tmp_path: pytest built-in temporary directory fixture.

    Returns:
        Path to the isolated config directory.
    """
    config = tmp_path / "claude-config"
    config.mkdir()
    for subdir in ("teams", "tasks", "projects", "agent-memory"):
        (config / subdir).mkdir()
    return config


@pytest.fixture
def stress_config_dir() -> Iterator[Path]:
    """Temporary CLAUDE_CONFIG_DIR scoped to one stress test (uses tempfile).

    Identical in purpose to ``stress_config`` but allocates storage via
    :func:`tempfile.TemporaryDirectory` rather than pytest's ``tmp_path``.
    Use this variant when you need the path *before* the test function body
    (e.g. when parameterising at collection time).

    Yields:
        Path to the isolated config directory, cleaned up after the test.
    """
    with tempfile.TemporaryDirectory(prefix="rune-stress-") as tmpdir:
        config = Path(tmpdir)
        for subdir in ("teams", "tasks", "projects", "agent-memory"):
            (config / subdir).mkdir()
        yield config
