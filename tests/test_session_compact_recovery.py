"""Unit tests for session-compact-recovery.sh (SessionStart:compact).

Tests the hook that re-injects team state after context compaction.
Verifies guard clauses, checkpoint reading, team correlation,
context message output, and one-time checkpoint deletion.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "session-compact-recovery.sh"


def run_compact_recovery(
    project: Path,
    config: Path,
    *,
    trigger: str = "compact",
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run session-compact-recovery.sh with a SessionStart:compact event."""
    input_json = {"trigger": trigger, "cwd": str(project)}
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


def create_checkpoint(
    project: Path,
    config: Path,  # noqa: ARG001 — kept for API consistency with other helpers
    team_name: str = "rune-review-test123",
    *,
    tasks: list[dict] | None = None,
    workflow_state: dict | None = None,
    team_config: dict | None = None,
    arc_checkpoint: dict | None = None,
) -> Path:
    """Create a compact recovery checkpoint file."""
    checkpoint = {
        "team_name": team_name,
        "saved_at": "2026-02-22T12:00:00Z",
        "tasks": tasks or [
            {"id": "1", "subject": "Review auth", "status": "completed"},
            {"id": "2", "subject": "Review api", "status": "in_progress"},
        ],
        "workflow_state": workflow_state or {
            "workflow": "review",
            "status": "active",
        },
        "team_config": team_config or {
            "members": [
                {"name": "ward-sentinel", "agentId": "a1"},
                {"name": "flaw-hunter", "agentId": "a2"},
            ]
        },
    }
    if arc_checkpoint:
        checkpoint["arc_checkpoint"] = arc_checkpoint
    path = project / "tmp" / ".rune-compact-checkpoint.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint))
    return path


def create_team_dir(config: Path, team_name: str = "rune-review-test123") -> Path:
    """Create a team directory to pass the correlation guard."""
    team_dir = config / "teams" / team_name
    team_dir.mkdir(parents=True, exist_ok=True)
    (team_dir / "config.json").write_text("{}")
    return team_dir


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestCompactRecoveryGuardClauses:
    @requires_jq
    def test_exit_0_non_compact_trigger(self, project_env):
        """Trigger != 'compact' -> exit 0 silently."""
        project, config = project_env
        create_checkpoint(project, config)
        create_team_dir(config)
        result = run_compact_recovery(project, config, trigger="startup")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_empty_trigger(self, project_env):
        """Missing trigger -> exit 0 silently."""
        project, config = project_env
        create_checkpoint(project, config)
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps({"cwd": str(project)}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_missing_cwd(self, project_env):
        _project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps({"trigger": "compact"}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_no_checkpoint_file(self, project_env):
        """No checkpoint file -> exit 0 silently."""
        project, config = project_env
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_invalid_checkpoint_json(self, project_env):
        """Corrupted checkpoint -> exit 0, checkpoint deleted."""
        project, config = project_env
        cp_path = project / "tmp" / ".rune-compact-checkpoint.json"
        cp_path.parent.mkdir(parents=True, exist_ok=True)
        cp_path.write_text("not valid json {{{")
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        # Corrupted checkpoint should be deleted
        assert not cp_path.exists()

    @requires_jq
    def test_exit_0_empty_team_name(self, project_env):
        """Checkpoint with empty team_name -> exit 0."""
        project, config = project_env
        cp_path = project / "tmp" / ".rune-compact-checkpoint.json"
        cp_path.parent.mkdir(parents=True, exist_ok=True)
        cp_path.write_text(json.dumps({"saved_at": "now"}))
        result = run_compact_recovery(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_non_rune_team(self, project_env):
        """Checkpoint for non-rune team -> exit 0, checkpoint deleted."""
        project, config = project_env
        cp_path = create_checkpoint(project, config, team_name="custom-team")
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        assert not cp_path.exists()

    @requires_jq
    def test_exit_0_invalid_team_name_chars(self, project_env):
        """Checkpoint with invalid team name chars -> exit 0."""
        project, config = project_env
        cp_path = project / "tmp" / ".rune-compact-checkpoint.json"
        cp_path.parent.mkdir(parents=True, exist_ok=True)
        cp_path.write_text(json.dumps({"team_name": "rune-$(whoami)"}))
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        assert not cp_path.exists()

    @requires_jq
    def test_exit_0_symlinked_checkpoint(self, project_env):
        """Symlinked checkpoint file -> skip."""
        project, config = project_env
        real = project / "tmp" / "real-checkpoint.json"
        real.parent.mkdir(parents=True, exist_ok=True)
        real.write_text(json.dumps({"team_name": "rune-review-test"}))
        link = project / "tmp" / ".rune-compact-checkpoint.json"
        link.symlink_to(real)
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Team Correlation Guard
# ---------------------------------------------------------------------------


class TestCompactRecoveryCorrelation:
    @requires_jq
    def test_discards_when_team_dir_missing(self, project_env):
        """Team no longer exists -> output discard message, delete checkpoint."""
        project, config = project_env
        cp_path = create_checkpoint(project, config)
        # Don't create team dir
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "no longer exists" in ctx
        assert not cp_path.exists()

    @requires_jq
    def test_discards_when_team_dir_is_symlink(self, project_env):
        """Team dir is a symlink -> treated as nonexistent."""
        project, config = project_env
        create_checkpoint(project, config)
        real_dir = project / "tmp" / "fake-team"
        real_dir.mkdir(parents=True, exist_ok=True)
        team_dir = config / "teams" / "rune-review-test123"
        team_dir.parent.mkdir(parents=True, exist_ok=True)
        team_dir.symlink_to(real_dir)
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "no longer exists" in ctx

    @requires_jq
    def test_recovers_when_team_exists(self, project_env):
        """Team still exists -> output recovery context, delete checkpoint."""
        project, config = project_env
        cp_path = create_checkpoint(project, config)
        create_team_dir(config)
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "RUNE COMPACT RECOVERY" in ctx
        assert "rune-review-test123" in ctx
        # Checkpoint should be deleted (one-time recovery)
        assert not cp_path.exists()


# ---------------------------------------------------------------------------
# Context Message Content
# ---------------------------------------------------------------------------


class TestCompactRecoveryContext:
    @requires_jq
    def test_includes_team_name(self, project_env):
        project, config = project_env
        create_checkpoint(project, config)
        create_team_dir(config)
        result = run_compact_recovery(project, config)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "rune-review-test123" in ctx

    @requires_jq
    def test_includes_member_count(self, project_env):
        project, config = project_env
        create_checkpoint(project, config)
        create_team_dir(config)
        result = run_compact_recovery(project, config)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Members: 2" in ctx

    @requires_jq
    def test_includes_task_summary(self, project_env):
        project, config = project_env
        create_checkpoint(project, config)
        create_team_dir(config)
        result = run_compact_recovery(project, config)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Tasks:" in ctx
        assert "completed" in ctx.lower()

    @requires_jq
    def test_includes_workflow_info(self, project_env):
        project, config = project_env
        create_checkpoint(project, config)
        create_team_dir(config)
        result = run_compact_recovery(project, config)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "review" in ctx.lower()

    @requires_jq
    def test_includes_arc_phase_when_present(self, project_env):
        project, config = project_env
        create_checkpoint(
            project,
            config,
            arc_checkpoint={"current_phase": "code_review"},
        )
        create_team_dir(config)
        result = run_compact_recovery(project, config)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "code_review" in ctx

    @requires_jq
    def test_includes_saved_at(self, project_env):
        project, config = project_env
        create_checkpoint(project, config)
        create_team_dir(config)
        result = run_compact_recovery(project, config)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "2026-02-22" in ctx


# ---------------------------------------------------------------------------
# One-Time Recovery
# ---------------------------------------------------------------------------


class TestCompactRecoveryOneTime:
    @requires_jq
    def test_deletes_checkpoint_after_recovery(self, project_env):
        """Checkpoint is deleted after successful recovery."""
        project, config = project_env
        cp_path = create_checkpoint(project, config)
        create_team_dir(config)
        run_compact_recovery(project, config)
        assert not cp_path.exists()

    @requires_jq
    def test_second_run_produces_no_output(self, project_env):
        """Second run after checkpoint deleted -> no output."""
        project, config = project_env
        create_checkpoint(project, config)
        create_team_dir(config)
        run_compact_recovery(project, config)
        # Second run
        result = run_compact_recovery(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""
