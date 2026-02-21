#!/bin/bash
# scripts/arc-batch-stop-hook.sh
# ARC-BATCH-LOOP: Stop hook implementing the ralph-wiggum self-invoking loop pattern.
#
# Each arc runs as a native Claude Code turn. When Claude finishes responding,
# this hook intercepts the Stop event, reads batch state from a file, determines
# the next plan, and re-injects the arc prompt for the next plan.
#
# Inspired by: https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum
#
# State file: .claude/arc-batch-loop.local.md (YAML frontmatter)
# Decision output: {"decision":"block","reason":"<prompt>","systemMessage":"<info>"}
#
# Hook event: Stop
# Timeout: 15s
# Exit 0 with no output: No active batch — allow stop
# Exit 0 with top-level decision=block: Re-inject next arc prompt

set -euo pipefail
trap 'exit 0' ERR
umask 077

# ── GUARD 1: jq dependency (fail-open) ──
if ! command -v jq &>/dev/null; then
  exit 0
fi

# ── GUARD 2: Input size cap (SEC-2: 1MB DoS prevention) ──
INPUT=$(head -c 1048576 2>/dev/null || true)

# ── GUARD 3: CWD extraction ──
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
if [[ -z "$CWD" || "$CWD" != /* ]]; then
  exit 0
fi

# ── GUARD 4: State file existence ──
STATE_FILE="${CWD}/.claude/arc-batch-loop.local.md"
if [[ ! -f "$STATE_FILE" ]]; then
  # No active batch — allow stop
  exit 0
fi

# ── GUARD 5: Symlink rejection ──
if [[ -L "$STATE_FILE" ]]; then
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

# ── Parse YAML frontmatter from state file ──
# Format: --- ... --- with key: value pairs
FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$STATE_FILE" 2>/dev/null | sed '1d;$d')
if [[ -z "$FRONTMATTER" ]]; then
  # Corrupted state file — fail-safe: remove and allow stop
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

# Extract fields using grep+sed (portable, no awk dependency)
get_field() {
  local field="$1"
  echo "$FRONTMATTER" | grep "^${field}:" | sed "s/^${field}:[[:space:]]*//" | sed 's/^"//' | sed 's/"$//' | head -1
}

ACTIVE=$(get_field "active")
ITERATION=$(get_field "iteration")
MAX_ITERATIONS=$(get_field "max_iterations")
TOTAL_PLANS=$(get_field "total_plans")
NO_MERGE=$(get_field "no_merge")
PLUGIN_DIR=$(get_field "plugin_dir")
PLANS_FILE=$(get_field "plans_file")
PROGRESS_FILE=$(get_field "progress_file")
STARTED_AT=$(get_field "started_at")

# ── GUARD 6: Validate active flag ──
if [[ "$ACTIVE" != "true" ]]; then
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

# ── GUARD 7: Validate numeric fields ──
if ! [[ "$ITERATION" =~ ^[0-9]+$ ]] || ! [[ "$TOTAL_PLANS" =~ ^[0-9]+$ ]]; then
  # Corrupted numeric fields — fail-safe cleanup
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

# ── GUARD 8: Max iterations check ──
if [[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]] && [[ "$MAX_ITERATIONS" -gt 0 ]] && [[ "$ITERATION" -ge "$MAX_ITERATIONS" ]]; then
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

# ── Read batch progress ──
if [[ ! -f "${CWD}/${PROGRESS_FILE}" ]]; then
  # Progress file missing — fail-safe cleanup
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

PROGRESS_CONTENT=$(cat "${CWD}/${PROGRESS_FILE}" 2>/dev/null || true)
if [[ -z "$PROGRESS_CONTENT" ]]; then
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

# ── Mark current in_progress plan as completed ──
UPDATED_PROGRESS=$(echo "$PROGRESS_CONTENT" | jq --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
  .updated_at = $ts |
  (.plans[] | select(.status == "in_progress")) |= (
    .status = "completed" |
    .completed_at = $ts
  )
' 2>/dev/null || true)

if [[ -z "$UPDATED_PROGRESS" ]]; then
  # jq failed — progress JSON is corrupted
  rm -f "$STATE_FILE" 2>/dev/null
  exit 0
fi

# Write updated progress
echo "$UPDATED_PROGRESS" > "${CWD}/${PROGRESS_FILE}"

# ── Find next pending plan ──
NEXT_PLAN=$(echo "$UPDATED_PROGRESS" | jq -r '
  [.plans[] | select(.status == "pending")] | first | .path // empty
' 2>/dev/null || true)

if [[ -z "$NEXT_PLAN" ]]; then
  # ── ALL PLANS DONE ──
  # Calculate duration
  ENDED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  COMPLETED_COUNT=$(echo "$UPDATED_PROGRESS" | jq '[.plans[] | select(.status == "completed")] | length' 2>/dev/null || echo 0)
  FAILED_COUNT=$(echo "$UPDATED_PROGRESS" | jq '[.plans[] | select(.status == "failed")] | length' 2>/dev/null || echo 0)

  # Update progress file to completed
  FINAL_PROGRESS=$(echo "$UPDATED_PROGRESS" | jq --arg ts "$ENDED_AT" '
    .status = "completed" |
    .completed_at = $ts |
    .updated_at = $ts
  ' 2>/dev/null || true)

  if [[ -n "$FINAL_PROGRESS" ]]; then
    echo "$FINAL_PROGRESS" > "${CWD}/${PROGRESS_FILE}"
  fi

  # Remove state file — next Stop event will allow session end
  rm -f "$STATE_FILE" 2>/dev/null

  # Block stop one more time to present summary
  SUMMARY_PROMPT="Arc Batch Complete — All Plans Processed

Read the batch progress file at ${PROGRESS_FILE} and present a summary:

1. Read ${PROGRESS_FILE}
2. For each plan: show status (completed/failed), path, and duration
3. Show total: ${COMPLETED_COUNT} completed, ${FAILED_COUNT} failed
4. If any failed: suggest /rune:arc-batch --resume

Present the summary clearly and concisely."

  SYSTEM_MSG="Arc batch loop completed. Iteration ${ITERATION}/${TOTAL_PLANS}. All plans processed."

  jq -n \
    --arg prompt "$SUMMARY_PROMPT" \
    --arg msg "$SYSTEM_MSG" \
    '{
      decision: "block",
      reason: $prompt,
      systemMessage: $msg
    }'
  exit 0
fi

# ── MORE PLANS TO PROCESS ──
# Increment iteration in state file (portable sed)
NEW_ITERATION=$((ITERATION + 1))
if [[ "$(uname)" == "Darwin" ]]; then
  sed -i '' "s/^iteration: ${ITERATION}$/iteration: ${NEW_ITERATION}/" "$STATE_FILE"
else
  sed -i "s/^iteration: ${ITERATION}$/iteration: ${NEW_ITERATION}/" "$STATE_FILE"
fi

# Mark next plan as in_progress
NEXT_PROGRESS=$(echo "$UPDATED_PROGRESS" | jq --arg plan "$NEXT_PLAN" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
  .updated_at = $ts |
  (.plans[] | select(.path == $plan and .status == "pending")) |= (
    .status = "in_progress" |
    .started_at = $ts
  )
' 2>/dev/null || true)

if [[ -n "$NEXT_PROGRESS" ]]; then
  echo "$NEXT_PROGRESS" > "${CWD}/${PROGRESS_FILE}"
fi

# ── Build merge flag ──
MERGE_FLAG=""
if [[ "$NO_MERGE" == "true" ]]; then
  MERGE_FLAG=" --no-merge"
fi

# ── Construct arc prompt for next plan ──
ARC_PROMPT="Arc Batch — Iteration ${NEW_ITERATION}/${TOTAL_PLANS}

You are continuing the arc batch pipeline. Process the next plan.

1. Verify git state is clean: git status
2. If dirty or not on main: git checkout main && git pull --ff-only origin main
3. Clean stale workflow state: rm -f tmp/.rune-*.json 2>/dev/null
4. Clean stale teams:
   CHOME=\"\${CLAUDE_CONFIG_DIR:-\$HOME/.claude}\"
   find \"\$CHOME/teams/\" -maxdepth 1 -type d \\( -name \"rune-*\" -o -name \"arc-*\" \\) -exec rm -rf {} + 2>/dev/null
   find \"\$CHOME/tasks/\" -maxdepth 1 -type d \\( -name \"rune-*\" -o -name \"arc-*\" \\) -exec rm -rf {} + 2>/dev/null
5. Execute: /rune:arc ${NEXT_PLAN} --skip-freshness${MERGE_FLAG}

IMPORTANT: Execute autonomously — do NOT ask for confirmation.
Plan: ${NEXT_PLAN}"

SYSTEM_MSG="Arc batch loop — iteration ${NEW_ITERATION} of ${TOTAL_PLANS}. Processing: ${NEXT_PLAN}"

# ── Output blocking JSON — Stop hooks use top-level decision/reason ──
jq -n \
  --arg prompt "$ARC_PROMPT" \
  --arg msg "$SYSTEM_MSG" \
  '{
    decision: "block",
    reason: $prompt,
    systemMessage: $msg
  }'
exit 0
