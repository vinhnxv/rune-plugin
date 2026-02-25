#!/bin/bash
# scripts/enforce-glyph-budget.sh
# GLYPH-BUDGET-001: Advisory enforcement for teammate message size.
# PostToolUse:SendMessage hook — injects additionalContext when a teammate
# sends a message exceeding the glyph budget (default: 300 words).
#
# Non-blocking: PostToolUse cannot block tool execution. This hook injects
# advisory context only, informing the orchestrator of the violation.
#
# Guard: Only active during Rune workflows (state files present).
# Concern C3: Uses explicit file paths with [[ -f ]] guards (no globs).

set -euo pipefail

# Fail-open wrapper
_fail_open() { exit 0; }
trap '_fail_open' ERR

# Guard: jq required
command -v jq >/dev/null 2>&1 || exit 0

# Read hook input from stdin (max 64KB — SEC-006)
INPUT=$(head -c 65536)
[[ -z "$INPUT" ]] && exit 0

# --- Guard 1: Only active during Rune workflows ---
# Check for active rune workflow state files (explicit paths — Concern C3)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[[ -z "$CWD" ]] && exit 0
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || exit 0
[[ -n "$CWD" && "$CWD" == /* ]] || exit 0

PROJECT_DIR="$CWD"
HAS_RUNE_WORKFLOW=false

# Explicit state file pattern check (Concern C3: [[ -f "$sf" ]] || continue)
for sf in \
  "$PROJECT_DIR/tmp/.rune-review-"*.json \
  "$PROJECT_DIR/tmp/.rune-work-"*.json \
  "$PROJECT_DIR/tmp/.rune-forge-"*.json \
  "$PROJECT_DIR/tmp/.rune-plan-"*.json \
  "$PROJECT_DIR/tmp/.rune-arc-"*.json; do
  [[ -f "$sf" ]] || continue
  HAS_RUNE_WORKFLOW=true
  break
done

[[ "$HAS_RUNE_WORKFLOW" == "true" ]] || exit 0

# --- Guard 2: Extract message content ---
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty' 2>/dev/null || true)
[[ -z "$CONTENT" ]] && exit 0

# --- Step 3: Count words ---
WORD_COUNT=$(echo "$CONTENT" | wc -w | tr -d ' ')

# --- Step 4: Configurable threshold (default 300 words) ---
BUDGET="${RUNE_GLYPH_BUDGET:-300}"

# Validate budget is numeric
[[ "$BUDGET" =~ ^[0-9]+$ ]] || BUDGET=300

# --- Step 5: Check compliance and inject advisory if over budget ---
if [[ "$WORD_COUNT" -gt "$BUDGET" ]]; then
  jq -n \
    --arg ctx "GLYPH-BUDGET-VIOLATION: Teammate message was ${WORD_COUNT} words (budget: ${BUDGET}). The Glyph Budget protocol requires teammates to write verbose output to tmp/ files and send only a file path + 50-word summary via SendMessage. Consider redirecting this teammate to file-based output for future messages." \
    '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}' 2>/dev/null || true
fi

exit 0
