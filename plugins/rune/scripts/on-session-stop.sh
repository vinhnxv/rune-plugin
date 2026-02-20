#!/bin/bash
# scripts/on-session-stop.sh
# STOP-001: Detects active Rune workflows and blocks session stop with cleanup guidance.
#
# When a user attempts to stop the session while Rune workflows are active (teams,
# arc checkpoints, or workflow state files), this hook blocks the stop and provides
# instructions for proper cleanup.
#
# DESIGN PRINCIPLES:
#   1. Fail-open — if anything goes wrong, allow the stop (exit 0)
#   2. Loop prevention — check stop_hook_active field to avoid re-entry
#   3. rune-*/arc-* prefix filter (never touch foreign plugin state)
#   4. Parameter expansion for basename (${dir##*/}) — no xargs
#
# Hook event: Stop
# Timeout: 5s
# Exit 0 with no output: Allow stop
# Exit 0 with hookSpecificOutput decision=block: Block stop with guidance

set -euo pipefail
umask 077

# ── GUARD 1: jq dependency (fail-open) ──
if ! command -v jq &>/dev/null; then
  exit 0
fi

# ── GUARD 2: Input size cap (SEC-2: 1MB DoS prevention) ──
INPUT=$(head -c 1048576)

# ── GUARD 3: Loop prevention ──
# If stop_hook_active is true, we are being called recursively — allow stop immediately
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // empty' 2>/dev/null || true)
if [[ "$STOP_HOOK_ACTIVE" == "true" ]]; then
  exit 0
fi

# ── GUARD 4: CWD extraction and canonicalization ──
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then
  exit 0
fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
if [[ -z "$CWD" || "$CWD" != /* ]]; then
  exit 0
fi

# ── CHOME resolution ──
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [[ -z "$CHOME" ]] || [[ "$CHOME" != /* ]]; then
  exit 0
fi

# ── SCAN FOR ACTIVE WORKFLOWS ──
active_workflows=()

# 1. Scan for active Rune/Arc teams in CHOME/teams/
if [[ -d "$CHOME/teams/" ]]; then
  for dir in "$CHOME/teams/"*/; do
    [[ ! -d "$dir" ]] && continue
    [[ -L "$dir" ]] && continue
    dirname="${dir%/}"
    dirname="${dirname##*/}"
    # Only rune-* and arc-* teams (not goldmask-*)
    if [[ "$dirname" == rune-* || "$dirname" == arc-* ]] && [[ "$dirname" != goldmask-* ]]; then
      # Validate safe characters
      [[ "$dirname" =~ ^[a-zA-Z0-9_-]+$ ]] || continue
      active_workflows+=("team:${dirname}")
    fi
  done
fi

# 2. Scan for workflow state files in tmp/
#    Covers 7 workflow types: review, audit, work, mend, plan, forge, inspect
if [[ -d "${CWD}/tmp/" ]]; then
  shopt -s nullglob
  for f in "${CWD}/tmp/"/.rune-review-*.json \
           "${CWD}/tmp/"/.rune-audit-*.json \
           "${CWD}/tmp/"/.rune-work-*.json \
           "${CWD}/tmp/"/.rune-mend-*.json \
           "${CWD}/tmp/"/.rune-plan-*.json \
           "${CWD}/tmp/"/.rune-forge-*.json \
           "${CWD}/tmp/"/.rune-inspect-*.json; do
    [[ ! -f "$f" ]] && continue
    [[ -L "$f" ]] && continue
    # Only consider files with "active" status
    if grep -q '"active"' "$f" 2>/dev/null; then
      fname="${f##*/}"
      active_workflows+=("state:${fname}")
    fi
  done
  shopt -u nullglob
fi

# 3. Scan for arc checkpoints with in_progress phases
#    Arc checkpoints live at .claude/arc/{id}/checkpoint.json
if [[ -d "${CWD}/.claude/arc/" ]]; then
  shopt -s nullglob
  for f in "${CWD}/.claude/arc/"*/checkpoint.json; do
    [[ ! -f "$f" ]] && continue
    [[ -L "$f" ]] && continue
    if jq -e '.phases | to_entries | map(.value.status) | any(. == "in_progress")' "$f" >/dev/null 2>&1; then
      arc_id="${f%/*}"
      arc_id="${arc_id##*/}"
      active_workflows+=("arc:${arc_id}")
    fi
  done
  shopt -u nullglob
fi

# ── DECISION ──
if [[ ${#active_workflows[@]} -eq 0 ]]; then
  # No active workflows — allow stop
  exit 0
fi

# Build human-readable workflow list
workflow_list=""
for w in "${active_workflows[@]}"; do
  workflow_list="${workflow_list}  - ${w}\n"
done

# Build cleanup instructions based on detected types
cleanup_instructions="To clean up before stopping:"
has_teams=false
has_arc=false
for w in "${active_workflows[@]}"; do
  case "$w" in
    team:*) has_teams=true ;;
    arc:*)  has_arc=true ;;
  esac
done

if [[ "$has_arc" == "true" ]]; then
  cleanup_instructions="${cleanup_instructions}\n  1. Run /rune:cancel-arc to cancel the active arc pipeline"
fi
if [[ "$has_teams" == "true" ]]; then
  cleanup_instructions="${cleanup_instructions}\n  2. Run /rune:rest to clean up workflow artifacts"
  cleanup_instructions="${cleanup_instructions}\n  3. Or shut down teams manually with TeamDelete"
fi

# Build reason message
reason="STOP-001: Active Rune workflow(s) detected:\\n${workflow_list}\\n${cleanup_instructions}"

# Output blocking JSON with hookSpecificOutput wrapper
jq -n --arg reason "$reason" '{
  hookSpecificOutput: {
    hookEventName: "Stop",
    decision: "block",
    reason: $reason
  }
}'
exit 0
