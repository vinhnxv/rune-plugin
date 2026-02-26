#!/bin/bash
# scripts/arc-result-signal-writer.sh
# PostToolUse:Write|Edit hook — deterministic arc completion signal writer.
#
# Fires on EVERY Write/Edit tool call. Fast-path exits in < 5ms for non-checkpoint
# writes (grep check). Only triggers full logic when:
#   1. Written file is an arc checkpoint (*/checkpoint.json under .claude/arc/ or tmp/arc/)
#   2. Checkpoint shows ship or merge phase completed
#
# Writes: tmp/arc-result-current.json (deterministic path, session-scoped)
# Read by: arc-batch-stop-hook.sh, arc-issues-stop-hook.sh via _read_arc_result_signal()
#
# ARCHITECTURE (v1.109.2): Replaces LLM-instructed signal write with deterministic hook.
# Arc pipeline writes checkpoint → this hook detects completion → writes signal.
# Stop hooks read signal (primary) → checkpoint scan (fallback).
#
# EXIT BEHAVIOR: Always exit 0 (non-blocking PostToolUse — fail-open).
# TIMEOUT: 5s (fast — single file read + atomic write).
# DEPENDENCIES: jq

set -euo pipefail
trap 'exit 0' ERR

# ── GUARD 0: jq dependency ──
command -v jq &>/dev/null || exit 0

# ── GUARD 1: Fast-path — skip if stdin doesn't mention checkpoint.json ──
# This avoids jq parsing entirely for 99.9% of Write/Edit calls (< 5ms exit).
INPUT=$(head -c 1048576 2>/dev/null || true)
echo "$INPUT" | grep -q 'checkpoint\.json' || exit 0

# ── GUARD 2: Extract file path from tool_input ──
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[[ -n "$FILE_PATH" ]] || exit 0

# ── GUARD 3: Is this an arc checkpoint file? ──
# Match: .claude/arc/*/checkpoint.json OR tmp/arc/*/checkpoint.json
case "$FILE_PATH" in
  */.claude/arc/*/checkpoint.json) ;;
  */tmp/arc/*/checkpoint.json) ;;
  *) exit 0 ;;
esac

# ── GUARD 4: File exists and is not symlink ──
[[ -f "$FILE_PATH" ]] && [[ ! -L "$FILE_PATH" ]] || exit 0

# ── GUARD 5: Check if ship or merge phase is completed ──
# Only write signal on arc COMPLETION, not mid-pipeline checkpoint updates.
_SHIP_STATUS=$(jq -r '.phases.ship.status // "pending"' "$FILE_PATH" 2>/dev/null || echo "pending")
_MERGE_STATUS=$(jq -r '.phases.merge.status // "pending"' "$FILE_PATH" 2>/dev/null || echo "pending")
if [[ "$_SHIP_STATUS" != "completed" ]] && [[ "$_MERGE_STATUS" != "completed" ]]; then
  exit 0
fi

# ── Extract CWD for signal file placement ──
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[[ -n "$CWD" && "$CWD" == /* ]] || exit 0

# ── Extract checkpoint data ──
# Single jq call to minimize subprocess overhead
CKPT_DATA=$(jq -r '[
  .id // "",
  .plan_file // "",
  (.pr_url // .phases.ship.pr_url // null | tostring),
  .owner_pid // "",
  .config_dir // "",
  (.phases | to_entries | map(select(.value.status == "completed")) | length | tostring),
  (.phases | length | tostring),
  (.phases | to_entries | map(select(.value.status == "failed" or .value.status == "timeout")) | length | tostring)
] | join("\t")' "$FILE_PATH" 2>/dev/null || true)
[[ -n "$CKPT_DATA" ]] || exit 0

IFS=$'\t' read -r ARC_ID PLAN_PATH PR_URL OWNER_PID CONFIG_DIR PHASES_COMPLETED PHASES_TOTAL PHASES_FAILED <<< "$CKPT_DATA"

# ── Determine status ──
if [[ "$PHASES_FAILED" -gt 0 ]]; then
  SIGNAL_STATUS="partial"
else
  SIGNAL_STATUS="completed"
fi

# ── Normalize PR_URL ──
[[ "$PR_URL" == "null" || "$PR_URL" == "none" || -z "$PR_URL" ]] && PR_URL="null" || PR_URL="\"${PR_URL}\""

# ── Write signal atomically (mktemp + mv) ──
SIGNAL_DIR="${CWD}/tmp"
mkdir -p "$SIGNAL_DIR" 2>/dev/null || exit 0
SIGNAL_FILE="${SIGNAL_DIR}/arc-result-current.json"
SIGNAL_TMP=$(mktemp "${SIGNAL_FILE}.XXXXXX" 2>/dev/null) || exit 0

cat > "$SIGNAL_TMP" <<SIGNAL_EOF
{
  "schema_version": 1,
  "arc_id": "${ARC_ID}",
  "plan_path": "${PLAN_PATH}",
  "status": "${SIGNAL_STATUS}",
  "pr_url": ${PR_URL},
  "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "phases_completed": ${PHASES_COMPLETED},
  "phases_total": ${PHASES_TOTAL},
  "owner_pid": "${OWNER_PID}",
  "config_dir": "${CONFIG_DIR}"
}
SIGNAL_EOF

mv -f "$SIGNAL_TMP" "$SIGNAL_FILE" 2>/dev/null || rm -f "$SIGNAL_TMP" 2>/dev/null
exit 0
