#!/bin/bash
# scripts/session-team-hygiene.sh
# TLC-003: Session startup orphan detection hook.
# Runs once at session start. Scans for orphaned rune-*/arc-* team dirs
# and stale state files. Reports findings to user.
#
# SessionStart hooks CANNOT block the session.
# Output on stdout is shown to Claude as context.
#
# Hook events: SessionStart
# Matcher: startup (only on fresh session start, not resume/clear/compact)
# Timeout: 5s

set -euo pipefail
umask 077

# Guard: jq dependency
if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(head -c 1048576)

# Extract CWD for state file scan
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then exit 0; fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || { exit 0; }
if [[ -z "$CWD" || "$CWD" != /* ]]; then exit 0; fi

CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

# FIX-1: CHOME absoluteness guard
if [[ -z "$CHOME" ]] || [[ "$CHOME" != /* ]]; then
  exit 0
fi

# Count orphaned team dirs (older than 30 min)
orphan_count=0
orphan_names=()
if [[ -d "$CHOME/teams/" ]]; then
  while IFS= read -r dir; do
    dirname=$(basename "$dir")
    if [[ "$dirname" =~ ^[a-zA-Z0-9_-]+$ ]] && [[ ! -L "$dir" ]]; then
      orphan_names+=("$dirname")
      ((orphan_count++))
    fi
  done < <(find "$CHOME/teams/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" \) -mmin +30 2>/dev/null)
fi

# Count stale state files
stale_state_count=0

# FIX-3: Handle both bash (nullglob) and zsh (NOMATCH) shell environments
if [[ -n "${ZSH_VERSION:-}" ]]; then
  setopt nullglob 2>/dev/null
else
  shopt -s nullglob 2>/dev/null
fi

for f in "${CWD}"/tmp/.rune-review-*.json "${CWD}"/tmp/.rune-audit-*.json "${CWD}"/tmp/.rune-work-*.json "${CWD}"/tmp/.rune-mend-*.json "${CWD}"/tmp/.rune-forge-*.json; do
  if [[ -f "$f" ]]; then
    # Check if status is "active" and file is older than 30 min
    # FIX-2: Use epoch 0 fallback — if stat fails, (now - 0) / 60 = huge number → triggers stale
    # This is correct: stat failure means we can't determine age, so assume stale (conservative)
    file_mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)
    file_age_min=$(( ($(date +%s) - file_mtime) / 60 ))
    if [[ $file_age_min -gt 30 ]] && grep -q '"active"' "$f" 2>/dev/null; then
      ((stale_state_count++))
    fi
  fi
done

if [[ -n "${ZSH_VERSION:-}" ]]; then
  unsetopt nullglob 2>/dev/null
else
  shopt -u nullglob 2>/dev/null
fi

# Report if anything found
if [[ $orphan_count -gt 0 ]] || [[ $stale_state_count -gt 0 ]]; then
  echo "TLC-003 SESSION HYGIENE: Found ${orphan_count} orphaned team dir(s) and ${stale_state_count} stale state file(s) from prior sessions. Run /rune:rest --heal to clean up. Orphans: ${orphan_names[*]:0:5}"
fi

exit 0
