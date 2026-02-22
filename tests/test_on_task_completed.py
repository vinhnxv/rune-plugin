"""Unit tests for on-task-completed.sh (TaskCompleted hook).

Tests the signal file writer that enables event-driven task completion detection.
Verifies guard clauses, signal file creation, all-done sentinel, and edge cases.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "on-task-completed.sh"


def run_task_completed(
    project: Path,
    config: Path,
    *,
    team_name: str = "rune-review-test123",
    task_id: str = "task-1",
    teammate_name: str = "ward-sentinel",
    task_subject: str = "Review auth module",
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run on-task-completed.sh with a TaskCompleted event."""
    input_json = {
        "team_name": team_name,
        "task_id": task_id,
        "teammate_name": teammate_name,
        "task_subject": task_subject,
        "cwd": str(project),
    }
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        input=json.dumps(input_json),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
        cwd=str(project),
    )


def setup_signal_dir(
    project: Path, team_name: str = "rune-review-test123", expected: int = 0
) -> Path:
    """Create signal directory with optional .expected file."""
    signal_dir = project / "tmp" / ".rune-signals" / team_name
    signal_dir.mkdir(parents=True, exist_ok=True)
    if expected > 0:
        (signal_dir / ".expected").write_text(str(expected))
    return signal_dir


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestTaskCompletedGuardClauses:
    @requires_jq
    def test_exit_0_empty_team_name(self, project_env):
        project, config = project_env
        result = run_task_completed(project, config, team_name="")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_empty_task_id(self, project_env):
        project, config = project_env
        result = run_task_completed(project, config, task_id="")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_non_rune_team(self, project_env):
        project, config = project_env
        setup_signal_dir(project, "custom-team")
        result = run_task_completed(project, config, team_name="custom-team")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_invalid_team_name_chars(self, project_env):
        project, config = project_env
        result = run_task_completed(project, config, team_name="rune-$(whoami)")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_team_name_too_long(self, project_env):
        project, config = project_env
        long_name = "rune-" + "a" * 200
        result = run_task_completed(project, config, team_name=long_name)
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_invalid_task_id_chars(self, project_env):
        project, config = project_env
        result = run_task_completed(project, config, task_id="task;rm -rf /")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_missing_cwd(self, project_env):
        _project, config = project_env
        input_json = {
            "team_name": "rune-review-test",
            "task_id": "task-1",
            "teammate_name": "ward",
        }
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps(input_json),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_no_signal_dir(self, project_env):
        """No signal dir → orchestrator didn't set up signals → exit 0."""
        project, config = project_env
        result = run_task_completed(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_invalid_json_input(self, project_env):
        _project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input="not valid json",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Signal File Creation
# ---------------------------------------------------------------------------


class TestTaskCompletedSignalFiles:
    @requires_jq
    def test_creates_signal_file(self, project_env):
        """Signal file created when signal dir exists."""
        project, config = project_env
        setup_signal_dir(project)
        run_task_completed(project, config, task_id="task-42")
        signal_file = (
            project / "tmp" / ".rune-signals" / "rune-review-test123" / "task-42.done"
        )
        assert signal_file.exists()

    @requires_jq
    def test_signal_file_contains_valid_json(self, project_env):
        project, config = project_env
        setup_signal_dir(project)
        run_task_completed(project, config, task_id="task-1", teammate_name="ward")
        signal_file = (
            project / "tmp" / ".rune-signals" / "rune-review-test123" / "task-1.done"
        )
        data = json.loads(signal_file.read_text())
        assert data["task_id"] == "task-1"
        assert data["teammate"] == "ward"
        assert "completed_at" in data

    @requires_jq
    def test_signal_file_contains_subject(self, project_env):
        project, config = project_env
        setup_signal_dir(project)
        run_task_completed(
            project, config, task_id="task-1", task_subject="Review auth"
        )
        signal_file = (
            project / "tmp" / ".rune-signals" / "rune-review-test123" / "task-1.done"
        )
        data = json.loads(signal_file.read_text())
        assert data["subject"] == "Review auth"

    @requires_jq
    def test_works_with_arc_team_prefix(self, project_env):
        project, config = project_env
        setup_signal_dir(project, "arc-review-abc")
        run_task_completed(
            project, config, team_name="arc-review-abc", task_id="task-1"
        )
        signal = (
            project / "tmp" / ".rune-signals" / "arc-review-abc" / "task-1.done"
        )
        assert signal.exists()


# ---------------------------------------------------------------------------
# All-Done Sentinel
# ---------------------------------------------------------------------------


class TestTaskCompletedAllDone:
    @requires_jq
    def test_creates_all_done_when_expected_met(self, project_env):
        """When done_count >= expected, .all-done sentinel is created."""
        project, config = project_env
        signal_dir = setup_signal_dir(project, expected=2)
        # Pre-create one signal file
        (signal_dir / "task-1.done").write_text('{"task_id":"task-1"}')
        # Complete second task
        run_task_completed(project, config, task_id="task-2")
        assert (signal_dir / ".all-done").exists()

    @requires_jq
    def test_all_done_contains_valid_json(self, project_env):
        project, config = project_env
        signal_dir = setup_signal_dir(project, expected=1)
        run_task_completed(project, config, task_id="task-1")
        data = json.loads((signal_dir / ".all-done").read_text())
        assert data["total"] >= 1
        assert data["expected"] == 1
        assert "completed_at" in data

    @requires_jq
    def test_no_all_done_when_under_expected(self, project_env):
        project, config = project_env
        signal_dir = setup_signal_dir(project, expected=3)
        run_task_completed(project, config, task_id="task-1")
        assert not (signal_dir / ".all-done").exists()

    @requires_jq
    def test_no_all_done_without_expected_file(self, project_env):
        project, config = project_env
        setup_signal_dir(project, expected=0)  # No .expected file
        run_task_completed(project, config, task_id="task-1")
        signal_dir = project / "tmp" / ".rune-signals" / "rune-review-test123"
        assert not (signal_dir / ".all-done").exists()

    @requires_jq
    def test_invalid_expected_file_skipped(self, project_env):
        """Non-numeric .expected → skip all-done check."""
        project, config = project_env
        signal_dir = setup_signal_dir(project)
        (signal_dir / ".expected").write_text("abc")
        run_task_completed(project, config, task_id="task-1")
        assert not (signal_dir / ".all-done").exists()


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestTaskCompletedEdgeCases:
    @requires_jq
    def test_truncates_long_subject(self, project_env):
        """Subject longer than 256 chars is truncated."""
        project, config = project_env
        setup_signal_dir(project)
        long_subject = "A" * 500
        run_task_completed(
            project, config, task_id="task-1", task_subject=long_subject
        )
        signal_file = (
            project / "tmp" / ".rune-signals" / "rune-review-test123" / "task-1.done"
        )
        data = json.loads(signal_file.read_text())
        assert len(data["subject"]) <= 256
