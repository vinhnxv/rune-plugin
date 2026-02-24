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
#      - tmp/.rune-inspect-*.json with "active" status
#      - tmp/.rune-mend-*.json with "active" status
#      - tmp/.rune-plan-*.json with "active" status
#      - tmp/.rune-forge-*.json with "active" status
#   3. If active workflow found, verify Task input includes team_name
#   4. Block if team_name missing — output deny JSON
#
# Exit 0 with hookSpecificOutput.permissionDecision="deny" JSON = tool call blocked.
# Exit 0 without JSON (or with permissionDecision="allow") = tool call allowed.
# Exit 2 = hook error, stderr fed to Claude (not used by this script).

set -euo pipefail
umask 077

# Pre-flight: jq is required for JSON parsing.
# If missing, exit 0 (non-blocking) — allow rather than crash.
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — enforce-teams.sh hook is inactive" >&2
  exit 0
fi

INPUT=$(head -c 1048576)  # SEC-2: 1MB cap to prevent unbounded stdin read

# Fast path: if caller is team-lead (not subagent), check for team_name in input.
# Team leads MUST also use team_name — this is the whole point of ATE-1.

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
if [[ "$TOOL_NAME" != "Task" ]]; then
  exit 0
fi

# QUAL-5: Canonicalize CWD to resolve symlinks (matches on-task-completed.sh pattern)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
if [[ -z "$CWD" || "$CWD" != /* ]]; then exit 0; fi

# Check for active Rune workflows
# NOTE: File-based state detection has inherent TOCTOU window (SEC-3). A workflow
# could start between this check and the Task executing. Claude Code processes tool
# calls sequentially within a session, making the race window effectively zero.
#
# STALENESS GUARD (v1.61.0): Skip files older than 30 minutes (mtime-based).
# Stale checkpoints from crashed/interrupted sessions should not block new work.
# Mirrors the 30-min threshold from enforce-team-lifecycle.sh (TLC-001).
STALE_THRESHOLD_MIN=30
active_workflow=""

# ── Session identity for cross-session ownership filtering ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=resolve-session-identity.sh
source "${SCRIPT_DIR}/resolve-session-identity.sh"

# Check arc checkpoints (skip stale files older than STALE_THRESHOLD_MIN)
if [[ -d "${CWD}/.claude/arc" ]]; then
  while IFS= read -r f; do
    if jq -e '(.phase == "in_progress") or (.status == "in_progress") or ([.phases[]?.status] | any(. == "in_progress"))' "$f" &>/dev/null; then
      # ── Ownership filter: skip checkpoints from other sessions ──
      stored_cfg=$(jq -r '.config_dir // empty' "$f" 2>/dev/null || true)
      stored_pid=$(jq -r '.owner_pid // empty' "$f" 2>/dev/null || true)
      if [[ -n "$stored_cfg" && "$stored_cfg" != "$RUNE_CURRENT_CFG" ]]; then continue; fi
      if [[ -n "$stored_pid" && "$stored_pid" =~ ^[0-9]+$ && "$stored_pid" != "$PPID" ]]; then
        rune_pid_alive "$stored_pid" && continue  # alive = different session
      fi
      active_workflow=1
      break
    fi
  done < <(find "${CWD}/.claude/arc" -name checkpoint.json -maxdepth 2 -type f -mmin -${STALE_THRESHOLD_MIN} 2>/dev/null)
fi

# Check review/audit/work state files (skip stale files)
# SEC-1 FIX: Use nullglob + flattened loop to prevent word splitting on paths with spaces
if [[ -z "$active_workflow" ]]; then
  shopt -s nullglob
  for f in "${CWD}"/tmp/.rune-review-*.json "${CWD}"/tmp/.rune-audit-*.json \
           "${CWD}"/tmp/.rune-work-*.json "${CWD}"/tmp/.rune-inspect-*.json \
           "${CWD}"/tmp/.rune-mend-*.json "${CWD}"/tmp/.rune-plan-*.json \
           "${CWD}"/tmp/.rune-forge-*.json; do
    # Skip files older than STALE_THRESHOLD_MIN minutes
    if [[ -f "$f" ]] && find "$f" -maxdepth 0 -mmin -${STALE_THRESHOLD_MIN} -print -quit 2>/dev/null | grep -q . && jq -e '.status == "active"' "$f" &>/dev/null; then
      # ── Ownership filter: skip state files from other sessions ──
      stored_cfg=$(jq -r '.config_dir // empty' "$f" 2>/dev/null || true)
      stored_pid=$(jq -r '.owner_pid // empty' "$f" 2>/dev/null || true)
      if [[ -n "$stored_cfg" && "$stored_cfg" != "$RUNE_CURRENT_CFG" ]]; then continue; fi
      if [[ -n "$stored_pid" && "$stored_pid" =~ ^[0-9]+$ && "$stored_pid" != "$PPID" ]]; then
        rune_pid_alive "$stored_pid" && continue  # alive = different session
      fi
      active_workflow=1
      break
    fi
  done
  shopt -u nullglob
fi

# No active workflow — allow all Task calls
if [[ -z "$active_workflow" ]]; then
  exit 0
fi

# Active workflow detected — verify Task input includes team_name
# BACK-2 FIX: Single-pass jq extraction (avoids fragile double-parse of tool_input)
HAS_TEAM_NAME=$(echo "$INPUT" | jq -r 'if .tool_input.team_name and (.tool_input.team_name | length > 0) then "yes" else "no" end' 2>/dev/null || echo "no")

if [[ "$HAS_TEAM_NAME" == "yes" ]]; then
  exit 0
fi

# ATE-1 EXEMPTION: Read-only built-in subagent types are safe without team_name.
# Explore (Haiku, read-only) and Plan (read-only) agents produce bounded output
# and cannot modify files — no risk of context explosion. The orchestrator needs
# these for quick codebase queries during workflow phases.
SUBAGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null || true)
if [[ "$SUBAGENT_TYPE" == "Explore" || "$SUBAGENT_TYPE" == "Plan" ]]; then
  exit 0
fi

# ATE-1 VIOLATION: Task call without team_name during active workflow
# Output deny decision with actionable feedback
cat << 'DENY_JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "ATE-1: Bare Task call blocked during active Rune workflow. All multi-agent phases MUST use Agent Teams. Add team_name to your Task call. Example: Task({ team_name: 'arc-forge-{id}', name: 'agent-name', subagent_type: 'general-purpose', ... }). See arc skill (skills/arc/SKILL.md) 'CRITICAL — Agent Teams Enforcement' section.",
    "additionalContext": "BLOCKED by enforce-teams.sh hook. You MUST create a team with TeamCreate first, then pass team_name to all Task calls. Using bare subagent types like 'rune:utility:scroll-reviewer' or 'compound-engineering:research:best-practices-researcher' as subagent_type bypasses Agent Teams and causes context explosion. Always use subagent_type: 'general-purpose' and inject agent identity via the prompt parameter."
  }
}
DENY_JSON
exit 0
