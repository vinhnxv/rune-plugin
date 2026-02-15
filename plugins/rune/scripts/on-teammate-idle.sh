#!/bin/bash
# scripts/on-teammate-idle.sh
# Validates teammate work quality before allowing idle.
# Exit 2 + stderr = block idle and send feedback to teammate.
# Exit 0 = allow teammate to go idle normally.

set -euo pipefail
umask 077

# Pre-flight: jq is required for parsing inscription and hook input.
# If missing, exit 0 (non-blocking) — skip quality gate rather than crash.
if ! command -v jq &>/dev/null; then
  echo "WARN: jq not found — quality gate skipped. Install jq for Phase 2 event-driven sync." >&2
  exit 0
fi

INPUT=$(cat)

TEAM_NAME=$(echo "$INPUT" | jq -r '.team_name // empty' 2>/dev/null || true)
TEAMMATE_NAME=$(echo "$INPUT" | jq -r '.teammate_name // empty' 2>/dev/null || true)

# Guard: only process Rune teams
if [[ -z "$TEAM_NAME" || "$TEAM_NAME" != rune-* ]]; then
  exit 0
fi

# Guard: validate names
if [[ ! "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  exit 0
fi

# Derive absolute path from hook input CWD (not relative — CWD is not guaranteed)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi

# --- Quality Gate: Check if teammate wrote its output file ---
# Rune teammates are expected to write output files before going idle.
# The expected output path is stored in the inscription.

INSCRIPTION="${CWD}/tmp/.rune-signals/${TEAM_NAME}/inscription.json"
if [[ ! -f "$INSCRIPTION" ]]; then
  # No inscription = no quality gate to enforce
  exit 0
fi

# Find this teammate's expected output file from inscription
EXPECTED_OUTPUT=$(jq -r --arg name "$TEAMMATE_NAME" \
  '.teammates[] | select(.name == $name) | .output_file // empty' \
  "$INSCRIPTION" 2>/dev/null || true)

if [[ -z "$EXPECTED_OUTPUT" ]]; then
  # Teammate not in inscription (e.g., dynamically spawned utility agent)
  exit 0
fi

# Resolve output path relative to the inscription's output_dir
# Note: output_dir in inscription must end with "/" (enforced by orchestrator setup)
OUTPUT_DIR=$(jq -r '.output_dir // empty' "$INSCRIPTION" 2>/dev/null || true)
FULL_OUTPUT_PATH="${CWD}/${OUTPUT_DIR}${EXPECTED_OUTPUT}"

if [[ ! -f "$FULL_OUTPUT_PATH" ]]; then
  # Output file missing — block idle, tell teammate to finish work
  echo "Output file not found: ${FULL_OUTPUT_PATH}. Please complete your review and write findings before stopping." >&2
  exit 2
fi

# Check output file has non-trivial content (>10 bytes as minimum for meaningful output)
FILE_SIZE=$(wc -c < "$FULL_OUTPUT_PATH" 2>/dev/null | tr -d ' ')
if [[ "$FILE_SIZE" -lt 10 ]]; then
  echo "Output file is empty or too small: ${FULL_OUTPUT_PATH} (${FILE_SIZE} bytes). Please write your findings." >&2
  exit 2
fi

# --- Quality Gate: Check for SEAL marker (Roundtable Circle only) ---
# Ash agents include a SEAL YAML block in their output.
# If no SEAL, warn but allow idle (soft gate — caught by Runebinder later).
if [[ "$TEAM_NAME" == rune-review-* || "$TEAM_NAME" == rune-audit-* ]]; then
  if ! grep -q "^SEAL:" "$FULL_OUTPUT_PATH" 2>/dev/null; then
    # SEAL missing — warn via stdout (non-blocking) but allow idle
    echo "Warning: SEAL marker not found in ${FULL_OUTPUT_PATH}. Runebinder will flag this."
    exit 0
  fi
fi

# All gates passed — allow idle
exit 0
