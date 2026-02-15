#!/bin/bash
# scripts/on-task-completed.sh
# Writes signal files for Rune task completion detection.
# Called by Claude Code's TaskCompleted hook for EVERY task completion —
# including non-Rune tasks (TodoWrite, etc.). Must be fast and safe to no-op.

set -euo pipefail
umask 077

# Pre-flight: jq is required for safe JSON parsing and construction.
# If missing, exit 0 (non-blocking) with a warning on stderr.
if ! command -v jq &>/dev/null; then
  echo "WARN: jq not found — signal files will not be written. Install jq for Phase 2 event-driven sync." >&2
  exit 0
fi

# Read hook input from stdin
INPUT=$(cat)

# Extract fields with safe defaults
TEAM_NAME=$(echo "$INPUT" | jq -r '.team_name // empty' 2>/dev/null || true)
TASK_ID=$(echo "$INPUT" | jq -r '.task_id // empty' 2>/dev/null || true)
TEAMMATE_NAME=$(echo "$INPUT" | jq -r '.teammate_name // empty' 2>/dev/null || true)
TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject // empty' 2>/dev/null || true)

# Guard: skip non-team tasks (TodoWrite, etc. have no team_name)
if [[ -z "$TEAM_NAME" || -z "$TASK_ID" ]]; then
  exit 0
fi

# Guard: only process Rune teams (rune-review-*, rune-work-*, rune-plan-*, etc.)
if [[ "$TEAM_NAME" != rune-* ]]; then
  exit 0
fi

# Guard: validate team name against safe characters (prevent path traversal)
if [[ ! "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  exit 0
fi

# Guard: validate team name length
if [[ ${#TEAM_NAME} -gt 128 ]]; then
  exit 0
fi

# Guard: validate task ID against safe characters
if [[ ! "$TASK_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  exit 0
fi

# Derive absolute path from hook input CWD (not relative — CWD is not guaranteed)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi

# Signal directory — created by orchestrator before spawning agents
SIGNAL_DIR="${CWD}/tmp/.rune-signals/${TEAM_NAME}"

# Guard: if signal dir doesn't exist, orchestrator didn't set up signals
# (e.g., Phase 1 monitor utility without Phase 2 hooks). Exit silently.
if [[ ! -d "$SIGNAL_DIR" ]]; then
  exit 0
fi

# Write signal file — atomic via temp + mv, safe JSON via jq
SIGNAL_FILE="${SIGNAL_DIR}/${TASK_ID}.done"
TEMP_FILE="${SIGNAL_FILE}.tmp.$$"
jq -n --arg tid "$TASK_ID" --arg tn "$TEAMMATE_NAME" --arg ts "$TASK_SUBJECT" \
  --arg ca "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{task_id: $tid, teammate: $tn, subject: $ts, completed_at: $ca}' > "$TEMP_FILE"
mv "$TEMP_FILE" "$SIGNAL_FILE"

# Check if all expected tasks are complete
EXPECTED_FILE="${SIGNAL_DIR}/.expected"
if [[ ! -f "$EXPECTED_FILE" ]]; then
  exit 0
fi

EXPECTED=$(cat "$EXPECTED_FILE" 2>/dev/null || echo "0")
# Validate numeric
if [[ ! "$EXPECTED" =~ ^[0-9]+$ ]]; then
  exit 0
fi

# Count .done files (excluding .tmp files)
DONE_COUNT=$(find "$SIGNAL_DIR" -maxdepth 1 -name "*.done" -not -name "*.tmp.*" 2>/dev/null | wc -l | tr -d ' ')

# Write .all-done sentinel when all tasks complete — atomic via temp + mv
if [[ "$DONE_COUNT" -ge "$EXPECTED" ]]; then
  ALL_DONE_TEMP="${SIGNAL_DIR}/.all-done.tmp.$$"
  jq -n --argjson total "$DONE_COUNT" --argjson expected "$EXPECTED" \
    --arg ca "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{total: $total, expected: $expected, completed_at: $ca}' > "$ALL_DONE_TEMP"
  mv "$ALL_DONE_TEMP" "${SIGNAL_DIR}/.all-done"
fi

exit 0
