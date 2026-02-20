#!/bin/bash
# scripts/session-compact-recovery.sh
# Re-injects team state after context compaction using checkpoint saved by
# pre-compact-checkpoint.sh. Provides Claude with critical team context
# that would otherwise be lost during compaction.
#
# DESIGN PRINCIPLES:
#   1. Non-blocking — always exit 0 (session start must never be prevented)
#   2. One-time injection — checkpoint is deleted after successful recovery
#   3. Correlation guard — verifies team still exists before injecting
#   4. JSON output via jq --arg (no printf or shell interpolation)
#
# Hook events: SessionStart
# Matcher: compact
# Timeout: 5s
# Exit 0: Always (non-blocking)

set -euo pipefail
umask 077

# ── PW-002 FIX: Opt-in trace logging (consistent with on-task-completed.sh) ──
_trace() {
  [[ "${RUNE_TRACE:-}" == "1" ]] && echo "[compact-recovery] $*" >> /tmp/rune-hook-trace.log 2>/dev/null
  return 0
}

# ── GUARD 1: jq dependency ──
if ! command -v jq &>/dev/null; then
  echo "WARN: jq not found — compact recovery skipped" >&2
  exit 0
fi

# ── GUARD 2: Input size cap (SEC-2: 1MB DoS prevention) ──
INPUT=$(head -c 1048576)

# ── GUARD 3: Trigger must be "compact" ──
TRIGGER=$(echo "$INPUT" | jq -r '.trigger // empty' 2>/dev/null || true)
if [[ "$TRIGGER" != "compact" ]]; then
  exit 0
fi

# ── GUARD 4: CWD extraction and canonicalization ──
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then exit 0; fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
if [[ -z "$CWD" || "$CWD" != /* ]]; then exit 0; fi

# ── GUARD 5: Checkpoint file must exist ──
CHECKPOINT_FILE="${CWD}/tmp/.rune-compact-checkpoint.json"
if [[ ! -f "$CHECKPOINT_FILE" ]] || [[ -L "$CHECKPOINT_FILE" ]]; then
  exit 0
fi

# ── GUARD 6: Validate checkpoint JSON and read into variable (FW-003 FIX: single-read) ──
CHECKPOINT_DATA=$(jq -c '.' "$CHECKPOINT_FILE" 2>/dev/null) || {
  echo "WARN: Compact checkpoint is not valid JSON — skipping recovery" >&2
  rm -f "$CHECKPOINT_FILE" 2>/dev/null
  exit 0
}

# ── EXTRACT: team name from checkpoint ──
TEAM_NAME=$(echo "$CHECKPOINT_DATA" | jq -r '.team_name // empty' 2>/dev/null || true)
if [[ -z "$TEAM_NAME" ]]; then
  rm -f "$CHECKPOINT_FILE" 2>/dev/null
  exit 0
fi

# Validate team name (defense-in-depth)
if [[ ! "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ ${#TEAM_NAME} -gt 128 ]]; then
  rm -f "$CHECKPOINT_FILE" 2>/dev/null
  exit 0
fi

# PW-006 FIX: Prefix filter — only recover rune-*/arc-* teams (consistent with on-task-completed.sh)
if [[ "$TEAM_NAME" != rune-* ]] && [[ "$TEAM_NAME" != arc-* ]]; then
  rm -f "$CHECKPOINT_FILE" 2>/dev/null
  exit 0
fi

# ── CORRELATION GUARD: Verify team still exists ──
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [[ -z "$CHOME" ]] || [[ "$CHOME" != /* ]]; then
  rm -f "$CHECKPOINT_FILE" 2>/dev/null
  exit 0
fi

TEAM_DIR="$CHOME/teams/${TEAM_NAME}"
if [[ ! -d "$TEAM_DIR" ]] || [[ -L "$TEAM_DIR" ]]; then
  # Team no longer exists — checkpoint is stale, clean up
  rm -f "$CHECKPOINT_FILE" 2>/dev/null
  jq -n --arg team "$TEAM_NAME" '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: ("Rune compact checkpoint found for team " + $team + " but team no longer exists. Checkpoint discarded.")
    }
  }'
  exit 0
fi

_trace "Recovery: team=${TEAM_NAME} checkpoint=$CHECKPOINT_FILE"

# ── BUILD COMPACT SUMMARY ──
# Extract key fields for the summary (keep it concise for context injection)
SAVED_AT=$(echo "$CHECKPOINT_DATA" | jq -r '.saved_at // "unknown"' 2>/dev/null || echo "unknown")

# Task summary: count by status
TASK_SUMMARY=$(echo "$CHECKPOINT_DATA" | jq -r '
  .tasks // [] |
  group_by(.status // "unknown") |
  map("\(.[0].status // "unknown"): \(length)") |
  join(", ")
' 2>/dev/null || echo "unavailable")
[[ -z "$TASK_SUMMARY" ]] && TASK_SUMMARY="no tasks"
# FW-006 FIX: Strip newlines from TASK_SUMMARY to prevent string assignment issues
TASK_SUMMARY="${TASK_SUMMARY//$'\n'/ }"

# Workflow type and status
WORKFLOW_TYPE=$(echo "$CHECKPOINT_DATA" | jq -r '.workflow_state.workflow // .workflow_state.type // "unknown"' 2>/dev/null || echo "unknown")
WORKFLOW_STATUS=$(echo "$CHECKPOINT_DATA" | jq -r '.workflow_state.status // "unknown"' 2>/dev/null || echo "unknown")

# WS-004 FIX: Validate WORKFLOW_TYPE and WORKFLOW_STATUS (consistent with ARC_PHASE validation)
if [[ ! "$WORKFLOW_TYPE" =~ ^[a-zA-Z0-9_:\ -]+$ ]] || [[ ${#WORKFLOW_TYPE} -gt 64 ]]; then
  WORKFLOW_TYPE="unknown"
fi
if [[ ! "$WORKFLOW_STATUS" =~ ^[a-zA-Z0-9_:\ -]+$ ]] || [[ ${#WORKFLOW_STATUS} -gt 64 ]]; then
  WORKFLOW_STATUS="unknown"
fi

# Arc phase if present
ARC_PHASE=$(echo "$CHECKPOINT_DATA" | jq -r '.arc_checkpoint.current_phase // empty' 2>/dev/null || true)
# WS-002 FIX: Validate ARC_PHASE against character allowlist (closes prompt injection surface)
ARC_INFO=""
if [[ -n "$ARC_PHASE" ]] && [[ "$ARC_PHASE" =~ ^[a-zA-Z0-9_:\ -]+$ ]] && [[ ${#ARC_PHASE} -le 64 ]]; then
  ARC_INFO=" Arc phase: ${ARC_PHASE}."
fi

# Team member count
MEMBER_COUNT=$(echo "$CHECKPOINT_DATA" | jq -r '.team_config.members // [] | length' 2>/dev/null || echo "0")

# Build the context message — point to full file for detailed Read
CONTEXT_MSG="RUNE COMPACT RECOVERY: Team '${TEAM_NAME}' state restored (saved at ${SAVED_AT}). Members: ${MEMBER_COUNT}. Tasks: ${TASK_SUMMARY}. Workflow: ${WORKFLOW_TYPE} (${WORKFLOW_STATUS}).${ARC_INFO} Re-read team config and task list to resume coordination."

# ── OUTPUT: hookSpecificOutput with hookEventName ──
# PW-008 FIX: Output JSON first, THEN delete checkpoint. If jq fails, checkpoint is preserved.
jq -n --arg ctx "$CONTEXT_MSG" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: $ctx
  }
}'

# ── DELETE CHECKPOINT (one-time recovery — after successful output) ──
rm -f "$CHECKPOINT_FILE" 2>/dev/null
exit 0
