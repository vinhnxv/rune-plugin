#!/bin/bash
set -euo pipefail
# Echo Search MCP Server launcher
#
# WHY THIS WRAPPER EXISTS:
# .mcp.json only supports ${CLAUDE_PLUGIN_ROOT} for env substitution.
# ECHO_DIR and DB_PATH need ${CLAUDE_PROJECT_DIR} which is NOT available
# in .mcp.json env blocks. This wrapper resolves them at runtime.
# Do NOT replace this with a direct python3 call in .mcp.json — it will
# fail silently because ECHO_DIR/DB_PATH would be unset.

# SEC-006: Canonicalize PROJECT_DIR and validate absoluteness
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PROJECT_DIR=$(cd "$PROJECT_DIR" 2>/dev/null && pwd -P) || { echo "ERROR: invalid PROJECT_DIR" >&2; exit 1; }
[[ "$PROJECT_DIR" == /* ]] || { echo "ERROR: PROJECT_DIR not absolute: $PROJECT_DIR" >&2; exit 1; }
export ECHO_DIR="$PROJECT_DIR/.claude/echoes"
export DB_PATH="$PROJECT_DIR/.claude/echoes/.search-index.db"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/server.py"
