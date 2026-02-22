"""Unit tests for enforce-readonly.sh (SEC-001).

Tests the PreToolUse hook that blocks Write/Edit/Bash/NotebookEdit for
review/audit Ashes when a .readonly-active marker exists. Verifies guard
clauses, subagent detection, signal directory scanning, and edge cases.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "enforce-readonly.sh"


def run_readonly_hook(
    project: Path,
    config: Path,
    tool_name: str = "Write",
    *,
    transcript_path: str = "/some/path/subagents/agent1/transcript.jsonl",
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run enforce-readonly.sh with configurable tool and transcript path."""
    input_json = {
        "tool_name": tool_name,
        "tool_input": {"file_path": "src/app.py"},
        "transcript_path": transcript_path,
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


def create_review_readonly(project: Path, team_name: str = "rune-review-test123") -> None:
    """Create a review signal dir with .readonly-active marker."""
    signal_dir = project / "tmp" / ".rune-signals" / team_name
    signal_dir.mkdir(parents=True, exist_ok=True)
    (signal_dir / ".readonly-active").write_text("")


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestReadonlyGuardClauses:
    @requires_jq
    def test_exit_0_non_subagent(self, project_env):
        """Team leads (no /subagents/ in transcript) are never blocked."""
        project, config = project_env
        create_review_readonly(project)
        result = run_readonly_hook(
            project, config,
            transcript_path="/path/to/main/transcript.jsonl",
        )
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_exit_0_empty_transcript(self, project_env):
        """Missing transcript_path → not a subagent → allow."""
        project, config = project_env
        create_review_readonly(project)
        input_json = {
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py"},
            "cwd": str(project),
        }
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
    def test_exit_0_no_signal_dir(self, project_env):
        """No .rune-signals/ directory → no enforcement."""
        project, config = project_env
        result = run_readonly_hook(project, config)
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_exit_0_missing_cwd(self, project_env):
        project, config = project_env
        input_json = {
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py"},
            "transcript_path": "/path/subagents/agent/t.jsonl",
        }
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps(input_json),
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert result.returncode == 0
        assert "deny" not in result.stdout


# ---------------------------------------------------------------------------
# Readonly Enforcement
# ---------------------------------------------------------------------------


class TestReadonlyEnforcement:
    @requires_jq
    def test_denies_write_for_subagent_during_review(self, project_env):
        project, config = project_env
        create_review_readonly(project)
        result = run_readonly_hook(project, config, "Write")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "SEC-001" in output["hookSpecificOutput"]["permissionDecisionReason"]

    @requires_jq
    def test_denies_edit_for_subagent_during_review(self, project_env):
        project, config = project_env
        create_review_readonly(project)
        result = run_readonly_hook(project, config, "Edit")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_bash_for_subagent_during_review(self, project_env):
        project, config = project_env
        create_review_readonly(project)
        result = run_readonly_hook(project, config, "Bash")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_notebook_edit_for_subagent_during_review(self, project_env):
        project, config = project_env
        create_review_readonly(project)
        result = run_readonly_hook(project, config, "NotebookEdit")
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    # NOTE: Read/Grep/Glob are never blocked because the hooks.json matcher
    # only triggers enforce-readonly.sh for Write|Edit|Bash|NotebookEdit.
    # The script itself does NOT filter by tool_name — it relies on the matcher.


# ---------------------------------------------------------------------------
# Signal Directory Types
# ---------------------------------------------------------------------------


class TestReadonlySignalTypes:
    @requires_jq
    def test_detects_rune_review_team(self, project_env):
        project, config = project_env
        create_review_readonly(project, "rune-review-abc123")
        result = run_readonly_hook(project, config)
        assert "deny" in result.stdout

    @requires_jq
    def test_detects_arc_review_team(self, project_env):
        project, config = project_env
        create_review_readonly(project, "arc-review-abc123")
        result = run_readonly_hook(project, config)
        assert "deny" in result.stdout

    @requires_jq
    def test_detects_rune_audit_team(self, project_env):
        project, config = project_env
        create_review_readonly(project, "rune-audit-abc123")
        result = run_readonly_hook(project, config)
        assert "deny" in result.stdout

    @requires_jq
    def test_detects_arc_audit_team(self, project_env):
        project, config = project_env
        create_review_readonly(project, "arc-audit-abc123")
        result = run_readonly_hook(project, config)
        assert "deny" in result.stdout

    @requires_jq
    def test_detects_rune_inspect_team(self, project_env):
        project, config = project_env
        create_review_readonly(project, "rune-inspect-abc123")
        result = run_readonly_hook(project, config)
        assert "deny" in result.stdout

    @requires_jq
    def test_ignores_work_team(self, project_env):
        """Work teams don't have .readonly-active markers."""
        project, config = project_env
        signal_dir = project / "tmp" / ".rune-signals" / "rune-work-abc123"
        signal_dir.mkdir(parents=True, exist_ok=True)
        (signal_dir / ".readonly-active").write_text("")
        result = run_readonly_hook(project, config)
        # rune-work-* doesn't match the directory name pattern
        assert "deny" not in result.stdout


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestReadonlyEdgeCases:
    @requires_jq
    def test_no_readonly_marker_allows(self, project_env):
        """Signal dir exists but no .readonly-active → allow."""
        project, config = project_env
        signal_dir = project / "tmp" / ".rune-signals" / "rune-review-test"
        signal_dir.mkdir(parents=True, exist_ok=True)
        # Don't create .readonly-active
        result = run_readonly_hook(project, config)
        assert result.returncode == 0
        assert "deny" not in result.stdout

    @requires_jq
    def test_invalid_team_name_skipped(self, project_env):
        """Signal dirs with invalid characters in name are skipped."""
        project, config = project_env
        # Name with path traversal — should be skipped by regex check
        signal_dir = project / "tmp" / ".rune-signals" / "rune-review-../../etc"
        signal_dir.mkdir(parents=True, exist_ok=True)
        (signal_dir / ".readonly-active").write_text("")
        result = run_readonly_hook(project, config)
        assert result.returncode == 0
        assert "deny" not in result.stdout
