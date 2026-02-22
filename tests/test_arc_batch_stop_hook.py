"""Unit tests for arc-batch-stop-hook.sh (ARC-BATCH-LOOP).

Tests the Stop hook that drives batch arc execution via the ralph-wiggum
self-invoking loop pattern. Verifies guard clauses, session isolation,
progress tracking, plan injection, and security checks.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "arc-batch-stop-hook.sh"


def write_state_file(
    project: Path,
    config: Path,
    *,
    active: bool = True,
    iteration: int = 1,
    max_iterations: int = 0,
    total_plans: int = 3,
    no_merge: bool = False,
    owner_pid: str | None = None,
) -> Path:
    """Create a .claude/arc-batch-loop.local.md state file."""
    state_file = project / ".claude" / "arc-batch-loop.local.md"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    # Default to os.getpid() because bash's $PPID = Python test process PID.
    # resolve() needed: macOS /var/folders → /private/var/folders symlink.
    pid = owner_pid or str(os.getpid())
    resolved_config = str(config.resolve())
    content = textwrap.dedent(f"""\
    ---
    active: {"true" if active else "false"}
    iteration: {iteration}
    max_iterations: {max_iterations}
    total_plans: {total_plans}
    no_merge: {"true" if no_merge else "false"}
    plugin_dir: /tmp/test-plugin
    config_dir: {resolved_config}
    owner_pid: {pid}
    session_id: test-session
    plans_file: tmp/arc-batch/batch-progress.json
    progress_file: tmp/arc-batch/batch-progress.json
    started_at: "2026-02-22T00:00:00.000Z"
    ---

    Arc batch loop state. Do not edit manually.
    """)
    state_file.write_text(content)
    return state_file


def write_progress_file(
    project: Path,
    plans: list[dict],
) -> Path:
    """Create a batch-progress.json file."""
    progress_dir = project / "tmp" / "arc-batch"
    progress_dir.mkdir(parents=True, exist_ok=True)
    progress = {
        "schema_version": 1,
        "status": "running",
        "started_at": "2026-02-22T00:00:00.000Z",
        "updated_at": "2026-02-22T00:00:00.000Z",
        "total_plans": len(plans),
        "plans": plans,
    }
    path = progress_dir / "batch-progress.json"
    path.write_text(json.dumps(progress, indent=2))
    return path


def run_batch_hook(
    project: Path,
    config: Path,
    *,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run arc-batch-stop-hook.sh."""
    input_json = {"cwd": str(project)}
    env = os.environ.copy()
    # resolve() needed: macOS /var/folders → /private/var/folders symlink
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


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestArcBatchGuardClauses:
    @requires_jq
    def test_exit_0_no_state_file(self, project_env):
        """No .claude/arc-batch-loop.local.md → exit 0."""
        project, config = project_env
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_missing_cwd(self, project_env):
        project, config = project_env
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            input="{}",
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_inactive_batch(self, project_env):
        """active: false → removes state file, exit 0."""
        project, config = project_env
        write_state_file(project, config, active=False)
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""
        assert not (project / ".claude" / "arc-batch-loop.local.md").exists()

    @requires_jq
    def test_exit_0_invalid_numeric_fields(self, project_env):
        """Non-numeric iteration → state file removed."""
        project, config = project_env
        state_file = project / ".claude" / "arc-batch-loop.local.md"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        resolved_config = str(config.resolve())
        state_file.write_text(textwrap.dedent(f"""\
        ---
        active: true
        iteration: abc
        max_iterations: 0
        total_plans: 3
        no_merge: false
        plugin_dir: /tmp
        config_dir: {resolved_config}
        owner_pid: {os.getpid()}
        session_id: test
        plans_file: tmp/progress.json
        progress_file: tmp/progress.json
        ---
        """))
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not state_file.exists()

    @requires_jq
    def test_exit_0_max_iterations_reached(self, project_env):
        """iteration >= max_iterations → state file removed."""
        project, config = project_env
        write_state_file(project, config, iteration=3, max_iterations=3)
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not (project / ".claude" / "arc-batch-loop.local.md").exists()

    @requires_jq
    def test_exit_0_empty_frontmatter(self, project_env):
        """Corrupted state file with empty frontmatter → cleaned up."""
        project, config = project_env
        state_file = project / ".claude" / "arc-batch-loop.local.md"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("no frontmatter here\n")
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not state_file.exists()

    @requires_jq
    def test_exit_0_symlinked_state_file(self, project_env):
        """Symlinked state file → removed, exit 0."""
        project, config = project_env
        target = project / "tmp" / "fake-state.md"
        target.write_text("---\nactive: true\n---\n")
        link = project / ".claude" / "arc-batch-loop.local.md"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not link.exists()


# ---------------------------------------------------------------------------
# Session Isolation
# ---------------------------------------------------------------------------


class TestArcBatchSessionIsolation:
    @requires_jq
    @pytest.mark.session_isolation
    def test_exit_0_different_config_dir(self, project_env):
        """Different CLAUDE_CONFIG_DIR → skip (another installation's batch)."""
        project, config = project_env
        write_state_file(project, Path("/different/config/dir"))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert result.stdout.strip() == ""
        # State file should NOT be removed (belongs to another session)
        assert (project / ".claude" / "arc-batch-loop.local.md").exists()

    @requires_jq
    @pytest.mark.session_isolation
    def test_processes_own_batch(self, project_env):
        """Same PPID and config_dir → processes normally."""
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "plans/b.md", "status": "pending", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        # Should output block decision for next plan
        output = json.loads(result.stdout)
        assert output["decision"] == "block"
        assert "plans/b.md" in output["reason"]


# ---------------------------------------------------------------------------
# Progress Tracking
# ---------------------------------------------------------------------------


class TestArcBatchProgressTracking:
    @requires_jq
    def test_marks_current_plan_completed(self, project_env):
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        progress_path = write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "plans/b.md", "status": "pending", "error": None, "completed_at": None},
        ])
        run_batch_hook(project, config)
        updated = json.loads(progress_path.read_text())
        plan_a = next(p for p in updated["plans"] if p["path"] == "plans/a.md")
        assert plan_a["status"] == "completed"
        assert plan_a["completed_at"] is not None

    @requires_jq
    def test_all_done_removes_state_file(self, project_env):
        """When no pending plans remain, state file is removed."""
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()), total_plans=1)
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not (project / ".claude" / "arc-batch-loop.local.md").exists()
        # Should output summary prompt
        output = json.loads(result.stdout)
        assert output["decision"] == "block"
        assert "Complete" in output["reason"] or "summary" in output["reason"].lower()

    @requires_jq
    def test_increments_iteration(self, project_env):
        project, config = project_env
        write_state_file(project, config, iteration=2, owner_pid=str(os.getpid()))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "completed", "error": None, "completed_at": "2026-02-22T00:00:00Z"},
            {"path": "plans/b.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "plans/c.md", "status": "pending", "error": None, "completed_at": None},
        ])
        run_batch_hook(project, config)
        state = (project / ".claude" / "arc-batch-loop.local.md").read_text()
        assert "iteration: 3" in state


# ---------------------------------------------------------------------------
# Next Plan Injection
# ---------------------------------------------------------------------------


class TestArcBatchNextPlanInjection:
    @requires_jq
    def test_outputs_block_decision_json(self, project_env):
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "plans/b.md", "status": "pending", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        output = json.loads(result.stdout)
        assert output["decision"] == "block"
        assert "systemMessage" in output

    @requires_jq
    def test_arc_prompt_contains_plan_path(self, project_env):
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "plans/next-plan.md", "status": "pending", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        output = json.loads(result.stdout)
        assert "plans/next-plan.md" in output["reason"]

    @requires_jq
    def test_arc_prompt_includes_truthbinding(self, project_env):
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "plans/b.md", "status": "pending", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        output = json.loads(result.stdout)
        assert "ANCHOR" in output["reason"]
        assert "RE-ANCHOR" in output["reason"]

    @requires_jq
    def test_no_merge_flag_included(self, project_env):
        project, config = project_env
        write_state_file(project, config, no_merge=True, owner_pid=str(os.getpid()))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "plans/b.md", "status": "pending", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        output = json.loads(result.stdout)
        assert "--no-merge" in output["reason"]


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TestArcBatchSecurity:
    @requires_jq
    @pytest.mark.security
    def test_rejects_path_traversal_in_progress_file(self, project_env):
        """Path traversal in progress_file → cleanup and exit."""
        project, config = project_env
        state_file = project / ".claude" / "arc-batch-loop.local.md"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(textwrap.dedent(f"""\
        ---
        active: true
        iteration: 1
        max_iterations: 0
        total_plans: 2
        no_merge: false
        plugin_dir: /tmp
        config_dir: {config}
        owner_pid: {os.getppid()}
        session_id: test
        plans_file: ../../etc/passwd
        progress_file: ../../etc/passwd
        ---
        """))
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not state_file.exists()

    @requires_jq
    @pytest.mark.security
    def test_rejects_shell_metachar_in_progress_file(self, project_env):
        """Shell metacharacters in progress_file → cleanup and exit."""
        project, config = project_env
        state_file = project / ".claude" / "arc-batch-loop.local.md"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(textwrap.dedent(f"""\
        ---
        active: true
        iteration: 1
        max_iterations: 0
        total_plans: 2
        no_merge: false
        plugin_dir: /tmp
        config_dir: {config}
        owner_pid: {os.getppid()}
        session_id: test
        plans_file: tmp/$(whoami).json
        progress_file: tmp/$(whoami).json
        ---
        """))
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not state_file.exists()

    @requires_jq
    @pytest.mark.security
    def test_rejects_path_traversal_in_next_plan(self, project_env):
        """Path traversal in plan path → cleanup and exit."""
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        write_progress_file(project, [
            {"path": "plans/a.md", "status": "in_progress", "error": None, "completed_at": None},
            {"path": "../../etc/passwd", "status": "pending", "error": None, "completed_at": None},
        ])
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not (project / ".claude" / "arc-batch-loop.local.md").exists()


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestArcBatchEdgeCases:
    @requires_jq
    def test_edge_missing_progress_file(self, project_env):
        """Progress file doesn't exist → cleanup state file."""
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        # Don't create progress file
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not (project / ".claude" / "arc-batch-loop.local.md").exists()

    @requires_jq
    def test_edge_empty_progress_file(self, project_env):
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        progress_dir = project / "tmp" / "arc-batch"
        progress_dir.mkdir(parents=True, exist_ok=True)
        (progress_dir / "batch-progress.json").write_text("")
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not (project / ".claude" / "arc-batch-loop.local.md").exists()

    @requires_jq
    def test_edge_corrupted_progress_json(self, project_env):
        project, config = project_env
        write_state_file(project, config, owner_pid=str(os.getpid()))
        progress_dir = project / "tmp" / "arc-batch"
        progress_dir.mkdir(parents=True, exist_ok=True)
        (progress_dir / "batch-progress.json").write_text("{invalid json}")
        result = run_batch_hook(project, config)
        assert result.returncode == 0
        assert not (project / ".claude" / "arc-batch-loop.local.md").exists()
