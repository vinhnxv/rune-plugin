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
# Matcher: startup|resume (fires on fresh start and post-crash resume — primary orphan scenarios)
# Timeout: 5s

set -euo pipefail
umask 077

# --- Fail-forward guard (OPERATIONAL hook) ---
# Crash before validation → allow operation (don't stall workflows).
_rune_fail_forward() {
  if [[ "${RUNE_TRACE:-}" == "1" ]]; then
    printf '[%s] %s: ERR trap — fail-forward activated (line %s)\n' \
      "$(date +%H:%M:%S 2>/dev/null || true)" \
      "${BASH_SOURCE[0]##*/}" \
      "${BASH_LINENO[0]:-?}" \
      >> "${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}" 2>/dev/null
  fi
  exit 0
}
trap '_rune_fail_forward' ERR

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

# ── Session identity for cross-session ownership filtering ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=resolve-session-identity.sh
source "${SCRIPT_DIR}/resolve-session-identity.sh"

# Extract session_id from hook input JSON (same pattern as enforce-team-lifecycle.sh)
HOOK_SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)

# Count orphaned team dirs (older than 30 min)
orphan_count=0
orphan_names=()
if [[ -d "$CHOME/teams/" ]]; then
  while IFS= read -r dir; do
    dirname=$(basename "$dir")
    if [[ "$dirname" =~ ^[a-zA-Z0-9_-]+$ ]] && [[ ! -L "$dir" ]]; then
      # Session ownership filter: skip teams owned by other live sessions
      if [[ -f "$dir/.session" ]] && [[ ! -L "$dir/.session" ]]; then
        marker_session=$(head -c 256 "$dir/.session" 2>/dev/null | tr -d '[:space:]' || true)
        if [[ -n "$marker_session" ]] && [[ -n "$HOOK_SESSION_ID" ]] && [[ "$marker_session" != "$HOOK_SESSION_ID" ]]; then
          continue  # Different session owns this team — not an orphan for us
        fi
      fi
      orphan_names+=("$dirname")
      # BACK-012 FIX: ((0++)) returns exit code 1 under set -e, killing the script
      orphan_count=$((orphan_count + 1))
    fi
  done < <(find "$CHOME/teams/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" -o -name "goldmask-*" \) -mmin +30 2>/dev/null)
fi

[[ "${RUNE_TRACE:-}" == "1" ]] && [[ ! -L "${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}" ]] && echo "[$(date '+%H:%M:%S')] TLC-003: orphan team dirs found: ${orphan_count}" >> "${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}"

# Count stale state files
stale_state_count=0

# QUAL-005 FIX: Run glob loop in subshell to scope nullglob (prevents leak on early exit)
# BACK-001 FIX: Simplified — script uses #!/bin/bash, so ZSH_VERSION is never set.
# Using subshell instead of setopt/unsetopt pair eliminates scope leak entirely.
# QUAL-002 NOTE: Uses stat for file age (not find -mmin) because we need BOTH age AND
# content check (status == "active"). find alone can't check JSON content.
stale_state_count=$(
  shopt -s nullglob 2>/dev/null
  count=0
  # BACK-015 FIX: Capture epoch once before loop (consistency + efficiency)
  NOW=$(date +%s)
  for f in "${CWD}"/tmp/.rune-review-*.json "${CWD}"/tmp/.rune-audit-*.json "${CWD}"/tmp/.rune-work-*.json "${CWD}"/tmp/.rune-mend-*.json "${CWD}"/tmp/.rune-inspect-*.json "${CWD}"/tmp/.rune-forge-*.json "${CWD}"/tmp/.rune-goldmask-*.json; do
    if [[ -f "$f" ]]; then
      # Check if status is "active" and file is older than 30 min
      # FIX-2: Fallback to epoch 0 (Jan 1 1970) if stat fails. Math: (NOW - 0) / 60 = ~29M minutes
      # = always triggers stale (>30 min). Forge suggested 999999999 but that's wrong: (NOW - 999999999)
      # could be small for timestamps near 2001. Epoch 0 is the safe default.
      # BACK-002 NOTE: macOS stat -f first, then Linux stat -c, then epoch-0 (assume stale)
      file_mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)
      file_age_min=$(( (NOW - file_mtime) / 60 ))
      if [[ $file_age_min -gt 30 ]]; then
        # SEC-4 FIX: Use jq for precise status extraction instead of grep string match
        file_status=$(jq -r '.status // empty' "$f" 2>/dev/null || true)
        if [[ "$file_status" == "active" ]]; then
          # ── Ownership filter: only count THIS session's stale state files ──
          sf_cfg=$(jq -r '.config_dir // empty' "$f" 2>/dev/null || true)
          sf_pid=$(jq -r '.owner_pid // empty' "$f" 2>/dev/null || true)
          if [[ -n "$sf_cfg" && "$sf_cfg" != "$RUNE_CURRENT_CFG" ]]; then continue; fi
          if [[ -n "$sf_pid" && "$sf_pid" =~ ^[0-9]+$ && "$sf_pid" != "$PPID" ]]; then
            rune_pid_alive "$sf_pid" && continue  # alive = different session
          fi
          count=$((count + 1))
        fi
      fi
    fi
  done
  echo "$count"
)

[[ "${RUNE_TRACE:-}" == "1" ]] && [[ ! -L "${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}" ]] && echo "[$(date '+%H:%M:%S')] TLC-003: stale state files found: ${stale_state_count}" >> "${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}"

# Count orphaned arc checkpoints (v1.110.0: Bug 2 fix)
# Scan .claude/arc/ and tmp/arc/ for checkpoints with dead owner_pid
orphan_checkpoint_count=0
orphan_checkpoint_count=$(
  count=0
  for ckpt_dir in "${CWD}/.claude/arc" "${CWD}/tmp/arc"; do
    [[ -d "$ckpt_dir" ]] || continue
    shopt -s nullglob 2>/dev/null || true
    for f in "$ckpt_dir"/*/checkpoint.json; do
      [[ -f "$f" ]] && [[ ! -L "$f" ]] || continue
      # Extract ownership fields
      ckpt_cfg=$(jq -r '.config_dir // empty' "$f" 2>/dev/null || true)
      ckpt_pid=$(jq -r '.owner_pid // empty' "$f" 2>/dev/null || true)
      # Skip if no owner_pid (backward compat with pre-session-isolation checkpoints)
      [[ -n "$ckpt_pid" && "$ckpt_pid" =~ ^[0-9]+$ ]] || continue
      # Skip if different config_dir (different installation)
      if [[ -n "$ckpt_cfg" && -n "$RUNE_CURRENT_CFG" && "$ckpt_cfg" != "$RUNE_CURRENT_CFG" ]]; then
        continue
      fi
      # Skip if same session (ours — not orphaned)
      [[ "$ckpt_pid" == "$PPID" ]] && continue
      # Skip if owner is alive (another live session)
      if rune_pid_alive "$ckpt_pid"; then
        continue
      fi
      # Dead owner — orphaned checkpoint
      count=$((count + 1))
    done
  done
  echo "$count"
)

[[ "${RUNE_TRACE:-}" == "1" ]] && [[ ! -L "${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}" ]] && echo "[$(date '+%H:%M:%S')] TLC-003: orphaned checkpoints found: ${orphan_checkpoint_count}" >> "${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}"

# Report if anything found
# BACK-007 FIX: Conditionally append orphan list to avoid trailing "Orphans: " with no names
if [[ $orphan_count -gt 0 ]] || [[ $stale_state_count -gt 0 ]] || [[ $orphan_checkpoint_count -gt 0 ]]; then
  msg="TLC-003 SESSION HYGIENE: Found ${orphan_count} orphaned team dir(s), ${stale_state_count} stale state file(s), and ${orphan_checkpoint_count} orphaned checkpoint(s) from prior sessions. Run /rune:rest --heal to clean up."
  if [[ ${#orphan_names[@]} -gt 0 ]]; then
    msg+=" Orphans: ${orphan_names[*]:0:5}"
  fi
  jq -n --arg ctx "$msg" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
fi

exit 0
