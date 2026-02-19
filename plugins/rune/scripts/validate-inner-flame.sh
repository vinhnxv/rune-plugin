#!/bin/bash
# scripts/validate-inner-flame.sh
# TaskCompleted hook: validates Inner Flame self-review was performed.
# Exit 2 to BLOCK task completion if self-review is missing.
# Exit 0 to allow (non-blocking).

set -euo pipefail

# Read hook input
INPUT=$(head -c 1048576)

# Pre-flight: jq required
if ! command -v jq &>/dev/null; then
  exit 0  # Non-blocking if jq missing
fi

# Validate JSON
if ! echo "$INPUT" | jq empty 2>/dev/null; then
  exit 0
fi

# Extract fields
IFS=$'\t' read -r TEAM_NAME TASK_ID TEAMMATE_NAME <<< \
  "$(echo "$INPUT" | jq -r '[.team_name // "", .task_id // "", .teammate_name // ""] | @tsv' 2>/dev/null)" || true

# Guard: only process Rune teams
if [[ -z "$TEAM_NAME" || -z "$TASK_ID" ]]; then
  exit 0
fi
if [[ "$TEAM_NAME" != rune-* && "$TEAM_NAME" != arc-* ]]; then
  exit 0
fi

# Guard: validate identifiers
if [[ ! "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ ! "$TASK_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  exit 0
fi

CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || exit 0

# Determine output directory based on team name pattern
OUTPUT_DIR=""
if [[ "$TEAM_NAME" == rune-review-* ]]; then
  REVIEW_ID="${TEAM_NAME#rune-review-}"
  OUTPUT_DIR="${CWD}/tmp/reviews/${REVIEW_ID}"
elif [[ "$TEAM_NAME" == rune-audit-* ]]; then
  AUDIT_ID="${TEAM_NAME#rune-audit-}"
  OUTPUT_DIR="${CWD}/tmp/audit/${AUDIT_ID}"
elif [[ "$TEAM_NAME" == rune-work-* ]]; then
  # Workers don't write to output files in the same way — skip for now
  # Inner Flame for workers is enforced via Seal message content
  exit 0
elif [[ "$TEAM_NAME" == rune-mend-* ]]; then
  # Mend fixers — check is via Seal message
  exit 0
fi

# If no output dir, skip
if [[ -z "$OUTPUT_DIR" || ! -d "$OUTPUT_DIR" ]]; then
  exit 0
fi

# Check if teammate's output file contains Self-Review Log
TEAMMATE_FILE="${OUTPUT_DIR}/${TEAMMATE_NAME}.md"
if [[ ! -f "$TEAMMATE_FILE" ]]; then
  # Output file not yet written — can't validate
  exit 0
fi

# Check for Self-Review Log section
if ! grep -q "Self-Review Log" "$TEAMMATE_FILE" 2>/dev/null; then
  echo "Inner Flame: Self-Review Log missing from ${TEAMMATE_NAME}'s output. Re-read your work and add a Self-Review Log section before sealing." >&2
  exit 2  # BLOCK — task completion denied
fi

exit 0
