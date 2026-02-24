#!/bin/bash
# scripts/enforce-polling.sh
# POLL-001: Enforce monitoring loop fidelity during active Rune workflows.
# Blocks sleep+echo anti-pattern (sleep N && echo ...) that skips TaskList
# and provides zero visibility into task progress.
#
# Detection strategy:
#   1. Fast-path: skip if command doesn't contain "sleep"
#   2. Normalize multiline commands (newline -> space)
#   3. Pattern match: sleep N <chain-op> echo/printf
#      Catches: && and ; separators + echo and printf variants
#   4. Threshold: only block sleep >= 10s (tiny sleeps are startup probes)
#   5. Check for active Rune workflow via state files
#   6. Block if anti-pattern detected during active workflow
#
# Exit 0 with hookSpecificOutput.permissionDecision="deny" JSON = tool call blocked.
# Exit 0 without JSON = tool call allowed.

set -euo pipefail
umask 077

# Pre-flight: jq is required for JSON parsing.
# If missing, exit 0 (non-blocking) — allow rather than crash.
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — enforce-polling.sh hook is inactive" >&2
  exit 0
fi

INPUT=$(head -c 1048576)  # SEC-2: 1MB cap to prevent unbounded stdin read

TOOL_NAME=$(printf '%s\n' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

CWD=$(printf '%s\n' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
if [[ -z "$CWD" || "$CWD" != /* ]]; then exit 0; fi

COMMAND=$(printf '%s\n' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# Fast-path: skip if no sleep in command
case "$COMMAND" in *sleep*) ;; *) exit 0 ;; esac

# Normalize multiline commands (catches newline-separated sleep/echo)
NORMALIZED=$(printf '%s\n' "$COMMAND" | tr '\n' ' ')

# Pre-filter: skip if command is a simple echo/printf/cat/grep WITHOUT chain operators.
# Known limitation: regex cannot distinguish shell quoting context. Commands that *mention*
# the anti-pattern in string literals (e.g., echo "sleep 30 && echo poll") would false-positive.
# This pre-filter catches the most common case, but ONLY when no chain operator is present —
# a chained command like "echo setup && sleep 30 && echo poll" must still be checked.
case "$NORMALIZED" in
  echo\ *|printf\ *|cat\ *|grep\ *)
    # Only skip if no chain operator that could hide a sleep+echo anti-pattern
    case "$NORMALIZED" in
      *"&&"*|*";"*) ;; # Contains chain operator — fall through to regex check
      *) exit 0 ;;     # Simple command — safe to skip
    esac
    ;;
esac

# Detection: sleep + echo/printf pattern
# Catches && and ; separators + echo and printf variants
# NOTE: || excluded — "sleep N || echo" is error fallback, not polling anti-pattern
# SEC-002 FIX: Word boundary — (^|[[:space:];|&(]) anchors "sleep" to prevent
# matching substrings like "nosleep" in variable/function names.
if printf '%s\n' "$NORMALIZED" | grep -qE '(^|[[:space:];|&(])sleep[[:space:]]+[0-9]+[[:space:]]*(&&|;)[[:space:]]*(echo|printf)'; then
  # Threshold: only block sleep >= 10s (startup probes use sleep 1-5)
  # Extract the sleep value specifically from the anti-pattern match (sleep N && echo / sleep N ; echo)
  # not just the first sleep token in the command — avoids bypass via "sleep 1 && setup; sleep 60 && echo poll"
  SLEEP_NUM=$(printf '%s\n' "$NORMALIZED" | grep -oE 'sleep[[:space:]]+[0-9]+[[:space:]]*(&&|;)[[:space:]]*(echo|printf)' | grep -oE 'sleep[[:space:]]+[0-9]+' | head -1 | grep -oE '[0-9]+')
  [[ "${SLEEP_NUM:-0}" -lt 10 ]] && exit 0

  # Check for active Rune workflow (THIS session only)
  active_workflow=""

  # ── Session identity for cross-session ownership filtering ──
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source=resolve-session-identity.sh
  source "${SCRIPT_DIR}/resolve-session-identity.sh"

  # Arc checkpoint detection
  if [[ -d "${CWD}/.claude/arc" ]]; then
    while IFS= read -r f; do
      # SEC-4 FIX: Use jq for precise field extraction instead of grep substring match
      phase_status=$(jq -r '.phase_status // .status // empty' "$f" 2>/dev/null || true)
      if [[ "$phase_status" == "in_progress" ]]; then
        # ── Ownership filter: skip checkpoints from other sessions ──
        stored_cfg=$(jq -r '.config_dir // empty' "$f" 2>/dev/null || true)
        stored_pid=$(jq -r '.owner_pid // empty' "$f" 2>/dev/null || true)
        if [[ -n "$stored_cfg" && "$stored_cfg" != "$RUNE_CURRENT_CFG" ]]; then continue; fi
        if [[ -n "$stored_pid" && "$stored_pid" =~ ^[0-9]+$ && "$stored_pid" != "$PPID" ]]; then
          kill -0 "$stored_pid" 2>/dev/null && continue  # alive = different session
        fi
        active_workflow="arc"
        break
      fi
    done < <(find "${CWD}/.claude/arc" -name checkpoint.json -maxdepth 2 -type f 2>/dev/null)
  fi

  # State file detection — all 8 workflow types
  if [[ -z "$active_workflow" ]]; then
    shopt -s nullglob
    for f in "${CWD}"/tmp/.rune-review-*.json "${CWD}"/tmp/.rune-audit-*.json \
             "${CWD}"/tmp/.rune-work-*.json "${CWD}"/tmp/.rune-mend-*.json \
             "${CWD}"/tmp/.rune-plan-*.json "${CWD}"/tmp/.rune-forge-*.json \
             "${CWD}"/tmp/.rune-inspect-*.json "${CWD}"/tmp/.rune-goldmask-*.json; do
      if [[ ! -f "$f" ]]; then continue; fi
      # SEC-4 FIX: Use jq for precise status extraction instead of grep substring match
      file_status=$(jq -r '.status // empty' "$f" 2>/dev/null || true)
      if [[ "$file_status" == "active" ]]; then
        # ── Ownership filter: skip state files from other sessions ──
        stored_cfg=$(jq -r '.config_dir // empty' "$f" 2>/dev/null || true)
        stored_pid=$(jq -r '.owner_pid // empty' "$f" 2>/dev/null || true)
        if [[ -n "$stored_cfg" && "$stored_cfg" != "$RUNE_CURRENT_CFG" ]]; then continue; fi
        if [[ -n "$stored_pid" && "$stored_pid" =~ ^[0-9]+$ && "$stored_pid" != "$PPID" ]]; then
          kill -0 "$stored_pid" 2>/dev/null && continue  # alive = different session
        fi
        active_workflow=1
        break
      fi
    done
    shopt -u nullglob
  fi

  if [[ -n "$active_workflow" ]]; then
    cat <<'DENY_JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "POLL-001: Blocked sleep+echo monitoring anti-pattern during active Rune workflow. This pattern skips TaskList and provides zero progress visibility.",
    "additionalContext": "CORRECT monitoring loop: (1) Call TaskList tool, (2) Count completed tasks, (3) Log progress, (4) Check if all done, (5) Check stale tasks, (6) Bash('sleep ${pollIntervalMs/1000}'). Derive sleep interval from per-command pollIntervalMs config — see monitor-utility.md configuration table for exact values. NEVER use 'sleep N && echo poll check' — it bypasses the entire monitoring contract."
  }
}
DENY_JSON
    exit 0
  fi
fi

exit 0
