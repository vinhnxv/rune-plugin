#!/bin/bash
# scripts/verify-team-cleanup.sh
# TLC-002: Post-TeamDelete verification hook.
# Runs AFTER every TeamDelete call. Checks if zombie team dirs remain.
#
# NOTE: TeamDelete() takes no arguments — it targets the caller's active team.
# The SDK doesn't expose which team was deleted in PostToolUse input.
# Strategy: Scan for ALL rune-*/arc-* dirs and report any that exist.
# This is broader than needed but catches zombies reliably.
#
# PostToolUse hooks CANNOT block — they are informational only.
# Output on stdout is shown in transcript.
#
# Hook events: PostToolUse:TeamDelete
# Timeout: 5s

set -euo pipefail
umask 077

# Guard: jq dependency
if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(head -c 1048576)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
if [[ "$TOOL_NAME" != "TeamDelete" ]]; then
  exit 0
fi

# Check for remaining rune-*/arc-* team dirs
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

# FIX-1: CHOME absoluteness guard
if [[ -z "$CHOME" ]] || [[ "$CHOME" != /* ]]; then
  exit 0
fi

remaining=()
if [[ -d "$CHOME/teams/" ]]; then
  while IFS= read -r dir; do
    dirname=$(basename "$dir")
    if [[ "$dirname" =~ ^[a-zA-Z0-9_-]+$ ]] && [[ ! -L "$dir" ]]; then
      remaining+=("$dirname")
    fi
  done < <(find "$CHOME/teams/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" \) 2>/dev/null)
fi

if [[ ${#remaining[@]} -gt 0 ]]; then
  echo "TLC-002 POST-DELETE: ${#remaining[@]} rune/arc team dir(s) still exist after TeamDelete: ${remaining[*]:0:5}. These may be from other workflows or zombie state. Run /rune:rest --heal if unexpected."
fi

exit 0
