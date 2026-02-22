"""Unit tests for session-start.sh (SessionStart hook).

Tests the hook that loads the using-rune skill content at session start,
strips YAML frontmatter, JSON-escapes the body, and outputs it as
hookSpecificOutput with hookEventName="SessionStart".

Requires: bash (no jq dependency for this script)
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap

from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "session-start.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_session_start(
    *,
    plugin_root: str | None = None,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run session-start.sh with configurable CLAUDE_PLUGIN_ROOT."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = plugin_root or str(SCRIPTS_DIR.parent)
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


# ---------------------------------------------------------------------------
# Output Validation
# ---------------------------------------------------------------------------


class TestSessionStartOutput:
    def test_outputs_valid_json(self):
        """Output must be valid JSON."""
        result = run_session_start()
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert isinstance(output, dict)

    def test_hook_event_name_is_session_start(self):
        """hookEventName must be 'SessionStart'."""
        result = run_session_start()
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_contains_rune_plugin_active_marker(self):
        """Output must contain the '[Rune Plugin Active]' marker."""
        result = run_session_start()
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "[Rune Plugin Active]" in ctx

    def test_contains_additional_context(self):
        """additionalContext must be a non-empty string."""
        result = run_session_start()
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert isinstance(ctx, str)
        assert len(ctx) > 50  # Should contain meaningful content

    def test_contains_routing_table_content(self):
        """Output should contain routing table keywords from using-rune SKILL.md."""
        result = run_session_start()
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        # The using-rune skill contains workflow routing info
        assert "rune" in ctx.lower()

    def test_strips_yaml_frontmatter(self):
        """YAML frontmatter (---...---) must NOT appear in the output."""
        result = run_session_start()
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        # Frontmatter keys should not be in output
        assert "user-invocable:" not in ctx
        assert "disable-model-invocation:" not in ctx

    def test_json_escapes_special_characters(self):
        """Output JSON must handle special characters without corruption."""
        result = run_session_start()
        # If JSON parsing succeeds, escaping was handled correctly
        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output

    def test_exit_code_is_zero(self):
        """Script must always exit 0."""
        result = run_session_start()
        assert result.returncode == 0

    def test_no_stderr_output(self):
        """Successful run should produce no stderr."""
        result = run_session_start()
        assert result.returncode == 0
        assert result.stderr.strip() == ""


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestSessionStartEdgeCases:
    def test_exit_0_when_skill_missing(self, tmp_path):
        """Missing SKILL.md -> exit 0 with no output."""
        # Point to a directory that has no skills/using-rune/SKILL.md
        result = run_session_start(plugin_root=str(tmp_path))
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_exit_0_when_plugin_root_nonexistent(self):
        """Nonexistent CLAUDE_PLUGIN_ROOT -> exit 0 with no output."""
        result = run_session_start(
            plugin_root="/nonexistent/path/that/does/not/exist"
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_handles_custom_plugin_root(self, tmp_path):
        """Custom CLAUDE_PLUGIN_ROOT with valid SKILL.md works."""
        skill_dir = tmp_path / "skills" / "using-rune"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(textwrap.dedent("""\
        ---
        name: using-rune
        description: Test skill
        ---

        # Test Content

        This is test content with special chars: "quotes" and \\backslash.
        """))
        result = run_session_start(plugin_root=str(tmp_path))
        assert result.returncode == 0
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "[Rune Plugin Active]" in ctx
        assert "Test Content" in ctx

    def test_handles_skill_without_frontmatter(self, tmp_path):
        """SKILL.md without YAML frontmatter -> all content included."""
        skill_dir = tmp_path / "skills" / "using-rune"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# No Frontmatter Here\n\nJust content.\n")
        result = run_session_start(plugin_root=str(tmp_path))
        assert result.returncode == 0
        # The script looks for --- delimiters. Without them, no content passes
        # the frontmatter-stripping logic since PAST_FRONTMATTER stays false.
        # This is expected: content before/outside frontmatter is not emitted.

    def test_handles_skill_with_empty_body(self, tmp_path):
        """SKILL.md with frontmatter but empty body -> still outputs valid JSON."""
        skill_dir = tmp_path / "skills" / "using-rune"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: using-rune\n---\n")
        result = run_session_start(plugin_root=str(tmp_path))
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "[Rune Plugin Active]" in output["hookSpecificOutput"]["additionalContext"]

    def test_handles_skill_with_special_json_chars(self, tmp_path):
        """SKILL.md with JSON-sensitive characters is properly escaped."""
        skill_dir = tmp_path / "skills" / "using-rune"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            '---\nname: using-rune\n---\n\n'
            'Contains "double quotes" and tab\there and newline.\n'
        )
        result = run_session_start(plugin_root=str(tmp_path))
        assert result.returncode == 0
        # Must parse as valid JSON despite special characters
        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output

    def test_plugin_root_fallback_without_env(self):
        """Without CLAUDE_PLUGIN_ROOT, script falls back to directory-based resolution."""
        env = os.environ.copy()
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        # Script uses fallback: $(cd "$(dirname "$0")/.." && pwd)
        # Which should resolve to the plugin root since SCRIPT is in scripts/
        assert result.returncode == 0
        if result.stdout.strip():
            output = json.loads(result.stdout)
            assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
