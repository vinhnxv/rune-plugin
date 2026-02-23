#!/bin/bash
# session-start.sh — Loads using-rune skill content at session start
# Ensures Rune workflow routing is available from the very first message.
# Runs synchronously (async: false) so content is present before user's first prompt.
set -euo pipefail

# ── Opt-in trace logging ──
_trace() {
  if [[ "${RUNE_TRACE:-}" == "1" ]]; then
    local _log="${RUNE_TRACE_LOG:-${TMPDIR:-/tmp}/rune-hook-trace-$(id -u).log}"
    [[ ! -L "$_log" ]] && echo "[session-start] $*" >> "$_log" 2>/dev/null
  fi
  return 0
}

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SKILL_FILE="${PLUGIN_ROOT}/skills/using-rune/SKILL.md"

if [ ! -f "$SKILL_FILE" ]; then
  exit 0
fi

# ── Read hook input for event type extraction ──
INPUT=$(head -c 1048576 2>/dev/null || true)
EVENT=""
if command -v jq &>/dev/null; then
  EVENT=$(echo "$INPUT" | jq -r '.event // empty' 2>/dev/null || true)
fi

# Read skill content, strip frontmatter
CONTENT=""
IN_FRONTMATTER=false
PAST_FRONTMATTER=false
while IFS= read -r line; do
  if [ "$PAST_FRONTMATTER" = true ]; then
    CONTENT="${CONTENT}${line}
"
  elif [ "$IN_FRONTMATTER" = true ] && [ "$line" = "---" ]; then
    PAST_FRONTMATTER=true
  elif [ "$IN_FRONTMATTER" = false ] && [ "$line" = "---" ]; then
    IN_FRONTMATTER=true
  fi
done < "$SKILL_FILE"

# JSON-escape the content
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

ESCAPED_CONTENT=$(json_escape "$CONTENT")

# Output as hookSpecificOutput with additionalContext
# This injects the skill routing table into Claude's context
cat <<EOF
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[Rune Plugin Active] ${ESCAPED_CONTENT}"}}
EOF

# Statusline configuration diagnostic (startup only, non-blocking)
if [[ "$EVENT" == "startup" ]]; then
  # Read context_monitor.enabled from talisman (graceful degradation — no yq required)
  CTX_ENABLED="true"
  CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
  if [[ -n "$CWD" ]]; then
    TALISMAN_FILE="${CWD}/.claude/talisman.yml"
    if [[ -f "$TALISMAN_FILE" && ! -L "$TALISMAN_FILE" ]]; then
      _val=$(grep -A1 'context_monitor:' "$TALISMAN_FILE" 2>/dev/null | grep 'enabled:' | grep -o 'false' || true)
      [[ "$_val" == "false" ]] && CTX_ENABLED="false"
    fi
  fi
  if [[ "${CTX_ENABLED:-true}" != "false" ]]; then
    RECENT_BRIDGE=$(find /tmp -maxdepth 1 -name "rune-ctx-*.json" -newer /tmp -mmin -60 2>/dev/null | head -1)
    if [[ -z "$RECENT_BRIDGE" ]]; then
      _trace "NOTE: No recent bridge file found. Context monitoring requires statusline configuration."
    fi
  fi
fi
