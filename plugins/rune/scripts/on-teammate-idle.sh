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

# Validate TEAMMATE_NAME characters
if [[ -n "$TEAMMATE_NAME" && ! "$TEAMMATE_NAME" =~ ^[a-zA-Z0-9_:-]+$ ]]; then
  exit 0
fi

# Guard: validate names (char-set and length before prefix check)
if [[ -z "$TEAM_NAME" ]] || [[ ! "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  exit 0
fi
if [[ ${#TEAM_NAME} -gt 128 ]]; then
  exit 0
fi

# Guard: only process Rune and Arc teams
# QUAL-001: Guard includes arc-* for arc pipeline support
if [[ "$TEAM_NAME" != rune-* && "$TEAM_NAME" != arc-* ]]; then
  exit 0
fi

# Derive absolute path from hook input CWD (not relative — CWD is not guaranteed)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  echo "WARN: TeammateIdle hook input missing 'cwd' field" >&2
  exit 0
fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P || echo "$CWD")
if [[ -z "$CWD" || "$CWD" != /* ]]; then
  exit 0
fi

# --- Quality Gate: Check if teammate wrote its output file ---
# Rune teammates are expected to write output files before going idle.
# The expected output path is stored in the inscription.

# NOTE: inscription.json is write-once by orchestrator. Teammates cannot modify it if signal dir has correct permissions (umask 077 in on-task-completed.sh).
INSCRIPTION="${CWD}/tmp/.rune-signals/${TEAM_NAME}/inscription.json"
if [[ ! -f "$INSCRIPTION" ]]; then
  # No inscription = no quality gate to enforce
  exit 0
fi

# Find this teammate's expected output file from inscription
# Note: inscription teammate uniqueness is validated during orchestrator setup, not here
EXPECTED_OUTPUT=$(jq -r --arg name "$TEAMMATE_NAME" \
  '.teammates[] | select(.name == $name) | .output_file // empty' \
  "$INSCRIPTION" 2>/dev/null || true)

# SEC-003: Path traversal check for EXPECTED_OUTPUT
# SEC-C01: Fast-fail heuristic only — rejects obvious traversal patterns early.
# The real security boundary is the realpath+prefix canonicalization at lines 104-110.
if [[ "$EXPECTED_OUTPUT" == *".."* || "$EXPECTED_OUTPUT" == /* ]]; then
  echo "ERROR: inscription output_file contains path traversal: ${EXPECTED_OUTPUT}" >&2
  exit 0
fi

if [[ -z "$EXPECTED_OUTPUT" ]]; then
  # Teammate not in inscription (e.g., dynamically spawned utility agent)
  exit 0
fi

# Resolve output path relative to the inscription's output_dir
# Note: output_dir in inscription must end with "/" (enforced by orchestrator setup)
OUTPUT_DIR=$(jq -r '.output_dir // empty' "$INSCRIPTION" 2>/dev/null || true)

# Validate OUTPUT_DIR
if [[ -z "$OUTPUT_DIR" ]]; then
  echo "WARN: inscription missing output_dir. Skipping quality gate." >&2
  exit 0
fi
# SEC-003: Path traversal check for OUTPUT_DIR
if [[ "$OUTPUT_DIR" == *".."* ]]; then
  echo "ERROR: inscription output_dir contains path traversal: ${OUTPUT_DIR}" >&2
  exit 0
fi
if [[ "$OUTPUT_DIR" != tmp/* ]]; then
  echo "ERROR: inscription output_dir outside tmp/: ${OUTPUT_DIR}" >&2
  exit 0
fi

# Normalize trailing slash
[[ -n "$OUTPUT_DIR" && "${OUTPUT_DIR: -1}" != "/" ]] && OUTPUT_DIR="${OUTPUT_DIR}/"

FULL_OUTPUT_PATH="${CWD}/${OUTPUT_DIR}${EXPECTED_OUTPUT}"

# SEC-004: Canonicalize and verify output path stays within output_dir
# Use grealpath -m (GNU coreutils on macOS) or realpath -m (Linux), with
# shell-based fallback for environments where neither is available.
# The fallback is safe because .. is already rejected above (lines 72, 92).
resolve_path() {
  grealpath -m "$1" 2>/dev/null || realpath -m "$1" 2>/dev/null || echo "$1"
}
RESOLVED_OUTPUT=$(resolve_path "$FULL_OUTPUT_PATH")
RESOLVED_OUTDIR=$(resolve_path "${CWD}/${OUTPUT_DIR}")
if [[ "$RESOLVED_OUTPUT" != "$RESOLVED_OUTDIR"* ]]; then
  echo "ERROR: output_file resolves outside output_dir" >&2
  exit 0
fi

if [[ ! -f "$FULL_OUTPUT_PATH" ]]; then
  # Output file missing — block idle, tell teammate to finish work
  echo "Output file not found: ${OUTPUT_DIR}${EXPECTED_OUTPUT}. Please complete your review and write findings before stopping." >&2
  exit 2
fi

# BACK-007: Minimum output size gate
MIN_OUTPUT_SIZE=50  # Minimum bytes for meaningful output
FILE_SIZE=$(wc -c < "$FULL_OUTPUT_PATH" 2>/dev/null | tr -d ' ')
if [[ "$FILE_SIZE" -lt "$MIN_OUTPUT_SIZE" ]]; then
  echo "Output file is empty or too small: ${FULL_OUTPUT_PATH} (${FILE_SIZE} bytes). Please write your findings." >&2
  exit 2
fi

# --- Quality Gate: Check for SEAL marker (Roundtable Circle only) ---
# BACK-004: SEAL enforcement for review/audit workflows
# Ash agents include a SEAL YAML block in their output.
# If no SEAL, block idle — output is incomplete.
if [[ "$TEAM_NAME" =~ ^(rune|arc)-(review|audit)- ]]; then
  # SEC-009: Simple string match — this is a quality gate, not a security boundary.
  # BACK-102: ^SEAL: requires column-0 positioning by design — partial or indented
  # SEAL lines are treated as incomplete output (fail-safe).
  if ! grep -q "^SEAL:" "$FULL_OUTPUT_PATH" 2>/dev/null; then
    echo "SEAL marker missing in ${FULL_OUTPUT_PATH}. Review output incomplete — add SEAL block." >&2
    exit 2  # Block idle until Ash adds SEAL
  fi
fi

# All gates passed — allow idle
exit 0
