"""Unit tests for verify-team-cleanup.sh (TLC-002).

Tests the PostToolUse:TeamDelete verification hook that checks for
remaining rune-*/arc-* team dirs after a TeamDelete call. Verifies
guard clauses, reporting behavior, symlink safety, and edge cases.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "verify-team-cleanup.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_cleanup_verify(
    config: Path,
    *,
    tool_name: str = "TeamDelete",
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run verify-team-cleanup.sh with configurable input."""
    input_json = {"tool_name": tool_name}
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        input=json.dumps(input_json),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestCleanupVerifyGuardClauses:
    @requires_jq
    def test_exit_0_non_teamdelete_tool(self, project_env):
        """Non-TeamDelete tool -> exit 0 with no output."""
        _project, config = project_env
        result = run_cleanup_verify(config, tool_name="Read")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_task_tool(self, project_env):
        """Task tool name is ignored."""
        _project, config = project_env
        result = run_cleanup_verify(config, tool_name="Task")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_write_tool(self, project_env):
        """Write tool name is ignored."""
        _project, config = project_env
        result = run_cleanup_verify(config, tool_name="Write")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_empty_tool_name(self, project_env):
        """Empty tool name -> exit 0."""
        _project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps({"tool_name": ""}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_missing_tool_name(self, project_env):
        """No tool_name field -> exit 0."""
        _project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps({}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Clean State (no remaining dirs)
# ---------------------------------------------------------------------------


class TestCleanupVerifyCleanState:
    @requires_jq
    def test_no_output_when_teams_dir_empty(self, project_env):
        """Empty teams/ directory -> no output."""
        _project, config = project_env
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_no_output_when_teams_dir_missing(self, project_env):
        """No teams/ directory -> no output."""
        _project, config = project_env
        import shutil
        shutil.rmtree(config / "teams")
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_no_output_with_only_non_rune_teams(self, project_env):
        """Only non-rune team dirs -> no report."""
        _project, config = project_env
        (config / "teams" / "my-custom-team").mkdir(parents=True)
        (config / "teams" / "another-team").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Remaining Dir Reporting
# ---------------------------------------------------------------------------


class TestCleanupVerifyReporting:
    @requires_jq
    def test_reports_remaining_rune_dirs(self, project_env):
        """Remaining rune-* dirs -> reported."""
        _project, config = project_env
        (config / "teams" / "rune-review-zombie").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "TLC-002" in result.stdout
        assert "rune-review-zombie" in result.stdout

    @requires_jq
    def test_reports_remaining_arc_dirs(self, project_env):
        """Remaining arc-* dirs -> reported."""
        _project, config = project_env
        (config / "teams" / "arc-plan-review-zombie").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "TLC-002" in result.stdout
        assert "arc-plan-review-zombie" in result.stdout

    @requires_jq
    def test_reports_multiple_remaining_dirs(self, project_env):
        """Multiple remaining dirs -> all counted."""
        _project, config = project_env
        (config / "teams" / "rune-review-z1").mkdir(parents=True)
        (config / "teams" / "rune-audit-z2").mkdir(parents=True)
        (config / "teams" / "arc-work-z3").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "TLC-002" in result.stdout
        assert "3 rune/arc team dir(s)" in result.stdout

    @requires_jq
    def test_does_not_report_non_rune_dirs(self, project_env):
        """Non-rune/arc dirs are not included in the report."""
        _project, config = project_env
        (config / "teams" / "rune-review-z1").mkdir(parents=True)
        (config / "teams" / "custom-team").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "1 rune/arc team dir(s)" in result.stdout
        assert "custom-team" not in result.stdout

    @requires_jq
    def test_message_mentions_post_delete(self, project_env):
        """Report message contextualizes this as post-delete check."""
        _project, config = project_env
        (config / "teams" / "rune-review-msg").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert "POST-DELETE" in result.stdout

    @requires_jq
    def test_message_suggests_rest_heal(self, project_env):
        """Report suggests /rune:rest --heal for unexpected dirs."""
        _project, config = project_env
        (config / "teams" / "rune-review-heal").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert "/rune:rest --heal" in result.stdout

    @requires_jq
    def test_limits_reported_names_to_five(self, project_env):
        """Report shows at most 5 dir names (to avoid flooding)."""
        _project, config = project_env
        for i in range(7):
            (config / "teams" / f"rune-review-z{i}").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "7 rune/arc team dir(s)" in result.stdout


# ---------------------------------------------------------------------------
# Symlink Safety
# ---------------------------------------------------------------------------


class TestCleanupVerifySymlinks:
    @requires_jq
    def test_skips_symlinked_dirs(self, project_env):
        """Symlinked team dirs are skipped in the report."""
        project, config = project_env
        target = project / "tmp" / "fake-team"
        target.mkdir(parents=True, exist_ok=True)
        link = config / "teams" / "rune-review-link"
        link.symlink_to(target)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "rune-review-link" not in result.stdout

    @requires_jq
    def test_reports_real_dir_alongside_symlink(self, project_env):
        """Real dirs are reported even when symlinks exist."""
        project, config = project_env
        # Real dir
        (config / "teams" / "rune-review-real").mkdir(parents=True)
        # Symlink
        target = project / "tmp" / "fake"
        target.mkdir(parents=True)
        (config / "teams" / "rune-review-link").symlink_to(target)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "rune-review-real" in result.stdout
        assert "rune-review-link" not in result.stdout


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestCleanupVerifyEdgeCases:
    @requires_jq
    def test_exit_0_always(self, project_env):
        """PostToolUse hooks are informational -- always exit 0."""
        _project, config = project_env
        (config / "teams" / "rune-review-edge").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0

    @requires_jq
    def test_handles_invalid_json_input_gracefully(self, project_env):
        """Invalid JSON input -> exit 0 (fail-open)."""
        _project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input="not json {{{",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0

    @requires_jq
    def test_handles_dir_with_special_but_valid_chars(self, project_env):
        """Team dirs with hyphens and underscores are valid."""
        _project, config = project_env
        (config / "teams" / "rune-review_test-123").mkdir(parents=True)
        result = run_cleanup_verify(config)
        assert result.returncode == 0
        assert "rune-review_test-123" in result.stdout
