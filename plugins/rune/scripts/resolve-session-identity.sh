#!/bin/bash
# scripts/resolve-session-identity.sh
# Resolve current session identity for cross-session ownership checks.
# Source this file — do not execute directly.
#
# Exports: RUNE_CURRENT_CFG (resolved config dir path)
#          rune_pid_alive()  (EPERM-safe PID liveness check function)
# Uses: $PPID (Claude Code process PID — available to all hooks)
#
# Pattern: Two-layer session identity
#   Layer 1: config_dir (CLAUDE_CONFIG_DIR) — installation/account isolation
#   Layer 2: owner_pid ($PPID) — process/session isolation within same account
#
# Ownership check pattern (for callers):
#   stored_cfg=$(jq -r '.config_dir // empty' "$f")
#   stored_pid=$(jq -r '.owner_pid // empty' "$f")
#   # Layer 1: config dir mismatch → different installation
#   if [[ -n "$stored_cfg" && "$stored_cfg" != "$RUNE_CURRENT_CFG" ]]; then continue; fi
#   # Layer 2: PID mismatch + alive → different session (skip)
#   #          PID mismatch + dead → orphaned state (proceed with cleanup)
#   if [[ -n "$stored_pid" && "$stored_pid" =~ ^[0-9]+$ && "$stored_pid" != "$PPID" ]]; then
#     rune_pid_alive "$stored_pid" && continue  # alive = different session
#   fi

if [[ -z "${RUNE_CURRENT_CFG:-}" ]]; then
  RUNE_CURRENT_CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  RUNE_CURRENT_CFG=$(cd "$RUNE_CURRENT_CFG" 2>/dev/null && pwd -P || echo "$RUNE_CURRENT_CFG")
  export RUNE_CURRENT_CFG
fi

# ── PID liveness check (EPERM-safe) ──
# kill -0 returns non-zero for BOTH "no such process" (ESRCH) AND "permission denied" (EPERM).
# EPERM means the process IS alive but owned by another user — treat as alive to avoid
# cross-session contamination in restricted/multi-user runtimes.
#
# Usage: rune_pid_alive "$pid" && continue  # alive = skip
# Returns: 0 if alive (or EPERM), 1 if dead
rune_pid_alive() {
  local pid="$1"
  # Fast path: kill -0 succeeds → definitely alive
  if kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  # kill -0 failed — distinguish ESRCH (dead) from EPERM (alive, different user)
  local err
  err=$(kill -0 "$pid" 2>&1) || true
  case "$err" in
    *"Operation not permitted"*|*"EPERM"*|*"permission"*)
      return 0  # alive but owned by another user
      ;;
    *)
      return 1  # dead (ESRCH or other error)
      ;;
  esac
}
