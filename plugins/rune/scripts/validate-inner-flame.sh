#!/bin/bash
# scripts/validate-inner-flame.sh
# TaskCompleted hook: validates Inner Flame self-review was performed.
# Exit 2 to BLOCK task completion if self-review is missing AND block_on_fail is true.
# Exit 0 to allow (non-blocking or soft enforcement).

set -euo pipefail

# Read hook input (64KB cap — sufficient for TaskCompleted JSON payloads)
INPUT=$(head -c 65536)

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

# Guard: validate ALL identifiers (SEC-001: TEAMMATE_NAME was missing)
if [[ ! "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ ! "$TASK_ID" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ ! "$TEAMMATE_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  exit 0
fi

CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || exit 0

# Check talisman config for inner_flame settings (QUAL-001/SEC-002)
# CHOME: CLAUDE_CONFIG_DIR pattern for multi-account support (user-level talisman)
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
BLOCK_ON_FAIL=false
INNER_FLAME_ENABLED=true
for TALISMAN_PATH in "${CWD}/.claude/talisman.yml" "${CHOME}/talisman.yml"; do
  if [[ -f "$TALISMAN_PATH" ]]; then
    if command -v yq &>/dev/null; then
      INNER_FLAME_ENABLED=$(yq -r '.inner_flame.enabled // true' "$TALISMAN_PATH" 2>/dev/null || echo "true")
      BLOCK_ON_FAIL=$(yq -r '.inner_flame.block_on_fail // true' "$TALISMAN_PATH" 2>/dev/null || echo "true")
    else
      echo "Inner Flame: yq not found — cannot read talisman config, defaulting to soft enforcement" >&2
    fi
    break
  fi
done

# If Inner Flame is disabled globally, skip
if [[ "$INNER_FLAME_ENABLED" == "false" ]]; then
  exit 0
fi

# Determine output directory based on team name pattern (QUAL-005: added arc-* patterns)
OUTPUT_DIR=""
if [[ "$TEAM_NAME" == rune-review-* ]]; then
  REVIEW_ID="${TEAM_NAME#rune-review-}"
  OUTPUT_DIR="${CWD}/tmp/reviews/${REVIEW_ID}"
elif [[ "$TEAM_NAME" == arc-review-* ]]; then
  REVIEW_ID="${TEAM_NAME#arc-review-}"
  OUTPUT_DIR="${CWD}/tmp/reviews/${REVIEW_ID}"
elif [[ "$TEAM_NAME" == rune-audit-* ]]; then
  AUDIT_ID="${TEAM_NAME#rune-audit-}"
  OUTPUT_DIR="${CWD}/tmp/audit/${AUDIT_ID}"
elif [[ "$TEAM_NAME" == arc-audit-* ]]; then
  AUDIT_ID="${TEAM_NAME#arc-audit-}"
  OUTPUT_DIR="${CWD}/tmp/audit/${AUDIT_ID}"
elif [[ "$TEAM_NAME" == rune-work-* || "$TEAM_NAME" == arc-work-* ]]; then
  # Workers don't write to output files in the same way — skip for now
  # Inner Flame for workers is enforced via Seal message content
  exit 0
elif [[ "$TEAM_NAME" == rune-mend-* || "$TEAM_NAME" == arc-mend-* ]]; then
  # Mend fixers — check is via Seal message
  exit 0
elif [[ "$TEAM_NAME" == rune-inspect-* || "$TEAM_NAME" == arc-inspect-* ]]; then
  INSPECT_ID="${TEAM_NAME#rune-inspect-}"
  [[ "$TEAM_NAME" == arc-inspect-* ]] && INSPECT_ID="${TEAM_NAME#arc-inspect-}"
  OUTPUT_DIR="${CWD}/tmp/inspect/${INSPECT_ID}"
fi

# If no output dir, skip
if [[ -z "$OUTPUT_DIR" || ! -d "$OUTPUT_DIR" ]]; then
  exit 0
fi

# Path containment check (SEC-003): verify OUTPUT_DIR is under CWD/tmp/
REAL_OUTPUT_DIR=$(cd "$OUTPUT_DIR" 2>/dev/null && pwd -P) || exit 0
case "$REAL_OUTPUT_DIR" in
  "${CWD}/tmp/"*) ;; # OK — within project tmp/
  *) exit 0 ;; # Outside project — skip
esac

# Check if teammate's output file contains Inner Flame content
TEAMMATE_FILE="${OUTPUT_DIR}/${TEAMMATE_NAME}.md"
if [[ ! -f "$TEAMMATE_FILE" ]]; then
  # Output file not yet written — can't validate
  exit 0
fi

# Check for Inner Flame content (SEC-007/QUAL-010: matches canonical SKILL.md format + Seal variants)
if ! grep -qE "Self-Review Log.*Inner Flame|Inner Flame:|Inner-flame:" "$TEAMMATE_FILE" 2>/dev/null; then
  if [[ "$BLOCK_ON_FAIL" == "true" ]]; then
    echo "Inner Flame: Self-Review Log with Inner Flame content missing from ${TEAMMATE_NAME}'s output. Re-read your work and add Inner Flame self-review before sealing." >&2
    exit 2  # BLOCK — task completion denied
  else
    echo "Inner Flame: Self-Review Log with Inner Flame content missing from ${TEAMMATE_NAME}'s output (soft enforcement — not blocking)." >&2
    exit 0  # WARN only — soft enforcement (default)
  fi
fi

exit 0
