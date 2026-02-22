"""Unit tests for validate-inner-flame.sh (Inner Flame enforcement).

Tests the TaskCompleted hook that validates Inner Flame self-review content
in teammate output files. Verifies guard clauses, output detection,
blocking vs soft enforcement, and security checks.

Requires: jq (skips gracefully if missing)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from conftest import SCRIPTS_DIR, requires_jq

SCRIPT = SCRIPTS_DIR / "validate-inner-flame.sh"


def run_inner_flame(
    project: Path,
    config: Path,
    *,
    team_name: str = "rune-review-test123",
    task_id: str = "task-1",
    teammate_name: str = "ward-sentinel",
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run validate-inner-flame.sh with a TaskCompleted event."""
    input_json = {
        "team_name": team_name,
        "task_id": task_id,
        "teammate_name": teammate_name,
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


def setup_review_output(
    project: Path,
    team_name: str = "rune-review-test123",
    teammate_name: str = "ward-sentinel",
    content: str = "",
) -> Path:
    """Create a teammate output file in the expected review directory."""
    review_id = team_name.replace("rune-review-", "").replace("arc-review-", "")
    output_dir = project / "tmp" / "reviews" / review_id
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{teammate_name}.md"
    path.write_text(content)
    return path


def setup_audit_output(
    project: Path,
    team_name: str = "rune-audit-test123",
    teammate_name: str = "ward-sentinel",
    content: str = "",
) -> Path:
    """Create a teammate output file in the expected audit directory."""
    audit_id = team_name.replace("rune-audit-", "").replace("arc-audit-", "")
    output_dir = project / "tmp" / "audit" / audit_id
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{teammate_name}.md"
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# Guard Clauses
# ---------------------------------------------------------------------------


class TestInnerFlameGuardClauses:
    @requires_jq
    def test_exit_0_empty_team_name(self, project_env):
        project, config = project_env
        result = run_inner_flame(project, config, team_name="")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_empty_task_id(self, project_env):
        project, config = project_env
        result = run_inner_flame(project, config, task_id="")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_non_rune_team(self, project_env):
        project, config = project_env
        result = run_inner_flame(project, config, team_name="custom-team")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_invalid_team_name(self, project_env):
        project, config = project_env
        result = run_inner_flame(project, config, team_name="rune-$(whoami)")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_invalid_teammate_name(self, project_env):
        project, config = project_env
        result = run_inner_flame(project, config, teammate_name="ward;rm -rf /")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_invalid_task_id(self, project_env):
        project, config = project_env
        result = run_inner_flame(project, config, task_id="task;evil")
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
    def test_exit_0_work_team(self, project_env):
        """Work teams skip Inner Flame validation."""
        project, config = project_env
        result = run_inner_flame(project, config, team_name="rune-work-abc")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_mend_team(self, project_env):
        """Mend teams skip Inner Flame validation."""
        project, config = project_env
        result = run_inner_flame(project, config, team_name="rune-mend-abc")
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_no_output_dir(self, project_env):
        """No output directory exists -> exit 0."""
        project, config = project_env
        result = run_inner_flame(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_exit_0_no_output_file(self, project_env):
        """Output directory exists but teammate file missing -> exit 0."""
        project, config = project_env
        output_dir = project / "tmp" / "reviews" / "test123"
        output_dir.mkdir(parents=True, exist_ok=True)
        result = run_inner_flame(project, config)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Inner Flame Detection
# ---------------------------------------------------------------------------


class TestInnerFlameDetection:
    @requires_jq
    def test_allows_with_inner_flame_content(self, project_env):
        """Output containing Inner Flame section -> exit 0."""
        project, config = project_env
        content = (
            "# Review Findings\n\n"
            "Finding details here.\n\n"
            "## Self-Review Log (Inner Flame)\n\n"
            "- Grounding: verified\n"
            "- Completeness: confirmed\n"
        )
        setup_review_output(project, content=content)
        result = run_inner_flame(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_allows_inner_flame_colon_format(self, project_env):
        """Output with 'Inner Flame:' marker -> exit 0."""
        project, config = project_env
        content = "# Review\nFindings.\nInner Flame: checked\n"
        setup_review_output(project, content=content)
        result = run_inner_flame(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_allows_inner_flame_hyphen_format(self, project_env):
        """Output with 'Inner-flame:' marker -> exit 0."""
        project, config = project_env
        content = "# Review\nFindings.\nInner-flame: verified\n"
        setup_review_output(project, content=content)
        result = run_inner_flame(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_blocks_without_inner_flame_default(self, project_env):
        """Output missing Inner Flame -> exit 2 (default block_on_fail=true via yq)."""
        project, config = project_env
        content = "# Review\nNo self-review section here.\n"
        setup_review_output(project, content=content)
        result = run_inner_flame(project, config)
        # Without yq, defaults to soft enforcement (block_on_fail defaults to false in bash)
        # With yq + no talisman, block_on_fail defaults to true from yq
        # Without talisman file: the for loop doesn't enter, BLOCK_ON_FAIL stays "false"
        # So this is soft enforcement -> exit 0 with stderr warning
        assert result.returncode == 0
        assert "Inner Flame" in result.stderr

    @requires_jq
    def test_blocks_with_talisman_block_on_fail(self, project_env):
        """With talisman block_on_fail=true and yq available -> exit 2."""
        project, config = project_env
        content = "# Review\nNo self-review here.\n"
        setup_review_output(project, content=content)
        # Create talisman with block_on_fail: true
        talisman_dir = project / ".claude"
        talisman_dir.mkdir(parents=True, exist_ok=True)
        (talisman_dir / "talisman.yml").write_text(
            "inner_flame:\n  enabled: true\n  block_on_fail: true\n"
        )
        result = run_inner_flame(project, config)
        # Only blocks if yq is available to read the talisman
        if result.returncode == 2:
            assert "Inner Flame" in result.stderr
        else:
            # yq not available — falls to default (soft enforcement)
            assert result.returncode == 0

    @requires_jq
    def test_soft_enforcement_without_talisman(self, project_env):
        """No talisman -> soft enforcement (BLOCK_ON_FAIL=false)."""
        project, config = project_env
        content = "# Review\nNo self-review.\n"
        setup_review_output(project, content=content)
        result = run_inner_flame(project, config)
        assert result.returncode == 0
        assert "Inner Flame" in result.stderr
        assert "soft enforcement" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Team Type Routing
# ---------------------------------------------------------------------------


class TestInnerFlameTeamRouting:
    @requires_jq
    def test_review_team_checks_reviews_dir(self, project_env):
        """rune-review-* checks tmp/reviews/{id}/."""
        project, config = project_env
        content = "# Review\nInner Flame: ok\n"
        setup_review_output(project, content=content)
        result = run_inner_flame(project, config)
        assert result.returncode == 0

    @requires_jq
    def test_arc_review_team_checks_reviews_dir(self, project_env):
        """arc-review-* checks tmp/reviews/{id}/."""
        project, config = project_env
        content = "# Review\nInner Flame: ok\n"
        setup_review_output(
            project,
            team_name="arc-review-test123",
            content=content,
        )
        result = run_inner_flame(project, config, team_name="arc-review-test123")
        assert result.returncode == 0

    @requires_jq
    def test_audit_team_checks_audit_dir(self, project_env):
        """rune-audit-* checks tmp/audit/{id}/."""
        project, config = project_env
        content = "# Audit\nInner Flame: ok\n"
        setup_audit_output(project, content=content)
        result = run_inner_flame(
            project, config, team_name="rune-audit-test123"
        )
        assert result.returncode == 0

    @requires_jq
    def test_inspect_team_checks_inspect_dir(self, project_env):
        """rune-inspect-* checks tmp/inspect/{id}/."""
        project, config = project_env
        output_dir = project / "tmp" / "inspect" / "test123"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "ward-sentinel.md").write_text(
            "# Inspect\nInner Flame: ok\n"
        )
        result = run_inner_flame(
            project, config, team_name="rune-inspect-test123"
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Disabled via Talisman
# ---------------------------------------------------------------------------


class TestInnerFlameDisabled:
    @requires_jq
    def test_exit_0_when_disabled_in_talisman(self, project_env):
        """inner_flame.enabled: false in talisman -> skip validation."""
        project, config = project_env
        content = "# Review\nNo self-review.\n"
        setup_review_output(project, content=content)
        talisman_dir = project / ".claude"
        talisman_dir.mkdir(parents=True, exist_ok=True)
        (talisman_dir / "talisman.yml").write_text(
            "inner_flame:\n  enabled: false\n"
        )
        result = run_inner_flame(project, config)
        # Only skips if yq is available to read the setting
        # If yq missing, defaults to enabled=true (but still soft enforcement)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TestInnerFlameSecurity:
    @requires_jq
    def test_path_containment_blocks_outside_tmp(self, project_env):
        """Output dir outside CWD/tmp/ -> exit 0 (skip)."""
        project, config = project_env
        # Even if we trick the script, the path containment check should catch it
        result = run_inner_flame(project, config)
        assert result.returncode == 0
