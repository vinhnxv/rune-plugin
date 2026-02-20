#!/bin/bash
# scripts/validate-mend-fixer-paths.sh
# SEC-MEND-001: Enforce file scope restrictions for mend fixer Ashes.
# Blocks Write/Edit/NotebookEdit when target file is outside the fixer's assigned file group.
#
# Detection strategy:
#   1. Fast-path: Check if tool is Write/Edit/NotebookEdit (only tools with file_path)
#   2. Fast-path: Check if caller is a subagent (team-lead is exempt)
#   3. Check for active mend workflow via tmp/.rune-mend-*.json state file
#   4. Read inscription.json to get fixer's assigned file group
#   5. Validate target file path against assigned group
#   6. Block (deny) if file is outside the group
#
# Exit 0 with hookSpecificOutput.permissionDecision="deny" JSON = tool call blocked.
# Exit 0 without JSON (or with permissionDecision="allow") = tool call allowed.
# Exit 2 = hook error, stderr fed to Claude (not used by this script).
#
# Fail-open design: On any parsing/validation error, allow the operation.
# False negatives (allowing out-of-scope edits) are preferable to false positives
# (blocking legitimate fixes).

set -euo pipefail
umask 077

# Pre-flight: jq is required for JSON parsing.
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — validate-mend-fixer-paths.sh hook is inactive" >&2
  exit 0
fi

# SEC-2: 1MB cap to prevent unbounded stdin read (DoS prevention)
# BACK-004: Guard against SIGPIPE (exit 141) when stdin closes early under set -e
INPUT=$(head -c 1048576 2>/dev/null || true)

# Fast-path 1: Extract tool name and file path in one jq call
IFS=$'\t' read -r TOOL_NAME FILE_PATH TRANSCRIPT_PATH <<< \
  "$(echo "$INPUT" | jq -r '[.tool_name // "", .tool_input.file_path // "", .transcript_path // ""] | @tsv' 2>/dev/null)" || true

# Only validate file-writing tools
case "$TOOL_NAME" in
  Write|Edit|NotebookEdit) ;;
  *) exit 0 ;;
esac

# Fast-path 2: File path must be non-empty
[[ -z "$FILE_PATH" ]] && exit 0

# Fast-path 3: Only enforce for subagents (team-lead is the orchestrator — exempt)
# transcript_path: documented common field (all hook events). Detection is best-effort.
# If transcript_path is missing or doesn't contain /subagents/, allow the operation.
if [[ -z "$TRANSCRIPT_PATH" ]] || [[ "$TRANSCRIPT_PATH" != */subagents/* ]]; then
  exit 0
fi

# Fast-path 4: Canonicalize CWD
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[[ -z "$CWD" ]] && exit 0
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
[[ -z "$CWD" || "$CWD" != /* ]] && exit 0

# Check for active mend workflow via state file
shopt -s nullglob
MEND_STATE_FILE=""
for f in "${CWD}"/tmp/.rune-mend-*.json; do
  if [[ -f "$f" ]] && grep -q '"active"' "$f" 2>/dev/null; then
    MEND_STATE_FILE="$f"
    break
  fi
done
shopt -u nullglob

# No active mend workflow — allow (hook only applies during mend)
[[ -z "$MEND_STATE_FILE" ]] && exit 0

# Extract identifier from .rune-mend-{identifier}.json
IDENTIFIER=$(basename "$MEND_STATE_FILE" .json | sed 's/^\.rune-mend-//')

# Security pattern: SAFE_IDENTIFIER — see security-patterns.md
# Validate identifier format (safe chars + length cap)
if [[ ! "$IDENTIFIER" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ ${#IDENTIFIER} -gt 64 ]]; then
  # Invalid identifier — fail open (allow)
  exit 0
fi

# Read inscription.json to find fixer's assigned file group
INSCRIPTION_PATH="${CWD}/tmp/mend/${IDENTIFIER}/inscription.json"
if [[ ! -f "$INSCRIPTION_PATH" ]]; then
  # No inscription found — fail open (allow)
  # This may happen if mend is in early setup phase before inscription is written
  exit 0
fi

# Extract all file_group entries from inscription to build the allowed file set.
# DESIGN LIMITATION (SEC-001): We collect ALL fixers' file groups into one flat
# allowlist because transcript_path format is undocumented and may not contain
# the fixer name reliably. This means fixer-A can write to fixer-B's files.
# Compensating controls: (1) blockedBy serialization prevents temporal overlap
# for dependent groups (Phase 1.5), (2) prompt instructions restrict each fixer
# to its assigned files, (3) ward check in Phase 5 catches any regressions.
# The key guarantee: files NOT in ANY fixer's group are blocked.
ALLOWED_FILES=$(jq -r '.fixers[].file_group[]' "$INSCRIPTION_PATH" 2>/dev/null || true)

if [[ -z "$ALLOWED_FILES" ]]; then
  # Empty file group list — fail open (allow) but warn if inscription exists
  echo "WARNING: inscription.json exists but yielded no allowed files — file ownership enforcement disabled for this call" >&2
  exit 0
fi

# Normalize the target file path (resolve relative to CWD, strip ./)
if [[ "$FILE_PATH" == /* ]]; then
  # Absolute path — make relative to CWD for comparison
  ABS_FILE_PATH="$FILE_PATH"
  REL_FILE_PATH="${FILE_PATH#"${CWD}/"}"
else
  ABS_FILE_PATH="${CWD}/${FILE_PATH}"
  REL_FILE_PATH="$FILE_PATH"
fi

# Strip leading ./ for consistent comparison
REL_FILE_PATH="${REL_FILE_PATH#./}"

# Check if the target file is in the allowed set
while IFS= read -r allowed; do
  # Strip leading ./ from allowed path too
  allowed="${allowed#./}"
  if [[ "$REL_FILE_PATH" == "$allowed" ]]; then
    # File is in an assigned group — allow
    exit 0
  fi
done <<< "$ALLOWED_FILES"

# Also allow writes to the mend output directory (fixers write reports there)
MEND_OUTPUT_PREFIX="tmp/mend/${IDENTIFIER}/"
if [[ "$REL_FILE_PATH" == "${MEND_OUTPUT_PREFIX}"* ]]; then
  exit 0
fi

# DENY: File is outside all assigned groups and output directory
DENY_MSG=$(jq -n \
  --arg fp "$REL_FILE_PATH" \
  --arg id "$IDENTIFIER" \
  '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("SEC-MEND-001: Mend fixer attempted to write outside assigned file group. Target: " + $fp + ". Only files listed in inscription.json file_group arrays are allowed."),
      additionalContext: ("Mend fixers are restricted to editing files in their assigned file group (from tmp/mend/" + $id + "/inscription.json). If you need to edit this file, mark the finding as SKIPPED with reason \"cross-file dependency, needs: [" + $fp + "]\" and the orchestrator will handle it in Phase 5.5.")
    }
  }')

echo "$DENY_MSG"
exit 0
