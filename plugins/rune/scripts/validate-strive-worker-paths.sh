#!/bin/bash
# scripts/validate-strive-worker-paths.sh
# SEC-STRIVE-001: Enforce file scope restrictions for strive worker Ashes.
# Blocks Write/Edit/NotebookEdit when target file is outside the worker's assigned file scope.
#
# Detection strategy:
#   1. Fast-path: Check if tool is Write/Edit/NotebookEdit (only tools with file_path)
#   2. Fast-path: Check if caller is a subagent (team-lead is exempt)
#   3. Check for active strive workflow via tmp/.rune-work-*.json state file
#   4. Verify session ownership (config_dir + owner_pid)
#   5. Read inscription.json to get task_ownership allowlist
#   6. Validate target file path against flat union of assigned files/dirs
#   7. Block (deny) if file is outside all assigned scopes
#
# Exit 0 with hookSpecificOutput.permissionDecision="deny" JSON = tool call blocked.
# Exit 0 without JSON (or with permissionDecision="allow") = tool call allowed.
# Exit 2 = hook error, stderr fed to Claude (not used by this script).
#
# Fail-open design: On any parsing/validation error, allow the operation.
# False negatives (allowing out-of-scope edits) are preferable to false positives
# (blocking legitimate work).

set -euo pipefail
umask 077

# Pre-flight: jq is required for JSON parsing.
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — validate-strive-worker-paths.sh hook is inactive" >&2
  exit 0
fi

# SEC-2: 1MB cap to prevent unbounded stdin read (DoS prevention)
# BACK-004: Guard against SIGPIPE (exit 141) when stdin closes early under set -e
INPUT=$(head -c 1048576 2>/dev/null || true)

# Fast-path 1: Extract tool name and file path in one jq call
IFS=$'\t' read -r TOOL_NAME FILE_PATH TRANSCRIPT_PATH <<< \
  "$(printf '%s' "$INPUT" | jq -r '[.tool_name // "", .tool_input.file_path // "", .transcript_path // ""] | @tsv' 2>/dev/null)" || true

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
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[[ -z "$CWD" ]] && exit 0
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
[[ -z "$CWD" || "$CWD" != /* ]] && exit 0

# Check for active strive workflow via state file (rune-work-* pattern)
shopt -s nullglob
WORK_STATE_FILE=""
for f in "${CWD}"/tmp/.rune-work-*.json; do
  if [[ -f "$f" ]] && jq -e '.status == "active"' "$f" >/dev/null 2>&1; then
    WORK_STATE_FILE="$f"
    break
  fi
done
shopt -u nullglob

# No active strive workflow — allow (hook only applies during strive)
[[ -z "$WORK_STATE_FILE" ]] && exit 0

# Session isolation: verify config_dir and owner_pid match current session
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
CHOME=$(cd "$CHOME" 2>/dev/null && pwd -P 2>/dev/null || echo "$CHOME")
STATE_CONFIG_DIR=$(jq -r '.config_dir // empty' "$WORK_STATE_FILE" 2>/dev/null || true)
STATE_OWNER_PID=$(jq -r '.owner_pid // empty' "$WORK_STATE_FILE" 2>/dev/null || true)

# Check config_dir matches (installation isolation)
if [[ -n "$STATE_CONFIG_DIR" && "$STATE_CONFIG_DIR" != "$CHOME" ]]; then
  # State belongs to a different installation — skip
  exit 0
fi

# Check owner_pid is alive and matches (session isolation)
if [[ -n "$STATE_OWNER_PID" ]]; then
  if kill -0 "$STATE_OWNER_PID" 2>/dev/null; then
    # PID is alive — check if it matches our parent
    if [[ "$STATE_OWNER_PID" != "$PPID" ]]; then
      # State belongs to another live session — skip
      exit 0
    fi
  else
    # PID is dead — orphan state, skip (orphan recovery handled elsewhere)
    exit 0
  fi
fi

# Extract identifier from .rune-work-{identifier}.json
IDENTIFIER=$(basename "$WORK_STATE_FILE" .json | sed 's/^\.rune-work-//')

# Security pattern: SAFE_IDENTIFIER — see security-patterns.md
# Validate identifier format (safe chars + length cap)
if [[ ! "$IDENTIFIER" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ ${#IDENTIFIER} -gt 64 ]]; then
  # Invalid identifier — fail open (allow)
  exit 0
fi

# Read inscription.json to find task ownership mapping
INSCRIPTION_PATH="${CWD}/tmp/.rune-signals/rune-work-${IDENTIFIER}/inscription.json"
if [[ ! -f "$INSCRIPTION_PATH" ]]; then
  # No inscription found — fail open (allow)
  # This may happen if strive is in early setup phase before inscription is written
  exit 0
fi

# Fast-path 7: Check for task_ownership key
if ! jq -e '.task_ownership' "$INSCRIPTION_PATH" >/dev/null 2>&1; then
  # No task_ownership key — old format or pre-Phase 1; fail open (allow)
  exit 0
fi

# Extract all file targets from task_ownership into a flat allowlist.
# DESIGN LIMITATION (SEC-STRIVE-001): We collect ALL tasks' file targets into one flat
# allowlist because transcript_path format is undocumented and may not contain
# the worker name reliably. This means worker-A can write to worker-B's files.
# Compensating controls: (1) blockedBy serialization prevents temporal overlap
# for dependent tasks (Phase 1), (2) prompt instructions restrict each worker
# to its assigned files, (3) ward check in Phase 4 catches any regressions.
# The key guarantee: files NOT in ANY task's target list are blocked.
ALLOWED_FILES=$(jq -r '.task_ownership | to_entries[].value.files[]? // empty' "$INSCRIPTION_PATH" 2>/dev/null || true)
ALLOWED_DIRS=$(jq -r '.task_ownership | to_entries[].value.dirs[]? // empty' "$INSCRIPTION_PATH" 2>/dev/null || true)

# Read talisman unrestricted_shared_files (if any)
TALISMAN_SHARED=""
for tpath in "${CWD}/.claude/talisman.yml" "${CHOME}/talisman.yml"; do
  if [[ -f "$tpath" ]]; then
    # Extract work.unrestricted_shared_files array values (simple YAML parsing via grep)
    # Look for lines under unrestricted_shared_files: that start with "- "
    TALISMAN_SHARED=$(sed -n '/unrestricted_shared_files:/,/^[^ ]/{ /^ *- /s/^ *- *//p; }' "$tpath" 2>/dev/null || true)
    break
  fi
done

# Fast-path 8: If no file targets AND no dir targets exist, all tasks are unrestricted
if [[ -z "$ALLOWED_FILES" && -z "$ALLOWED_DIRS" && -z "$TALISMAN_SHARED" ]]; then
  exit 0
fi

# Normalize the target file path (resolve relative to CWD, strip ./)
if [[ "$FILE_PATH" == /* ]]; then
  # Absolute path — make relative to CWD for comparison
  REL_FILE_PATH="${FILE_PATH#"${CWD}/"}"
else
  REL_FILE_PATH="$FILE_PATH"
fi

# Strip leading ./ for consistent comparison
REL_FILE_PATH="${REL_FILE_PATH#./}"

# Also allow writes to the strive output directory (workers write reports/patches there)
WORK_OUTPUT_PREFIX="tmp/work/${IDENTIFIER}/"
if [[ "$REL_FILE_PATH" == "${WORK_OUTPUT_PREFIX}"* ]]; then
  exit 0
fi

# Also allow writes to the signal directory
SIGNAL_PREFIX="tmp/.rune-signals/rune-work-${IDENTIFIER}/"
if [[ "$REL_FILE_PATH" == "${SIGNAL_PREFIX}"* ]]; then
  exit 0
fi

# Check against exact file matches
if [[ -n "$ALLOWED_FILES" ]]; then
  while IFS= read -r allowed; do
    allowed="${allowed#./}"
    if [[ "$REL_FILE_PATH" == "$allowed" ]]; then
      exit 0
    fi
  done <<< "$ALLOWED_FILES"
fi

# Check against directory prefix matches
if [[ -n "$ALLOWED_DIRS" ]]; then
  while IFS= read -r allowed_dir; do
    allowed_dir="${allowed_dir#./}"
    # Ensure dir ends with /
    [[ "$allowed_dir" != */ ]] && allowed_dir="${allowed_dir}/"
    if [[ "$REL_FILE_PATH" == "${allowed_dir}"* ]]; then
      exit 0
    fi
  done <<< "$ALLOWED_DIRS"
fi

# Check against talisman unrestricted_shared_files
if [[ -n "$TALISMAN_SHARED" ]]; then
  while IFS= read -r shared; do
    shared="${shared#./}"
    [[ -z "$shared" ]] && continue
    if [[ "$REL_FILE_PATH" == "$shared" ]]; then
      exit 0
    fi
  done <<< "$TALISMAN_SHARED"
fi

# DENY: File is outside all assigned scopes
DENY_MSG=$(jq -n \
  --arg fp "$REL_FILE_PATH" \
  --arg id "$IDENTIFIER" \
  '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("SEC-STRIVE-001: Strive worker attempted to write outside assigned file scope. Target: " + $fp + ". Only files listed in task_ownership (inscription.json) are allowed."),
      additionalContext: ("Strive workers are restricted to editing files in their assigned task scope (from tmp/.rune-signals/rune-work-" + $id + "/inscription.json task_ownership). If you need to edit this file, send a message to team-lead requesting a new task that includes this file, or mark it as a dependency in your task output.")
    }
  }')

echo "$DENY_MSG"
exit 0
