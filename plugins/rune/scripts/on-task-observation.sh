#!/bin/bash
# scripts/on-task-observation.sh
# Auto-observation recording for Rune workflow tasks.
# Fires on TaskCompleted — appends lightweight observation entries to the
# appropriate role MEMORY.md in .claude/echoes/.
#
# Design goals:
# - Non-blocking: exit 0 on all error paths
# - Dedup: ${TEAM_NAME}_${TASK_ID} as dedup key (portable, C2)
# - Role detection from team name pattern
# - Append-only to .claude/echoes/{role}/MEMORY.md (Observations tier)
# - Signals echo-search dirty for auto-reindex

set -euo pipefail

# Fail-open wrapper — any unexpected error → allow
_fail_open() { exit 0; }
trap '_fail_open' ERR

# Guard: jq required for safe JSON parsing
command -v jq >/dev/null 2>&1 || exit 0

# Read hook input from stdin (max 64KB — SEC-006)
INPUT=$(head -c 65536)
[[ -z "$INPUT" ]] && exit 0

# --- Guard 1: Only process Rune workflow tasks ---
IFS=$'\t' read -r TEAM_NAME TASK_ID TASK_SUBJECT TASK_DESC AGENT_NAME < <(
  echo "$INPUT" | jq -r '
    [
      .team_name // "",
      .task_id // "",
      .task_subject // "",
      (.task_description // "" | .[0:500]),
      .teammate_name // "unknown"
    ] | @tsv' 2>/dev/null || echo ""
) || true

[[ -z "$TEAM_NAME" ]] && exit 0
[[ "$TEAM_NAME" =~ ^(rune-|arc-) ]] || exit 0

# Guard: safe characters only (prevent path traversal)
[[ "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 0
[[ ${#TEAM_NAME} -le 128 ]] || exit 0
[[ -n "$TASK_ID" ]] || exit 0
[[ "$TASK_ID" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 0

# --- Guard 2: Skip cleanup/shutdown/meta tasks ---
case "${TASK_SUBJECT,,}" in
  *shutdown*|*cleanup*|*aggregate*|*monitor*|*"shut down"*) exit 0 ;;
esac

# --- Guard 3: Resolve project directory ---
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[[ -z "$CWD" ]] && exit 0
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || exit 0
[[ -n "$CWD" && "$CWD" == /* ]] || exit 0

PROJECT_DIR="$CWD"

# --- Guard 4: Check .claude/echoes/ directory exists ---
ECHO_DIR="$PROJECT_DIR/.claude/echoes"
[[ -d "$ECHO_DIR" ]] || exit 0

# --- Guard 5: Symlink protection on echoes dir ---
[[ -L "$ECHO_DIR" ]] && exit 0

# --- Guard 6: Determine role from team name pattern ---
ROLE="orchestrator"
case "$TEAM_NAME" in
  *review*|*appraise*|*audit*) ROLE="reviewer" ;;
  *plan*|*devise*)             ROLE="planner" ;;
  *work*|*strive*|*arc*)       ROLE="workers" ;;
esac

# --- Guard 7: Check role MEMORY.md exists ---
MEMORY_FILE="$ECHO_DIR/$ROLE/MEMORY.md"
[[ -f "$MEMORY_FILE" ]] || exit 0

# Symlink guard on MEMORY.md
[[ -L "$MEMORY_FILE" ]] && exit 0

# --- Guard 8: Dedup by ${TEAM_NAME}_${TASK_ID} (Concern C2 — portable, no md5) ---
SIGNAL_DIR="$PROJECT_DIR/tmp/.rune-signals"
mkdir -p "$SIGNAL_DIR" 2>/dev/null || exit 0
DEDUP_KEY="${TEAM_NAME}_${TASK_ID}"
DEDUP_FILE="$SIGNAL_DIR/.obs-${DEDUP_KEY}"
[[ -f "$DEDUP_FILE" ]] && exit 0
touch "$DEDUP_FILE" 2>/dev/null || exit 0

# --- Step 9: Generate and append observation entry ---
DATE=$(date +%Y-%m-%d)

ENTRY=$(cat <<'ENTRY_EOF'

## Observations — Task: __TASK_SUBJECT__ (__DATE__)
- **layer**: observations
- **source**: `__TEAM_NAME__/__AGENT_NAME__`
- **Confidence**: LOW (auto-generated, unverified)
- Task completed: __TASK_SUBJECT__
- Context: __TASK_DESC__
ENTRY_EOF
)
# Inject actual values via variable replacement (safe — no shell expansion in heredoc body)
ENTRY="${ENTRY//__TASK_SUBJECT__/$TASK_SUBJECT}"
ENTRY="${ENTRY//__DATE__/$DATE}"
ENTRY="${ENTRY//__TEAM_NAME__/$TEAM_NAME}"
ENTRY="${ENTRY//__AGENT_NAME__/$AGENT_NAME}"
ENTRY="${ENTRY//__TASK_DESC__/$TASK_DESC}"

# Atomic append via temp file (prevent partial writes)
TMPFILE=$(mktemp 2>/dev/null) || exit 0
printf '%s\n' "$ENTRY" > "$TMPFILE"
cat "$TMPFILE" >> "$MEMORY_FILE" 2>/dev/null || { rm -f "$TMPFILE"; exit 0; }
rm -f "$TMPFILE"

# --- Step 10: Signal echo-search dirty for auto-reindex ---
touch "$SIGNAL_DIR/.echo-dirty" 2>/dev/null || true

exit 0
