"""
Echo Search MCP Server

A Model Context Protocol (MCP) stdio server that provides full-text search
over the Rune plugin's echo system (persistent learnings stored in
.claude/echoes/<role>/MEMORY.md files).

Provides 5 tools:
  - echo_search:        BM25 full-text search with composite re-ranking
  - echo_details:       Fetch full content for specific entry IDs
  - echo_reindex:       Re-parse all MEMORY.md files and rebuild the FTS index
  - echo_stats:         Summary statistics of the echo index
  - echo_record_access: Manually record access events for entries

Environment variables:
  ECHO_DIR  - Path to the echoes directory (e.g., .claude/echoes)
  DB_PATH   - Path to the SQLite database file
  ECHO_WEIGHT_RELEVANCE   - BM25 relevance weight (default 0.30)
  ECHO_WEIGHT_IMPORTANCE  - Layer importance weight (default 0.30)
  ECHO_WEIGHT_RECENCY     - Recency weight (default 0.20)
  ECHO_WEIGHT_PROXIMITY   - File proximity weight (default 0.10)
  ECHO_WEIGHT_FREQUENCY   - Access frequency weight (default 0.10)

Usage:
  # As MCP stdio server (normal mode):
  python3 server.py

  # Standalone reindex:
  python3 server.py --reindex
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ECHO_DIR = os.environ.get("ECHO_DIR", "")
DB_PATH = os.environ.get("DB_PATH", "")
# Dual-mode validation: when set, runs both BM25-only and composite scoring
# in parallel and logs divergence to tmp/.rune-signals/.echo-scoring-validation.log
ECHO_VALIDATION_MODE = os.environ.get("ECHO_VALIDATION_MODE", "").lower() in ("1", "true", "yes")

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
# Composite scoring — 5-factor re-ranking
# ---------------------------------------------------------------------------
#
# After BM25 retrieval, results are re-scored using a weighted blend of:
#   1. Relevance  — normalized BM25 score (0.0–1.0)
#   2. Importance — layer-based weight (Etched > Inscribed > Traced)
#   3. Recency    — exponential decay based on entry age
#   4. Proximity  — file proximity to current context (placeholder, Task 3)
#   5. Frequency  — access frequency from echo_access_log (placeholder, Task 2)
#
# BM25 sign convention: SQLite FTS5 bm25() returns NEGATIVE values where
# more negative = more relevant. We normalize via min-max scaling:
#   normalized = (bm25_max - bm25_i) / (bm25_max - bm25_min)
# This inverts the sign so 1.0 = most relevant, 0.0 = least relevant.
# The log(1+count) formula for frequency scoring uses a logarithmic scale
# to prevent high-access entries from dominating — diminishing returns
# after the first few accesses.

# Default weights — overridable via environment variables (C4 concern:
# server.py does NOT read talisman.yml; weights come from env vars only).
_DEFAULT_WEIGHTS = {
    "relevance": 0.30,
    "importance": 0.30,
    "recency": 0.20,
    "proximity": 0.10,
    "frequency": 0.10,
}

# Layer importance mapping — higher = more important
_LAYER_IMPORTANCE = {
    "Etched": 1.0,
    "Inscribed": 0.6,
    "Traced": 0.3,
    "Notes": 0.9,       # User-explicit memories (Task 6)
    "Observations": 0.5, # Agent-observed patterns (Task 7)
}

# Recency half-life in days — entries older than this get < 0.5 score
_RECENCY_HALF_LIFE_DAYS = 30.0


def _load_scoring_weights() -> Dict[str, float]:
    """Load composite scoring weights from environment variables.

    Each weight is read from ECHO_WEIGHT_<NAME> env var. Falls back to
    _DEFAULT_WEIGHTS if not set. Weights are auto-normalized to sum to 1.0
    with a stderr warning if they don't (EDGE-002).

    Returns:
        Dict mapping factor name to its normalized weight (0.0-1.0).
    """
    weights = {}  # type: Dict[str, float]
    env_map = {
        "relevance": "ECHO_WEIGHT_RELEVANCE",
        "importance": "ECHO_WEIGHT_IMPORTANCE",
        "recency": "ECHO_WEIGHT_RECENCY",
        "proximity": "ECHO_WEIGHT_PROXIMITY",
        "frequency": "ECHO_WEIGHT_FREQUENCY",
    }
    for key, env_name in env_map.items():
        raw = os.environ.get(env_name)
        if raw is not None:
            try:
                val = float(raw)
                if val < 0.0:
                    raise ValueError("negative weight")
                weights[key] = val
            except ValueError:
                print(
                    "Warning: invalid %s=%r, using default %.2f"
                    % (env_name, raw, _DEFAULT_WEIGHTS[key]),
                    file=sys.stderr,
                )
                weights[key] = _DEFAULT_WEIGHTS[key]
        else:
            weights[key] = _DEFAULT_WEIGHTS[key]

    # EDGE-002: Auto-normalize if sum != 1.0
    total = sum(weights.values())
    if total <= 0.0:
        print(
            "Warning: scoring weights sum to 0, falling back to defaults",
            file=sys.stderr,
        )
        return dict(_DEFAULT_WEIGHTS)
    if abs(total - 1.0) > 1e-6:
        print(
            "Warning: scoring weights sum to %.4f (not 1.0), auto-normalizing"
            % total,
            file=sys.stderr,
        )
        weights = {k: v / total for k, v in weights.items()}

    return weights


def _score_bm25_relevance(scores: List[float]) -> List[float]:
    """Normalize BM25 scores to 0.0-1.0 range via min-max scaling.

    BM25 sign convention: FTS5 bm25() returns negative values where more
    negative = more relevant. We invert: 1.0 = most relevant, 0.0 = least.

    Args:
        scores: Raw BM25 scores (negative floats) from FTS5.

    Returns:
        List of normalized scores in [0.0, 1.0].
    """
    if not scores:
        return []
    # EDGE-006: Single result gets score 1.0
    if len(scores) == 1:
        return [1.0]
    bm25_min = min(scores)  # Most relevant (most negative)
    bm25_max = max(scores)  # Least relevant (least negative)
    spread = bm25_max - bm25_min
    # EDGE-005: All scores identical → all equally relevant
    if abs(spread) < 1e-9:
        return [1.0] * len(scores)
    return [(bm25_max - s) / spread for s in scores]


def _score_importance(layer: str) -> float:
    """Score entry importance based on its echo layer.

    Args:
        layer: Echo layer name (Etched, Inscribed, Traced, Notes, Observations).

    Returns:
        Importance score in [0.0, 1.0]. Unknown layers get 0.3 (same as Traced).
    """
    return _LAYER_IMPORTANCE.get(layer, 0.3)


def _score_recency(date_str: Optional[str]) -> float:
    """Score entry recency using exponential decay.

    Uses a half-life of 30 days: an entry from 30 days ago scores ~0.5,
    from 60 days ago ~0.25, etc.

    Args:
        date_str: ISO date string (YYYY-MM-DD) or None/empty.

    Returns:
        Recency score in [0.0, 1.0]. Returns 0.0 for missing/malformed dates
        (EDGE-003).
    """
    if not date_str:
        return 0.0
    try:
        entry_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        now = datetime.utcnow()
        age_days = max((now - entry_date).days, 0)
        # Exponential decay: score = 2^(-age/half_life)
        return math.pow(2.0, -age_days / _RECENCY_HALF_LIFE_DAYS)
    except (ValueError, TypeError):
        # EDGE-003: Malformed date → recency 0.0
        return 0.0


# Regex for extracting file paths from echo content (C5 concern).
# Matches backtick-fenced tokens that look like file paths (contain / and end
# with a common extension). Limited to 10 evidence paths per entry.
_EVIDENCE_PATH_RE = re.compile(r'`([^`]+\.[a-z]{1,6})`')


def _extract_evidence_paths(entry: Dict[str, Any]) -> List[str]:
    """Extract file paths referenced in an echo entry's content and source.

    C5 concern: Parses backtick-fenced tokens matching file path patterns
    plus the source field. Limited to 10 paths per entry to bound cost.

    SECURITY: These paths are used for string comparison ONLY — never
    passed to os.path.exists(), open(), or any filesystem operation.

    Args:
        entry: Echo entry dict with content_preview, source, etc.

    Returns:
        List of normalized evidence file paths (max 10).
    """
    paths = []  # type: List[str]

    # Extract from content (content_preview in search results)
    content = entry.get("content_preview", "") or entry.get("full_content", "") or ""
    for match in _EVIDENCE_PATH_RE.finditer(content):
        candidate = match.group(1)
        # Filter to paths that contain a directory separator
        if "/" in candidate or os.sep in candidate:
            paths.append(os.path.normpath(candidate))

    # Extract from source field
    source = entry.get("source", "") or ""
    if source and ("/" in source or os.sep in source):
        # Source might be like "rune:appraise src/auth.py" — extract path-like tokens
        for token in source.split():
            if "/" in token and ":" not in token:
                paths.append(os.path.normpath(token))

    # Deduplicate while preserving order, cap at 10
    seen = set()  # type: set
    unique = []  # type: List[str]
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
            if len(unique) >= 10:
                break

    return unique


def compute_file_proximity(evidence_path: str, context_path: str) -> float:
    """Compute proximity score between an evidence file and a context file.

    Scoring tiers:
    - Exact match: 1.0
    - Same directory: 0.8
    - Shared path prefix: 0.2-0.6 (proportional to common depth)
    - No match: 0.0

    SECURITY: String comparison ONLY. No filesystem operations on
    untrusted MCP input (context_files are untrusted).

    Args:
        evidence_path: Normalized path from echo content.
        context_path: Normalized path from user's context_files.

    Returns:
        Proximity score in [0.0, 1.0].
    """
    # EDGE-012: Normalize both paths (no realpath — no filesystem access)
    ev = os.path.normpath(evidence_path)
    ctx = os.path.normpath(context_path)

    # Exact match
    if ev == ctx:
        return 1.0

    # Same directory
    ev_dir = os.path.dirname(ev)
    ctx_dir = os.path.dirname(ctx)
    if ev_dir and ev_dir == ctx_dir:
        return 0.8

    # Shared prefix — score proportional to common path depth
    ev_parts = ev.split(os.sep)
    ctx_parts = ctx.split(os.sep)
    common = 0
    for a, b in zip(ev_parts, ctx_parts):
        if a == b:
            common += 1
        else:
            break

    if common == 0:
        return 0.0

    max_depth = max(len(ev_parts), len(ctx_parts))
    if max_depth == 0:
        return 0.0

    # Scale from 0.2 to 0.6 based on common prefix ratio
    ratio = common / max_depth
    return 0.2 + 0.4 * ratio


def _score_proximity(entry: Dict[str, Any], context_files: Optional[List[str]] = None) -> float:
    """Score file proximity between echo evidence files and context files.

    Extracts file paths referenced in the echo entry content, then computes
    the best proximity score against the user's current context files.

    Args:
        entry: Echo entry dict with content_preview, source, etc.
        context_files: List of currently open/edited file paths (untrusted
            MCP input — string comparison only, no filesystem access).

    Returns:
        Proximity score in [0.0, 1.0]. Returns 0.0 if no context files
        or no evidence paths found (EDGE-011).
    """
    # EDGE-011: Unified guard for None, [], and omitted context_files
    if not context_files:
        return 0.0

    evidence_paths = _extract_evidence_paths(entry)
    if not evidence_paths:
        return 0.0

    # Best proximity across all evidence/context path pairs
    best = 0.0
    for ev in evidence_paths:
        for ctx in context_files:
            ctx_norm = os.path.normpath(ctx)
            score = compute_file_proximity(ev, ctx_norm)
            if score > best:
                best = score
            if best >= 1.0:
                return 1.0  # Can't do better than exact match

    return best


def _get_access_counts(conn: sqlite3.Connection, entry_ids: List[str]) -> Dict[str, int]:
    """Fetch access counts for a batch of entry IDs from echo_access_log.

    Uses a single query with IN clause for efficiency. Only counts accesses
    for entries that still exist in echo_entries (EDGE-007: orphan safety).

    Args:
        conn: Database connection with echo_access_log table.
        entry_ids: List of echo entry IDs to look up.

    Returns:
        Dict mapping entry_id to access count. Missing IDs have count 0.
    """
    if not entry_ids:
        return {}
    # Cap to prevent oversized IN clause
    capped_ids = entry_ids[:200]
    placeholders = ",".join(["?"] * len(capped_ids))
    cursor = conn.execute(
        """SELECT entry_id, COUNT(*) AS cnt
           FROM echo_access_log
           WHERE entry_id IN (%s)
           GROUP BY entry_id""" % placeholders,
        capped_ids,
    )
    return {row["entry_id"]: row["cnt"] for row in cursor.fetchall()}


def _score_frequency(
    entry_id: str,
    conn: Optional[sqlite3.Connection] = None,
    access_counts: Optional[Dict[str, int]] = None,
    max_log_count: float = 0.0,
) -> float:
    """Score access frequency from echo_access_log.

    Uses log(1+count) scaling to prevent high-access entries from
    dominating — diminishing returns after the first few accesses.
    Normalized to [0.0, 1.0] by dividing by the max log-count in
    the current result set.

    Args:
        entry_id: Echo entry ID.
        conn: Database connection (unused when access_counts provided).
        access_counts: Pre-fetched dict of entry_id -> count (batch mode).
        max_log_count: Maximum log(1+count) across the result set for
            normalization. If 0.0, returns 0.0 (EDGE-004).

    Returns:
        Frequency score in [0.0, 1.0].
    """
    if access_counts is None:
        # EDGE-004: No access data → return 0.0
        return 0.0
    count = access_counts.get(entry_id, 0)
    if count == 0:
        return 0.0
    # EDGE-004: max_log_count=0 → return 0.0 (division by zero guard)
    if max_log_count <= 0.0:
        return 0.0
    return math.log(1.0 + count) / max_log_count


def _record_access(
    conn: sqlite3.Connection,
    results: List[Dict[str, Any]],
    query: str,
) -> None:
    """Synchronously record access events for search results.

    C2 concern: This is called SYNCHRONOUSLY before returning results.
    No asyncio.create_task() — MCP server is single-threaded asyncio.
    WAL mode allows concurrent reads during this write.

    Also enforces EDGE-010: caps echo_access_log at 100k rows by
    deleting oldest entries when threshold is exceeded.

    Args:
        conn: Database connection (WAL mode for concurrent read/write).
        results: List of search result dicts, each with 'id' key.
        query: The search query that produced these results.
    """
    if not results:
        return
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        for entry in results:
            entry_id = entry.get("id", "")
            if entry_id:
                conn.execute(
                    "INSERT INTO echo_access_log (entry_id, accessed_at, query) VALUES (?, ?, ?)",
                    (entry_id, now, query[:500]),  # SEC-7: cap query length
                )
        conn.commit()

        # EDGE-010: Bounded growth — check row count every write and
        # prune oldest entries if over 100k threshold.
        row_count = conn.execute("SELECT COUNT(*) FROM echo_access_log").fetchone()[0]
        if row_count > 100000:
            # Keep newest 90k rows (delete oldest 10k+ surplus)
            conn.execute("""
                DELETE FROM echo_access_log
                WHERE id NOT IN (
                    SELECT id FROM echo_access_log
                    ORDER BY accessed_at DESC
                    LIMIT 90000
                )
            """)
            conn.commit()
    except sqlite3.OperationalError:
        # Non-fatal: access logging failure should not break search
        pass


def compute_composite_score(
    results: List[Dict[str, Any]],
    weights: Dict[str, float],
    conn: Optional[sqlite3.Connection] = None,
    context_files: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Re-rank search results using 5-factor composite scoring.

    Blends BM25 relevance with importance, recency, file proximity, and
    access frequency to produce a final composite score. Results are sorted
    by composite score (descending).

    BM25 sign convention: FTS5 bm25() returns negative values where more
    negative = more relevant. Normalization inverts this to 0.0-1.0 scale
    via min-max scaling: (bm25_max - score_i) / (bm25_max - bm25_min).
    The log(1+count) rationale for frequency: logarithmic scaling provides
    diminishing returns so that entries accessed 100x don't dominate over
    entries accessed 10x.

    Args:
        results: List of search result dicts from search_entries(), each
            containing 'score' (raw BM25), 'layer', 'id', etc.
        weights: Dict of factor weights (relevance, importance, recency,
            proximity, frequency) summing to 1.0.
        conn: Optional DB connection for frequency lookups.
        context_files: Optional list of current file paths for proximity.

    Returns:
        Results list re-sorted by composite score, with 'composite_score'
        and 'score_factors' added to each entry. Returns [] for empty input
        (EDGE-001).
    """
    # EDGE-001: Empty results → return []
    if not results:
        return []

    # Step 1: Normalize BM25 scores across the result set
    raw_bm25 = [r.get("score", 0.0) for r in results]
    norm_bm25 = _score_bm25_relevance(raw_bm25)

    # Step 1.5: Batch-fetch access counts for frequency scoring
    access_counts = None  # type: Optional[Dict[str, int]]
    max_log_count = 0.0
    if conn is not None:
        entry_ids = [r.get("id", "") for r in results if r.get("id")]
        access_counts = _get_access_counts(conn, entry_ids)
        if access_counts:
            max_log_count = max(
                math.log(1.0 + c) for c in access_counts.values()
            )

    # Step 2: Compute per-entry composite scores
    scored = []  # type: List[Tuple[float, Dict[str, Any]]]
    for i, entry in enumerate(results):
        factors = {
            "relevance": norm_bm25[i],
            "importance": _score_importance(entry.get("layer", "")),
            "recency": _score_recency(entry.get("date", "")),
            "proximity": _score_proximity(entry, context_files),
            "frequency": _score_frequency(
                entry.get("id", ""),
                conn=conn,
                access_counts=access_counts,
                max_log_count=max_log_count,
            ),
        }

        composite = sum(
            weights.get(k, 0.0) * v for k, v in factors.items()
        )

        enriched = dict(entry)
        enriched["composite_score"] = round(composite, 4)
        enriched["score_factors"] = {
            k: round(v, 4) for k, v in factors.items()
        }
        scored.append((composite, enriched))

    # Step 3: Sort by composite score (descending — highest = best)
    scored.sort(key=lambda x: x[0], reverse=True)

    return [entry for _, entry in scored]


# Load weights once at module level (evaluated at import time).
# This avoids re-parsing env vars on every search call.
_SCORING_WEIGHTS = _load_scoring_weights()


# ---------------------------------------------------------------------------
# Dual-mode validation (C8 concern)
# ---------------------------------------------------------------------------

def _kendall_tau_distance(ranking_a: List[str], ranking_b: List[str]) -> float:
    """Compute normalized Kendall tau distance between two rankings.

    Measures the fraction of pairwise disagreements between two orderings
    of the same items. Returns 0.0 for identical rankings, 1.0 for
    completely reversed rankings.

    Args:
        ranking_a: List of item IDs in first ranking order.
        ranking_b: List of item IDs in second ranking order.

    Returns:
        Normalized Kendall tau distance in [0.0, 1.0].
    """
    if not ranking_a or not ranking_b:
        return 0.0

    # Build rank position maps
    pos_a = {item: i for i, item in enumerate(ranking_a)}
    pos_b = {item: i for i, item in enumerate(ranking_b)}

    # Only compare items present in both rankings
    common = [item for item in ranking_a if item in pos_b]
    n = len(common)
    if n < 2:
        return 0.0

    # Count pairwise disagreements
    discordant = 0
    total_pairs = n * (n - 1) // 2
    for i in range(n):
        for j in range(i + 1, n):
            item_i = common[i]
            item_j = common[j]
            # Concordant if relative order is same in both rankings
            a_order = pos_a[item_i] - pos_a[item_j]
            b_order = pos_b[item_i] - pos_b[item_j]
            if (a_order > 0) != (b_order > 0):
                discordant += 1

    return discordant / total_pairs if total_pairs > 0 else 0.0


def _log_validation_divergence(
    query: str,
    bm25_ranking: List[Dict[str, Any]],
    composite_ranking: List[Dict[str, Any]],
) -> None:
    """Log scoring divergence between BM25-only and composite rankings.

    Writes JSON lines to tmp/.rune-signals/.echo-scoring-validation.log.
    Non-blocking: silently catches I/O errors.

    Exit criteria (documented for operators):
    - Safe to switch when divergence > 0.2 in < 5% of queries
    - No Etched entry drops more than 0.15 in composite score
    - No original top-5 entry falls below top-20 in composite ranking

    Args:
        query: The search query.
        bm25_ranking: Top results from BM25-only scoring.
        composite_ranking: Top results from composite scoring.
    """
    bm25_ids = [r.get("id", "") for r in bm25_ranking[:5]]
    comp_ids = [r.get("id", "") for r in composite_ranking[:5]]

    tau = _kendall_tau_distance(
        [r.get("id", "") for r in bm25_ranking[:20]],
        [r.get("id", "") for r in composite_ranking[:20]],
    )

    # Check if any original top-5 fell below top-20
    comp_id_set_20 = {r.get("id", "") for r in composite_ranking[:20]}
    top5_drops = [eid for eid in bm25_ids if eid and eid not in comp_id_set_20]

    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query": query[:200],
        "bm25_top5": bm25_ids,
        "composite_top5": comp_ids,
        "tau_distance": round(tau, 4),
        "top5_dropped_from_top20": top5_drops,
    }

    # Derive log path from ECHO_DIR
    log_path = ""
    if ECHO_DIR:
        normalized = ECHO_DIR.rstrip(os.sep)
        suffix = os.path.join(".claude", "echoes")
        if normalized.endswith(suffix):
            project_root = normalized[: -len(suffix)].rstrip(os.sep)
        else:
            project_root = os.path.dirname(os.path.dirname(normalized))
        log_path = os.path.join(
            project_root, "tmp", ".rune-signals", ".echo-scoring-validation.log"
        )

    if not log_path:
        return

    try:
        log_dir = os.path.dirname(log_path)
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except OSError:
        pass  # Non-fatal: validation logging failure is silent


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


SCHEMA_VERSION = 2


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Apply V1 schema: core echo tables, access log, and FTS index."""
    conn.execute("""CREATE TABLE IF NOT EXISTS echo_entries (
        id TEXT PRIMARY KEY, role TEXT NOT NULL, layer TEXT NOT NULL,
        date TEXT, source TEXT, content TEXT NOT NULL,
        tags TEXT DEFAULT '', line_number INTEGER, file_path TEXT NOT NULL)""")
    conn.execute("CREATE TABLE IF NOT EXISTS echo_meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("""CREATE TABLE IF NOT EXISTS echo_access_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id TEXT NOT NULL,
        accessed_at TEXT NOT NULL, query TEXT DEFAULT '')""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access_log_entry_id ON echo_access_log(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access_log_accessed_at ON echo_access_log(accessed_at)")
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='echo_entries_fts'")
    if cursor.fetchone() is None:
        conn.execute("""CREATE VIRTUAL TABLE echo_entries_fts USING fts5(
            content, tags, source, content=echo_entries, tokenize='porter unicode61')""")


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Apply V2 schema: semantic groups and search failure tracking (EDGE-011)."""
    conn.execute("""CREATE TABLE IF NOT EXISTS semantic_groups (
        group_id TEXT NOT NULL, entry_id TEXT NOT NULL,
        similarity REAL NOT NULL DEFAULT 0.0, created_at TEXT NOT NULL,
        PRIMARY KEY (group_id, entry_id),
        FOREIGN KEY (entry_id) REFERENCES echo_entries(id) ON DELETE CASCADE)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_groups_entry ON semantic_groups(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_groups_group ON semantic_groups(group_id)")
    conn.execute("""CREATE TABLE IF NOT EXISTS echo_search_failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id TEXT NOT NULL,
        token_fingerprint TEXT NOT NULL, retry_count INTEGER NOT NULL DEFAULT 0,
        first_failed_at TEXT NOT NULL, last_retried_at TEXT,
        FOREIGN KEY (entry_id) REFERENCES echo_entries(id) ON DELETE CASCADE)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_search_failures_fingerprint ON echo_search_failures(token_fingerprint)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_search_failures_entry ON echo_search_failures(entry_id)")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure database schema is at the current version via PRAGMA user_version."""
    conn.execute("PRAGMA foreign_keys = ON")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        conn.execute("BEGIN IMMEDIATE")
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version < 1:
                _migrate_v1(conn)
            if version < 2:
                _migrate_v2(conn)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _tokenize_for_grouping(text: str) -> set[str]:
    """Extract lowercased, stopword-filtered tokens for Jaccard similarity."""
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) >= 2}


def _evidence_basenames(entry: Dict[str, Any]) -> set[str]:
    """Extract basenames of evidence file paths from an entry."""
    basenames = set()  # type: set[str]
    content = entry.get("content", "") or entry.get("content_preview", "") or ""
    for match in _EVIDENCE_PATH_RE.finditer(content):
        candidate = match.group(1)
        if "/" in candidate or os.sep in candidate:
            basenames.add(os.path.basename(candidate).lower())
    source = entry.get("source", "") or ""
    for token in source.split():
        if "/" in token and ":" not in token:
            basenames.add(os.path.basename(token).lower())
    file_path = entry.get("file_path", "") or ""
    if file_path:
        basenames.add(os.path.basename(file_path).lower())
    return basenames


def compute_entry_similarity(entry_a: Dict[str, Any], entry_b: Dict[str, Any]) -> float:
    """Compute Jaccard similarity between two echo entries (EDGE-007)."""
    features_a = _evidence_basenames(entry_a) | _tokenize_for_grouping(
        (entry_a.get("content", "") or "") + " " + (entry_a.get("tags", "") or ""))
    features_b = _evidence_basenames(entry_b) | _tokenize_for_grouping(
        (entry_b.get("content", "") or "") + " " + (entry_b.get("tags", "") or ""))
    if not features_a and not features_b:
        return 0.0
    union = features_a | features_b
    return len(features_a & features_b) / len(union) if union else 0.0


def assign_semantic_groups(
    conn: sqlite3.Connection, entries: list[Dict[str, Any]],
    threshold: float = 0.3, max_group_size: int = 20,
) -> int:
    """Assign entries to semantic groups based on Jaccard similarity."""
    if len(entries) < 2:
        return 0
    entry_map = {e["id"]: e for e in entries}
    entry_ids = list(entry_map.keys())
    groups = []  # type: list[tuple[str, set[str], dict[str, float]]]
    for i in range(len(entry_ids)):
        for j in range(i + 1, len(entry_ids)):
            id_a, id_b = entry_ids[i], entry_ids[j]
            sim = compute_entry_similarity(entry_map[id_a], entry_map[id_b])
            if sim < threshold:
                continue
            group_a = group_b = None
            for g in groups:
                if id_a in g[1]:
                    group_a = g
                if id_b in g[1]:
                    group_b = g
            if group_a is None and group_b is None:
                groups.append((uuid.uuid4().hex[:16], {id_a, id_b}, {id_a: sim, id_b: sim}))
            elif group_a is not None and group_b is None:
                group_a[1].add(id_b)
                group_a[2][id_b] = max(group_a[2].get(id_b, 0.0), sim)
            elif group_a is None and group_b is not None:
                group_b[1].add(id_a)
                group_b[2][id_a] = max(group_b[2].get(id_a, 0.0), sim)
            elif group_a is not None and group_b is not None and group_a is not group_b:
                group_a[1].update(group_b[1])
                for eid, s in group_b[2].items():
                    group_a[2][eid] = max(group_a[2].get(eid, 0.0), s)
                groups.remove(group_b)
            elif group_a is group_b and group_a is not None:
                group_a[2][id_a] = max(group_a[2].get(id_a, 0.0), sim)
                group_a[2][id_b] = max(group_a[2].get(id_b, 0.0), sim)
    groups = [g for g in groups if len(g[1]) >= 2]
    final_groups = []  # type: list[tuple[str, set[str], dict[str, float]]]
    for gid, members, sims in groups:
        if len(members) <= max_group_size:
            final_groups.append((gid, members, sims))
        else:
            sorted_m = sorted(members, key=lambda eid: sims.get(eid, 0.0), reverse=True)
            for cs in range(0, len(sorted_m), max_group_size):
                chunk = set(sorted_m[cs:cs + max_group_size])
                if len(chunk) >= 2:
                    final_groups.append(
                        (gid if cs == 0 else uuid.uuid4().hex[:16], chunk,
                         {eid: sims.get(eid, 0.0) for eid in chunk}))
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    count = 0
    for gid, members, sims in final_groups:
        for eid in members:
            conn.execute(
                "INSERT OR REPLACE INTO semantic_groups (group_id, entry_id, similarity, created_at) VALUES (?, ?, ?, ?)",
                (gid, eid, sims.get(eid, 0.0), now))
            count += 1
    conn.commit()
    return count


def upsert_semantic_group(
    conn: sqlite3.Connection, group_id: str,
    entry_ids: list[str], similarities: list[float] | None = None,
) -> int:
    """Insert or update a semantic group with the given entry memberships."""
    if not entry_ids:
        return 0
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if similarities is None:
        similarities = [0.0] * len(entry_ids)
    count = 0
    for eid, sim in zip(entry_ids, similarities):
        conn.execute(
            "INSERT OR REPLACE INTO semantic_groups (group_id, entry_id, similarity, created_at) VALUES (?, ?, ?, ?)",
            (group_id, eid, sim, now))
        count += 1
    conn.commit()
    return count


def expand_semantic_groups(
    conn: sqlite3.Connection,
    scored_results: list[Dict[str, Any]],
    weights: Dict[str, float],
    context_files: Optional[List[str]] = None,
    discount: float = 0.7,
    max_expansion: int = 5,
) -> list[Dict[str, Any]]:
    """Expand search results by fetching semantic group members.

    Runs AFTER composite scoring, BEFORE retry injection. For each
    result, looks up its group memberships, fetches other members not
    already in results, computes their composite scores, applies a
    discount factor, and appends them.

    Pipeline position rationale:
    - After composite: expanded entries need their OWN composite scores
    - Before retry: retry entries should NOT trigger group expansion
    - Before reranking: expanded entries must be in reranking candidate set

    Args:
        conn: Database connection with V2 schema.
        scored_results: Results with composite_score from compute_composite_score().
        weights: Scoring weights dict for composite score computation.
        context_files: Optional file paths for proximity scoring.
        discount: Multiplier for expanded entry scores (default 0.7).
        max_expansion: Max expanded entries to add per group (default 5).

    Returns:
        Combined list: original results + expanded entries (deduped by
        highest score per entry ID, EDGE-010).
    """
    if not scored_results:
        return scored_results

    # Collect entry IDs already in results
    existing_ids = {r.get("id", "") for r in scored_results if r.get("id")}

    # Batch-fetch group_ids for all result entries
    if not existing_ids:
        return scored_results

    placeholders = ",".join(["?"] * len(existing_ids))
    id_list = list(existing_ids)
    try:
        group_rows = conn.execute(
            "SELECT DISTINCT group_id FROM semantic_groups WHERE entry_id IN (%s)" % placeholders,
            id_list,
        ).fetchall()
    except sqlite3.OperationalError:
        return scored_results  # Table may not exist (pre-V2)

    group_ids = [r[0] for r in group_rows]
    if not group_ids:
        return scored_results

    # Batch-fetch all members of those groups NOT already in results
    gid_placeholders = ",".join(["?"] * len(group_ids))
    eid_placeholders = ",".join(["?"] * len(existing_ids))
    try:
        expanded_rows = conn.execute(
            """SELECT sg.group_id, e.id, e.source, e.layer, e.role, e.date,
                      substr(e.content, 1, 200) AS content_preview,
                      e.line_number, e.tags
               FROM semantic_groups sg
               JOIN echo_entries e ON e.id = sg.entry_id
               WHERE sg.group_id IN (%s)
                 AND sg.entry_id NOT IN (%s)""" % (gid_placeholders, eid_placeholders),
            group_ids + id_list,
        ).fetchall()
    except sqlite3.OperationalError:
        return scored_results

    if not expanded_rows:
        return scored_results

    # Build expanded entry dicts
    expanded_entries = []  # type: list[Dict[str, Any]]
    for row in expanded_rows:
        expanded_entries.append({
            "id": row["id"],
            "source": row["source"],
            "layer": row["layer"],
            "role": row["role"],
            "date": row["date"],
            "content_preview": row["content_preview"],
            "line_number": row["line_number"],
            "tags": row["tags"],
            "score": 0.0,  # No BM25 score for expanded entries
            "expansion_source": "group_expansion",
        })

    # Dedup expanded entries (keep first occurrence per ID)
    seen = set()  # type: set[str]
    unique_expanded = []  # type: list[Dict[str, Any]]
    for entry in expanded_entries:
        eid = entry["id"]
        if eid not in seen and eid not in existing_ids:
            seen.add(eid)
            unique_expanded.append(entry)

    # Cap at max_expansion per group (apply globally since groups may overlap)
    unique_expanded = unique_expanded[:max_expansion * len(group_ids)]

    if not unique_expanded:
        return scored_results

    # Compute composite scores for expanded entries
    scored_expanded = compute_composite_score(
        unique_expanded, weights, conn=conn, context_files=context_files,
    )

    # Apply discount to composite scores
    for entry in scored_expanded:
        original_score = entry.get("composite_score", 0.0)
        entry["composite_score"] = round(original_score * discount, 4)
        entry["expansion_source"] = "group_expansion"

    # Merge: combine original + expanded, dedup by highest composite_score (EDGE-010)
    combined = {}  # type: dict[str, Dict[str, Any]]
    for entry in scored_results:
        eid = entry.get("id", "")
        if eid:
            combined[eid] = entry

    for entry in scored_expanded:
        eid = entry.get("id", "")
        if eid and (eid not in combined or
                    entry.get("composite_score", 0.0) > combined[eid].get("composite_score", 0.0)):
            combined[eid] = entry

    # Sort by composite score descending
    result = sorted(combined.values(), key=lambda x: x.get("composite_score", 0.0), reverse=True)
    return result


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

        # EDGE-007: Orphan cleanup — remove access log rows for entry IDs
        # that no longer exist after reindex (stale references).
        conn.execute("""
            DELETE FROM echo_access_log
            WHERE entry_id NOT IN (SELECT id FROM echo_entries)
        """)

        # EDGE-010: Age-based pruning — remove access log entries older
        # than 180 days to prevent unbounded growth.
        cutoff = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(time.time() - 180 * 86400),
        )
        conn.execute(
            "DELETE FROM echo_access_log WHERE accessed_at < ?",
            (cutoff,),
        )

        # EDGE-020: Cleanup aged-out search failures at reindex time.
        # Removes entries whose first_failed_at is older than 30 days,
        # and orphaned failures referencing deleted entries.
        failure_cutoff = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(time.time() - 30 * 86400),
        )
        try:
            conn.execute(
                "DELETE FROM echo_search_failures WHERE first_failed_at < ?",
                (failure_cutoff,),
            )
            conn.execute("""
                DELETE FROM echo_search_failures
                WHERE entry_id NOT IN (SELECT id FROM echo_entries)
            """)
        except sqlite3.OperationalError:
            pass  # Table may not exist yet (pre-V2 schema)

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


# ---------------------------------------------------------------------------
# Failed entry retry with token fingerprinting (Task 6)
# ---------------------------------------------------------------------------

_FAILURE_MAX_RETRIES = 3
_FAILURE_MAX_AGE_DAYS = 30
_FAILURE_SCORE_BOOST = 1.2  # Multiply BM25 score by 1.2 (more negative = better)


def compute_token_fingerprint(query: str) -> str:
    """Compute a stable token fingerprint for a search query.

    Uses the same tokenization as build_fts_query(): extract alphanumeric
    tokens, filter stopwords and short tokens, then sort and deduplicate.
    The sorted unique tokens are joined and hashed with SHA-256 (EDGE-016).

    Args:
        query: Raw search query string.

    Returns:
        Hex SHA-256 digest of the normalized token set. Returns empty string
        for queries with no usable tokens.
    """
    tokens = re.findall(r"[a-zA-Z0-9_]+", query.lower()[:500])
    filtered = sorted(set(t for t in tokens if t not in STOPWORDS and len(t) >= 2))
    if not filtered:
        return ""
    return hashlib.sha256(" ".join(filtered).encode("utf-8")).hexdigest()


def record_search_failure(
    conn: sqlite3.Connection,
    entry_id: str,
    token_fingerprint: str,
) -> None:
    """Record a failed match for an entry against a query fingerprint.

    Inserts a new failure record or increments retry_count for an existing
    one. Respects max retry limit (_FAILURE_MAX_RETRIES). Ages from
    first failure timestamp, not last retry (EDGE-018).

    Args:
        conn: SQLite database connection.
        entry_id: The echo entry ID that was not matched.
        token_fingerprint: SHA-256 hex digest of query tokens.
    """
    if not entry_id or not token_fingerprint:
        return
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        existing = conn.execute(
            """SELECT id, retry_count FROM echo_search_failures
               WHERE entry_id = ? AND token_fingerprint = ?""",
            (entry_id, token_fingerprint),
        ).fetchone()
        if existing is None:
            conn.execute(
                """INSERT INTO echo_search_failures
                   (entry_id, token_fingerprint, retry_count, first_failed_at, last_retried_at)
                   VALUES (?, ?, 0, ?, NULL)""",
                (entry_id, token_fingerprint, now),
            )
        elif existing["retry_count"] < _FAILURE_MAX_RETRIES:
            conn.execute(
                """UPDATE echo_search_failures
                   SET retry_count = retry_count + 1, last_retried_at = ?
                   WHERE id = ?""",
                (now, existing["id"]),
            )
        # If retry_count >= MAX, don't update (entry is exhausted)
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Table may not exist (pre-V2)


def reset_failure_on_match(
    conn: sqlite3.Connection,
    entry_id: str,
    token_fingerprint: str,
) -> None:
    """Reset failure tracking when an entry is successfully matched.

    Removes the failure record for the entry+fingerprint pair, allowing
    future re-discovery (EDGE-017).

    Args:
        conn: SQLite database connection.
        entry_id: The echo entry ID that was matched.
        token_fingerprint: SHA-256 hex digest of query tokens.
    """
    if not entry_id or not token_fingerprint:
        return
    try:
        conn.execute(
            """DELETE FROM echo_search_failures
               WHERE entry_id = ? AND token_fingerprint = ?""",
            (entry_id, token_fingerprint),
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Table may not exist (pre-V2)


def get_retry_entries(
    conn: sqlite3.Connection,
    token_fingerprint: str,
    matched_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve entries eligible for retry based on a query fingerprint.

    Returns entries that previously failed to match a similar query
    (same token fingerprint), haven't exceeded max retries, and aren't
    older than 30 days. Applies a 20% score boost (EDGE-019).

    Args:
        conn: SQLite database connection.
        token_fingerprint: SHA-256 hex digest of query tokens.
        matched_ids: Entry IDs already in results (to skip duplicates).

    Returns:
        List of result dicts with boosted scores, ready to merge with
        primary search results.
    """
    if not token_fingerprint:
        return []

    age_cutoff = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.time() - _FAILURE_MAX_AGE_DAYS * 86400),
    )

    try:
        sql = """
            SELECT
                f.entry_id,
                e.source, e.layer, e.role, e.date,
                substr(e.content, 1, 200) AS content_preview,
                e.line_number,
                f.retry_count
            FROM echo_search_failures f
            JOIN echo_entries e ON e.id = f.entry_id
            WHERE f.token_fingerprint = ?
              AND f.retry_count < ?
              AND f.first_failed_at >= ?
        """
        params: List[Any] = [token_fingerprint, _FAILURE_MAX_RETRIES, age_cutoff]

        if matched_ids:
            placeholders = ",".join(["?"] * len(matched_ids))
            sql += " AND f.entry_id NOT IN (%s)" % placeholders
            params.extend(matched_ids)

        cursor = conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            # EDGE-019: Score boost — use a base BM25-like score and multiply
            # by 1.2 to make it more negative (better rank).
            # Base score: -1.0 (reasonable default for retry entries)
            base_score = -1.0
            boosted_score = round(base_score * _FAILURE_SCORE_BOOST, 4)
            results.append({
                "id": row["entry_id"],
                "source": row["source"],
                "layer": row["layer"],
                "role": row["role"],
                "date": row["date"],
                "content_preview": row["content_preview"],
                "score": boosted_score,
                "line_number": row["line_number"],
                "retry_source": True,
            })
        return results
    except sqlite3.OperationalError:
        return []  # Table may not exist (pre-V2)


def cleanup_aged_failures(conn: sqlite3.Connection) -> int:
    """Remove search failure entries older than 30 days.

    Probability-based: called from search handler with 1% chance to
    avoid running on every query (EDGE-020). Also called unconditionally
    during reindex.

    Args:
        conn: SQLite database connection.

    Returns:
        Number of rows deleted.
    """
    cutoff = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.time() - _FAILURE_MAX_AGE_DAYS * 86400),
    )
    try:
        cursor = conn.execute(
            "DELETE FROM echo_search_failures WHERE first_failed_at < ?",
            (cutoff,),
        )
        conn.commit()
        return cursor.rowcount
    except sqlite3.OperationalError:
        return 0  # Table may not exist (pre-V2)


# ---------------------------------------------------------------------------
# Talisman config with mtime caching (Task 7)
# ---------------------------------------------------------------------------

_talisman_cache = {"mtime": 0.0, "config": {}}  # type: Dict[str, Any]
_RUNE_TRACE = os.environ.get("RUNE_TRACE", "") == "1"


def _trace(stage: str, start: float) -> None:
    """Log pipeline stage timing to stderr when RUNE_TRACE=1 (EDGE-029)."""
    if _RUNE_TRACE:
        elapsed_ms = (time.time() - start) * 1000
        print("[echo-search] %s: %.1fms" % (stage, elapsed_ms), file=sys.stderr)


def _load_talisman() -> Dict[str, Any]:
    """Load talisman.yml config with file mtime caching.

    Lazy-imports PyYAML inside the function. If PyYAML is not installed
    or talisman.yml doesn't exist, returns empty dict (all features disabled).
    Config is cached and only re-read when file mtime changes.

    Returns:
        Parsed talisman config dict, or empty dict on any failure.
    """
    # Find talisman.yml: project-level (.claude/talisman.yml)
    # Fall back to CLAUDE_CONFIG_DIR/talisman.yml
    talisman_paths = []
    if ECHO_DIR:
        # ECHO_DIR is <project>/.claude/echoes — go up 2 levels for .claude/
        claude_dir = os.path.dirname(ECHO_DIR.rstrip(os.sep))
        talisman_paths.append(os.path.join(claude_dir, "talisman.yml"))
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    talisman_paths.append(os.path.join(config_dir, "talisman.yml"))

    for talisman_path in talisman_paths:
        try:
            mtime = os.path.getmtime(talisman_path)
        except OSError:
            continue

        if mtime == _talisman_cache["mtime"] and _talisman_cache["config"]:
            return _talisman_cache["config"]

        try:
            import yaml  # Lazy import — zero cost if file absent
        except ImportError:
            return {}

        try:
            with open(talisman_path, "r") as f:
                config = yaml.safe_load(f)
            if isinstance(config, dict):
                _talisman_cache["mtime"] = mtime
                _talisman_cache["config"] = config
                return config
        except (OSError, ValueError):
            pass

    return {}


def _get_echoes_config(talisman: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Extract a nested echoes config section from talisman.

    Args:
        talisman: Full talisman config dict.
        key: Config key under 'echoes' (e.g., 'decomposition', 'reranking').

    Returns:
        Config dict for the section, or empty dict if not found.
    """
    echoes = talisman.get("echoes", {})
    if not isinstance(echoes, dict):
        return {}
    section = echoes.get(key, {})
    return section if isinstance(section, dict) else {}


# ---------------------------------------------------------------------------
# Multi-pass retrieval pipeline (Task 7)
# ---------------------------------------------------------------------------

async def pipeline_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
    layer: Optional[str] = None,
    role: Optional[str] = None,
    context_files: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Multi-pass retrieval pipeline wiring all enhancement stages.

    Pipeline: Query -> decomposition -> per-facet BM25 -> merge ->
    composite scoring -> group expansion -> retry injection ->
    reranking -> top N

    Each stage is independently toggleable via talisman.yml config.
    Config is re-read per call (mtime-cached) for hot-reload support.

    Args:
        conn: Database connection with V2 schema.
        query: Search query string.
        limit: Max results to return.
        layer: Optional layer filter.
        role: Optional role filter.
        context_files: Optional file paths for proximity scoring.

    Returns:
        Final ranked list of search result dicts, capped at limit.
    """
    talisman = _load_talisman()
    overfetch_limit = min(limit * 3, 150)
    pipeline_start = time.time()

    # Stage 1: Query decomposition (async subprocess, 3s timeout)
    decomp_config = _get_echoes_config(talisman, "decomposition")
    facets = [query]
    if decomp_config.get("enabled", False):
        t0 = time.time()
        try:
            from decomposer import decompose_query
            facets = await decompose_query(query)
            if not facets:
                facets = [query]
        except (ImportError, OSError) as e:
            if _RUNE_TRACE:
                print("[echo-search] decomposition error: %s" % e, file=sys.stderr)
            facets = [query]
        _trace("decomposition", t0)

    # Stage 2: Per-facet BM25 search
    t0 = time.time()
    all_facet_results = []  # type: list[list[Dict[str, Any]]]
    for facet in facets:
        results = search_entries(conn, facet, overfetch_limit, layer, role)
        all_facet_results.append(results)
    _trace("bm25_search (%d facets)" % len(facets), t0)

    # Stage 3: Merge multi-facet results (EDGE-013: most-negative = best)
    t0 = time.time()
    if len(all_facet_results) == 1:
        candidates = all_facet_results[0]
    else:
        try:
            from decomposer import merge_results_by_best_score
            candidates = merge_results_by_best_score(all_facet_results)
        except ImportError:
            candidates = all_facet_results[0] if all_facet_results else []
    _trace("merge", t0)

    # Stage 4: Composite scoring
    t0 = time.time()
    scored = compute_composite_score(
        candidates, _SCORING_WEIGHTS, conn=conn, context_files=context_files,
    )
    _trace("composite_scoring", t0)

    # Stage 5: Group expansion (after composite, before retry)
    groups_config = _get_echoes_config(talisman, "semantic_groups")
    if groups_config.get("expansion_enabled", False):
        t0 = time.time()
        discount = groups_config.get("discount", 0.7)
        max_expansion = groups_config.get("max_expansion", 5)
        scored = expand_semantic_groups(
            conn, scored, _SCORING_WEIGHTS,
            context_files=context_files,
            discount=discount, max_expansion=max_expansion,
        )
        _trace("group_expansion", t0)

    # Stage 6: Retry injection (after group expansion, before reranking)
    retry_config = _get_echoes_config(talisman, "retry")
    if retry_config.get("enabled", False):
        t0 = time.time()
        fingerprint = compute_token_fingerprint(query)
        if fingerprint:
            matched_ids = [r.get("id", "") for r in scored if r.get("id")]
            retry_entries = get_retry_entries(conn, fingerprint, matched_ids)
            if retry_entries:
                # Score retry entries and merge
                retry_scored = compute_composite_score(
                    retry_entries, _SCORING_WEIGHTS, conn=conn, context_files=context_files,
                )
                for entry in retry_scored:
                    entry["retry_source"] = True
                # Dedup: keep best composite_score per entry ID
                combined = {r.get("id", ""): r for r in scored if r.get("id")}
                for entry in retry_scored:
                    eid = entry.get("id", "")
                    if eid and (eid not in combined or
                                entry.get("composite_score", 0.0) > combined[eid].get("composite_score", 0.0)):
                        combined[eid] = entry
                scored = sorted(combined.values(), key=lambda x: x.get("composite_score", 0.0), reverse=True)
        _trace("retry_injection", t0)

    # Stage 7: Haiku reranking (async subprocess, 4s timeout)
    # EDGE-028: threshold check happens AFTER all enrichment stages
    rerank_config = _get_echoes_config(talisman, "reranking")
    if rerank_config.get("enabled", False):
        t0 = time.time()
        try:
            from reranker import rerank_results
            scored = await rerank_results(query, scored, rerank_config)
        except (ImportError, OSError) as e:
            if _RUNE_TRACE:
                print("[echo-search] reranking error: %s" % e, file=sys.stderr)
        _trace("reranking", t0)

    _trace("pipeline_total", pipeline_start)

    return scored[:limit]


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
            e.id, e.source, e.layer, e.role, e.date,
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
            "date": row["date"],
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
# Observations auto-promotion
# ---------------------------------------------------------------------------
#
# Observations entries auto-promote to Inscribed after reaching 3 access_count
# references in echo_access_log (C1 concern: depends on Task 2).
# Promotion rewrites the H2 header in the source MEMORY.md file from
# "## Observations" to "## Inscribed".
#
# C3 concern (CRITICAL): Atomic file rewrite — read full file -> modify
# in-memory -> write to temp file -> os.replace(tmp, original). os.replace()
# is POSIX-atomic (rename syscall), so readers never see a partial write.

_PROMOTION_THRESHOLD = 3  # access_count >= 3 triggers promotion
_OBSERVATIONS_HEADER_RE = re.compile(
    r"^(##\s+)Observations(\s*[\u2014\-\u2013]+\s*.+)$"
)


def _promote_observations_in_file(
    memory_file: str,
    entry_ids_to_promote: set,
    entry_line_map: Dict[str, int],
) -> int:
    """Rewrite Observations headers to Inscribed in a single MEMORY.md file.

    Uses atomic file rewrite (C3 concern): read -> modify in-memory ->
    write to temp file -> os.replace().

    Args:
        memory_file: Absolute path to the MEMORY.md file.
        entry_ids_to_promote: Set of entry IDs that qualify for promotion.
        entry_line_map: Mapping of entry_id -> line_number in this file.

    Returns:
        Number of entries promoted in this file.
    """
    # Collect line numbers that need promotion in this file
    promote_lines = set()  # type: set
    for eid in entry_ids_to_promote:
        line_num = entry_line_map.get(eid)
        if line_num is not None:
            promote_lines.add(line_num)

    if not promote_lines:
        return 0

    # EDGE-023: Check writability before attempting
    if not os.access(memory_file, os.W_OK):
        print(
            "Warning: Observations promotion skipped — file not writable: %s"
            % memory_file,
            file=sys.stderr,
        )
        return 0

    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as exc:
        print(
            "Warning: Observations promotion — cannot read %s: %s"
            % (memory_file, exc),
            file=sys.stderr,
        )
        return 0

    promoted = 0
    for i, line in enumerate(lines):
        line_num = i + 1  # 1-indexed to match entry_line_map
        if line_num not in promote_lines:
            continue
        match = _OBSERVATIONS_HEADER_RE.match(line.rstrip("\n"))
        if match:
            # EDGE-022: Only match layer="observations" headers — skip
            # if already rewritten to Inscribed (idempotent).
            lines[i] = match.group(1) + "Inscribed" + match.group(2) + "\n"
            promoted += 1

    if promoted == 0:
        return 0

    # C3: Atomic rewrite — write to temp file in same directory, then
    # os.replace() which is a POSIX-atomic rename syscall.
    file_dir = os.path.dirname(memory_file)
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=file_dir, prefix=".promote-", suffix=".md"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
                tmp_f.writelines(lines)
            os.replace(tmp_path, memory_file)
        except BaseException:
            # Clean up temp file on any failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as exc:
        print(
            "Warning: Observations promotion — atomic write failed for %s: %s"
            % (memory_file, exc),
            file=sys.stderr,
        )
        return 0

    return promoted


def _check_promotions(echo_dir: str, db_path: str) -> int:
    """Check for Observations entries eligible for promotion to Inscribed.

    Called from do_reindex() BEFORE discover_and_parse() so that promoted
    entries are re-indexed with their new layer name.

    Promotion criteria: access_count >= _PROMOTION_THRESHOLD (3) in
    echo_access_log (C1 concern: requires Task 2 schema).
    EDGE-022: Only promotes entries with layer='observations'
    (skips already-promoted entries for idempotency).

    Args:
        echo_dir: Path to .claude/echoes/ directory.
        db_path: Path to SQLite database.

    Returns:
        Number of entries promoted. Returns 0 on any failure (non-fatal).
    """
    if not echo_dir or not db_path:
        return 0

    conn = get_db(db_path)
    try:
        ensure_schema(conn)

        # Find all Observations entries.
        # EDGE-022: Filter by layer='observations' only — already-promoted
        # entries have layer='inscribed' and won't match.
        cursor = conn.execute(
            """SELECT e.id, e.file_path, e.line_number
               FROM echo_entries e
               WHERE e.layer = 'observations'"""
        )
        obs_entries = cursor.fetchall()
        if not obs_entries:
            return 0

        # Batch-fetch access counts from echo_access_log (Task 2).
        # Uses _get_access_counts() added by Task 2. If the table doesn't
        # exist yet, the OperationalError catch below handles it gracefully.
        entry_ids = [row["id"] for row in obs_entries]
        capped_ids = entry_ids[:200]
        placeholders = ",".join(["?"] * len(capped_ids))
        count_cursor = conn.execute(
            """SELECT entry_id, COUNT(*) AS cnt
               FROM echo_access_log
               WHERE entry_id IN (%s)
               GROUP BY entry_id""" % placeholders,
            capped_ids,
        )
        access_counts = {
            row["entry_id"]: row["cnt"] for row in count_cursor.fetchall()
        }  # type: Dict[str, int]

        # Build promotion candidates per file
        promote_by_file = {}  # type: Dict[str, tuple]
        for row in obs_entries:
            eid = row["id"]
            fpath = row["file_path"]
            line_num = row["line_number"]
            count = access_counts.get(eid, 0)

            if count >= _PROMOTION_THRESHOLD:
                if fpath not in promote_by_file:
                    promote_by_file[fpath] = (set(), {})
                promote_by_file[fpath][0].add(eid)
                promote_by_file[fpath][1][eid] = line_num

        total_promoted = 0
        for fpath, (ids_to_promote, line_map) in promote_by_file.items():
            promoted = _promote_observations_in_file(fpath, ids_to_promote, line_map)
            total_promoted += promoted

        # EDGE-021: Trigger dirty signal after promotion so FTS re-indexes
        # on the next search call (if not already in a reindex cycle).
        if total_promoted > 0:
            sig_path = _signal_path(echo_dir)
            if sig_path:
                try:
                    sig_dir = os.path.dirname(sig_path)
                    os.makedirs(sig_dir, exist_ok=True)
                    with open(sig_path, "w") as f:
                        f.write("promoted")
                except OSError:
                    pass  # Non-fatal: signal write failure doesn't break promotion

    except sqlite3.OperationalError as exc:
        # Non-fatal: promotion failure should not break reindex.
        # This also gracefully handles the case where echo_access_log
        # table doesn't exist yet (before Task 2 schema migration).
        print(
            "Warning: Observations promotion check failed: %s" % exc,
            file=sys.stderr,
        )
        return 0
    finally:
        conn.close()

    return total_promoted


# ---------------------------------------------------------------------------
# Reindex helper (used by both CLI and MCP tool)
# ---------------------------------------------------------------------------

def do_reindex(echo_dir: str, db_path: str) -> Dict[str, Any]:
    """Re-parse all MEMORY.md files and rebuild the FTS index.

    Runs auto-promotion of Observations to Inscribed BEFORE parsing,
    so promoted entries are indexed with their new layer name.

    Args:
        echo_dir: Path to .claude/echoes/ directory.
        db_path: Path to SQLite database file.

    Returns:
        Dict with entries_indexed, time_ms, roles, and optionally
        observations_promoted count.
    """
    from indexer import discover_and_parse

    start_ms = int(time.time() * 1000)

    # Auto-promote eligible Observations to Inscribed BEFORE parsing.
    # This ensures promoted entries are indexed with their new layer name.
    promotions = _check_promotions(echo_dir, db_path)

    entries = discover_and_parse(echo_dir)
    conn = get_db(db_path)
    try:
        ensure_schema(conn)
        count = rebuild_index(conn, entries)
    finally:
        conn.close()
    elapsed_ms = int(time.time() * 1000) - start_ms

    roles = sorted(set(e["role"] for e in entries))

    result = {
        "entries_indexed": count,
        "time_ms": elapsed_ms,
        "roles": roles,
    }  # type: Dict[str, Any]
    if promotions > 0:
        result["observations_promoted"] = promotions

    return result


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
                        "context_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of currently open/edited file paths for proximity scoring",
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
            types.Tool(
                name="echo_record_access",
                description=(
                    "Manually record access events for specific echo entry IDs. "
                    "Normally access is auto-recorded on search, but this tool "
                    "allows explicit recording (e.g., when an entry is viewed)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entry_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of echo entry IDs to record access for",
                        },
                        "query": {
                            "type": "string",
                            "description": "Optional context query that led to this access",
                            "default": "",
                        },
                    },
                    "required": ["entry_ids"],
                },
            ),
            types.Tool(
                name="echo_upsert_group",
                description=(
                    "Create or update a semantic group of echo entries. "
                    "Groups cluster related entries for expanded retrieval."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "group_id": {
                            "type": "string",
                            "description": "Group identifier (16-char hex). Auto-generated if omitted.",
                        },
                        "entry_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of echo entry IDs to include in the group",
                        },
                        "similarities": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Optional similarity scores per entry (default 0.0)",
                        },
                    },
                    "required": ["entry_ids"],
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
            elif name == "echo_record_access":
                return await _handle_record_access(arguments)
            elif name == "echo_upsert_group":
                return await _handle_upsert_group(arguments)
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
        context_files = arguments.get("context_files")

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

        # Validate context_files: must be list of strings, capped at 20
        if context_files is not None:
            if not isinstance(context_files, list):
                context_files = None
            else:
                context_files = [
                    str(f) for f in context_files[:20]
                    if isinstance(f, str) and f
                ]
                if not context_files:
                    context_files = None

        # Clamp limit
        if not isinstance(limit, int) or limit < 1:
            limit = 10
        limit = min(limit, 50)

        conn = get_db(DB_PATH)
        try:
            ensure_schema(conn)

            # Auto-reindex when DB is empty OR dirty signal is present.
            count = conn.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
            is_dirty = _check_and_clear_dirty(ECHO_DIR)
            if (count == 0 or is_dirty) and ECHO_DIR:
                conn.close()
                do_reindex(ECHO_DIR, DB_PATH)
                conn = get_db(DB_PATH)

            # Multi-pass retrieval pipeline (Task 7)
            results = await pipeline_search(
                conn, query, limit, layer, role, context_files,
            )

            # C2 concern: Record access SYNCHRONOUSLY before returning.
            _record_access(conn, results, query)
        finally:
            conn.close()

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

    async def _handle_record_access(arguments):
        # type: (Dict) -> List[types.TextContent]
        """Handle echo_record_access tool — manually record access events."""
        entry_ids = arguments.get("entry_ids", [])
        query = arguments.get("query", "")

        # SEC-3: Type validation
        if not isinstance(entry_ids, list):
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "entry_ids must be a list"}),
                    isError=True,
                )
            ]
        if not entry_ids:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "entry_ids is required"}),
                    isError=True,
                )
            ]
        if not isinstance(query, str):
            query = ""

        # Coerce and cap
        entry_ids = [str(eid) for eid in entry_ids if eid is not None][:50]

        # Build pseudo-results for _record_access
        pseudo_results = [{"id": eid} for eid in entry_ids]

        conn = get_db(DB_PATH)
        try:
            ensure_schema(conn)
            _record_access(conn, pseudo_results, query)
        finally:
            conn.close()

        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "recorded": len(entry_ids),
                    "entry_ids": entry_ids,
                }),
            )
        ]

    async def _handle_upsert_group(arguments):
        # type: (Dict) -> List[types.TextContent]
        """Handle echo_upsert_group tool — create or update a semantic group."""
        entry_ids = arguments.get("entry_ids", [])
        group_id = arguments.get("group_id", "")
        similarities = arguments.get("similarities")

        # SEC-3: Type validation
        if not isinstance(entry_ids, list):
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "entry_ids must be a list"}),
                    isError=True,
                )
            ]
        if not entry_ids:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "entry_ids is required"}),
                    isError=True,
                )
            ]

        # Coerce and cap
        entry_ids = [str(eid) for eid in entry_ids if eid is not None][:50]

        if not isinstance(group_id, str) or not group_id:
            group_id = uuid.uuid4().hex[:16]

        # Validate similarities if provided
        if similarities is not None:
            if not isinstance(similarities, list):
                similarities = None
            else:
                # Ensure same length as entry_ids, pad or truncate
                similarities = [
                    float(s) if isinstance(s, (int, float)) else 0.0
                    for s in similarities[:len(entry_ids)]
                ]
                if len(similarities) < len(entry_ids):
                    similarities.extend([0.0] * (len(entry_ids) - len(similarities)))

        conn = get_db(DB_PATH)
        try:
            ensure_schema(conn)
            count = upsert_semantic_group(conn, group_id, entry_ids, similarities)
        finally:
            conn.close()

        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "group_id": group_id,
                    "memberships": count,
                    "entry_ids": entry_ids,
                }),
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
                    server_version="1.54.0",
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
