#!/bin/bash
# scripts/guard-context-critical.sh
# CTX-GUARD-001: Blocks TeamCreate and Task at critical context levels.
# Uses the statusline bridge file (/tmp/rune-ctx-{SESSION_ID}.json) as data source.
# Hard deny at critical threshold (default: 25% remaining / 75% used).
# Explore/Plan agent types exempt (Task tool only — TeamCreate always checked per EC-4).
# Fail-open: any error → exit 0 (allow tool).
#
# BD-2 tension: This hook uses hard-block (deny) but fail-open on dependencies
# (no jq → allow, no bridge → allow, stale bridge → allow). This is intentional:
# blocking on missing data is worse than allowing at critical context.

set -euo pipefail

# --- Fail-open wrapper ---
_fail_open() { exit 0; }
trap '_fail_open' ERR

# --- Guard: jq dependency ---
command -v jq >/dev/null 2>&1 || exit 0

# --- Guard: Input size cap (SEC-2) ---
INPUT=$(head -c 65536)
[[ -z "$INPUT" ]] && exit 0

# --- Single-pass jq extraction (performance: runs on EVERY TeamCreate/Task) ---
read -r TOOL_NAME SUBAGENT_TYPE CWD SESSION_ID < <(
  echo "$INPUT" | jq -r '[.tool_name//"", .tool_input.subagent_type//"", .cwd//"", .session_id//""] | @tsv' 2>/dev/null || echo ""
) || true

[[ -z "$TOOL_NAME" || -z "$CWD" || -z "$SESSION_ID" ]] && exit 0

# --- Guard: Teammate bypass (subagents can't spawn teams) ---
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)
if [[ -n "$TRANSCRIPT_PATH" && "$TRANSCRIPT_PATH" == *"/subagents/"* ]]; then
  exit 0
fi

# --- SESSION_ID validation ---
if [[ ! "$SESSION_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  exit 0
fi

# --- Session identity ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=resolve-session-identity.sh
source "${SCRIPT_DIR}/resolve-session-identity.sh"

# --- Explore/Plan exemption (Task tool only, NOT TeamCreate per EC-4) ---
if [[ "$TOOL_NAME" == "Task" ]]; then
  case "$SUBAGENT_TYPE" in
    Explore|Plan) exit 0 ;;  # Read-only agents — minimal context cost
  esac
fi

# --- Read bridge file ---
BRIDGE_FILE="/tmp/rune-ctx-${SESSION_ID}.json"

# Bridge must exist
[[ -f "$BRIDGE_FILE" ]] || exit 0

# Symlink guard
[[ -L "$BRIDGE_FILE" ]] && exit 0

# OS-level UID check (EC-H5)
BRIDGE_UID=""
if [[ "$(uname)" == "Darwin" ]]; then
  BRIDGE_UID=$(stat -f %u "$BRIDGE_FILE" 2>/dev/null || true)
else
  BRIDGE_UID=$(stat -c %u "$BRIDGE_FILE" 2>/dev/null || true)
fi
if [[ -n "$BRIDGE_UID" && "$BRIDGE_UID" != "$(id -u)" ]]; then
  exit 0  # Not our file
fi

# --- Bridge freshness (30s for blocking guard per EC-1) ---
STALE_SECONDS=30
if [[ "$(uname)" == "Darwin" ]]; then
  FILE_MTIME=$(stat -f %m "$BRIDGE_FILE" 2>/dev/null || echo 0)
else
  FILE_MTIME=$(stat -c %Y "$BRIDGE_FILE" 2>/dev/null || echo 0)
fi
NOW=$(date +%s)
AGE=$(( NOW - FILE_MTIME ))

# Future timestamp guard (spoofed timestamp)
[[ "$AGE" -lt 0 ]] && exit 0

# Stale bridge → allow
[[ "$AGE" -ge "$STALE_SECONDS" ]] && exit 0

# --- Parse bridge data ---
read -r BRIDGE_CFG BRIDGE_PID REM_INT < <(
  jq -r '[.config_dir//"", .owner_pid//"", (.remaining_percentage // -1 | tostring)] | @tsv' "$BRIDGE_FILE" 2>/dev/null || echo ""
) || true

# --- Session ownership check ---
if [[ -n "$BRIDGE_CFG" && "$BRIDGE_CFG" != "$RUNE_CURRENT_CFG" ]]; then
  exit 0  # Foreign bridge
fi

if [[ -n "$BRIDGE_PID" && "$BRIDGE_PID" =~ ^[0-9]+$ && "$BRIDGE_PID" != "$PPID" ]]; then
  if kill -0 "$BRIDGE_PID" 2>/dev/null; then
    exit 0  # Different live session
  else
    # Orphaned bridge — cleanup and allow
    rm -f "$BRIDGE_FILE" 2>/dev/null
    exit 0
  fi
fi

# --- Validate remaining_percentage ---
[[ -z "$REM_INT" || ! "$REM_INT" =~ ^[0-9]+$ ]] && exit 0
# Clamp to valid range (bogus bridge data → fail-open)
[[ "$REM_INT" -gt 100 ]] && exit 0

# --- Threshold check ---
# Default: 25% remaining. Configurable via talisman (not read here — hooks are fast).
CRITICAL_THRESHOLD=25

# Clamp threshold to [10, 50] range
[[ "$CRITICAL_THRESHOLD" -lt 10 ]] && CRITICAL_THRESHOLD=10
[[ "$CRITICAL_THRESHOLD" -gt 50 ]] && CRITICAL_THRESHOLD=50

# Above threshold → allow silently
if [[ "$REM_INT" -gt "$CRITICAL_THRESHOLD" ]]; then
  exit 0
fi

# --- DENY: Context at critical level ---
USED_PCT=$(( 100 - REM_INT ))

jq -n \
  --arg reason "Context at ${USED_PCT}% (${REM_INT}% remaining). Spawning new agents risks session freeze. Finish current work, then start fresh." \
  --arg ctx "BLOCKED by guard-context-critical.sh. Escape hatches: (1) /rune:rest to free artifacts, (2) talisman: context_monitor.pretooluse_guard.enabled: false, (3) Explore/Plan agents remain available for read-only research." \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason, additionalContext: $ctx}}' 2>/dev/null || true

exit 0
