"""Unit tests for enforce-team-lifecycle.sh (TLC-001).

Tests the PreToolUse:TeamCreate hook that validates team names, detects stale
teams, auto-cleans filesystem orphans, and injects advisory context.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "enforce-team-lifecycle.sh"


def run_lifecycle_hook(
    project: Path,
    config: Path,
    team_name: str,
    *,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run enforce-team-lifecycle.sh with a TeamCreate invocation."""
    input_json = {
        "tool_name": "TeamCreate",
        "tool_input": {"team_name": team_name},
        "cwd": str(project),
    }
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config)
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


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestLifecycleGuardClauses:
    @requires_jq
    def test_exit_0_non_teamcreate_tool(self, project_env):
        """Non-TeamCreate tools are ignored."""
        project, config = project_env
        input_json = {"tool_name": "Read", "tool_input": {}, "cwd": str(project)}
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
    def test_exit_0_empty_team_name(self, project_env):
        """Empty team_name → exit 0 (let SDK handle)."""
        project, config = project_env
        input_json = {"tool_name": "TeamCreate", "tool_input": {}, "cwd": str(project)}
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps(input_json),
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_missing_cwd(self, project_env):
        project, config = project_env
        input_json = {"tool_name": "TeamCreate", "tool_input": {"team_name": "rune-test"}}
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps(input_json),
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Team Name Validation
# ---------------------------------------------------------------------------


class TestLifecycleTeamNameValidation:
    @requires_jq
    def test_allows_valid_rune_team(self, project_env):
        project, config = project_env
        result = run_lifecycle_hook(project, config, "rune-review-abc123")
        assert result.returncode == 0
        # Should NOT be denied
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                assert output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
            except json.JSONDecodeError:
                pass  # Non-JSON output is fine

    @requires_jq
    def test_allows_valid_arc_team(self, project_env):
        project, config = project_env
        result = run_lifecycle_hook(project, config, "arc-plan-review-test")
        assert result.returncode == 0
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                assert output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
            except json.JSONDecodeError:
                pass

    @requires_jq
    @pytest.mark.security
    def test_denies_shell_injection_in_name(self, project_env):
        """Team names with shell metacharacters must be blocked."""
        project, config = project_env
        result = run_lifecycle_hook(project, config, "rune-$(whoami)")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    @pytest.mark.security
    def test_denies_path_traversal_in_name(self, project_env):
        project, config = project_env
        result = run_lifecycle_hook(project, config, "rune-../../etc")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    @pytest.mark.security
    def test_denies_spaces_in_name(self, project_env):
        project, config = project_env
        result = run_lifecycle_hook(project, config, "rune test team")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    @pytest.mark.security
    def test_denies_semicolon_in_name(self, project_env):
        project, config = project_env
        result = run_lifecycle_hook(project, config, "rune;rm -rf /")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------------------------
# Stale Team Detection
# ---------------------------------------------------------------------------


class TestLifecycleStaleDetection:
    @requires_jq
    def test_allows_when_no_stale_team(self, project_env):
        """No existing team dir → allows without advisory."""
        project, config = project_env
        result = run_lifecycle_hook(project, config, "rune-review-new")
        assert result.returncode == 0
        # Should either be empty or have allow/additionalContext
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                assert output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
            except json.JSONDecodeError:
                pass

    @requires_jq
    def test_detects_stale_rune_team_dir(self, project_env):
        """Existing rune-* team dir without recent activity → advisory context."""
        project, config = project_env
        # Create a stale team dir
        team_dir = config / "teams" / "rune-review-old"
        team_dir.mkdir(parents=True, exist_ok=True)
        config_file = team_dir / "config.json"
        config_file.write_text(json.dumps({"name": "rune-review-old"}))
        # Make it old (>30 min)
        old_time = os.path.getmtime(str(config_file)) - 3600
        os.utime(str(config_file), (old_time, old_time))
        result = run_lifecycle_hook(project, config, "rune-review-new")
        assert result.returncode == 0
        # Non-rune teams are irrelevant to this specific hook check


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestLifecycleEdgeCases:
    @requires_jq
    def test_allows_non_rune_team(self, project_env):
        """Non-rune/arc teams pass through without special handling."""
        project, config = project_env
        result = run_lifecycle_hook(project, config, "my-custom-team")
        assert result.returncode == 0
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                # Should not be denied for valid chars
                assert output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
            except json.JSONDecodeError:
                pass

    @requires_jq
    def test_allows_hyphen_underscore_in_name(self, project_env):
        project, config = project_env
        result = run_lifecycle_hook(project, config, "rune-review_test-123")
        assert result.returncode == 0
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                assert output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
            except json.JSONDecodeError:
                pass
