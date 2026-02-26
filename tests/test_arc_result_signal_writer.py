"""Unit tests for arc-result-signal-writer.sh (ARC-SIGNAL-001 PostToolUse hook).

Tests the deterministic signal writer that fires on Write/Edit tool calls and
generates tmp/arc-result-current.json when an arc checkpoint shows completion.
Verifies fast-path exits, completion detection, signal content, and security guards.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "arc-result-signal-writer.sh"


def make_checkpoint(
    project: Path,
    *,
    arc_id: str = "arc-test-123",
    plan_file: str = "plans/a.md",
    ship_status: str = "completed",
    merge_status: str = "pending",
    pr_url: str | None = "https://github.com/test/repo/pull/42",
    owner_pid: str | None = None,
    config_dir: str | None = None,
    use_tmp_path: bool = False,
) -> Path:
    """Create a mock arc checkpoint file."""
    pid = owner_pid or str(os.getpid())
    cfg = config_dir or "/tmp/test-config"
    base = project / ("tmp" if use_tmp_path else ".claude")
    ckpt_dir = base / "arc" / arc_id
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "checkpoint.json"

    checkpoint = {
        "id": arc_id,
        "plan_file": plan_file,
        "pr_url": pr_url,
        "owner_pid": pid,
        "config_dir": cfg,
        "phases": {
            "forge": {"status": "completed"},
            "work": {"status": "completed"},
            "code_review": {"status": "completed"},
            "mend": {"status": "completed"},
            "ship": {"status": ship_status, "pr_url": pr_url},
            "merge": {"status": merge_status},
        },
    }
    ckpt_path.write_text(json.dumps(checkpoint, indent=2))
    return ckpt_path


def make_hook_input(project: Path, file_path: str) -> str:
    """Create PostToolUse hook stdin JSON for a Write/Edit call."""
    return json.dumps({
        "cwd": str(project),
        "tool_name": "Write",
        "tool_input": {"file_path": file_path},
    })


def run_signal_writer(project: Path, config: Path, file_path: str, *, timeout: int = 10):
    """Run the signal writer hook with given file path."""
    import subprocess

    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config)

    return subprocess.run(
        ["bash", str(SCRIPT)],
        input=make_hook_input(project, file_path),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(project),
    )


class TestSignalWriterFastPath:
    """Guard clauses that should exit 0 without writing a signal."""

    @requires_jq
    def test_non_checkpoint_write_skipped(self, project_env):
        """Write to a non-checkpoint file → fast-path exit, no signal."""
        project, config = project_env
        result = run_signal_writer(project, config, str(project / "src" / "main.py"))
        assert result.returncode == 0
        assert not (project / "tmp" / "arc-result-current.json").exists()

    @requires_jq
    def test_random_checkpoint_json_skipped(self, project_env):
        """Write to some other checkpoint.json → not in arc path, skipped."""
        project, config = project_env
        other_ckpt = project / "tmp" / "other" / "checkpoint.json"
        other_ckpt.parent.mkdir(parents=True, exist_ok=True)
        other_ckpt.write_text('{"foo": "bar"}')
        result = run_signal_writer(project, config, str(other_ckpt))
        assert result.returncode == 0
        assert not (project / "tmp" / "arc-result-current.json").exists()

    @requires_jq
    def test_ship_pending_skipped(self, project_env):
        """Checkpoint with ship=pending, merge=pending → no signal."""
        project, config = project_env
        ckpt_path = make_checkpoint(project, ship_status="pending", merge_status="pending")
        result = run_signal_writer(project, config, str(ckpt_path))
        assert result.returncode == 0
        assert not (project / "tmp" / "arc-result-current.json").exists()

    @requires_jq
    def test_ship_in_progress_skipped(self, project_env):
        """Checkpoint with ship=in_progress → no signal."""
        project, config = project_env
        ckpt_path = make_checkpoint(project, ship_status="in_progress", merge_status="pending")
        result = run_signal_writer(project, config, str(ckpt_path))
        assert result.returncode == 0
        assert not (project / "tmp" / "arc-result-current.json").exists()


class TestSignalWriterCompletion:
    """Successful signal generation when arc completes."""

    @requires_jq
    def test_ship_completed_writes_signal(self, project_env):
        """Checkpoint with ship=completed → signal written."""
        project, config = project_env
        ckpt_path = make_checkpoint(
            project,
            ship_status="completed",
            pr_url="https://github.com/test/repo/pull/42",
            owner_pid=str(os.getpid()),
            config_dir=str(config.resolve()),
        )
        result = run_signal_writer(project, config, str(ckpt_path))
        assert result.returncode == 0
        signal_file = project / "tmp" / "arc-result-current.json"
        assert signal_file.exists()
        signal = json.loads(signal_file.read_text())
        assert signal["schema_version"] == 1
        assert signal["status"] == "completed"
        assert signal["pr_url"] == "https://github.com/test/repo/pull/42"
        assert signal["plan_path"] == "plans/a.md"

    @requires_jq
    def test_merge_completed_writes_signal(self, project_env):
        """Checkpoint with merge=completed → signal written."""
        project, config = project_env
        ckpt_path = make_checkpoint(
            project,
            ship_status="pending",
            merge_status="completed",
            owner_pid=str(os.getpid()),
            config_dir=str(config.resolve()),
        )
        result = run_signal_writer(project, config, str(ckpt_path))
        assert result.returncode == 0
        signal_file = project / "tmp" / "arc-result-current.json"
        assert signal_file.exists()
        signal = json.loads(signal_file.read_text())
        assert signal["status"] == "completed"

    @requires_jq
    def test_signal_preserves_session_identity(self, project_env):
        """Signal file carries owner_pid and config_dir from checkpoint."""
        project, config = project_env
        pid = str(os.getpid())
        cfg = str(config.resolve())
        ckpt_path = make_checkpoint(
            project,
            owner_pid=pid,
            config_dir=cfg,
        )
        run_signal_writer(project, config, str(ckpt_path))
        signal = json.loads((project / "tmp" / "arc-result-current.json").read_text())
        assert signal["owner_pid"] == pid
        assert signal["config_dir"] == cfg

    @requires_jq
    def test_failed_phases_produce_partial_status(self, project_env):
        """Checkpoint with failed phases → signal status is 'partial'."""
        project, config = project_env
        ckpt_dir = project / ".claude" / "arc" / "arc-partial"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = ckpt_dir / "checkpoint.json"
        checkpoint = {
            "id": "arc-partial",
            "plan_file": "plans/a.md",
            "pr_url": None,
            "owner_pid": str(os.getpid()),
            "config_dir": str(config.resolve()),
            "phases": {
                "forge": {"status": "completed"},
                "work": {"status": "failed"},
                "ship": {"status": "completed"},
            },
        }
        ckpt_path.write_text(json.dumps(checkpoint))
        result = run_signal_writer(project, config, str(ckpt_path))
        assert result.returncode == 0
        signal = json.loads((project / "tmp" / "arc-result-current.json").read_text())
        assert signal["status"] == "partial"

    @requires_jq
    def test_tmp_arc_path_also_detected(self, project_env):
        """Checkpoint under tmp/arc/ (post-compaction) → signal written."""
        project, config = project_env
        ckpt_path = make_checkpoint(
            project,
            use_tmp_path=True,
            owner_pid=str(os.getpid()),
            config_dir=str(config.resolve()),
        )
        result = run_signal_writer(project, config, str(ckpt_path))
        assert result.returncode == 0
        assert (project / "tmp" / "arc-result-current.json").exists()


class TestSignalWriterSecurity:
    """Security guards: symlink rejection, PR URL validation."""

    @requires_jq
    def test_symlinked_checkpoint_rejected(self, project_env):
        """Checkpoint file that is a symlink → rejected, no signal."""
        project, config = project_env
        # Create real checkpoint elsewhere
        real_dir = project / "tmp" / "real-ckpt"
        real_dir.mkdir(parents=True, exist_ok=True)
        real_ckpt = real_dir / "checkpoint.json"
        real_ckpt.write_text(json.dumps({
            "id": "arc-sym",
            "plan_file": "plans/a.md",
            "pr_url": None,
            "owner_pid": str(os.getpid()),
            "config_dir": str(config.resolve()),
            "phases": {"ship": {"status": "completed"}},
        }))
        # Symlink it into the arc checkpoint path
        ckpt_dir = project / ".claude" / "arc" / "arc-sym"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        symlink_path = ckpt_dir / "checkpoint.json"
        symlink_path.symlink_to(real_ckpt)
        result = run_signal_writer(project, config, str(symlink_path))
        assert result.returncode == 0
        assert not (project / "tmp" / "arc-result-current.json").exists()

    @requires_jq
    def test_null_pr_url_becomes_json_null(self, project_env):
        """Checkpoint with null pr_url → signal pr_url is JSON null."""
        project, config = project_env
        ckpt_path = make_checkpoint(
            project,
            pr_url=None,
            owner_pid=str(os.getpid()),
            config_dir=str(config.resolve()),
        )
        run_signal_writer(project, config, str(ckpt_path))
        signal = json.loads((project / "tmp" / "arc-result-current.json").read_text())
        assert signal["pr_url"] is None

    @requires_jq
    def test_invalid_pr_url_becomes_null(self, project_env):
        """Checkpoint with invalid PR URL → normalized to null."""
        project, config = project_env
        # Manually create checkpoint with invalid URL
        ckpt_dir = project / ".claude" / "arc" / "arc-bad-url"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = ckpt_dir / "checkpoint.json"
        checkpoint = {
            "id": "arc-bad-url",
            "plan_file": "plans/a.md",
            "pr_url": "javascript:alert(1)",
            "owner_pid": str(os.getpid()),
            "config_dir": str(config.resolve()),
            "phases": {"ship": {"status": "completed"}},
        }
        ckpt_path.write_text(json.dumps(checkpoint))
        run_signal_writer(project, config, str(ckpt_path))
        signal = json.loads((project / "tmp" / "arc-result-current.json").read_text())
        assert signal["pr_url"] is None
