"""Unit tests for arc-batch-preflight.sh.

Tests the pre-validation script that reads plan file paths from stdin,
validates each one (exists, not symlink, no path traversal, no shell
metacharacters, non-empty, deduplication), and writes validated paths
to stdout. Invalid paths produce errors on stderr and exit 1.

No jq dependency.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "arc-batch-preflight.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_preflight(
    plan_paths: list[str],
    *,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run arc-batch-preflight.sh with plan paths on stdin."""
    return subprocess.run(
        ["bash", str(SCRIPT)],
        input="\n".join(plan_paths),
        capture_output=True,
        text=True,
        timeout=10,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Valid Paths
# ---------------------------------------------------------------------------


class TestPreflightValidPaths:
    def test_passes_valid_plan_files(self, tmp_path):
        """Valid plan files are echoed to stdout."""
        plan1 = tmp_path / "plan1.md"
        plan2 = tmp_path / "plan2.md"
        plan1.write_text("# Plan 1\nContent here.\n")
        plan2.write_text("# Plan 2\nMore content.\n")
        result = run_preflight([str(plan1), str(plan2)])
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        assert str(plan1) in lines
        assert str(plan2) in lines

    def test_passes_single_plan_file(self, tmp_path):
        """Single valid plan file passes."""
        plan = tmp_path / "single.md"
        plan.write_text("# Single Plan\n")
        result = run_preflight([str(plan)])
        assert result.returncode == 0
        assert str(plan) in result.stdout

    def test_exit_0_on_success(self, tmp_path):
        """Exit code 0 when all paths are valid."""
        plan = tmp_path / "valid.md"
        plan.write_text("content\n")
        result = run_preflight([str(plan)])
        assert result.returncode == 0

    def test_no_stderr_on_success(self, tmp_path):
        """No stderr output when all paths are valid."""
        plan = tmp_path / "clean.md"
        plan.write_text("content\n")
        result = run_preflight([str(plan)])
        assert result.returncode == 0
        assert result.stderr.strip() == ""

    def test_paths_with_spaces_rejected(self, tmp_path):
        """Plan files with spaces in path are rejected (SEC-001 allowlist)."""
        dir_with_space = tmp_path / "my plans"
        dir_with_space.mkdir()
        plan = dir_with_space / "plan file.md"
        plan.write_text("# Plan\n")
        result = run_preflight([str(plan)])
        assert result.returncode == 1
        assert "disallowed characters" in result.stderr.lower()

    def test_paths_with_tilde_in_name_rejected(self, tmp_path):
        """Plan files with tilde in filename are rejected (SEC-001 allowlist)."""
        plan = tmp_path / "plan~backup.md"
        plan.write_text("# Plan\n")
        result = run_preflight([str(plan)])
        assert result.returncode == 1
        assert "disallowed characters" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Invalid Paths: Nonexistent
# ---------------------------------------------------------------------------


class TestPreflightNonexistent:
    def test_rejects_nonexistent_file(self):
        """Nonexistent file -> exit 1, stderr contains ERROR."""
        result = run_preflight(["/nonexistent/path/plan.md"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr
        assert "not found" in result.stderr.lower()

    def test_rejects_nonexistent_among_valid(self, tmp_path):
        """One bad file among valid ones -> exit 1."""
        good = tmp_path / "good.md"
        good.write_text("content\n")
        result = run_preflight([str(good), "/nonexistent/bad.md"])
        assert result.returncode == 1
        # Good file still appears in stdout
        assert str(good) in result.stdout
        assert "ERROR" in result.stderr

    def test_rejects_directory_path(self, tmp_path):
        """Directory path (not a file) -> exit 1."""
        dir_path = tmp_path / "a_directory"
        dir_path.mkdir()
        result = run_preflight([str(dir_path)])
        assert result.returncode == 1
        assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# Invalid Paths: Symlinks
# ---------------------------------------------------------------------------


class TestPreflightSymlinks:
    def test_rejects_symlink(self, tmp_path):
        """Symlinked plan file -> exit 1, stderr mentions symlink."""
        target = tmp_path / "real-plan.md"
        target.write_text("# Real Plan\n")
        link = tmp_path / "symlink-plan.md"
        link.symlink_to(target)
        result = run_preflight([str(link)])
        assert result.returncode == 1
        assert "ERROR" in result.stderr
        assert "ymlink" in result.stderr  # "Symlink" case-insensitive

    def test_rejects_broken_symlink(self, tmp_path):
        """Broken symlink -> exit 1 (file not found, since target doesn't exist)."""
        link = tmp_path / "broken-link.md"
        link.symlink_to("/nonexistent/target.md")
        result = run_preflight([str(link)])
        assert result.returncode == 1
        assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# Invalid Paths: Path Traversal
# ---------------------------------------------------------------------------


class TestPreflightPathTraversal:
    @pytest.mark.security
    def test_rejects_dot_dot_in_path(self, tmp_path):
        """Path with .. -> exit 1.

        The script checks file existence (step 1) before path traversal (step 3),
        so non-existent paths with .. may be rejected by the existence check first.
        Either way, the path is rejected.
        """
        result = run_preflight(["plans/../../../etc/passwd"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_dot_dot_at_start(self):
        """Path starting with .. -> exit 1."""
        result = run_preflight(["../secret/plan.md"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_dot_dot_in_middle(self, tmp_path):
        """Path with .. in the middle -> exit 1."""
        result = run_preflight([f"{tmp_path}/plans/../../../etc/passwd"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_dot_dot_even_when_file_exists(self, tmp_path):
        """Path traversal check fires even for existing file paths with ..

        Create a real file, then reference it via a path containing ..
        The file exists, is not a symlink, but contains .. -> rejected.
        """
        subdir = tmp_path / "plans" / "sub"
        subdir.mkdir(parents=True)
        plan = subdir / "plan.md"
        plan.write_text("content\n")
        # Reference it via ..: plans/sub/../sub/plan.md (which resolves to the real file)
        traversal_path = str(tmp_path / "plans" / "sub" / ".." / "sub" / "plan.md")
        result = run_preflight([traversal_path])
        assert result.returncode == 1
        assert "ERROR" in result.stderr
        assert "traversal" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Invalid Paths: Shell Metacharacters
# ---------------------------------------------------------------------------


class TestPreflightShellMetachars:
    @pytest.mark.security
    def test_rejects_dollar_sign(self, tmp_path):
        """$ in path -> exit 1.

        The script checks file existence before metacharacters, so for
        nonexistent paths the existence check fires first. Either way, rejected.
        """
        result = run_preflight(["plans/$(whoami).md"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_dollar_sign_in_existing_file(self, tmp_path):
        """$ in path of existing file -> rejected by metachar check."""
        # Create a file with $ in the name (literal, not shell expansion)
        plan = tmp_path / "plan$evil.md"
        plan.write_text("content\n")
        result = run_preflight([str(plan)])
        assert result.returncode == 1
        assert "ERROR" in result.stderr
        assert "disallowed characters" in result.stderr.lower()

    @pytest.mark.security
    def test_rejects_semicolon(self, tmp_path):
        """Semicolon in path -> exit 1."""
        result = run_preflight(["plans/plan.md; rm -rf /"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_pipe(self, tmp_path):
        """Pipe in path -> exit 1."""
        result = run_preflight(["plans/plan.md | cat /etc/passwd"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_ampersand(self, tmp_path):
        """Ampersand in path -> exit 1."""
        result = run_preflight(["plans/plan.md & echo pwned"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_backtick(self, tmp_path):
        """Backtick in path -> exit 1."""
        result = run_preflight(["plans/`whoami`.md"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_parentheses(self, tmp_path):
        """Parentheses in path -> exit 1."""
        result = run_preflight(["plans/$(echo hack).md"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_curly_braces(self, tmp_path):
        """Curly braces in path -> exit 1."""
        result = run_preflight(["plans/{a,b}.md"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    @pytest.mark.security
    def test_rejects_exclamation(self, tmp_path):
        """Exclamation mark in path -> exit 1."""
        result = run_preflight(["plans/plan!.md"])
        assert result.returncode == 1
        assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# Invalid Paths: Empty Files
# ---------------------------------------------------------------------------


class TestPreflightEmptyFiles:
    def test_rejects_empty_file(self, tmp_path):
        """Empty plan file -> exit 1."""
        empty = tmp_path / "empty.md"
        empty.write_text("")
        result = run_preflight([str(empty)])
        assert result.returncode == 1
        assert "ERROR" in result.stderr
        assert "mpty" in result.stderr  # "Empty" case-insensitive


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestPreflightDeduplication:
    def test_deduplicates_same_path(self, tmp_path):
        """Same path twice -> only one in stdout."""
        plan = tmp_path / "dup.md"
        plan.write_text("content\n")
        result = run_preflight([str(plan), str(plan)])
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 1
        # WARNING about duplicate should be on stderr
        assert "uplicate" in result.stderr or "WARNING" in result.stderr

    def test_deduplicates_via_realpath(self, tmp_path):
        """Different string representations of same file -> deduplicated."""
        plan = tmp_path / "plan.md"
        plan.write_text("content\n")
        # Use path/./plan.md which resolves to same file
        alt_path = str(tmp_path / "." / "plan.md")
        result = run_preflight([str(plan), alt_path])
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 1

    def test_does_not_deduplicate_different_files(self, tmp_path):
        """Different files with similar names -> both pass."""
        plan1 = tmp_path / "plan-a.md"
        plan2 = tmp_path / "plan-b.md"
        plan1.write_text("Plan A\n")
        plan2.write_text("Plan B\n")
        result = run_preflight([str(plan1), str(plan2)])
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Blank Lines and Comments
# ---------------------------------------------------------------------------


class TestPreflightBlankAndComments:
    def test_skips_blank_lines(self, tmp_path):
        """Blank lines in input are skipped."""
        plan = tmp_path / "plan.md"
        plan.write_text("content\n")
        result = run_preflight(["", str(plan), "", ""])
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 1
        assert str(plan) in lines[0]

    def test_skips_comment_lines(self, tmp_path):
        """Lines starting with # are skipped."""
        plan = tmp_path / "plan.md"
        plan.write_text("content\n")
        result = run_preflight(["# This is a comment", str(plan), "# Another comment"])
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 1
        assert str(plan) in lines[0]

    def test_only_comments_and_blanks(self):
        """Input with only comments and blanks -> exit 0 with no output."""
        result = run_preflight(["", "# comment", "", "# another"])
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestPreflightEdgeCases:
    def test_empty_input(self):
        """Empty stdin -> exit 0 with no output."""
        result = run_preflight([])
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_error_count_in_stderr(self, tmp_path):
        """Error count summary appears in stderr."""
        result = run_preflight(["/bad1.md", "/bad2.md", "/bad3.md"])
        assert result.returncode == 1
        assert "3 error(s)" in result.stderr

    def test_mixed_valid_and_invalid(self, tmp_path):
        """Mix of valid and invalid -> exit 1, valid paths still in stdout."""
        good = tmp_path / "good.md"
        good.write_text("content\n")
        result = run_preflight([str(good), "/nonexistent.md", "plans/../hack.md"])
        assert result.returncode == 1
        assert str(good) in result.stdout
        assert "ERROR" in result.stderr

    def test_large_number_of_paths(self, tmp_path):
        """Many valid paths are all passed through."""
        plans = []
        for i in range(20):
            p = tmp_path / f"plan-{i:03d}.md"
            p.write_text(f"Plan {i}\n")
            plans.append(str(p))
        result = run_preflight(plans)
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 20
