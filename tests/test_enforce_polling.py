"""Unit tests for enforce-polling.sh (POLL-001).

Tests the PreToolUse:Bash hook that blocks sleep+echo monitoring anti-patterns
during active Rune workflows. Verifies guard clauses, pattern detection,
threshold behavior, workflow detection, and session isolation.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "enforce-polling.sh"


def run_polling_hook(
    project: Path,
    config: Path,
    command: str,
    *,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run enforce-polling.sh with a Bash tool invocation."""
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(project),
    }
    env = os.environ.copy()
    # resolve() needed: macOS /var/folders → /private/var/folders symlink.
    # The script uses pwd -P which resolves symlinks; paths must match.
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


def create_active_review(project: Path, config: Path) -> None:
    """Create an active review state file owned by this session."""
    state = {
        "team_name": "rune-review-test",
        "status": "active",
        # resolve() to match pwd -P symlink resolution in hook scripts
        "config_dir": str(config.resolve()),
        "owner_pid": str(os.getpid()),
    }
    (project / "tmp" / ".rune-review-test123.json").write_text(json.dumps(state))


def create_arc_checkpoint(project: Path, config: Path) -> None:
    """Create an arc checkpoint with an in_progress phase."""
    arc_dir = project / ".claude" / "arc" / "arc-test"
    arc_dir.mkdir(parents=True, exist_ok=True)
    # NOTE: Nested "phases" format — matches arc checkpoint schema. test_enforce_teams.py uses flat "phase" for enforce-teams hook.
    checkpoint = {
        "id": "arc-test",
        # resolve() to match pwd -P symlink resolution in hook scripts
        "config_dir": str(config.resolve()),
        "owner_pid": str(os.getpid()),
        "phases": {"work": {"status": "in_progress"}},
    }
    (arc_dir / "checkpoint.json").write_text(json.dumps(checkpoint))


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestPollingGuardClauses:
    @requires_jq
    def test_exit_0_non_bash_tool(self, project_env):
        project, config = project_env
        input_json = {"tool_name": "Read", "tool_input": {"file_path": "foo.py"}, "cwd": str(project)}
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps(input_json),
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_exit_0_no_sleep_in_command(self, project_env):
        project, config = project_env
        result = run_polling_hook(project, config, "ls -la")
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_exit_0_missing_cwd(self, project_env):
        _project, config = project_env
        input_json = {"tool_name": "Bash", "tool_input": {"command": "sleep 30 && echo poll"}}
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps(input_json),
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_exit_0_empty_command(self, project_env):
        project, config = project_env
        result = run_polling_hook(project, config, "")
        assert result.returncode == 0
        assert "deny" not in result.stdout


# ---------------------------------------------------------------------------
# Pattern Detection
# ---------------------------------------------------------------------------


class TestPollingPatternDetection:
    @requires_jq
    def test_denies_sleep_and_echo(self, project_env):
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 30 && echo poll check")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_sleep_semicolon_echo(self, project_env):
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 30; echo check")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_sleep_and_printf(self, project_env):
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 30 && printf 'done'")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_allows_sleep_or_echo(self, project_env):
        """sleep N || echo is error fallback, not polling anti-pattern."""
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 30 || echo error")
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_allows_bare_sleep(self, project_env):
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 30")
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_allows_echo_about_sleep(self, project_env):
        """Commands starting with echo that mention the pattern are not blocked."""
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, 'echo "sleep 30 && echo poll"')
        assert result.returncode == 0
        assert "deny" not in result.stdout


# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------


class TestPollingThreshold:
    @requires_jq
    def test_allows_sleep_under_10(self, project_env):
        """Startup probes use sleep 1-5, should not be blocked."""
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 5 && echo ready")
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_allows_sleep_9(self, project_env):
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 9 && echo ready")
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_denies_sleep_10(self, project_env):
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 10 && echo poll")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------------------------
# Workflow Detection
# ---------------------------------------------------------------------------


class TestPollingWorkflowDetection:
    @requires_jq
    def test_allows_when_no_active_workflow(self, project_env):
        """No state files → no active workflow → allow."""
        project, config = project_env
        result = run_polling_hook(project, config, "sleep 30 && echo poll")
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_denies_with_active_review(self, project_env):
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 30 && echo poll")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_with_active_arc(self, project_env):
        project, config = project_env
        create_arc_checkpoint(project, config)
        result = run_polling_hook(project, config, "sleep 30 && echo poll")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------------------------
# Session Isolation
# ---------------------------------------------------------------------------


class TestPollingSessionIsolation:
    @requires_jq
    @pytest.mark.session_isolation
    def test_skips_other_config_dir_state_files(self, project_env):
        """State files with different config_dir are from another installation."""
        project, config = project_env
        state = {
            "team_name": "rune-review-other",
            "status": "active",
            "config_dir": "/different/config/dir",
            "owner_pid": str(os.getpid()),
        }
        (project / "tmp" / ".rune-review-other.json").write_text(json.dumps(state))
        result = run_polling_hook(project, config, "sleep 30 && echo poll")
        assert result.returncode == 0
        assert "deny" not in result.stdout


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestPollingEdgeCases:
    @requires_jq
    def test_edge_multiline_sleep_echo(self, project_env):
        """Newline-separated sleep/echo is detected via normalization."""
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "sleep 30\necho poll")
        # Script normalizes newlines to spaces, then checks for && or ;
        # Newline alone (no &&/;) should NOT be detected as anti-pattern
        assert result.returncode == 0

    @requires_jq
    def test_edge_word_boundary_nosleep(self, project_env):
        """Variable names containing 'sleep' should not match."""
        project, config = project_env
        create_active_review(project, config)
        result = run_polling_hook(project, config, "nosleep30=true && echo done")
        assert result.returncode == 0
        assert "deny" not in result.stdout
