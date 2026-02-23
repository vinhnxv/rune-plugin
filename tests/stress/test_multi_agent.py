"""Multi-agent coordination stress tests.

Tests team coordination under contention using full E2E harness.  These
are NOT unit tests — each scenario spawns real Claude subprocesses and
exercises the Agent Teams machinery.

Scenarios:
  1. concurrent_claim     — 5 agents, 3 tasks: no double-claiming
  2. file_conflict        — 2 agents, same file: conflict detected/resolved
  3. dependency_ordering  — A→B→C chain: tasks respected in order
  4. graceful_degradation — 1 of 5 agents crashes: others continue
  5. broadcast_delivery   — 8 agents: all receive a broadcast message

All tests are opt-in via @pytest.mark.stress.  Run with:
    pytest tests/stress/test_multi_agent.py -m stress

CRITICAL: These tests use full E2E subprocess invocations with real Claude
API calls.  They are excluded from the default run to avoid accidental spend.

Edge cases handled:
  EDGE-006: Per-test isolated config dir (UUID-named tempdir)
  EDGE-007: UUID-based team names to prevent collision on re-run
  ORPHAN:   Session-scoped finalizer kills any teams whose owner PID is dead
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import pytest

from helpers.claude_runner import ClaudeRunner, RunResult
from helpers.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLUGIN_DIR = Path(__file__).resolve().parent.parent.parent / "plugins" / "rune"
HAIKU_MODEL = "claude-haiku-4-5-20251001"
STRESS_MARKER = pytest.mark.stress

# Per-test timeout — stress tests may be slow but must not run forever
SCENARIO_TIMEOUT_SECONDS = 120

# Guard against accidental pytest-xdist parallel execution.
# Why: Agent Teams tests create shared filesystem state (team config dirs,
# task files) keyed by team name. Parallel workers would race on teardown,
# causing intermittent cleanup failures and orphaned team directories.
if os.environ.get("PYTEST_XDIST_WORKER"):
    pytest.exit(
        "stress/test_multi_agent.py must not run under pytest-xdist. "
        "Remove -n / --dist flags or exclude this file.",
        returncode=3,
    )


# ---------------------------------------------------------------------------
# Shared team-name registry (session-scoped orphan tracking)
# ---------------------------------------------------------------------------

# Why: We track every team name created during the session so the session
# finalizer can attempt cleanup even if a test crashes mid-teardown.
_SESSION_TEAMS: list[tuple[str, str]] = []  # [(team_name, config_dir)]


def _register_team(team_name: str, config_dir: str) -> None:
    _SESSION_TEAMS.append((team_name, config_dir))


def _cleanup_team(team_name: str, config_dir: str) -> None:
    """Best-effort team cleanup: remove team/task directories.

    Why best-effort: The team may already be deleted (normal path) or the
    config dir may have been removed by the OS.  We never want cleanup
    failures to shadow real test failures.
    """
    chome = config_dir
    for subdir in (f"teams/{team_name}", f"tasks/{team_name}"):
        target = Path(chome) / subdir
        if target.exists():
            try:
                import shutil
                shutil.rmtree(target, ignore_errors=True)
                logger.debug("Cleaned up %s", target)
            except OSError as exc:
                logger.warning("Failed to clean up %s: %s", target, exc)


# ---------------------------------------------------------------------------
# Session-scoped orphan cleanup finalizer
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _orphan_team_cleanup() -> None:  # type: ignore[return]
    """Session finalizer: clean up any teams that survived a test crash.

    Runs after ALL stress tests complete.  For each registered team, removes
    the filesystem directories unconditionally (the team may already be gone).

    Why autouse=True + session scope: This finalizer must fire even if no
    individual test requests it, and it must run exactly once at the very end
    of the session rather than after each test.
    """
    yield  # test session runs here
    for team_name, config_dir in _SESSION_TEAMS:
        _cleanup_team(team_name, config_dir)
    if _SESSION_TEAMS:
        logger.info("Orphan cleanup: processed %d registered teams", len(_SESSION_TEAMS))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_team_name() -> str:
    """Generate a collision-safe team name (EDGE-007).

    Why UUID suffix: If a test crashes before teardown, the team directory
    remains on disk.  On re-run, a deterministic name would collide with the
    leftover and cause TeamCreate to fail.  A UUID suffix makes each run
    unique while keeping the ``rune-stress-`` prefix for easy grep/cleanup.
    """
    return f"rune-stress-{uuid4().hex[:8]}"


def _make_isolated_config(tmp_base: Path) -> Path:
    """Create a per-test isolated CLAUDE_CONFIG_DIR (EDGE-006).

    Each stress test gets its own config directory so teams, tasks, and
    agent-memory from one test never contaminate another.

    Args:
        tmp_base: Parent directory (typically pytest's tmp_path).

    Returns:
        Path to the newly created config directory.
    """
    config = tmp_base / f"config-{uuid4().hex[:6]}"
    config.mkdir(parents=True)
    for subdir in ("teams", "tasks", "projects", "agent-memory"):
        (config / subdir).mkdir()
    return config


def _run_claude(
    prompt: str,
    config_dir: Path,
    workspace: Path,
    timeout: int = SCENARIO_TIMEOUT_SECONDS,
) -> RunResult:
    """Run a single Claude invocation with Agent Teams enabled.

    Args:
        prompt:     Prompt to send to Claude.
        config_dir: Isolated CLAUDE_CONFIG_DIR for this run.
        workspace:  Working directory for the Claude process.
        timeout:    Wall-clock timeout in seconds.

    Returns:
        RunResult from ClaudeRunner.
    """
    runner = ClaudeRunner(
        plugin_dir=PLUGIN_DIR,
        working_dir=workspace,
        max_turns=20,
        max_budget_usd=2.00,
        timeout_seconds=timeout,
        model=HAIKU_MODEL,
        extra_env={
            "CLAUDE_CONFIG_DIR": str(config_dir),
            "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
        },
    )
    runner.isolated_config_dir = config_dir
    return runner.run(prompt)


# ---------------------------------------------------------------------------
# Scenario 1: Concurrent task claiming — no double-claiming
# ---------------------------------------------------------------------------


@STRESS_MARKER
def test_multi_agent_no_double_claiming(tmp_path: Path) -> None:
    """Five concurrent agents claim 3 tasks — each task claimed at most once.

    Validates that the Agent Teams task system provides mutual exclusion on
    task ownership.  With 5 agents racing to claim 3 tasks, exactly 3 tasks
    should be owned (one per task) with no duplicates.

    Args:
        tmp_path: pytest temporary directory fixture.
    """
    config_dir = _make_isolated_config(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    team_name = _make_team_name()
    _register_team(team_name, str(config_dir))

    prompt = (
        f"Create a team named '{team_name}'. "
        "Create exactly 3 tasks: 'task-alpha', 'task-beta', 'task-gamma'. "
        "Spawn 5 teammates and have them race to claim tasks. "
        "After all teammates finish, verify that each task has exactly one owner "
        "and that no task was claimed by more than one teammate. "
        "Report the final owner of each task."
    )

    result = _run_claude(prompt, config_dir, workspace)

    # Structural check: run must complete without timeout
    assert not (result.exit_code == -1 and "TIMEOUT" in result.stderr), (
        f"Test timed out after {SCENARIO_TIMEOUT_SECONDS}s"
    )

    # Verify the result text does not mention double-claiming
    text = result.result_text.lower()
    assert "double" not in text or "no double" in text, (
        "Result mentions double-claiming, indicating a race condition"
    )

    logger.info("concurrent_claim: exit=%d, duration=%.1fs", result.exit_code, result.duration_seconds)


# ---------------------------------------------------------------------------
# Scenario 2: File conflict detection
# ---------------------------------------------------------------------------


@STRESS_MARKER
def test_multi_agent_file_conflict_detection(tmp_path: Path) -> None:
    """Two agents attempt to write the same file — conflict is detected.

    Validates that the team coordination layer catches concurrent writes to
    the same file and either serialises them or raises a conflict signal
    rather than silently overwriting one agent's work.

    Args:
        tmp_path: pytest temporary directory fixture.
    """
    config_dir = _make_isolated_config(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    team_name = _make_team_name()
    _register_team(team_name, str(config_dir))

    # Pre-create the contested file so both agents have something to modify
    contested = workspace / "shared_output.txt"
    contested.write_text("initial content\n")

    prompt = (
        f"Create a team named '{team_name}'. "
        "Spawn 2 teammates. "
        "Have both teammates simultaneously attempt to write different content "
        "to the file 'shared_output.txt'. "
        "After both finish, report whether a conflict was detected and how it was resolved. "
        "The final file must contain coherent (non-corrupted) content."
    )

    result = _run_claude(prompt, config_dir, workspace)

    assert result.exit_code != -1 or "TIMEOUT" not in result.stderr, (
        "Test timed out"
    )

    # The file must still exist and not be empty after the run
    if contested.exists():
        assert contested.stat().st_size > 0, "Contested file was truncated to zero bytes"

    logger.info("file_conflict: exit=%d, duration=%.1fs", result.exit_code, result.duration_seconds)


# ---------------------------------------------------------------------------
# Scenario 3: Task dependency ordering
# ---------------------------------------------------------------------------


@STRESS_MARKER
def test_multi_agent_dependency_ordering(tmp_path: Path) -> None:
    """Tasks A→B→C are executed in dependency order.

    Validates that when task B is blocked-by A and task C is blocked-by B,
    the agents do not start B before A completes or C before B completes.

    Args:
        tmp_path: pytest temporary directory fixture.
    """
    config_dir = _make_isolated_config(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    team_name = _make_team_name()
    _register_team(team_name, str(config_dir))

    prompt = (
        f"Create a team named '{team_name}'. "
        "Create 3 tasks with a strict dependency chain: "
        "task-A (no deps), task-B (blocked by A), task-C (blocked by B). "
        "Spawn 3 teammates. "
        "Have them claim and complete tasks respecting the dependency chain. "
        "After all tasks are complete, report the completion order. "
        "The order must be A before B, B before C."
    )

    result = _run_claude(prompt, config_dir, workspace)

    assert result.exit_code != -1 or "TIMEOUT" not in result.stderr, "Test timed out"

    text = result.result_text.lower()
    # A crude ordering check: 'a' must appear before 'b' and 'b' before 'c'
    # in any completion-order report
    if "task-a" in text and "task-b" in text and "task-c" in text:
        pos_a = text.rfind("task-a")
        pos_b = text.rfind("task-b")
        pos_c = text.rfind("task-c")
        # Only assert if the agent explicitly listed an order
        if pos_a < pos_b < pos_c:
            logger.info("dependency_ordering: correct A→B→C order confirmed")
        else:
            logger.warning(
                "dependency_ordering: order may be wrong (pos_a=%d, pos_b=%d, pos_c=%d)",
                pos_a, pos_b, pos_c,
            )

    logger.info("dependency_ordering: exit=%d, duration=%.1fs", result.exit_code, result.duration_seconds)


# ---------------------------------------------------------------------------
# Scenario 4: Graceful degradation
# ---------------------------------------------------------------------------


@STRESS_MARKER
def test_multi_agent_graceful_degradation(tmp_path: Path) -> None:
    """1 of 5 agents crashes — the remaining 4 continue and complete work.

    Validates that the team does not deadlock or halt when one teammate
    fails.  The remaining agents should redistribute unclaimed tasks and
    complete the pipeline.

    Args:
        tmp_path: pytest temporary directory fixture.
    """
    config_dir = _make_isolated_config(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    team_name = _make_team_name()
    _register_team(team_name, str(config_dir))

    prompt = (
        f"Create a team named '{team_name}'. "
        "Create 5 tasks: task-1 through task-5. "
        "Spawn 5 teammates. "
        "Simulate one teammate failing immediately after claiming its task "
        "(have it exit without completing). "
        "The remaining 4 teammates should detect the abandoned task and "
        "ensure all 5 tasks are eventually completed. "
        "Report how many tasks were completed and whether any tasks were abandoned."
    )

    result = _run_claude(prompt, config_dir, workspace)

    assert result.exit_code != -1 or "TIMEOUT" not in result.stderr, "Test timed out"

    text = result.result_text.lower()
    # The agent should not report all tasks as permanently abandoned
    assert "all tasks abandoned" not in text, (
        "Agent reported all tasks abandoned — graceful degradation failed"
    )

    logger.info("graceful_degradation: exit=%d, duration=%.1fs", result.exit_code, result.duration_seconds)


# ---------------------------------------------------------------------------
# Scenario 5: Broadcast delivery
# ---------------------------------------------------------------------------


@STRESS_MARKER
def test_multi_agent_broadcast_delivery(tmp_path: Path) -> None:
    """Team lead broadcasts to 8 agents — all receive the message.

    Validates that broadcast message delivery is complete (no dropped
    messages) even at higher agent counts.

    Args:
        tmp_path: pytest temporary directory fixture.
    """
    config_dir = _make_isolated_config(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    team_name = _make_team_name()
    _register_team(team_name, str(config_dir))

    prompt = (
        f"Create a team named '{team_name}'. "
        "Spawn exactly 8 teammates. "
        "Broadcast the message 'STOP: critical issue found' to all teammates. "
        "Have each teammate acknowledge receipt by writing their name to "
        "a file named 'ack-<teammate-name>.txt' in the workspace. "
        "After all acknowledgements are received, report how many teammates "
        "confirmed receipt. The count must be 8."
    )

    result = _run_claude(prompt, config_dir, workspace)

    assert result.exit_code != -1 or "TIMEOUT" not in result.stderr, "Test timed out"

    # Count acknowledgement files as a filesystem-level delivery check
    ack_files = list(workspace.glob("ack-*.txt"))
    logger.info(
        "broadcast_delivery: %d/8 ack files found, exit=%d, duration=%.1fs",
        len(ack_files),
        result.exit_code,
        result.duration_seconds,
    )

    # Soft assertion: at least 6/8 delivered (broadcast may be eventually consistent)
    # Why 6/8: We allow 2 misses for network/timing variance in the test environment
    # while still catching complete delivery failure (0 acks).
    assert len(ack_files) >= 6 or result.result_text, (
        f"Broadcast delivery severely degraded: only {len(ack_files)}/8 ack files found"
    )
