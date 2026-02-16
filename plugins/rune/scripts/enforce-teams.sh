#!/bin/bash
# scripts/enforce-teams.sh
# ATE-1: Enforce Agent Teams usage during active Rune multi-agent workflows.
# Blocks bare Task calls (without team_name) when an arc/review/audit/work
# workflow is active. Prevents context explosion from subagent output flowing
# into the orchestrator's context window.
#
# Detection strategy:
#   1. Check if tool_name is "Task" (only tool this hook targets)
#   2. Check for active Rune workflow via state files:
#      - .claude/arc/*/checkpoint.json with "in_progress" phase
#      - tmp/.rune-review-*.json with "active" status
#      - tmp/.rune-audit-*.json with "active" status
#      - tmp/.rune-work-*.json with "active" status
#   3. If active workflow found, verify Task input includes team_name
#   4. Block if team_name missing — output deny JSON
#
# Exit 0 with deny JSON = blocked. Exit 0 without JSON = allowed.

set -euo pipefail
umask 077

# Pre-flight: jq is required for JSON parsing.
# If missing, exit 0 (non-blocking) — allow rather than crash.
if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)

# Fast path: if caller is team-lead (not subagent), check for team_name in input.
# Team leads MUST also use team_name — this is the whole point of ATE-1.

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
if [[ "$TOOL_NAME" != "Task" ]]; then
  exit 0
fi

CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi

# Check for active Rune workflows
active_workflow=""

# Check arc checkpoints
if [[ -d "${CWD}/.claude/arc" ]]; then
  while IFS= read -r f; do
    if grep -q '"in_progress"' "$f" 2>/dev/null; then
      active_workflow="arc ($(basename "$(dirname "$f")"))"
      break
    fi
  done < <(find "${CWD}/.claude/arc" -name checkpoint.json -maxdepth 2 2>/dev/null)
fi

# Check review/audit/work state files
if [[ -z "$active_workflow" ]]; then
  for pattern in "${CWD}"/tmp/.rune-review-*.json "${CWD}"/tmp/.rune-audit-*.json "${CWD}"/tmp/.rune-work-*.json; do
    for f in $pattern; do
      if [[ -f "$f" ]] && grep -q '"active"' "$f" 2>/dev/null; then
        active_workflow="$(basename "$f" .json)"
        break 2
      fi
    done
  done
fi

# No active workflow — allow all Task calls
if [[ -z "$active_workflow" ]]; then
  exit 0
fi

# Active workflow detected — verify Task input includes team_name
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // empty' 2>/dev/null || true)
if [[ -z "$TOOL_INPUT" ]]; then
  exit 0
fi

# Check if team_name is present and non-empty in the Task input
HAS_TEAM_NAME=$(echo "$TOOL_INPUT" | jq -r 'if .team_name and (.team_name | length > 0) then "yes" else "no" end' 2>/dev/null || echo "no")

if [[ "$HAS_TEAM_NAME" == "yes" ]]; then
  exit 0
fi

# ATE-1 VIOLATION: Task call without team_name during active workflow
# Output deny decision with actionable feedback
cat << 'DENY_JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "ATE-1: Bare Task call blocked during active Rune workflow. All multi-agent phases MUST use Agent Teams. Add team_name to your Task call. Example: Task({ team_name: 'arc-forge-{id}', name: 'agent-name', subagent_type: 'general-purpose', ... }). See arc.md 'CRITICAL — Agent Teams Enforcement' section.",
    "additionalContext": "BLOCKED by enforce-teams.sh hook. You MUST create a team with TeamCreate first, then pass team_name to all Task calls. Using bare subagent types like 'rune:utility:scroll-reviewer' or 'compound-engineering:research:best-practices-researcher' as subagent_type bypasses Agent Teams and causes context explosion. Always use subagent_type: 'general-purpose' and inject agent identity via the prompt parameter."
  }
}
DENY_JSON
exit 0
