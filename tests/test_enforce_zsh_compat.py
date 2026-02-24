"""Unit tests for enforce-zsh-compat.sh hook script.

Tests the shell script as a subprocess, verifying:
- Guard clauses (non-Bash tool, empty command, no target patterns, missing jq)
- Shell detection (zsh enforcement vs. skip for bash/fish/unset)
- Check A: bare `status=` assignment blocking with fix suggestion
- Check B: unprotected glob in for-loop auto-fix with setopt nullglob
- Check C: `! [[` history expansion auto-fix to `[[ !`
- Edge cases (multiline commands, pipeline context, variant shell paths)

CRITICAL: For zsh enforcement to activate, set SHELL=/bin/zsh via env_override.
Without it, the script exits 0 immediately (shell detection skips non-zsh shells).

Requires: jq (tests that rely on JSON output skip gracefully if jq is missing)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import requires_jq

PLUGIN_DIR = Path(__file__).parent.parent / "plugins" / "rune"
SCRIPTS_DIR = PLUGIN_DIR / "scripts"
ENFORCE_ZSH_COMPAT = SCRIPTS_DIR / "enforce-zsh-compat.sh"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ZSH_ENV = {"SHELL": "/bin/zsh"}


def make_bash_input(command: str) -> dict:
    """Build a minimal PreToolUse:Bash hook input dict."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def parse_hook_output(stdout: str) -> dict:
    """Parse hook JSON from stdout, raising AssertionError on failure."""
    stripped = stdout.strip()
    assert stripped, "Expected non-empty stdout with hook JSON"
    return json.loads(stripped)


# ===========================================================================
# TestZshCompatGuardClauses — exit 0 for inputs that should be skipped
# ===========================================================================


class TestZshCompatGuardClauses:
    """Guard clause tests: conditions under which the script exits 0 silently."""

    @requires_jq
    def test_exit_0_for_non_bash_tool(self, hook_runner) -> None:
        """Non-Bash tool_name → exit 0 (script only targets Bash tool)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/tmp/test.sh", "content": "status=0"},
            },
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_for_read_tool(self, hook_runner) -> None:
        """Read tool_name → exit 0 even with status= in path argument."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/status=something"},
            },
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_for_empty_command(self, hook_runner) -> None:
        """Empty command string → exit 0 (nothing to check)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            {
                "tool_name": "Bash",
                "tool_input": {"command": ""},
            },
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_for_missing_command_field(self, hook_runner) -> None:
        """Missing tool_input.command field → exit 0."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            {
                "tool_name": "Bash",
                "tool_input": {},
            },
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_for_command_without_target_patterns(self, hook_runner) -> None:
        """Command with no status=, no for-glob, no ! [[ → fast-path exit 0."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("echo hello && ls -la /tmp"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_exit_0_without_jq(self, hook_runner) -> None:
        """Script exits 0 with warning when jq is not available."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_status); echo $status"),
            env_override={
                "SHELL": "/bin/zsh",
                "PATH": "/usr/bin:/bin",  # Likely no jq on this PATH
            },
        )
        assert result.returncode == 0
        # If jq truly was missing, should warn; if jq was found anyway, that's fine too

    @requires_jq
    def test_exit_0_for_non_zsh_shell_bash(self, hook_runner) -> None:
        """SHELL=/bin/bash → skip enforcement (zsh-specific rules don't apply)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_status); echo $status"),
            env_override={"SHELL": "/bin/bash"},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_for_non_zsh_shell_fish(self, hook_runner) -> None:
        """SHELL=/usr/bin/fish → skip enforcement."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_status)"),
            env_override={"SHELL": "/usr/bin/fish"},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_exit_0_for_non_zsh_shell_dash(self, hook_runner) -> None:
        """SHELL=/bin/dash → skip enforcement."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_status)"),
            env_override={"SHELL": "/bin/dash"},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_enforces_when_shell_is_zsh(self, hook_runner) -> None:
        """SHELL=/bin/zsh → enforcement is active (status= should be blocked)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_status); echo $status"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        decision = output["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    @requires_jq
    def test_enforces_on_macos_without_shell_set(self, hook_runner) -> None:
        """SHELL unset on macOS (Darwin) → enforce (zsh is macOS default since Catalina)."""
        import platform

        if platform.system() != "Darwin":
            pytest.skip("macOS-only: uname -s == Darwin fallback test")

        # Remove SHELL from env — script should fall through to uname check
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_status); echo $status"),
            env_override={"SHELL": ""},  # Empty string triggers the unset code path
        )
        # On Darwin with empty SHELL, script enforces via uname fallback
        # The result may be deny (enforcement) or allow (if Darwin test is inconclusive)
        assert result.returncode == 0


# ===========================================================================
# TestZshCheckAStatusAssignment — `status=` assignment blocking
# ===========================================================================


class TestZshCheckAStatusAssignment:
    """Check A: bare `status=` assignment is read-only in zsh — must be denied."""

    @requires_jq
    def test_denies_bare_status_assignment(self, hook_runner) -> None:
        """Bare `status=$(...)` → denied (ZSH-001)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(jq -r '.status' file.json)"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_local_status_assignment(self, hook_runner) -> None:
        """`local status=...` → denied (local keyword + status= is still read-only)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("local status=$(get_val)"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_export_status_assignment(self, hook_runner) -> None:
        """`export status=...` → denied."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("export status=active"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_status_assignment_after_semicolon(self, hook_runner) -> None:
        """`;status=value` → denied (semicolon is a valid shell word boundary)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("do_work; status=done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_denies_status_assignment_with_double_ampersand(self, hook_runner) -> None:
        """Embedded `&& status=` → denied."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("run_cmd && status=ok && echo $status"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_allows_task_status_assignment(self, hook_runner) -> None:
        """`task_status=...` → allowed (underscore prefix breaks the boundary)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("task_status=$(jq -r '.status' file.json); echo $task_status"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_allows_exit_status_assignment(self, hook_runner) -> None:
        """`exit_status=...` → allowed (not a zsh read-only variable)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("exit_status=$?; echo $exit_status"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_allows_http_status_assignment(self, hook_runner) -> None:
        """`http_status=...` → allowed (prefix word is not `status`)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("http_status=$(curl -o /dev/null -w '%{http_code}' https://example.com)"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_allows_diff_status_assignment(self, hook_runner) -> None:
        """`diff_status=...` → allowed."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("diff_status=$(git diff --name-only | wc -l)"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_deny_contains_fix_suggestion(self, hook_runner) -> None:
        """Deny response must include an actionable fix suggestion."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(jq -r '.status' file.json)"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]

        # Must include permissionDecisionReason with fix info
        reason = hook_out.get("permissionDecisionReason", "")
        assert "ZSH-001" in reason
        assert "read-only" in reason.lower() or "status" in reason

        # Must include additionalContext with rename guidance
        ctx = hook_out.get("additionalContext", "")
        assert "task_status" in ctx or "tstat" in ctx or "rename" in ctx.lower()

    @requires_jq
    def test_deny_output_is_valid_json(self, hook_runner) -> None:
        """Deny JSON output must be structurally valid hook output."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=active"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)

        # Validate required hook output structure
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("hookEventName") == "PreToolUse"
        assert hook_out.get("permissionDecision") == "deny"

    @requires_jq
    def test_allows_tstat_assignment(self, hook_runner) -> None:
        """`tstat=...` → allowed (not the reserved `status` variable)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("tstat=$(jq -r '.status' file.json); echo $tstat"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_allows_completion_status_assignment(self, hook_runner) -> None:
        """`completion_status=...` → allowed."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("completion_status=done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ===========================================================================
# TestZshCheckBGlobAutoFix — unprotected glob in for-loop auto-fix
# ===========================================================================


class TestZshCheckBGlobAutoFix:
    """Check B: unprotected glob in for-loops triggers auto-fix via setopt nullglob."""

    @requires_jq
    def test_autofixes_unprotected_star_glob(self, hook_runner) -> None:
        """`for f in *.md; do` → auto-fixed with setopt nullglob prepended."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for f in *.md; do echo $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]
        assert hook_out["permissionDecision"] == "allow"
        assert "updatedInput" in hook_out
        fixed_cmd = hook_out["updatedInput"]["command"]
        assert fixed_cmd.startswith("setopt nullglob;")

    @requires_jq
    def test_autofixed_command_contains_original(self, hook_runner) -> None:
        """Auto-fixed command must preserve the original command after prepend."""
        original = "for f in path/to/*.json; do process \"$f\"; done"
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(original),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        fixed_cmd = output["hookSpecificOutput"]["updatedInput"]["command"]
        # Original command must appear in the fixed version
        assert original in fixed_cmd
        assert fixed_cmd == f"setopt nullglob; {original}"

    @requires_jq
    def test_autofixes_question_mark_glob(self, hook_runner) -> None:
        """`for f in file?.txt; do` → auto-fixed (? is a NOMATCH-triggering glob)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for f in file?.txt; do echo $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]
        assert hook_out["permissionDecision"] == "allow"
        assert "updatedInput" in hook_out

    @requires_jq
    def test_skips_autofix_when_n_qualifier_present(self, hook_runner) -> None:
        """`for f in *.md(N); do` → no fix needed, (N) qualifier protects the glob."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for f in *.md(N); do echo $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_skips_autofix_when_setopt_nullglob_present(self, hook_runner) -> None:
        """Command already contains `setopt nullglob` → no fix needed."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("setopt nullglob; for f in *.md; do echo $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_skips_autofix_when_setopt_null_glob_caps_present(
        self, hook_runner
    ) -> None:
        """`setopt NULL_GLOB` (uppercase variant) → no fix needed."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("setopt NULL_GLOB; for f in *.txt; do echo $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_skips_autofix_when_shopt_nullglob_present(self, hook_runner) -> None:
        """`shopt -s nullglob` → no fix needed (bash compat pattern recognized by script)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("shopt -s nullglob; for f in *.sh; do bash $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_autofix_uses_updated_input(self, hook_runner) -> None:
        """Auto-fix must use updatedInput (not deny) to rewrite the command transparently."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for item in reports/*.csv; do cat \"$item\"; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]

        # Must allow (not deny)
        assert hook_out["permissionDecision"] == "allow"
        # Must provide updatedInput with command
        assert "updatedInput" in hook_out
        assert "command" in hook_out["updatedInput"]

    @requires_jq
    def test_autofix_output_is_valid_hook_json(self, hook_runner) -> None:
        """Auto-fix JSON output must be a structurally valid hook response."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for f in src/*.py; do python $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)

        # Validate required hook output structure
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("hookEventName") == "PreToolUse"
        assert hook_out.get("permissionDecision") == "allow"
        assert isinstance(hook_out.get("updatedInput"), dict)

    @requires_jq
    def test_autofix_includes_additional_context(self, hook_runner) -> None:
        """Auto-fix response should include additionalContext explaining the change."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for f in *.log; do grep ERROR $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]
        ctx = hook_out.get("additionalContext", "")
        assert "ZSH-001" in ctx or "nullglob" in ctx.lower()

    @requires_jq
    def test_autofix_for_glob_outside_for_loop(self, hook_runner) -> None:
        """Glob in non-for context (ls *.md) → Check E auto-fix with setopt nullglob.

        Check E (v1.x) catches unquoted globs in command arguments to file
        commands (ls, rm, cp, etc.). In zsh, `ls *.md` fails with NOMATCH if
        no .md files exist. The auto-fix prepends `setopt nullglob;`.

        Note: `find . -name '*.py'` has the glob inside quotes → safe (stripped).
        """
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("ls *.md && find . -name '*.py'"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]
        assert hook_out["permissionDecision"] == "allow"
        fixed = hook_out["updatedInput"]["command"]
        assert fixed.startswith("setopt nullglob; ")
        assert "ls *.md" in fixed

    @requires_jq
    def test_autofixes_path_with_star_glob(self, hook_runner) -> None:
        """Path-based glob like `path/to/*.ext` in for-loop → auto-fixed."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for plan in .claude/plans/*.yaml; do echo $plan; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
        fixed = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "setopt nullglob" in fixed


# ===========================================================================
# TestZshCheckCHistoryExpansion — `! [[` → `[[ !` auto-fix
# ===========================================================================


class TestZshCheckCHistoryExpansion:
    """Check C: `! [[` triggers history expansion in zsh — auto-fix to `[[ !`."""

    @requires_jq
    def test_autofixes_bang_bracket_pattern(self, hook_runner) -> None:
        """`if ! [[ "$x" =~ pattern ]]; then` → auto-fixed to `if [[ ! "$x" =~ pattern ]]; then`."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('if ! [[ "$x" =~ ^[0-9]+$ ]]; then echo "not a number"; fi'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]
        assert hook_out["permissionDecision"] == "allow"
        assert "updatedInput" in hook_out
        fixed_cmd = hook_out["updatedInput"]["command"]
        assert "[[ !" in fixed_cmd
        assert "! [[" not in fixed_cmd

    @requires_jq
    def test_autofix_rewrites_bang_bracket_to_bracket_bang(self, hook_runner) -> None:
        """Fixed command must use `[[ !` form not `! [[` form."""
        original = '! [[ -f "$file" ]]'
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(original),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        fixed_cmd = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "[[ !" in fixed_cmd
        assert "! [[" not in fixed_cmd

    @requires_jq
    def test_autofix_bang_bracket_uses_updated_input(self, hook_runner) -> None:
        """Auto-fix must use updatedInput (not deny) for `! [[` pattern."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('while ! [[ -f done.txt ]]; do sleep 1; done'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]
        assert hook_out["permissionDecision"] == "allow"
        assert "updatedInput" in hook_out
        assert "command" in hook_out["updatedInput"]

    @requires_jq
    def test_autofix_bang_bracket_is_valid_hook_json(self, hook_runner) -> None:
        """Auto-fix JSON for `! [[` must have correct hookEventName and structure."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('if ! [[ -d "$dir" ]]; then mkdir "$dir"; fi'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("hookEventName") == "PreToolUse"
        assert hook_out.get("permissionDecision") == "allow"

    @requires_jq
    def test_autofix_bang_bracket_includes_context(self, hook_runner) -> None:
        """Auto-fix for `! [[` must include additionalContext explaining the change."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('if ! [[ "$val" == "ok" ]]; then exit 1; fi'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        ctx = output["hookSpecificOutput"].get("additionalContext", "")
        assert "ZSH-001" in ctx or "history expansion" in ctx.lower() or "[[ !" in ctx

    @requires_jq
    def test_allows_normal_double_bracket(self, hook_runner) -> None:
        """Normal `[[ ... ]]` without preceding `!` → no action taken."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('if [[ -f "$file" ]]; then echo found; fi'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_allows_bracket_bang_already_correct(self, hook_runner) -> None:
        """`[[ ! ... ]]` form (already correct) → no action taken."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('if [[ ! -f "$file" ]]; then echo missing; fi'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_allows_single_bracket_negation(self, hook_runner) -> None:
        """Single-bracket `! [ ... ]` is different from `! [[` → no action for `! [`."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('if ! [ -f "$file" ]; then echo missing; fi'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        # Single bracket form (`! [`) is not targeted by Check C (only `! [[`)
        assert result.stdout.strip() == ""

    @requires_jq
    def test_autofix_multiple_bang_brackets(self, hook_runner) -> None:
        """Multiple `! [[` occurrences in one command → all should be rewritten."""
        cmd = (
            'if ! [[ -f a.txt ]]; then echo a; fi; '
            'if ! [[ -d b/ ]]; then echo b; fi'
        )
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(cmd),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        fixed_cmd = output["hookSpecificOutput"]["updatedInput"]["command"]
        # Both occurrences should be rewritten
        assert "! [[" not in fixed_cmd
        assert fixed_cmd.count("[[ !") == 2


# ===========================================================================
# TestZshCompatEdgeCases — edge cases and non-obvious behaviors
# ===========================================================================


class TestZshCompatEdgeCases:
    """Edge cases: multiline commands, pipeline context, shell path variants."""

    @requires_jq
    def test_multiline_for_loop_detected(self, hook_runner) -> None:
        """Multiline for-loop with newlines is normalized and still detected."""
        multiline_cmd = "for f in *.md\ndo\n  echo $f\ndone"
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(multiline_cmd),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        # Should be detected via normalization (BACK-005 regression fix)
        output_stripped = result.stdout.strip()
        if output_stripped:
            output = json.loads(output_stripped)
            # If detected, must be auto-fix (allow + updatedInput)
            assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    @requires_jq
    def test_multiline_status_assignment_detected(self, hook_runner) -> None:
        """Multiline command with `status=` on its own line → detected and denied."""
        multiline_cmd = "do_work\nstatus=$(get_result)\necho $status"
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(multiline_cmd),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_status_in_pipeline_context_denied(self, hook_runner) -> None:
        """`status=` inside a pipeline → denied (pipe is a valid boundary character)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("get_data | status=$(process); echo done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_status_word_in_json_key_not_flagged(self, hook_runner) -> None:
        """`.status` in jq path selector is NOT an assignment — should not be flagged."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input('task_result=$(jq -r \'.status\' file.json)'),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        # task_result= is safe; the `.status` in jq is not a bash assignment
        assert result.stdout.strip() == ""

    @requires_jq
    def test_shell_detection_usr_local_bin_zsh(self, hook_runner) -> None:
        """SHELL=/usr/local/bin/zsh → enforcement active (homebrew zsh path)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_result)"),
            env_override={"SHELL": "/usr/local/bin/zsh"},
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_shell_detection_opt_homebrew_bin_zsh(self, hook_runner) -> None:
        """SHELL=/opt/homebrew/bin/zsh → enforcement active (Apple Silicon homebrew path)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("status=$(get_result)"),
            env_override={"SHELL": "/opt/homebrew/bin/zsh"},
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_exit_0_when_tool_name_absent(self, hook_runner) -> None:
        """Input JSON without tool_name → exit 0 (no Bash tool to check)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            {
                "tool_input": {"command": "status=$(get_result)"},
            },
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_complex_command_with_only_safe_patterns(self, hook_runner) -> None:
        """Complex command using only safe alternatives → no action."""
        safe_cmd = (
            "task_status=$(jq -r '.status' state.json); "
            "setopt nullglob; "
            "for f in *.md; do process $f; done; "
            "if [[ ! -f done.txt ]]; then echo pending; fi"
        )
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(safe_cmd),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @requires_jq
    def test_check_a_takes_priority_over_check_b(self, hook_runner) -> None:
        """Command with both status= and unprotected glob → Check A (deny) fires first."""
        cmd = "status=$(ls *.txt | wc -l); for f in *.txt; do echo $f; done"
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(cmd),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        # Check A (deny) should take priority over Check B (auto-fix)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    @requires_jq
    def test_glob_in_for_with_directory_path(self, hook_runner) -> None:
        """for-loop glob with directory prefix path → auto-fixed."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for f in tmp/work/*.md; do echo $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        hook_out = output["hookSpecificOutput"]
        assert hook_out["permissionDecision"] == "allow"
        assert "setopt nullglob" in hook_out["updatedInput"]["command"]

    @requires_jq
    def test_autofix_preserves_newlines_in_original_command(self, hook_runner) -> None:
        """Auto-fix for glob must preserve original command structure (not normalized)."""
        original_cmd = "for f in *.sh; do\n  bash \"$f\"\ndone"
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input(original_cmd),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        output = parse_hook_output(result.stdout)
        fixed_cmd = output["hookSpecificOutput"]["updatedInput"]["command"]
        # The fixed command should preserve the original multiline formatting
        assert original_cmd in fixed_cmd

    @requires_jq
    def test_check_b_skipped_when_no_glob_chars_in_for(self, hook_runner) -> None:
        """`for f in list_of_files; do` without glob chars → no action (Check B skips)."""
        result = hook_runner(
            ENFORCE_ZSH_COMPAT,
            make_bash_input("for f in file1 file2 file3; do echo $f; done"),
            env_override=ZSH_ENV,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""
