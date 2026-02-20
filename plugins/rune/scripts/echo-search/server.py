"""
Echo Search MCP Server

A Model Context Protocol (MCP) stdio server that provides full-text search
over the Rune plugin's echo system (persistent learnings stored in
.claude/echoes/<role>/MEMORY.md files).

Provides 4 tools:
  - echo_search:  BM25 full-text search over indexed echo entries
  - echo_details: Fetch full content for specific entry IDs
  - echo_reindex: Re-parse all MEMORY.md files and rebuild the FTS index
  - echo_stats:   Summary statistics of the echo index

Environment variables:
  ECHO_DIR  - Path to the echoes directory (e.g., .claude/echoes)
  DB_PATH   - Path to the SQLite database file

Usage:
  # As MCP stdio server (normal mode):
  python3 server.py

  # Standalone reindex:
  python3 server.py --reindex
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ECHO_DIR = os.environ.get("ECHO_DIR", "")
DB_PATH = os.environ.get("DB_PATH", "")

# SEC-003: Validate env vars don't point to system directories
_FORBIDDEN_PREFIXES = ("/etc", "/usr", "/bin", "/sbin", "/var/run", "/proc", "/sys")
for _env_name, _env_val in [("ECHO_DIR", ECHO_DIR), ("DB_PATH", DB_PATH)]:
    if _env_val:
        _resolved = os.path.realpath(_env_val)
        if any(_resolved.startswith(p) for p in _FORBIDDEN_PREFIXES):
            print(
                "Error: %s points to system directory: %s" % (_env_name, _resolved),
                file=sys.stderr,
            )
            sys.exit(1)

STOPWORDS = frozenset([
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
    "from", "had", "has", "have", "he", "her", "his", "i", "in",
    "is", "it", "its", "my", "not", "of", "on", "or", "our", "she",
    "so", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "to", "us", "was", "we", "what", "when", "which",
    "who", "will", "with", "you", "your",
])

# ---------------------------------------------------------------------------
# Dirty signal helpers (consumed from annotate-hook.sh)
# ---------------------------------------------------------------------------

# The PostToolUse hook (annotate-hook.sh) writes a sentinel file when a
# MEMORY.md is edited.  Before each search we check for this file and
# trigger a reindex so new echoes appear immediately in results.

_SIGNAL_SUFFIX = os.path.join(".claude", "echoes")


def _signal_path(echo_dir):
    # type: (str) -> str
    """Derive the dirty-signal file path from ECHO_DIR.

    ECHO_DIR is ``<project>/.claude/echoes``.  The hook writes the signal to
    ``<project>/tmp/.rune-signals/.echo-dirty``.
    """
    if not echo_dir:
        return ""
    # Strip /.claude/echoes (or .claude/echoes) suffix to get project root
    normalized = echo_dir.rstrip(os.sep)
    if normalized.endswith(_SIGNAL_SUFFIX):
        project_root = normalized[: -len(_SIGNAL_SUFFIX)].rstrip(os.sep)
    else:
        # Fallback: walk up two directories
        project_root = os.path.dirname(os.path.dirname(normalized))
    return os.path.join(project_root, "tmp", ".rune-signals", ".echo-dirty")


def _check_and_clear_dirty(echo_dir):
    # type: (str) -> bool
    """Return True (and delete the file) if the dirty signal is present."""
    path = _signal_path(echo_dir)
    if not path:
        return False
    try:
        if os.path.isfile(path):
            os.remove(path)
            return True
    except OSError:
        pass  # Race with another consumer or permission issue — safe to ignore
    return False


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db(db_path):
    # type: (str) -> sqlite3.Connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def ensure_schema(conn):
    # type: (sqlite3.Connection) -> None
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS echo_entries (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            layer TEXT NOT NULL,
            date TEXT,
            source TEXT,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            line_number INTEGER,
            file_path TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS echo_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    # Check if FTS table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='echo_entries_fts'"
    )
    if cursor.fetchone() is None:
        conn.executescript("""
            CREATE VIRTUAL TABLE echo_entries_fts USING fts5(
                content, tags, source,
                content=echo_entries,
                tokenize='porter unicode61'
            );
        """)

    conn.commit()


def rebuild_index(conn, entries):
    # type: (sqlite3.Connection, List[Dict]) -> int
    conn.execute("BEGIN")  # QUAL-3: explicit transaction for crash safety
    try:
        conn.execute("DELETE FROM echo_entries")
        conn.execute("INSERT INTO echo_entries_fts(echo_entries_fts) VALUES('delete-all')")

        for entry in entries:
            conn.execute(
                """INSERT OR REPLACE INTO echo_entries
                   (id, role, layer, date, source, content, tags, line_number, file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["id"],
                    entry["role"],
                    entry["layer"],
                    entry.get("date", ""),
                    entry.get("source", ""),
                    entry["content"],
                    entry.get("tags", ""),
                    entry.get("line_number", 0),
                    entry["file_path"],
                ),
            )

        # Rebuild the FTS index from the content table
        conn.execute(
            "INSERT INTO echo_entries_fts(echo_entries_fts) VALUES('rebuild')"
        )

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        conn.execute(
            "INSERT OR REPLACE INTO echo_meta (key, value) VALUES ('last_indexed', ?)",
            (now,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return len(entries)


def build_fts_query(raw_query):
    # type: (str) -> str
    raw_query = raw_query[:500]  # SEC-7: cap input length
    tokens = re.findall(r"[a-zA-Z0-9_]+", raw_query.lower())
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]
    if not filtered:
        filtered = [t for t in tokens if len(t) >= 2]
    if not filtered:
        return ""  # SEC-2: never pass raw input to FTS5 MATCH
    return " OR ".join(filtered[:20])  # SEC-7: cap token count


def search_entries(conn, query, limit=10, layer=None, role=None):
    # type: (sqlite3.Connection, str, int, Optional[str], Optional[str]) -> List[Dict]
    fts_query = build_fts_query(query)
    if not fts_query:
        return []

    sql = """
        SELECT
            e.id, e.source, e.layer, e.role,
            substr(e.content, 1, 200) AS content_preview,
            e.line_number,
            bm25(echo_entries_fts) AS score
        FROM echo_entries_fts f
        JOIN echo_entries e ON e.rowid = f.rowid
        WHERE echo_entries_fts MATCH ?
    """
    params = [fts_query]  # type: List[Any]

    if layer:
        sql += " AND e.layer = ?"
        params.append(layer)
    if role:
        sql += " AND e.role = ?"
        params.append(role)

    sql += " ORDER BY bm25(echo_entries_fts) ASC LIMIT ?"  # ASC: more negative = more relevant
    params.append(limit)

    cursor = conn.execute(sql, params)
    results = []
    for row in cursor.fetchall():
        results.append({
            "id": row["id"],
            "source": row["source"],
            "layer": row["layer"],
            "role": row["role"],
            "content_preview": row["content_preview"],
            "score": round(row["score"], 4),
            "line_number": row["line_number"],
        })
    return results


def get_details(conn, ids):
    # type: (sqlite3.Connection, List[str]) -> List[Dict]
    if not ids:
        return []
    # SEC-002: Defense-in-depth cap + type validation (coerce non-strings, filter None)
    ids = [str(i) for i in ids if i is not None][:100]
    if not ids:
        return []
    placeholders = ",".join(["?"] * len(ids))
    sql = """
        SELECT id, source, layer, role, content AS full_content,
               date, tags, line_number, file_path
        FROM echo_entries
        WHERE id IN (%s)
    """ % placeholders

    cursor = conn.execute(sql, ids)
    results = []
    for row in cursor.fetchall():
        results.append({
            "id": row["id"],
            "source": row["source"],
            "layer": row["layer"],
            "role": row["role"],
            "full_content": row["full_content"],
            "date": row["date"],
            "tags": row["tags"],
            "line_number": row["line_number"],
            "file_path": row["file_path"],
        })
    return results


def get_stats(conn):
    # type: (sqlite3.Connection) -> Dict
    total = conn.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]

    by_layer = {}  # type: Dict[str, int]
    for row in conn.execute(
        "SELECT layer, COUNT(*) as cnt FROM echo_entries GROUP BY layer"
    ):
        by_layer[row["layer"]] = row["cnt"]

    by_role = {}  # type: Dict[str, int]
    for row in conn.execute(
        "SELECT role, COUNT(*) as cnt FROM echo_entries GROUP BY role"
    ):
        by_role[row["role"]] = row["cnt"]

    last_row = conn.execute(
        "SELECT value FROM echo_meta WHERE key='last_indexed'"
    ).fetchone()
    last_indexed = last_row[0] if last_row else ""

    return {
        "total_entries": total,
        "by_layer": by_layer,
        "by_role": by_role,
        "last_indexed": last_indexed,
    }


# ---------------------------------------------------------------------------
# Reindex helper (used by both CLI and MCP tool)
# ---------------------------------------------------------------------------

def do_reindex(echo_dir, db_path):
    # type: (str, str) -> Dict
    from indexer import discover_and_parse

    start_ms = int(time.time() * 1000)
    entries = discover_and_parse(echo_dir)
    conn = get_db(db_path)
    try:
        ensure_schema(conn)
        count = rebuild_index(conn, entries)
    finally:
        conn.close()
    elapsed_ms = int(time.time() * 1000) - start_ms

    roles = sorted(set(e["role"] for e in entries))

    return {
        "entries_indexed": count,
        "time_ms": elapsed_ms,
        "roles": roles,
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

def run_mcp_server():
    # type: () -> None
    if not DB_PATH:  # SEC-4: fail fast instead of silent in-memory DB
        print("Error: DB_PATH environment variable not set", file=sys.stderr)
        sys.exit(1)
    db_parent = os.path.dirname(DB_PATH) or "."
    if not os.access(db_parent, os.W_OK):
        print("Error: DB_PATH parent directory is not writable: %s" % db_parent,
              file=sys.stderr)
        sys.exit(1)

    import asyncio
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server.lowlevel import Server, NotificationOptions
    from mcp.server.models import InitializationOptions

    server = Server("echo-search")

    # -- list_tools --------------------------------------------------------

    @server.list_tools()
    async def handle_list_tools():
        # type: () -> List[types.Tool]
        return [
            types.Tool(
                name="echo_search",
                description=(
                    "Search the Rune echo system for learnings, patterns, "
                    "and insights using BM25 full-text search."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (natural language or keywords)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results to return (default 10)",
                            "default": 10,
                        },
                        "layer": {
                            "type": "string",
                            "description": "Filter by echo layer (e.g., inscribed)",
                        },
                        "role": {
                            "type": "string",
                            "description": "Filter by role (e.g., orchestrator, reviewer, planner)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="echo_details",
                description=(
                    "Fetch full content for specific echo entries by their IDs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of entry IDs to fetch",
                        },
                    },
                    "required": ["ids"],
                },
            ),
            types.Tool(
                name="echo_reindex",
                description=(
                    "Re-parse all MEMORY.md files and rebuild the search index."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            types.Tool(
                name="echo_stats",
                description=(
                    "Get summary statistics about the echo search index."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]

    # -- call_tool ---------------------------------------------------------

    @server.call_tool()
    async def handle_call_tool(name, arguments):
        # type: (str, Dict) -> List[types.TextContent]
        try:
            if name == "echo_search":
                return await _handle_search(arguments)
            elif name == "echo_details":
                return await _handle_details(arguments)
            elif name == "echo_reindex":
                return await _handle_reindex()
            elif name == "echo_stats":
                return await _handle_stats()
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"error": "Unknown tool: %s" % name}),
                        isError=True,
                    )
                ]
        except Exception as e:
            # SEC-NEW-001: Cap error message to avoid leaking internal paths
            # Python exceptions can include absolute filesystem paths in their message.
            err_msg = str(e)[:200] if str(e) else "Internal server error"
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": err_msg}),
                    isError=True,
                )
            ]

    async def _handle_search(arguments):
        # type: (Dict) -> List[types.TextContent]
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        layer = arguments.get("layer")
        role = arguments.get("role")

        # SEC-3: Type validation
        if not isinstance(query, str) or not query:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "query must be a non-empty string"}),
                    isError=True,
                )
            ]
        if layer is not None and not isinstance(layer, str):
            layer = None
        if role is not None and not isinstance(role, str):
            role = None

        # Clamp limit
        if not isinstance(limit, int) or limit < 1:
            limit = 10
        limit = min(limit, 50)

        conn = get_db(DB_PATH)
        try:
            ensure_schema(conn)

            # Auto-reindex when DB is empty OR dirty signal is present.
            # SEC-NEW-002: This close-reindex-reopen pattern is safe because:
            # 1. MCP stdio transport is single-threaded asyncio — no concurrent calls overlap
            # 2. If do_reindex() raises, finally calls conn.close() on the already-closed
            #    original conn. CPython's sqlite3.Connection.close() is a no-op on closed conns.
            count = conn.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
            is_dirty = _check_and_clear_dirty(ECHO_DIR)
            if (count == 0 or is_dirty) and ECHO_DIR:
                conn.close()  # QUAL-1: close before reindex opens its own conn
                do_reindex(ECHO_DIR, DB_PATH)
                conn = get_db(DB_PATH)

            results = search_entries(conn, query, limit, layer, role)
        finally:
            conn.close()  # QUAL-8: always close on any path

        return [
            types.TextContent(
                type="text",
                text=json.dumps({"entries": results}, indent=2),
            )
        ]

    async def _handle_details(arguments):
        # type: (Dict) -> List[types.TextContent]
        ids = arguments.get("ids", [])

        # SEC-3: Type validation
        if not isinstance(ids, list):
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "ids must be a list"}),
                    isError=True,
                )
            ]
        if not ids:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "ids is required"}),
                    isError=True,
                )
            ]

        ids = ids[:50]  # SEC-1: cap ids to prevent DoS via large IN clause

        conn = get_db(DB_PATH)
        try:
            ensure_schema(conn)

            # Reindex on dirty signal so newly-written entries are available
            if _check_and_clear_dirty(ECHO_DIR) and ECHO_DIR:
                conn.close()
                do_reindex(ECHO_DIR, DB_PATH)
                conn = get_db(DB_PATH)

            results = get_details(conn, ids)
        finally:
            conn.close()

        return [
            types.TextContent(
                type="text",
                text=json.dumps({"entries": results}, indent=2),
            )
        ]

    async def _handle_reindex():
        # type: () -> List[types.TextContent]
        if not ECHO_DIR:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "ECHO_DIR not set"}),
                    isError=True,
                )
            ]

        result = do_reindex(ECHO_DIR, DB_PATH)
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]

    async def _handle_stats():
        # type: () -> List[types.TextContent]
        conn = get_db(DB_PATH)
        try:
            ensure_schema(conn)
            stats = get_stats(conn)
        finally:
            conn.close()

        return [
            types.TextContent(
                type="text",
                text=json.dumps(stats, indent=2),
            )
        ]

    # -- run ---------------------------------------------------------------

    async def main():
        # type: () -> None
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="echo-search",
                    server_version="1.53.4",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(main())


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main_cli():
    # type: () -> None
    parser = argparse.ArgumentParser(
        description="Echo Search MCP Server"
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Reindex all MEMORY.md files and exit",
    )
    args = parser.parse_args()

    if args.reindex:
        if not ECHO_DIR:
            print("Error: ECHO_DIR environment variable not set", file=sys.stderr)
            sys.exit(1)
        if not DB_PATH:
            print("Error: DB_PATH environment variable not set", file=sys.stderr)
            sys.exit(1)

        result = do_reindex(ECHO_DIR, DB_PATH)
        print("Indexed %d entries in %dms" % (result["entries_indexed"], result["time_ms"]))
        print("Roles: %s" % ", ".join(result["roles"]))
        sys.exit(0)

    # Default: run as MCP stdio server
    if not DB_PATH:
        print("Error: DB_PATH environment variable not set", file=sys.stderr)
        sys.exit(1)

    run_mcp_server()


if __name__ == "__main__":
    main_cli()
