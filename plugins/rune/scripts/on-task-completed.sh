#!/bin/bash
# scripts/on-task-completed.sh
# Writes signal files for Rune task completion detection.
# Called by Claude Code's TaskCompleted hook for EVERY task completion —
# including non-Rune tasks (TodoWrite, etc.). Must be fast and safe to no-op.

set -euo pipefail
umask 077

# Cleanup trap — remove temp files on exit (BACK-002)
cleanup() { [[ -z "${SIGNAL_DIR:-}" ]] && return; rm -f "${SIGNAL_DIR}/${TASK_ID:-unknown}.done.tmp.$$" "${SIGNAL_DIR}/.all-done.tmp.$$" 2>/dev/null; }
trap cleanup EXIT

# Pre-flight: jq is required for safe JSON parsing and construction.
# If missing, exit 0 (non-blocking) with a warning on stderr.
if ! command -v jq &>/dev/null; then
  echo "WARN: jq not found — signal files will not be written. Install jq for Phase 2 event-driven sync." >&2
  exit 0
fi

# Read hook input from stdin
INPUT=$(cat)

# BACK-101: Validate JSON before attempting field extraction
if ! echo "$INPUT" | jq empty 2>/dev/null; then
  echo "WARN: Hook input is not valid JSON — signal file will not be written" >&2
  exit 0
fi

# Extract fields with safe defaults
# NOTE(QUAL-003): Separate jq calls are intentional — avoids eval and keeps each
# extraction independently safe. The DRY trade-off is accepted for clarity and safety.
TEAM_NAME=$(echo "$INPUT" | jq -r '.team_name // empty' 2>/dev/null || true)
TASK_ID=$(echo "$INPUT" | jq -r '.task_id // empty' 2>/dev/null || true)
TEAMMATE_NAME=$(echo "$INPUT" | jq -r '.teammate_name // empty' 2>/dev/null || true)
TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject // empty' 2>/dev/null || true)
# SEC-C05: Truncate subject to prevent oversized values in signal files
TASK_SUBJECT="${TASK_SUBJECT:0:256}"
# BACK-012: Default empty subject
[[ -z "$TASK_SUBJECT" ]] && TASK_SUBJECT="Task $TASK_ID"

# Guard: skip non-team tasks (TodoWrite, etc. have no team_name)
if [[ -z "$TEAM_NAME" || -z "$TASK_ID" ]]; then
  exit 0
fi

# Guard: only process Rune teams (rune-review-*, rune-work-*, rune-plan-*, arc-*, etc.)
if [[ "$TEAM_NAME" != rune-* && "$TEAM_NAME" != arc-* ]]; then
  exit 0
fi

# QUAL-002: Validation order is intentional — emptiness checks first (cheap bail-out),
# then prefix match, then character-set and length validation.
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
# BACK-009: Add warning when CWD is missing
if [[ -z "$CWD" ]]; then
  echo "WARN: TaskCompleted hook input missing 'cwd' field" >&2
  exit 0
fi

# SEC-002: Canonicalize CWD after extraction
CWD=$(cd "$CWD" 2>/dev/null && pwd -P || echo "$CWD")
if [[ -z "$CWD" || "$CWD" != /* ]]; then
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

# SEC-001: Extract date command to shell variable before passing to jq
COMPLETED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# BACK-002: Wrap jq+mv in error handler
if ! jq -n --arg tid "$TASK_ID" --arg tn "$TEAMMATE_NAME" --arg ts "$TASK_SUBJECT" \
  --arg ca "$COMPLETED_AT" \
  '{task_id: $tid, teammate: $tn, subject: $ts, completed_at: $ca}' > "$TEMP_FILE" 2>/dev/null; then
  echo "ERROR: Failed to write signal file for task ${TASK_ID}" >&2
  rm -f "$TEMP_FILE" 2>/dev/null
  exit 0
fi

# SEC-003: Use mv -n (noclobber)
mv -n "$TEMP_FILE" "$SIGNAL_FILE" 2>/dev/null || { rm -f "$TEMP_FILE"; exit 0; }

# Check if all expected tasks are complete
EXPECTED_FILE="${SIGNAL_DIR}/.expected"
if [[ ! -f "$EXPECTED_FILE" ]]; then
  exit 0
fi

# BACK-005: Strengthen .expected validation
# SEC-004: .expected is write-once by the orchestrator before agents spawn — no real TOCTOU risk.
EXPECTED=$(head -c 4 "$EXPECTED_FILE" 2>/dev/null | tr -d '[:space:]')
if [[ ! "$EXPECTED" =~ ^[1-9][0-9]*$ ]]; then
  echo "WARN: .expected file contains invalid count: ${EXPECTED}" >&2
  exit 0
fi

# Count .done files (excluding .tmp files)
DONE_COUNT=$(find "$SIGNAL_DIR" -maxdepth 1 -type f -name "*.done" -not -name "*.tmp.*" 2>/dev/null | wc -l | tr -d ' ')

# BACK-001: Add existence check before writing .all-done to prevent double-write race.
# Note: total is a lower bound — concurrent completions may increment .done count between
# our find and the jq write (TOCTOU), but mv -n prevents double-write so this is benign.
if [[ "$DONE_COUNT" -ge "$EXPECTED" ]] && [[ ! -f "${SIGNAL_DIR}/.all-done" ]]; then
  ALL_DONE_TEMP="${SIGNAL_DIR}/.all-done.tmp.$$"

  # SEC-001: Extract date command to shell variable (same as above)
  COMPLETED_AT_ALL=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # BACK-002: Wrap jq+mv in error handler (mirrors lines 88-94)
  if ! jq -n --argjson total "$DONE_COUNT" --argjson expected "$EXPECTED" \
    --arg ca "$COMPLETED_AT_ALL" \
    '{total: $total, expected: $expected, completed_at: $ca}' > "$ALL_DONE_TEMP" 2>/dev/null; then
    rm -f "$ALL_DONE_TEMP" 2>/dev/null
    exit 0
  fi

  # SEC-003: Use mv -n (noclobber)
  mv -n "$ALL_DONE_TEMP" "${SIGNAL_DIR}/.all-done" 2>/dev/null || rm -f "$ALL_DONE_TEMP"
fi

exit 0
