#!/usr/bin/env bash
# session-start.sh — Loads using-rune skill content at session start
# Ensures Rune workflow routing is available from the very first message.
# Runs synchronously (async: false) so content is present before user's first prompt.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SKILL_FILE="${PLUGIN_ROOT}/skills/using-rune/SKILL.md"

if [ ! -f "$SKILL_FILE" ]; then
  exit 0
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
