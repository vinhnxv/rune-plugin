#!/usr/bin/env bash
# Echo Search MCP Server launcher
#
# Claude Code launches MCP servers with cwd = project root.
# We use this to resolve ECHO_DIR and DB_PATH at runtime,
# since ${CLAUDE_PROJECT_DIR} is not available for .mcp.json
# env substitution (only ${CLAUDE_PLUGIN_ROOT} is supported).

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
export ECHO_DIR="$PROJECT_DIR/.claude/echoes"
export DB_PATH="$PROJECT_DIR/.claude/echoes/.search-index.db"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/server.py"
