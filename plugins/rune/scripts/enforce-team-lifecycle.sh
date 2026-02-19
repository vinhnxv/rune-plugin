#!/bin/bash
# scripts/enforce-team-lifecycle.sh
# TLC-001: Centralized team lifecycle guard for TeamCreate.
# Runs BEFORE every TeamCreate call. Validates team name, detects stale
# teams, auto-cleans filesystem orphans, and injects advisory context.
#
# DESIGN PRINCIPLES:
#   1. Advisory-only for stale detection (additionalContext, NOT deny)
#   2. Hard-block ONLY for invalid team names (shell injection prevention)
#   3. 30-minute stale threshold (avoids false positives in arc/concurrent)
#   4. rune-*/arc-* prefix filter (never touch foreign plugin teams)
#
# Hook events: PreToolUse:TeamCreate
# Timeout: 5s (fast-path guard)
# Exit 0: Allow (with optional JSON for additionalContext or deny)

set -euo pipefail
umask 077

# ── GUARD 1: jq dependency ──
# SEC-3 FIX: When jq is missing, perform basic team name validation with pure bash
# instead of silently allowing all names. SDK also validates, so this is defense-in-depth.
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — enforce-team-lifecycle.sh using fallback validation" >&2
  # Best-effort: extract team_name from raw JSON input using grep/sed
  RAW_INPUT=$(head -c 1048576)
  RAW_NAME=$(echo "$RAW_INPUT" | grep -o '"team_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"team_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  if [[ -n "$RAW_NAME" ]] && [[ ! "$RAW_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "TLC-001: BLOCKED — invalid team name (jq-free fallback validation)" >&2
    # Output deny JSON manually (no jq available)
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"TLC-001: Invalid team name (jq-free fallback). Names must match /^[a-zA-Z0-9_-]+$/."}}\n'
  fi
  exit 0
fi

# ── GUARD 2: Input size cap (SEC-2: 1MB DoS prevention) ──
INPUT=$(head -c 1048576)

# ── GUARD 3: Tool name match (fast path) ──
# SEC-5 NOTE: Exact string match here provides defense-in-depth against any
# SDK matcher ambiguity (hooks.json "TeamCreate" matcher is regex-based).
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
if [[ "$TOOL_NAME" != "TeamCreate" ]]; then
  exit 0
fi

# ── GUARD 4: CWD canonicalization (QUAL-5) ──
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
if [[ -z "$CWD" ]]; then exit 0; fi
CWD=$(cd "$CWD" 2>/dev/null && pwd -P) || {
  [[ "${RUNE_TRACE:-}" == "1" ]] && echo "TLC-001: CWD canonicalization failed for original CWD" >> /tmp/rune-hook-trace.log
  exit 0
}
if [[ -z "$CWD" || "$CWD" != /* ]]; then exit 0; fi

# ── EXTRACT: team_name from tool_input (single-pass jq) ──
TEAM_NAME=$(echo "$INPUT" | jq -r '.tool_input.team_name // empty' 2>/dev/null || true)
if [[ -z "$TEAM_NAME" ]]; then
  exit 0  # No team_name — let SDK handle the error
fi

# ── GATE 1: Team name validation (HARD BLOCK — D-5) ──
# This is the ONLY deny case. Invalid names can cause shell injection.
if [[ ! "$TEAM_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || [[ "$TEAM_NAME" == *".."* ]]; then
  # Sanitize team name for JSON output — strip chars that break JSON
  # SEC-002 FIX: Dash at end of tr charset to avoid ambiguous range interpretation
  # QUAL-012 FIX: Exclude '.' from sanitization charset — prevents '..' in error messages
  SAFE_NAME=$(printf '%s' "${TEAM_NAME:0:64}" | tr -cd 'a-zA-Z0-9 _-')
  # BACK-004 FIX: Fallback for empty SAFE_NAME (team name was ALL special chars)
  SAFE_NAME="${SAFE_NAME:-<invalid>}"
  # SEC-001 FIX: Use jq --arg for JSON-safe output instead of unquoted heredoc
  jq -n --arg name "$SAFE_NAME" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("TLC-001: Invalid team name \"" + $name + "\". Team names must match /^[a-zA-Z0-9_-]+$/ and must not contain \"..\"."),
      additionalContext: "BLOCKED by enforce-team-lifecycle.sh. Fix the team name to use only alphanumeric characters, hyphens, and underscores. Example: rune-review-abc123."
    }
  }'
  exit 0
fi

# ── GATE 2: Team name length (max 128 chars) ──
if [[ ${#TEAM_NAME} -gt 128 ]]; then
  # SEC-001 FIX: Use jq for JSON-safe output (consistency with GATE 1)
  jq -n --argjson len "${#TEAM_NAME}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("TLC-001: Team name exceeds 128 characters (" + ($len | tostring) + " chars)."),
      additionalContext: "BLOCKED by enforce-team-lifecycle.sh. Shorten the team name to 128 characters or fewer."
    }
  }'
  exit 0
fi

# ── STALE TEAM DETECTION (Advisory — D-1, D-2) ──
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

# FIX-1: CHOME absoluteness guard (flaw-hunter EC-A5)
if [[ -z "$CHOME" ]] || [[ "$CHOME" != /* ]]; then
  exit 0  # CHOME is invalid (not absolute), skip scan
fi

# Find stale rune-*/arc-* team dirs older than 30 min (ORPHAN_STALE_THRESHOLD)
# BACK-004 NOTE: -mmin +30 checks directory mtime (updated on any file write inside),
# not creation time. An active team with FS activity stays fresh. A team idle >30 min
# (e.g., waiting on long LLM call) may be flagged — increase to -mmin +60 if observed.
# Using -mmin +30 for age check (fast, no jq needed per dir)
stale_teams=()
if [[ -d "$CHOME/teams/" ]]; then
  while IFS= read -r dir; do
    dirname=$(basename "$dir")
    # Validate dirname before adding (defense-in-depth)
    if [[ "$dirname" =~ ^[a-zA-Z0-9_-]+$ ]] && [[ ! -L "$dir" ]]; then
      stale_teams+=("$dirname")
    fi
  done < <(find "$CHOME/teams/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" \) -mmin +30 2>/dev/null)
fi

# If no stale teams found, allow TeamCreate silently
if [[ ${#stale_teams[@]} -eq 0 ]]; then
  exit 0
fi

# ── AUTO-CLEANUP: Remove stale filesystem dirs (D-3) ──
# BACK-005 NOTE: rm-rf removes dirs without SDK TeamDelete. This clears filesystem
# state but not SDK leadership. Advisory message tells Claude to run TeamDelete()
# if "Already leading" errors occur. SDK TeamDelete can't be called from a hook script.
cleaned_teams=()
for team in "${stale_teams[@]}"; do
  # Double-validate before rm-rf (defense-in-depth)
  # SEC-1 FIX: Re-check symlink immediately before rm-rf (collapses TOCTOU window from scan loop)
  if [[ "$team" =~ ^[a-zA-Z0-9_-]+$ ]] && [[ "$team" != *".."* ]] && [[ ! -L "$CHOME/teams/${team}" ]]; then
    rm -rf "$CHOME/teams/${team}/" "$CHOME/tasks/${team}/" 2>/dev/null
    cleaned_teams+=("$team")
  fi
done

# ── ADVISORY CONTEXT: Tell Claude what was found and cleaned ──
# Build comma-separated list for JSON (truncate to first 5)
cleaned_list=""
count=0
for team in "${cleaned_teams[@]}"; do
  if [[ $count -ge 5 ]]; then
    cleaned_list="${cleaned_list}, ... and $((${#cleaned_teams[@]} - 5)) more"
    break
  fi
  if [[ -n "$cleaned_list" ]]; then
    cleaned_list="${cleaned_list}, ${team}"
  else
    cleaned_list="${team}"
  fi
  # BACK-006 FIX: ((0++)) returns exit code 1 under set -e, killing the script
  count=$((count + 1))
done

# SEC-003 FIX: Use jq --arg/--argjson for JSON-safe output instead of unquoted heredoc
jq -n --argjson count "${#cleaned_teams[@]}" --arg list "$cleaned_list" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow",
    additionalContext: ("TLC-001 PRE-FLIGHT: Found and cleaned " + ($count | tostring) + " orphaned team dir(s) older than 30 min: [" + $list + "]. Filesystem dirs removed. If you encounter an Already leading team error, the SDK leadership state may still be stale — run TeamDelete() to clear it before retrying TeamCreate.")
  }
}'
exit 0
