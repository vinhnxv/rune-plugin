#!/bin/bash
# scripts/on-session-stop.sh
# STOP-001: Auto-cleans stale Rune workflows on session stop.
#
# When a session ends, this hook automatically cleans up orphaned resources
# instead of blocking the user. Resources cleaned:
#   1. Team dirs (rune-*/arc-*) — rm team + task dirs
#   2. State files (.rune-*.json with status "active") — set status to "stopped"
#   3. Arc checkpoints with in_progress phases — set to "cancelled"
#
# DESIGN PRINCIPLES:
#   1. Fail-open — if anything goes wrong, allow the stop (exit 0)
#   2. Loop prevention — check stop_hook_active field to avoid re-entry
#   3. rune-*/arc-* prefix filter (never touch foreign plugin state)
#   4. Auto-clean, don't block — "janitor on the way out, not security guard"
#   5. Report what was cleaned via additionalContext (informational)
#
# Hook event: Stop
# Timeout: 5s
# Exit 0 with no output: Allow stop (nothing to clean)
# Exit 0 with stdout summary: Report what was cleaned (informational, non-blocking)

set -euo pipefail
trap 'exit 0' ERR
umask 077

# ── GUARD 1: jq dependency (fail-open) ──
if ! command -v jq &>/dev/null; then
  exit 0
fi

# ── GUARD 2: Input size cap (SEC-2: 1MB DoS prevention) ──
INPUT=$(head -c 1048576 2>/dev/null || true)

# ── GUARD 3: Loop prevention ──
# If stop_hook_active is true, we already cleaned on a previous pass — allow stop
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

# ── GUARD 5: Defer to arc-batch stop hook (with ownership check) ──
# When arc-batch loop is active AND belongs to THIS session, arc-batch-stop-hook.sh
# handles the Stop event. Only defer if we're the owning session.
# If the batch belongs to another session, proceed with normal cleanup for THIS session.
if [[ -f "${CWD}/.claude/arc-batch-loop.local.md" ]] && [[ ! -L "${CWD}/.claude/arc-batch-loop.local.md" ]]; then
  _BATCH_FM=$(sed -n '/^---$/,/^---$/p' "${CWD}/.claude/arc-batch-loop.local.md" 2>/dev/null | sed '1d;$d')
  _BATCH_CFG=$(echo "$_BATCH_FM" | grep "^config_dir:" | sed 's/^config_dir:[[:space:]]*//' | sed 's/^"//' | sed 's/"$//' | head -1)
  _BATCH_PID=$(echo "$_BATCH_FM" | grep "^owner_pid:" | sed 's/^owner_pid:[[:space:]]*//' | sed 's/^"//' | sed 's/"$//' | head -1)
  _CURRENT_CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  _CURRENT_CFG=$(cd "$_CURRENT_CFG" 2>/dev/null && pwd -P || echo "$_CURRENT_CFG")

  _is_owner=true
  # Check config_dir
  if [[ -n "$_BATCH_CFG" && "$_BATCH_CFG" != "$_CURRENT_CFG" ]]; then
    _is_owner=false
  fi
  # Check PID
  if [[ "$_is_owner" == "true" && -n "$_BATCH_PID" && "$_BATCH_PID" =~ ^[0-9]+$ && "$_BATCH_PID" != "$PPID" ]]; then
    if kill -0 "$_BATCH_PID" 2>/dev/null; then
      _is_owner=false
    fi
  fi

  if [[ "$_is_owner" == "true" ]]; then
    # This session owns the batch — defer to arc-batch-stop-hook.sh
    exit 0
  fi
  # Not our batch — proceed with normal cleanup for THIS session
fi

# ── CHOME resolution ──
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [[ -z "$CHOME" ]] || [[ "$CHOME" != /* ]]; then
  exit 0
fi

# ── BUILD STATE FILE TEAM SET ──
# Collect team names referenced by state files in THIS project's tmp/.
# This scopes cleanup to teams owned by workflows in the current CWD,
# preventing cross-session interference when multiple sessions run concurrently.
state_team_names=()
if [[ -d "${CWD}/tmp/" ]]; then
  shopt -s nullglob
  for sf in "${CWD}/tmp/"/.rune-*.json; do
    [[ ! -f "$sf" ]] && continue
    [[ -L "$sf" ]] && continue
    # Extract team_name ONLY from active state files (skip completed/stopped/failed)
    # This prevents matching old state files from previous workflows
    tname=$(jq -r 'select(.status == "active") | .team_name // empty' "$sf" 2>/dev/null || true)
    if [[ -n "$tname" ]] && [[ "$tname" =~ ^[a-zA-Z0-9_-]+$ ]]; then
      state_team_names+=("$tname")
    fi
  done
  shopt -u nullglob
fi

# ── AUTO-CLEAN PHASE 1: Team dirs (rune-*/arc-*) ──
# Strategy:
#   - Teams WITH a matching state file in CWD → always clean (belongs to this project)
#   - Teams WITHOUT a state file → only clean if older than 30 min (orphan fallback)
# This protects active teams from other sessions while still catching true orphans.
cleaned_teams=()
if [[ -d "$CHOME/teams/" ]]; then
  NOW=$(date +%s)
  for dir in "$CHOME/teams/"*/; do
    [[ ! -d "$dir" ]] && continue
    [[ -L "$dir" ]] && continue
    dirname="${dir%/}"
    dirname="${dirname##*/}"
    if [[ "$dirname" == rune-* || "$dirname" == arc-* ]] && [[ "$dirname" != goldmask-* ]]; then
      [[ "$dirname" =~ ^[a-zA-Z0-9_-]+$ ]] || continue

      # Check if this team has a corresponding state file in CWD
      has_state_file=false
      for stn in "${state_team_names[@]+"${state_team_names[@]}"}"; do
        if [[ "$stn" == "$dirname" ]]; then
          has_state_file=true
          break
        fi
      done

      should_clean=false
      if [[ "$has_state_file" == "true" ]]; then
        # State file in CWD → belongs to this project's workflow → safe to clean
        should_clean=true
      else
        # No state file → only clean if older than 30 min (true orphan)
        dir_mtime=$(stat -f %m "$dir" 2>/dev/null || stat -c %Y "$dir" 2>/dev/null || echo 0)
        dir_age_min=$(( (NOW - dir_mtime) / 60 ))
        if [[ $dir_age_min -gt 30 ]]; then
          should_clean=true
        fi
      fi

      if [[ "$should_clean" == "true" ]]; then
        # SEC-1: Re-check symlink immediately before rm-rf (TOCTOU mitigation)
        if [[ ! -L "$CHOME/teams/${dirname}" ]]; then
          rm -rf "$CHOME/teams/${dirname}/" "$CHOME/tasks/${dirname}/" 2>/dev/null
          cleaned_teams+=("$dirname")
        fi
      fi
    fi
  done
fi

# ── AUTO-CLEAN PHASE 2: State files (set active → stopped) ──
cleaned_states=()
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
    if jq -e '.status == "active"' "$f" >/dev/null 2>&1; then
      # Update status to "stopped" (not "completed" — distinguishes clean exit from crash)
      jq '.status = "stopped" | .stopped_by = "STOP-001"' "$f" > "${f}.tmp" 2>/dev/null && mv "${f}.tmp" "$f" 2>/dev/null
      fname="${f##*/}"
      cleaned_states+=("$fname")
    fi
  done
  shopt -u nullglob
fi

# ── AUTO-CLEAN PHASE 3: Arc checkpoints (in_progress → cancelled) ──
# Only cancel checkpoints older than 5 min to avoid hitting active arc in another session.
# 5 min is shorter than the 30 min team threshold because arc checkpoints are CWD-scoped
# (less cross-session risk) and in_progress phases from crashed sessions should be cancelled quickly.
cleaned_arcs=()
if [[ -d "${CWD}/.claude/arc/" ]]; then
  [[ -z "${NOW:-}" ]] && NOW=$(date +%s)
  shopt -s nullglob
  for f in "${CWD}/.claude/arc/"*/checkpoint.json; do
    [[ ! -f "$f" ]] && continue
    [[ -L "$f" ]] && continue
    # Age guard: skip checkpoints modified within the last 5 minutes
    f_mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)
    f_age_min=$(( (NOW - f_mtime) / 60 ))
    if [[ $f_age_min -le 5 ]]; then
      continue
    fi
    if jq -e '.phases | to_entries | map(.value.status) | any(. == "in_progress")' "$f" >/dev/null 2>&1; then
      # Cancel all in_progress phases
      jq '.phases |= with_entries(if .value.status == "in_progress" then .value.status = "cancelled" else . end)' "$f" > "${f}.tmp" 2>/dev/null && mv "${f}.tmp" "$f" 2>/dev/null
      arc_id="${f%/*}"
      arc_id="${arc_id##*/}"
      cleaned_arcs+=("$arc_id")
    fi
  done
  shopt -u nullglob
fi

# ── REPORT ──
total=$((${#cleaned_teams[@]} + ${#cleaned_states[@]} + ${#cleaned_arcs[@]}))

if [[ $total -eq 0 ]]; then
  # Nothing to clean — allow stop silently
  exit 0
fi

# Build summary of what was cleaned
summary="STOP-001 AUTO-CLEANUP: Cleaned ${total} stale resource(s) on session exit."

if [[ ${#cleaned_teams[@]} -gt 0 ]]; then
  team_list="${cleaned_teams[*]:0:5}"
  summary="${summary} Teams: [${team_list}]."
  if [[ ${#cleaned_teams[@]} -gt 5 ]]; then
    summary="${summary} (+$((${#cleaned_teams[@]} - 5)) more)"
  fi
fi

if [[ ${#cleaned_states[@]} -gt 0 ]]; then
  state_list="${cleaned_states[*]:0:3}"
  summary="${summary} States: [${state_list}]."
fi

if [[ ${#cleaned_arcs[@]} -gt 0 ]]; then
  arc_list="${cleaned_arcs[*]:0:3}"
  summary="${summary} Arcs: [${arc_list}]."
fi

# Log to trace file for debugging (always, not just RUNE_TRACE)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] $summary" >> "${CWD}/tmp/.rune-stop-cleanup.log" 2>/dev/null

# Silent cleanup — allow stop immediately, no block
# Summary is echoed to stdout so Claude sees it as context (informational only)
echo "$summary"
exit 0
