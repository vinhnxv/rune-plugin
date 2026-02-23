"""Tests for failed entry retry with token fingerprinting (Task 6)."""

from __future__ import annotations

import hashlib
import sqlite3
import time

import pytest

from server import (
    STOPWORDS,
    _FAILURE_MAX_RETRIES,
    _FAILURE_SCORE_BOOST,
    cleanup_aged_failures,
    compute_token_fingerprint,
    ensure_schema,
    get_retry_entries,
    record_search_failure,
    reset_failure_on_match,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _create_v2_tables(conn: sqlite3.Connection) -> None:
    """Create V2 tables that Task 1 migration adds.

    Task 1's patch adds these via _migrate_v2(), but since that patch
    isn't applied to the working tree, we create them manually for testing.
    """
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS echo_search_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            token_fingerprint TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            first_failed_at TEXT NOT NULL,
            last_retried_at TEXT,
            FOREIGN KEY (entry_id) REFERENCES echo_entries(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_failures_fingerprint
            ON echo_search_failures(token_fingerprint)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_failures_entry
            ON echo_search_failures(entry_id)
    """)
    conn.commit()


@pytest.fixture
def db():
    """In-memory SQLite database with V1 schema + V2 failure tracking table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    _create_v2_tables(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_entry(db):
    """Insert a sample echo entry and return its ID."""
    entry_id = "retry_test_ent_01"
    db.execute(
        """INSERT INTO echo_entries
           (id, role, layer, date, source, content, tags, line_number, file_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (entry_id, "reviewer", "inscribed", "2026-01-15",
         "rune:appraise", "Test content for retry", "tags", 5, "/path/MEMORY.md"),
    )
    db.commit()
    return entry_id


@pytest.fixture
def second_entry(db):
    """Insert a second sample echo entry and return its ID."""
    entry_id = "retry_test_ent_02"
    db.execute(
        """INSERT INTO echo_entries
           (id, role, layer, date, source, content, tags, line_number, file_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (entry_id, "orchestrator", "etched", "2026-02-01",
         "rune:arc", "Another test entry", "more tags", 10, "/path2/MEMORY.md"),
    )
    db.commit()
    return entry_id


# ---------------------------------------------------------------------------
# compute_token_fingerprint tests
# ---------------------------------------------------------------------------

class TestComputeTokenFingerprint:
    def test_basic_fingerprint(self) -> None:
        fp = compute_token_fingerprint("team lifecycle cleanup")
        assert len(fp) == 64  # SHA-256 hex digest length
        assert fp  # Not empty

    def test_stopwords_removed(self) -> None:
        """Fingerprint should exclude stopwords (same as build_fts_query)."""
        fp_with_stops = compute_token_fingerprint("the team and the lifecycle")
        fp_without = compute_token_fingerprint("team lifecycle")
        assert fp_with_stops == fp_without

    def test_order_independent(self) -> None:
        """Token fingerprint is order-independent (sorted tokens)."""
        fp1 = compute_token_fingerprint("lifecycle team cleanup")
        fp2 = compute_token_fingerprint("team cleanup lifecycle")
        assert fp1 == fp2

    def test_case_insensitive(self) -> None:
        fp1 = compute_token_fingerprint("Team Lifecycle")
        fp2 = compute_token_fingerprint("team lifecycle")
        assert fp1 == fp2

    def test_deduplication(self) -> None:
        """Duplicate tokens are deduplicated."""
        fp1 = compute_token_fingerprint("team team lifecycle lifecycle")
        fp2 = compute_token_fingerprint("team lifecycle")
        assert fp1 == fp2

    def test_short_tokens_excluded(self) -> None:
        """Tokens shorter than 2 chars are excluded."""
        fp = compute_token_fingerprint("a b c team")
        fp_just_team = compute_token_fingerprint("team")
        assert fp == fp_just_team

    def test_empty_query(self) -> None:
        assert compute_token_fingerprint("") == ""

    def test_all_stopwords(self) -> None:
        assert compute_token_fingerprint("the and or but") == ""

    def test_input_capped_at_500(self) -> None:
        """Query input is capped at 500 chars for safety."""
        long_query = "token " * 200  # 1200 chars
        fp = compute_token_fingerprint(long_query)
        assert fp  # Should still produce a fingerprint

    def test_known_hash(self) -> None:
        """Verify fingerprint matches expected SHA-256 for known input."""
        # "cleanup lifecycle team" (sorted, deduplicated)
        expected = hashlib.sha256(
            "cleanup lifecycle team".encode("utf-8")
        ).hexdigest()
        fp = compute_token_fingerprint("team lifecycle cleanup")
        assert fp == expected


# ---------------------------------------------------------------------------
# record_search_failure tests
# ---------------------------------------------------------------------------

class TestRecordSearchFailure:
    def test_records_new_failure(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)

        row = db.execute(
            "SELECT * FROM echo_search_failures WHERE entry_id=?", (sample_entry,)
        ).fetchone()
        assert row is not None
        assert row["retry_count"] == 0
        assert row["token_fingerprint"] == fp
        assert row["first_failed_at"]  # Non-empty timestamp
        assert row["last_retried_at"] is None

    def test_increments_retry_count(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)
        record_search_failure(db, sample_entry, fp)

        row = db.execute(
            "SELECT * FROM echo_search_failures WHERE entry_id=?", (sample_entry,)
        ).fetchone()
        assert row["retry_count"] == 1
        assert row["last_retried_at"] is not None

    def test_max_retries_respected(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        # Record initial + MAX retries
        for _ in range(_FAILURE_MAX_RETRIES + 2):
            record_search_failure(db, sample_entry, fp)

        row = db.execute(
            "SELECT * FROM echo_search_failures WHERE entry_id=?", (sample_entry,)
        ).fetchone()
        # retry_count should not exceed MAX - 1 (starts at 0, increments MAX-1 times)
        assert row["retry_count"] <= _FAILURE_MAX_RETRIES

    def test_noop_for_empty_entry_id(self, db) -> None:
        record_search_failure(db, "", "somefingerprint")
        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 0

    def test_noop_for_empty_fingerprint(self, db, sample_entry) -> None:
        record_search_failure(db, sample_entry, "")
        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 0

    def test_first_failed_at_preserved(self, db, sample_entry) -> None:
        """First failure timestamp is NOT updated on subsequent failures (EDGE-018)."""
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)

        first_ts = db.execute(
            "SELECT first_failed_at FROM echo_search_failures WHERE entry_id=?",
            (sample_entry,),
        ).fetchone()["first_failed_at"]

        # Record again — first_failed_at should be preserved
        record_search_failure(db, sample_entry, fp)

        second_ts = db.execute(
            "SELECT first_failed_at FROM echo_search_failures WHERE entry_id=?",
            (sample_entry,),
        ).fetchone()["first_failed_at"]

        assert first_ts == second_ts


# ---------------------------------------------------------------------------
# reset_failure_on_match tests
# ---------------------------------------------------------------------------

class TestResetFailureOnMatch:
    def test_resets_on_match(self, db, sample_entry) -> None:
        """Successful match removes the failure record (EDGE-017)."""
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)

        # Verify failure exists
        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 1

        # Reset on match
        reset_failure_on_match(db, sample_entry, fp)

        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 0

    def test_noop_for_nonexistent(self, db) -> None:
        """Reset for non-existent entry/fingerprint does nothing."""
        reset_failure_on_match(db, "nonexistent", "fakefingerprint")
        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 0

    def test_noop_for_empty_values(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)

        reset_failure_on_match(db, "", fp)
        reset_failure_on_match(db, sample_entry, "")

        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 1  # Still exists

    def test_only_resets_matching_fingerprint(self, db, sample_entry) -> None:
        """Reset only removes the specific fingerprint match."""
        fp1 = compute_token_fingerprint("team lifecycle")
        fp2 = compute_token_fingerprint("debug error handling pattern")
        record_search_failure(db, sample_entry, fp1)
        record_search_failure(db, sample_entry, fp2)

        reset_failure_on_match(db, sample_entry, fp1)

        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 1  # fp2 still exists


# ---------------------------------------------------------------------------
# get_retry_entries tests
# ---------------------------------------------------------------------------

class TestGetRetryEntries:
    def test_returns_eligible_entries(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)

        results = get_retry_entries(db, fp)
        assert len(results) == 1
        assert results[0]["id"] == sample_entry
        assert results[0]["retry_source"] is True

    def test_score_boost_direction(self, db, sample_entry) -> None:
        """Score boost makes score more negative (EDGE-019)."""
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)

        results = get_retry_entries(db, fp)
        assert results[0]["score"] < 0  # Negative
        expected_score = round(-1.0 * _FAILURE_SCORE_BOOST, 4)
        assert results[0]["score"] == expected_score

    def test_excludes_matched_ids(self, db, sample_entry, second_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)
        record_search_failure(db, second_entry, fp)

        results = get_retry_entries(db, fp, matched_ids=[sample_entry])
        assert len(results) == 1
        assert results[0]["id"] == second_entry

    def test_excludes_exhausted_retries(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        # Exhaust retries
        for _ in range(_FAILURE_MAX_RETRIES + 2):
            record_search_failure(db, sample_entry, fp)

        results = get_retry_entries(db, fp)
        assert len(results) == 0

    def test_excludes_aged_out(self, db, sample_entry) -> None:
        """Entries older than 30 days are excluded (EDGE-018)."""
        fp = compute_token_fingerprint("team lifecycle")
        # Insert a failure with old timestamp
        old_ts = "2025-01-01T00:00:00Z"  # Very old
        db.execute(
            """INSERT INTO echo_search_failures
               (entry_id, token_fingerprint, retry_count, first_failed_at)
               VALUES (?, ?, 0, ?)""",
            (sample_entry, fp, old_ts),
        )
        db.commit()

        results = get_retry_entries(db, fp)
        assert len(results) == 0

    def test_empty_fingerprint(self, db) -> None:
        results = get_retry_entries(db, "")
        assert results == []

    def test_no_matching_fingerprint(self, db) -> None:
        results = get_retry_entries(db, "nonexistent_fingerprint_hash")
        assert results == []


# ---------------------------------------------------------------------------
# cleanup_aged_failures tests
# ---------------------------------------------------------------------------

class TestCleanupAgedFailures:
    def test_removes_old_entries(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        old_ts = "2025-01-01T00:00:00Z"
        db.execute(
            """INSERT INTO echo_search_failures
               (entry_id, token_fingerprint, retry_count, first_failed_at)
               VALUES (?, ?, 0, ?)""",
            (sample_entry, fp, old_ts),
        )
        db.commit()

        deleted = cleanup_aged_failures(db)
        assert deleted == 1

        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 0

    def test_preserves_recent_entries(self, db, sample_entry) -> None:
        fp = compute_token_fingerprint("team lifecycle")
        record_search_failure(db, sample_entry, fp)

        deleted = cleanup_aged_failures(db)
        assert deleted == 0

        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 1

    def test_returns_zero_on_empty_table(self, db) -> None:
        deleted = cleanup_aged_failures(db)
        assert deleted == 0


# ---------------------------------------------------------------------------
# Rebuild index cleanup integration test
# ---------------------------------------------------------------------------

class TestRebuildIndexCleanup:
    def test_reindex_cleans_aged_failures(self, db, sample_entry) -> None:
        """rebuild_index should clean up aged-out failures (EDGE-020)."""
        from server import rebuild_index

        fp = compute_token_fingerprint("team lifecycle")
        old_ts = "2025-01-01T00:00:00Z"
        db.execute(
            """INSERT INTO echo_search_failures
               (entry_id, token_fingerprint, retry_count, first_failed_at)
               VALUES (?, ?, 0, ?)""",
            (sample_entry, fp, old_ts),
        )
        db.commit()

        # Rebuild with the same entry
        entries = [{
            "id": sample_entry,
            "role": "reviewer",
            "layer": "inscribed",
            "date": "2026-01-15",
            "source": "rune:appraise",
            "content": "Test content for retry",
            "tags": "tags",
            "line_number": 5,
            "file_path": "/path/MEMORY.md",
        }]
        rebuild_index(db, entries)

        # Aged failure should be cleaned up
        count = db.execute("SELECT COUNT(*) FROM echo_search_failures").fetchone()[0]
        assert count == 0
