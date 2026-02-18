#!/bin/bash
# scripts/enforce-zsh-compat.sh
# ZSH-001: Block zsh-incompatible patterns in Bash commands.
# macOS uses zsh as the default shell. Two common zsh pitfalls:
#
# (A) Read-only variable assignment:
#     zsh has read-only special variables (status, pipestatus, ERRNO, signals).
#     `status=$(...)` fails with: (eval):N: read-only variable: status
#
# (B) Unprotected glob in for-loops:
#     In bash, `for f in *.nothing; do` silently loops with literal string.
#     In zsh, it throws: no matches found: *.nothing (NOMATCH option, on by default).
#     Fix: use `(N)` qualifier or `setopt nullglob` before the glob.
#
# Detection strategy:
#   1. Shell detection: skip if user's shell is not zsh
#   2. Fast-path: skip if command doesn't contain any target patterns
#   3. Check A: bare `status=` assignment (not `task_status=`, etc.)
#   4. Check B: `for VAR in GLOB; do` without nullglob protection
#   5. Block with actionable fix suggestion
#
# Only active when user's shell is zsh — these are valid patterns in bash.
#
# Exit 0 with hookSpecificOutput.permissionDecision="deny" JSON = tool call blocked.
# Exit 0 without JSON = tool call allowed.

set -euo pipefail
umask 077

# Shell detection: only enforce when zsh is the user's shell.
# Claude Code's Bash tool inherits $SHELL, so commands execute under the user's default shell.
# Logic:
#   - $SHELL contains "zsh"  → enforce (user uses zsh)
#   - $SHELL set, not "zsh"  → skip (user explicitly chose bash/fish/etc.)
#   - $SHELL unset + macOS   → enforce (zsh is macOS default since Catalina)
#   - $SHELL unset + Linux   → skip (bash is typical default)
if [[ -n "${SHELL:-}" ]]; then
  # $SHELL is set — check if it's zsh
  case "$SHELL" in *zsh*) ;; *) exit 0 ;; esac
else
  # $SHELL is unset — only enforce on macOS where zsh is the default
  if [[ "$(uname -s 2>/dev/null)" != "Darwin" ]]; then
    exit 0
  fi
fi

# Pre-flight: jq is required for JSON parsing.
# If missing, exit 0 (non-blocking) — allow rather than crash.
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — enforce-zsh-compat.sh hook is inactive" >&2
  exit 0
fi

INPUT=$(head -c 1048576)  # SEC-2: 1MB cap to prevent unbounded stdin read

TOOL_NAME=$(printf '%s\n' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

COMMAND=$(printf '%s\n' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# Normalize multiline commands BEFORE fast-path (BACK-005: multiline for-loops missed)
NORMALIZED=$(printf '%s\n' "$COMMAND" | tr '\n' ' ')

# Fast-path: skip if none of the target patterns appear (operates on normalized input)
has_status_assign=""
has_for_glob=""
case "$NORMALIZED" in *status=*) has_status_assign=1 ;; esac
# BACK-005: Also detect `?` glob character (zsh NOMATCH-triggering)
case "$NORMALIZED" in *for*in*[*?]*do*) has_for_glob=1 ;; esac

if [[ -z "$has_status_assign" && -z "$has_for_glob" ]]; then
  exit 0
fi

# ─── Check A: bare `status=` assignment ───────────────────────────────────────
# Anchored to: start of string, whitespace, semicolon, pipe, ampersand, parenthesis,
# or shell keywords (local, export, declare, readonly, typeset)
#
# The boundary anchor (^|[[:space:];|&(]) ensures that `task_status=`, `exit_status=`,
# `http_status=` etc. do NOT match — the character before `status` in those cases is
# `_` which is not in the boundary set. Only bare `status=` at a shell word boundary matches.
#
# Matches: status=$(...) | local status= | export status= | ;status= | &&status=
# Skips:   task_status= | exit_status= | http_status= | diff_status=
if [[ -n "$has_status_assign" ]]; then
  if printf '%s\n' "$NORMALIZED" | grep -qE '(^|[[:space:];|&(])(local[[:space:]]+|export[[:space:]]+|declare[[:space:]]+|readonly[[:space:]]+|typeset[[:space:]]+)?status='; then
    cat << 'DENY_JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "ZSH-001: Blocked assignment to `status` — this is a read-only built-in variable in zsh (macOS default shell). The command will fail with '(eval):N: read-only variable: status'.",
    "additionalContext": "FIX: Rename the variable. Use `task_status`, `tstat`, `wf_status`, or `completion_status` instead of `status`. Example: task_status=$(jq -r '.status' \"$f\") instead of status=$(jq -r '.status' \"$f\"). Other zsh read-only variables to avoid: pipestatus, ERRNO, signals."
  }
}
DENY_JSON
    exit 0
  fi
fi

# ─── Check B: unprotected glob in for-loop ────────────────────────────────────
# In zsh, `for f in path/*.ext; do` throws "no matches found" if no files match.
# Bash silently expands to the literal string — zsh aborts with NOMATCH (default on).
#
# Detection: `for VAR in <something-with-*>; do` or `for VAR in <something-with-?>; do`
# without nullglob protection.
#
# Nullglob protection patterns (any of these = safe):
#   - `(N)` glob qualifier: `for f in *.md(N); do`
#   - `setopt nullglob` or `setopt NULL_GLOB` before the for-loop
#   - `shopt -s nullglob` (bash compat, also works in zsh with emulation)
#
# Skips: globs inside quotes, globs in non-for contexts (find, ls, etc.)
if [[ -n "$has_for_glob" ]]; then
  # Extract the glob portion: `for VAR in GLOB; do`
  # This regex captures the text between "in" and "; do" or ";do"
  glob_text=$(printf '%s\n' "$NORMALIZED" | grep -oE 'for[[:space:]]+[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]+in[[:space:]]+[^;]+;[[:space:]]*do' | head -1 || true)
  if [[ -n "$glob_text" ]]; then
    # Check if the glob portion contains * or ? (actual glob characters)
    in_portion=$(printf '%s\n' "$glob_text" | sed 's/.*[[:space:]]in[[:space:]]//' | sed 's/;[[:space:]]*do$//')
    if printf '%s\n' "$in_portion" | grep -qE '[*?]'; then
      # Check for nullglob protection
      has_protection=""
      # (N) qualifier right before ; do
      if printf '%s\n' "$in_portion" | grep -qE '\(N\)'; then
        has_protection=1
      fi
      # setopt nullglob / setopt NULL_GLOB anywhere in command
      if printf '%s\n' "$NORMALIZED" | grep -qiE 'setopt[[:space:]]+(nullglob|null_glob)'; then
        has_protection=1
      fi
      # shopt -s nullglob anywhere in command
      if printf '%s\n' "$NORMALIZED" | grep -qE 'shopt[[:space:]]+-s[[:space:]]+nullglob'; then
        has_protection=1
      fi

      if [[ -z "$has_protection" ]]; then
        cat << 'DENY_JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "ZSH-001: Blocked unprotected glob in for-loop — zsh's NOMATCH option (on by default) will abort with 'no matches found' if the glob matches no files.",
    "additionalContext": "FIX: Add nullglob protection. Three options:\n  1. (N) qualifier: for f in path/*.md(N); do ...\n  2. setopt nullglob before the loop: setopt nullglob; for f in path/*.md; do ...\n  3. Existence check: if compgen -G 'path/*.md' >/dev/null 2>&1; then for f in path/*.md; do ...\nThe (N) qualifier is preferred — it's zsh-native and scoped to one glob."
  }
}
DENY_JSON
        exit 0
      fi
    fi
  fi
fi

exit 0
