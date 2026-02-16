#!/bin/bash
# scripts/enforce-readonly.sh
# SEC-001: Enforce read-only for review/audit Ashes at platform level.
# Blocks Write/Edit/Bash/NotebookEdit when a review/audit team is active
# and the caller is a subagent (not the team lead).
#
# Detection strategy (PreToolUse does NOT receive team_name):
#   1. Check transcript_path for /subagents/ — team leads are never blocked
#   2. Check for .readonly-active marker in review/audit signal directories
#
# Exit 0 with deny JSON = blocked. Exit 0 without JSON = allowed.

set -euo pipefail
umask 077

# Pre-flight: jq is required for JSON parsing.
# If missing, exit 0 (non-blocking) — allow rather than crash.
if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)

# Fast path: if not a subagent, allow immediately.
# Team leads and direct user sessions have transcript paths at root level,
# not in the /subagents/ subdirectory.
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)
if [[ -z "$TRANSCRIPT_PATH" ]] || [[ "$TRANSCRIPT_PATH" != */subagents/* ]]; then
  exit 0
fi

# Subagent detected — check if any review/audit team has a readonly marker.
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi

SIGNAL_BASE="${CWD}/tmp/.rune-signals"
if [[ ! -d "$SIGNAL_BASE" ]]; then
  exit 0
fi

# Scan for .readonly-active marker in review/audit signal directories.
# Only rune-review-*, arc-review-*, rune-audit-*, arc-audit-* teams create this marker.
# Work teams (rune-work-*) and mend teams (rune-mend-*) do NOT have this marker.
for dir in "$SIGNAL_BASE"/rune-review-* "$SIGNAL_BASE"/arc-review-* \
           "$SIGNAL_BASE"/rune-audit-* "$SIGNAL_BASE"/arc-audit-*; do
  if [[ -f "${dir}/.readonly-active" ]] 2>/dev/null; then
    # Active review/audit team found + caller is a subagent → deny
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SEC-001: review/audit Ashes are read-only. Use Read, Glob, Grep only."}}'
    exit 0
  fi
done

# No active review/audit team with readonly marker — allow
exit 0
