"""Unit tests for session-team-hygiene.sh (TLC-003).

Tests the SessionStart orphan detection hook that scans for orphaned
rune-*/arc-* team dirs and stale state files at session start. Verifies
guard clauses, orphan detection (30-min threshold), stale state file
counting, session isolation via config_dir/owner_pid, and edge cases.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "session-team-hygiene.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_hygiene_hook(
    project: Path,
    config: Path,
    *,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run session-team-hygiene.sh with configurable environment."""
    input_json = {"cwd": str(project)}
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
        cwd=str(project),
    )


def create_stale_state_file(
    project: Path,
    config: Path,
    *,
    name: str = ".rune-review-stale.json",
    status: str = "active",
    age_minutes: int = 45,
    owner_pid: str | None = None,
) -> Path:
    """Create a stale workflow state file in project/tmp/."""
    state_dir = project / "tmp"
    state_dir.mkdir(exist_ok=True)
    pid = owner_pid or str(os.getpid())
    state = {
        "status": status,
        "team_name": name.replace(".json", "").lstrip("."),
        "config_dir": str(config.resolve()),
        "owner_pid": pid,
        "session_id": "test-session",
    }
    path = state_dir / name
    path.write_text(json.dumps(state))
    if age_minutes > 0:
        old_time = time.time() - (age_minutes * 60)
        os.utime(str(path), (old_time, old_time))
    return path


def create_orphan_team_dir(
    config: Path,
    name: str = "rune-review-orphan",
    age_minutes: int = 45,
) -> Path:
    """Create an orphaned team directory and backdate its mtime."""
    team_dir = config / "teams" / name
    team_dir.mkdir(parents=True, exist_ok=True)
    (team_dir / "config.json").write_text("{}")
    if age_minutes > 0:
        old_time = time.time() - (age_minutes * 60)
        os.utime(str(team_dir), (old_time, old_time))
    return team_dir


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestHygieneGuardClauses:
    @requires_jq
    def test_exit_0_no_cwd(self, project_env):
        """Missing CWD -> exit 0."""
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

    @requires_jq
    def test_exit_0_empty_cwd(self, project_env):
        """Empty CWD string -> exit 0."""
        _project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps({"cwd": ""}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_nonexistent_cwd(self, project_env):
        """Nonexistent CWD -> exit 0."""
        _project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config.resolve())
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input=json.dumps({"cwd": "/nonexistent/path/xyz"}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_no_orphans_no_stale(self, project_env):
        """Clean state -> exit 0 with no output."""
        project, config = project_env
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Orphan Team Dir Detection
# ---------------------------------------------------------------------------


class TestHygieneOrphanDetection:
    @requires_jq
    def test_reports_orphaned_rune_team_dir(self, project_env):
        """Old rune-* team dir -> reported as orphan."""
        project, config = project_env
        create_orphan_team_dir(config, "rune-review-orphan1", age_minutes=45)
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "TLC-003" in result.stdout
        assert "rune-review-orphan1" in result.stdout

    @requires_jq
    def test_reports_orphaned_arc_team_dir(self, project_env):
        """Old arc-* team dir -> reported as orphan."""
        project, config = project_env
        create_orphan_team_dir(config, "arc-plan-review-orphan", age_minutes=45)
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "TLC-003" in result.stdout
        assert "arc-plan-review-orphan" in result.stdout

    @requires_jq
    def test_does_not_report_young_team_dir(self, project_env):
        """Team dir < 30 min old -> NOT reported."""
        project, config = project_env
        create_orphan_team_dir(config, "rune-review-fresh", age_minutes=5)
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_does_not_report_non_rune_team_dir(self, project_env):
        """Non-rune/arc team dir -> NOT reported."""
        project, config = project_env
        team_dir = config / "teams" / "my-custom-team"
        team_dir.mkdir(parents=True, exist_ok=True)
        old_time = time.time() - 3600
        os.utime(str(team_dir), (old_time, old_time))
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "my-custom-team" not in result.stdout

    @requires_jq
    def test_skips_symlinked_team_dir(self, project_env):
        """Symlinked team dirs are skipped."""
        project, config = project_env
        target = project / "tmp" / "fake-orphan"
        target.mkdir(parents=True, exist_ok=True)
        link = config / "teams" / "rune-review-link"
        link.symlink_to(target)
        old_time = time.time() - 3600
        os.utime(str(target), (old_time, old_time))
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "rune-review-link" not in result.stdout

    @requires_jq
    def test_reports_multiple_orphans(self, project_env):
        """Multiple orphaned dirs -> reports count."""
        project, config = project_env
        create_orphan_team_dir(config, "rune-review-o1", age_minutes=45)
        create_orphan_team_dir(config, "rune-audit-o2", age_minutes=60)
        create_orphan_team_dir(config, "arc-work-o3", age_minutes=90)
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "TLC-003" in result.stdout
        assert "3 orphaned team dir(s)" in result.stdout

    @requires_jq
    def test_message_suggests_rest_heal(self, project_env):
        """Report message suggests /rune:rest --heal."""
        project, config = project_env
        create_orphan_team_dir(config, "rune-review-heal-test", age_minutes=45)
        result = run_hygiene_hook(project, config)
        assert "/rune:rest --heal" in result.stdout


# ---------------------------------------------------------------------------
# Stale State File Detection
# ---------------------------------------------------------------------------


class TestHygieneStaleStateFiles:
    @requires_jq
    def test_reports_stale_active_review_state(self, project_env):
        """Active review state file > 30 min -> reported as stale."""
        project, config = project_env
        create_stale_state_file(
            project, config,
            name=".rune-review-stale1.json",
            age_minutes=45,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "TLC-003" in result.stdout
        assert "1 stale state file(s)" in result.stdout

    @requires_jq
    def test_reports_stale_active_audit_state(self, project_env):
        """Active audit state file > 30 min -> reported as stale."""
        project, config = project_env
        create_stale_state_file(
            project, config,
            name=".rune-audit-stale1.json",
            age_minutes=45,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "1 stale state file(s)" in result.stdout

    @requires_jq
    def test_does_not_report_young_state_file(self, project_env):
        """Active state file < 30 min -> NOT reported."""
        project, config = project_env
        create_stale_state_file(
            project, config,
            name=".rune-review-young.json",
            age_minutes=5,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_does_not_report_completed_state_file(self, project_env):
        """Completed state files are not stale (regardless of age)."""
        project, config = project_env
        create_stale_state_file(
            project, config,
            name=".rune-review-done.json",
            status="completed",
            age_minutes=120,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_does_not_report_stopped_state_file(self, project_env):
        """Stopped state files are not stale (regardless of age)."""
        project, config = project_env
        create_stale_state_file(
            project, config,
            name=".rune-review-stopped.json",
            status="stopped",
            age_minutes=120,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_reports_multiple_stale_types(self, project_env):
        """Multiple stale state file types -> all counted."""
        project, config = project_env
        create_stale_state_file(
            project, config, name=".rune-review-s1.json", age_minutes=45,
        )
        create_stale_state_file(
            project, config, name=".rune-work-s2.json", age_minutes=60,
        )
        create_stale_state_file(
            project, config, name=".rune-mend-s3.json", age_minutes=90,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "3 stale state file(s)" in result.stdout


# ---------------------------------------------------------------------------
# Session Isolation
# ---------------------------------------------------------------------------


class TestHygieneSessionIsolation:
    @requires_jq
    @pytest.mark.session_isolation
    def test_skips_state_file_different_config_dir(self, project_env):
        """State files with different config_dir are not counted as stale."""
        project, config = project_env
        sf_path = project / "tmp" / ".rune-review-foreign.json"
        sf_path.parent.mkdir(exist_ok=True)
        sf_path.write_text(json.dumps({
            "status": "active",
            "team_name": "rune-review-foreign",
            "config_dir": "/different/config/dir",
            "owner_pid": str(os.getpid()),
        }))
        old_time = time.time() - 3600
        os.utime(str(sf_path), (old_time, old_time))
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        # Should not count this as stale (different config)
        assert "stale state file" not in result.stdout or "0 stale state file(s)" in result.stdout

    @requires_jq
    @pytest.mark.session_isolation
    def test_counts_state_file_with_matching_config(self, project_env):
        """State files with matching config_dir ARE counted."""
        project, config = project_env
        create_stale_state_file(
            project, config,
            name=".rune-review-own.json",
            age_minutes=45,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "1 stale state file(s)" in result.stdout

    @requires_jq
    @pytest.mark.session_isolation
    def test_skips_state_file_with_live_different_pid(self, project_env):
        """State files owned by a different live PID are skipped.

        We use os.getppid() (the parent process of the test runner) which is
        guaranteed to be alive and kill-checkable by the current user. This
        simulates another live session owning the state file.
        """
        project, config = project_env
        # Use the parent PID (always alive, always kill-checkable by current user).
        # This differs from os.getpid() which is what $PPID resolves to in the
        # subprocess, so the script sees a different-but-alive PID.
        other_pid = str(os.getppid())
        # Guard: ensure this PID is not the same as what the script sees as $PPID
        # (which is os.getpid() from Python's perspective).
        assert other_pid != str(os.getpid()), "Test requires parent PID != current PID"
        sf_path = project / "tmp" / ".rune-review-other-pid.json"
        sf_path.parent.mkdir(exist_ok=True)
        sf_path.write_text(json.dumps({
            "status": "active",
            "team_name": "rune-review-other-pid",
            "config_dir": str(config.resolve()),
            "owner_pid": other_pid,
        }))
        old_time = time.time() - 3600
        os.utime(str(sf_path), (old_time, old_time))
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        # Should skip since the parent PID is alive -> another session
        assert "stale state file" not in result.stdout or "0 stale state file(s)" in result.stdout


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestHygieneEdgeCases:
    @requires_jq
    def test_handles_empty_teams_dir(self, project_env):
        """Empty teams/ directory -> no orphans reported."""
        project, config = project_env
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_handles_missing_teams_dir(self, project_env):
        """No teams/ directory -> no crash."""
        project, config = project_env
        import shutil
        shutil.rmtree(config / "teams")
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_handles_corrupted_state_file(self, project_env):
        """Corrupted (non-JSON) state files don't crash the hook."""
        project, config = project_env
        sf_path = project / "tmp" / ".rune-review-corrupt.json"
        sf_path.parent.mkdir(exist_ok=True)
        sf_path.write_text("not valid json {{{")
        old_time = time.time() - 3600
        os.utime(str(sf_path), (old_time, old_time))
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_orphan_and_stale_combined(self, project_env):
        """Both orphan dirs and stale state files -> single report message."""
        project, config = project_env
        create_orphan_team_dir(config, "rune-review-combo-orphan", age_minutes=45)
        create_stale_state_file(
            project, config,
            name=".rune-review-combo-stale.json",
            age_minutes=60,
        )
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
        assert "TLC-003" in result.stdout
        assert "1 orphaned team dir(s)" in result.stdout
        assert "1 stale state file(s)" in result.stdout

    @requires_jq
    def test_handles_missing_tmp_dir(self, project_env):
        """No tmp/ directory -> stale state scan skips gracefully."""
        project, config = project_env
        import shutil
        shutil.rmtree(project / "tmp")
        result = run_hygiene_hook(project, config)
        assert result.returncode == 0
