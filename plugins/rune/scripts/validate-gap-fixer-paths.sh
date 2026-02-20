#!/bin/bash
# scripts/validate-gap-fixer-paths.sh
# SEC-GAP-001: Enforce path restrictions for gap-fixer Ashes.
# Blocks Write/Edit/NotebookEdit to sensitive infrastructure paths during gap-fix workflows.
#
# Detection strategy:
#   1. Fast-path: Check if tool is Write/Edit/NotebookEdit (only tools with file_path)
#   2. Fast-path: Check if caller is a subagent (team-lead is exempt)
#   3. Check for active gap-fix workflow via tmp/.rune-gap-fix-*.json state file
#   4. Validate target file path against blocked path patterns
#   5. Block (deny) if file matches a restricted path
#
# Exit 0 with hookSpecificOutput.permissionDecision="deny" JSON = tool call blocked.
# Exit 0 without JSON (or with permissionDecision="allow") = tool call allowed.
# Exit 2 = hook error, stderr fed to Claude (not used by this script).
#
# Fail-open design: On any parsing/validation error, allow the operation.
# False negatives (allowing risky writes) are preferable to false positives
# (blocking legitimate gap fixes during remediation).

set -euo pipefail
umask 077

# Pre-flight: jq is required for JSON parsing.
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — validate-gap-fixer-paths.sh hook is inactive (blocking)" >&2
  exit 2
fi

# SEC-2: 1MB cap to prevent unbounded stdin read (DoS prevention)
# BACK-004: Guard against SIGPIPE (exit 141) when stdin closes early under set -e
INPUT=$(head -c 1048576 2>/dev/null || true)

# Fast-path 1: Extract tool name, file path, and transcript path in one jq call
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
# SEC-5 NOTE: transcript_path detection is best-effort (undocumented/internal).
# If transcript_path is missing or doesn't contain /subagents/, allow the operation.
if [[ -z "$TRANSCRIPT_PATH" ]] || [[ "$TRANSCRIPT_PATH" != */subagents/* ]]; then
  exit 0
fi

# Fast-path 4: Canonicalize CWD
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[[ -z "$CWD" ]] && exit 0
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
[[ -z "$CWD" || "$CWD" != /* ]] && exit 0

# Check for active gap-fix workflow via state file
shopt -s nullglob
GAP_FIX_STATE_FILE=""
for f in "${CWD}"/tmp/.rune-gap-fix-*.json; do
  if [[ -f "$f" ]] && grep -q '"active"' "$f" 2>/dev/null; then
    GAP_FIX_STATE_FILE="$f"
    break
  fi
done
shopt -u nullglob

# No active gap-fix workflow — allow (hook only applies during gap-fix)
[[ -z "$GAP_FIX_STATE_FILE" ]] && exit 0

# Normalize the target file path (resolve relative to CWD, strip ./)
if [[ "$FILE_PATH" == /* ]]; then
  # Absolute path — make relative to CWD for comparison
  REL_FILE_PATH="${FILE_PATH#"${CWD}/"}"
else
  REL_FILE_PATH="$FILE_PATH"
fi
# Strip leading ./ for consistent comparison
REL_FILE_PATH="${REL_FILE_PATH#./}"

# Extract identifier from .rune-gap-fix-{identifier}.json
IDENTIFIER=$(basename "$GAP_FIX_STATE_FILE" .json | sed 's/^\.rune-gap-fix-//')

# Security pattern: SAFE_IDENTIFIER — validate format (safe chars + length cap)
if [[ ! "$IDENTIFIER" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ ${#IDENTIFIER} -gt 64 ]]; then
  # Invalid identifier — fail open (allow)
  exit 0
fi

# ── Blocked path patterns ──────────────────────────────────────────────────
# Gap fixers must not touch infrastructure config, CI pipelines, or secret files.
# Path traversal check: reject paths that navigate outside CWD.
if [[ "$REL_FILE_PATH" == *../* ]] || [[ "$REL_FILE_PATH" == */.* && "$REL_FILE_PATH" != .claude/* ]]; then
  DENY_REASON="SEC-GAP-001: Path traversal or hidden file access denied."
  DENY=1
elif [[ "$REL_FILE_PATH" == .claude/* ]]; then
  DENY_REASON="SEC-GAP-001: Gap fixers must not modify .claude/ configuration files."
  DENY=1
elif [[ "$REL_FILE_PATH" == .github/* ]]; then
  DENY_REASON="SEC-GAP-001: Gap fixers must not modify .github/ CI/CD configuration."
  DENY=1
elif [[ "$REL_FILE_PATH" == node_modules/* ]]; then
  DENY_REASON="SEC-GAP-001: Gap fixers must not modify node_modules/."
  DENY=1
elif [[ "$REL_FILE_PATH" == .env || "$REL_FILE_PATH" == .env.* ]]; then
  DENY_REASON="SEC-GAP-001: Gap fixers must not modify environment/secret files."
  DENY=1
elif [[ "$REL_FILE_PATH" == *.yml && (
    "$REL_FILE_PATH" == .github/* ||
    "$REL_FILE_PATH" == *ci*.yml ||
    "$REL_FILE_PATH" == *pipeline*.yml ||
    "$REL_FILE_PATH" == *deploy*.yml ||
    "$REL_FILE_PATH" == *release*.yml
  ) ]]; then
  DENY_REASON="SEC-GAP-001: Gap fixers must not modify CI/deployment YAML files."
  DENY=1
else
  DENY=0
fi

# Allow writes to the gap-fix output directory (fixers write reports there)
GAP_OUTPUT_PREFIX="tmp/arc/${IDENTIFIER}/"
if [[ "$REL_FILE_PATH" == "${GAP_OUTPUT_PREFIX}"* ]]; then
  exit 0
fi

if [[ "$DENY" -eq 1 ]]; then
  DENY_MSG=$(jq -n \
    --arg fp "$REL_FILE_PATH" \
    --arg reason "$DENY_REASON" \
    --arg id "$IDENTIFIER" \
    '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: ($reason + " Target: " + $fp),
        additionalContext: ("Gap fixers are restricted to source code changes only. Infrastructure, CI config, secrets, and .claude/ files are off-limits. If this file genuinely needs updating as part of gap remediation, flag it as NEEDS_HUMAN_REVIEW in your output report (tmp/arc/" + $id + "/).")
      }
    }')
  echo "$DENY_MSG"
fi

exit 0
