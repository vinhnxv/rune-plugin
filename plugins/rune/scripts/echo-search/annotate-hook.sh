#!/bin/bash
# PostToolUse hook: detects writes to .claude/echoes/ and writes dirty signal
# Exits 0 for non-echo file writes. May exit non-zero on malformed JSON (set -e).
# Signal-file pattern for debounced reindex.
set -euo pipefail
umask 077

# QUAL-002: jq guard
if ! command -v jq &>/dev/null; then
  exit 0
fi

# SEC-006: Cap stdin to 64KB (only need file_path, not full content)
TOOL_INPUT=$(head -c 65536)

FILE_PATH=$(printf '%s' "$TOOL_INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

if [[ "$FILE_PATH" == *".claude/echoes/"*"MEMORY.md" ]]; then
  # Write dirty signal for next echo-reader invocation to pick up
  SIGNAL_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}/tmp/.rune-signals"
  mkdir -p "$SIGNAL_DIR" 2>/dev/null
  printf '1' > "$SIGNAL_DIR/.echo-dirty" 2>/dev/null
fi

exit 0
