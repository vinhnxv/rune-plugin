#!/bin/bash
# scripts/pre-compact-checkpoint.sh
# Saves team state before context compaction so the post-compact
# SessionStart handler can re-inject critical state into the fresh context.
#
# DESIGN PRINCIPLES:
#   1. Non-blocking — always exit 0 (compaction must never be prevented)
#   2. Atomic writes — temp+mv pattern prevents partial checkpoint files
#   3. rune-*/arc-* prefix filter (never touch foreign plugin teams)
#   4. JSON output via jq --arg (no printf or shell interpolation)
#
# Hook events: PreCompact
# Matcher: manual|auto
# Timeout: 5s
# Exit 0: Always (non-blocking)

set -euo pipefail
umask 077

# ── GUARD 1: jq dependency ──
if ! command -v jq &>/dev/null; then
  echo "WARN: jq not found — compact checkpoint will not be written" >&2
  exit 0
fi

# ── GUARD 2: Input size cap (SEC-2: 1MB DoS prevention) ──
INPUT=$(head -c 1048576)

# ── GUARD 3: CWD extraction and canonicalization ──
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then exit 0; fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
if [[ -z "$CWD" || "$CWD" != /* ]]; then exit 0; fi

# ── GUARD 4: tmp/ directory must exist ──
if [[ ! -d "${CWD}/tmp" ]]; then exit 0; fi

# ── CHOME resolution ──
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [[ -z "$CHOME" ]] || [[ "$CHOME" != /* ]]; then
  exit 0
fi

# ── Cleanup trap — remove temp files on exit ──
CHECKPOINT_TMP=""
cleanup() { [[ -n "$CHECKPOINT_TMP" ]] && rm -f "$CHECKPOINT_TMP" 2>/dev/null; return 0; }
trap cleanup EXIT

# ── FIND ACTIVE RUNE TEAM ──
# Look for rune-*/arc-* team dirs (NOT goldmask-*) — pick the most recently modified
active_team=""
if [[ -d "$CHOME/teams/" ]]; then
  while IFS= read -r dir; do
    dirname=$(basename "$dir")
    if [[ "$dirname" =~ ^[a-zA-Z0-9_-]+$ ]] && [[ ! -L "$dir" ]]; then
      active_team="$dirname"
      break  # find -printf sorts by mtime desc via sort below
    fi
  done < <(find "$CHOME/teams/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" \) -not -name "goldmask-*" 2>/dev/null | while read -r d; do
    # macOS stat: -f %m for mtime epoch
    mtime=$(stat -f %m "$d" 2>/dev/null || stat -c %Y "$d" 2>/dev/null || echo 0)
    printf '%s\t%s\n' "$mtime" "$d"
  done | sort -rn | cut -f2)
fi

# If no active team, nothing to checkpoint
if [[ -z "$active_team" ]]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreCompact",
      additionalContext: "No active Rune team found — compact checkpoint skipped."
    }
  }'
  exit 0
fi

# ── COLLECT TEAM STATE ──

# 1. Team config (members list)
team_config="{}"
config_file="$CHOME/teams/${active_team}/config.json"
if [[ -f "$config_file" ]] && [[ ! -L "$config_file" ]]; then
  team_config=$(jq -c '.' "$config_file" 2>/dev/null || echo '{}')
fi

# 2. Task list — collect from tasks directory
tasks_json="[]"
tasks_dir="$CHOME/tasks/${active_team}"
if [[ -d "$tasks_dir" ]] && [[ ! -L "$tasks_dir" ]]; then
  # Read all task JSON files, merge into array
  task_files=()
  while IFS= read -r tf; do
    if [[ -f "$tf" ]] && [[ ! -L "$tf" ]]; then
      task_files+=("$tf")
    fi
  done < <(find "$tasks_dir" -maxdepth 1 -type f -name "*.json" 2>/dev/null)

  if [[ ${#task_files[@]} -gt 0 ]]; then
    tasks_json=$(jq -s '.' "${task_files[@]}" 2>/dev/null || echo '[]')
  fi
fi

# 3. Active workflow state file (tmp/.rune-*.json)
# FW-001 FIX: Use find-based approach instead of glob loop (zsh compat — shopt unavailable on zsh)
workflow_state="{}"
workflow_file=""
workflow_file=$(find "${CWD}/tmp/" -maxdepth 1 -type f \
  \( -name ".rune-review-*.json" -o -name ".rune-audit-*.json" \
     -o -name ".rune-work-*.json" -o -name ".rune-mend-*.json" \
     -o -name ".rune-inspect-*.json" -o -name ".rune-forge-*.json" \
     -o -name ".rune-arc-*.json" \) 2>/dev/null | while read -r f; do
    [[ -L "$f" ]] && continue
    mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)
    printf '%s\t%s\n' "$mtime" "$f"
  done | sort -rn | head -1 | cut -f2)
if [[ -n "$workflow_file" ]] && [[ -f "$workflow_file" ]]; then
  workflow_state=$(jq -c '.' "$workflow_file" 2>/dev/null || echo '{}')
fi

# 4. Arc checkpoint if it exists
arc_checkpoint="{}"
arc_file="${CWD}/tmp/.arc-checkpoint.json"
if [[ -f "$arc_file" ]] && [[ ! -L "$arc_file" ]]; then
  arc_checkpoint=$(jq -c '.' "$arc_file" 2>/dev/null || echo '{}')
fi

# ── WRITE CHECKPOINT (atomic) ──
CHECKPOINT_FILE="${CWD}/tmp/.rune-compact-checkpoint.json"
CHECKPOINT_TMP="${CHECKPOINT_FILE}.tmp.$$"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if ! jq -n \
  --arg team "$active_team" \
  --arg ts "$TIMESTAMP" \
  --argjson config "$team_config" \
  --argjson tasks "$tasks_json" \
  --argjson workflow "$workflow_state" \
  --argjson arc "$arc_checkpoint" \
  '{
    team_name: $team,
    saved_at: $ts,
    team_config: $config,
    tasks: $tasks,
    workflow_state: $workflow,
    arc_checkpoint: $arc
  }' > "$CHECKPOINT_TMP" 2>/dev/null; then
  echo "WARN: Failed to write compact checkpoint" >&2
  rm -f "$CHECKPOINT_TMP" 2>/dev/null
  exit 0
fi

# SEC-003: Atomic rename
# FW-002 FIX: Use mv -f (force) instead of mv -n (no-clobber). A stale checkpoint
# with an old team name is worse than a fresh one — always write latest state.
mv -f "$CHECKPOINT_TMP" "$CHECKPOINT_FILE" 2>/dev/null || {
  rm -f "$CHECKPOINT_TMP" 2>/dev/null
  exit 0
}
CHECKPOINT_TMP=""  # Clear for cleanup trap — file was moved successfully

# ── OUTPUT: hookSpecificOutput with hookEventName ──
jq -n --arg team "$active_team" '{
  hookSpecificOutput: {
    hookEventName: "PreCompact",
    additionalContext: ("Rune compact checkpoint saved for team " + $team + ". State will be restored after compaction via session-compact-recovery.sh.")
  }
}'
exit 0
