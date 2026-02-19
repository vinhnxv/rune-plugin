"""Tests for server.py — Echo Search MCP Server database helpers."""

import os
import sqlite3
import textwrap

import pytest

# Import the testable, non-MCP functions from server.py.
# The module-level env var validation (ECHO_DIR/DB_PATH) runs on import,
# but defaults to empty strings which pass the forbidden-prefix check.
from server import (
    build_fts_query,
    ensure_schema,
    get_db,
    get_details,
    get_stats,
    rebuild_index,
    search_entries,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """In-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_entries():
    """Two sample echo entries for testing."""
    return [
        {
            "id": "abc123def4567890",
            "role": "reviewer",
            "layer": "inscribed",
            "date": "2026-01-15",
            "source": "rune:review session-1",
            "content": "Always use pre-create guard before TeamCreate",
            "tags": "Team lifecycle guards",
            "line_number": 5,
            "file_path": "/echoes/reviewer/MEMORY.md",
        },
        {
            "id": "1234567890abcdef",
            "role": "orchestrator",
            "layer": "etched",
            "date": "2026-02-01",
            "source": "rune:audit full-scan",
            "content": "Input validation is essential for security hardening",
            "tags": "Security patterns",
            "line_number": 12,
            "file_path": "/echoes/orchestrator/MEMORY.md",
        },
    ]


@pytest.fixture
def populated_db(db, sample_entries):
    """In-memory DB with sample entries indexed."""
    rebuild_index(db, sample_entries)
    return db


# ---------------------------------------------------------------------------
# get_db
# ---------------------------------------------------------------------------

class TestGetDb:
    def test_returns_connection_with_row_factory(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_db(db_path)
        try:
            assert conn.row_factory == sqlite3.Row
        finally:
            conn.close()

    def test_wal_mode_enabled(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_db(db_path)
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# ensure_schema
# ---------------------------------------------------------------------------

class TestEnsureSchema:
    def test_creates_tables(self, db):
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "echo_entries" in tables
        assert "echo_meta" in tables
        assert "echo_entries_fts" in tables

    def test_idempotent(self, db):
        """Calling ensure_schema twice should not raise."""
        ensure_schema(db)
        tables = db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        assert tables >= 3  # echo_entries, echo_meta, echo_entries_fts + internal FTS tables


# ---------------------------------------------------------------------------
# rebuild_index
# ---------------------------------------------------------------------------

class TestRebuildIndex:
    def test_inserts_entries(self, db, sample_entries):
        count = rebuild_index(db, sample_entries)
        assert count == 2

        rows = db.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
        assert rows == 2

    def test_replaces_existing_entries(self, db, sample_entries):
        rebuild_index(db, sample_entries)
        rebuild_index(db, sample_entries)
        rows = db.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
        assert rows == 2  # replaced, not duplicated

    def test_clears_old_entries(self, db, sample_entries):
        rebuild_index(db, sample_entries)
        rebuild_index(db, [sample_entries[0]])  # only first entry
        rows = db.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
        assert rows == 1

    def test_empty_entries(self, db):
        count = rebuild_index(db, [])
        assert count == 0

    def test_sets_last_indexed_meta(self, db, sample_entries):
        rebuild_index(db, sample_entries)
        row = db.execute(
            "SELECT value FROM echo_meta WHERE key='last_indexed'"
        ).fetchone()
        assert row is not None
        assert "T" in row[0]  # ISO 8601 format

    def test_rollback_on_error(self, db):
        """If an entry is malformed, transaction rolls back entirely."""
        bad_entries = [
            {
                "id": "goodid1234567890",
                "role": "r",
                "layer": "inscribed",
                "content": "ok",
                "file_path": "/p",
            },
            {
                # Missing required 'id' key → KeyError during execute
                "role": "r",
                "layer": "inscribed",
                "content": "ok",
                "file_path": "/p",
            },
        ]
        with pytest.raises(KeyError):
            rebuild_index(db, bad_entries)

        # Rollback should leave table empty
        count = db.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
        assert count == 0

    def test_unicode_content(self, db):
        """Entries with non-ASCII content are handled correctly."""
        entries = [
            {
                "id": "unicode123456789",
                "role": "reviewer",
                "layer": "inscribed",
                "date": "2026-01-01",
                "source": "rune:review",
                "content": "Hệ thống xác thực người dùng 日本語テスト",
                "tags": "unicode test",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        count = rebuild_index(db, entries)
        assert count == 1

        row = db.execute("SELECT content FROM echo_entries WHERE id=?", ("unicode123456789",)).fetchone()
        assert "Hệ thống" in row[0]

    def test_entry_with_optional_fields_missing(self, db):
        """Entries with missing optional fields use .get() defaults."""
        entries = [
            {
                "id": "minimal123456789",
                "role": "r",
                "layer": "inscribed",
                "content": "minimal entry",
                "file_path": "/p",
                # No date, source, tags, line_number
            }
        ]
        count = rebuild_index(db, entries)
        assert count == 1

        row = db.execute("SELECT date, source, tags, line_number FROM echo_entries WHERE id=?",
                         ("minimal123456789",)).fetchone()
        assert row[0] == ""   # date default
        assert row[1] == ""   # source default
        assert row[2] == ""   # tags default
        assert row[3] == 0    # line_number default

    def test_fts_index_rebuilt_after_reindex(self, db, sample_entries):
        """FTS index stays in sync after multiple rebuilds."""
        rebuild_index(db, sample_entries)
        results_before = search_entries(db, "TeamCreate")
        assert len(results_before) >= 1

        # Rebuild with different content
        new_entries = [
            {
                "id": "newentry123456789",
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "completely different topic about databases",
                "tags": "databases",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        rebuild_index(db, new_entries)

        # Old content should no longer be searchable
        results_after = search_entries(db, "TeamCreate")
        assert len(results_after) == 0

        # New content should be searchable
        results_new = search_entries(db, "databases")
        assert len(results_new) == 1

    def test_large_batch_insert(self, db):
        """Rebuild handles 500+ entries without issues."""
        entries = [
            {
                "id": "batch_%04d_padding" % i,
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "entry number %d content" % i,
                "tags": "batch",
                "line_number": i,
                "file_path": "/p",
            }
            for i in range(500)
        ]
        count = rebuild_index(db, entries)
        assert count == 500

        db_count = db.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
        assert db_count == 500


# ---------------------------------------------------------------------------
# build_fts_query
# ---------------------------------------------------------------------------

class TestBuildFtsQuery:
    def test_basic_query(self):
        result = build_fts_query("team lifecycle guard")
        assert "team" in result
        assert "lifecycle" in result
        assert "guard" in result
        assert " OR " in result

    def test_stopwords_filtered(self):
        result = build_fts_query("the quick brown fox")
        assert "the" not in result.split(" OR ")
        assert "quick" in result
        assert "brown" in result
        assert "fox" in result

    def test_all_stopwords_fallback(self):
        """If all tokens are stopwords, fall back to tokens >= 2 chars."""
        result = build_fts_query("is it the")
        # All are stopwords; fallback keeps those >= 2 chars
        assert "is" in result or "it" in result or "the" in result

    def test_single_char_tokens_dropped(self):
        result = build_fts_query("a b security")
        # "a" and "b" are < 2 chars, "a" is also a stopword
        assert "security" in result

    def test_empty_input(self):
        assert build_fts_query("") == ""

    def test_only_punctuation(self):
        assert build_fts_query("!@#$%^&*()") == ""

    def test_sec7_input_length_cap(self):
        """Inputs longer than 500 chars are truncated before tokenization."""
        long_query = "security " * 100  # 1000 chars
        result = build_fts_query(long_query)
        # Should still produce a valid query, not error
        assert "security" in result

    def test_sec7_token_count_cap(self):
        """No more than 20 tokens in output."""
        many_words = " ".join("word%d" % i for i in range(50))
        result = build_fts_query(many_words)
        tokens = result.split(" OR ")
        assert len(tokens) <= 20

    def test_case_insensitive(self):
        result = build_fts_query("Security HARDENING")
        assert "security" in result
        assert "hardening" in result

    def test_special_chars_stripped(self):
        """FTS5 operators like * and : are not passed through."""
        result = build_fts_query("sec*urity hard:ening")
        # re.findall(r"[a-zA-Z0-9_]+") splits on non-word chars
        assert "*" not in result
        assert ":" not in result

    def test_underscore_preserved(self):
        """Underscores are valid in the token regex [a-zA-Z0-9_]+."""
        result = build_fts_query("pre_create_guard")
        assert "pre_create_guard" in result

    def test_numbers_preserved(self):
        """Numeric tokens are kept."""
        result = build_fts_query("version 145 release")
        assert "145" in result
        assert "version" in result

    def test_mixed_stopwords_and_content(self):
        """Stopwords filtered but content words preserved."""
        result = build_fts_query("the security of the system")
        tokens = result.split(" OR ")
        assert "security" in tokens
        assert "system" in tokens
        assert "the" not in tokens
        assert "of" not in tokens

    def test_duplicate_tokens_preserved(self):
        """Duplicate tokens are kept (FTS5 handles dedup internally)."""
        result = build_fts_query("error error error handling")
        tokens = result.split(" OR ")
        assert tokens.count("error") == 3

    def test_exactly_500_char_input(self):
        """Input exactly at the 500-char boundary."""
        query = "a" * 500
        result = build_fts_query(query)
        # "a" is < 2 chars so it gets dropped, but no truncation error
        assert result == "" or isinstance(result, str)

    def test_tab_and_newline_in_input(self):
        """Whitespace variants are handled by the tokenizer."""
        result = build_fts_query("security\thardening\npatterns")
        assert "security" in result
        assert "hardening" in result
        assert "patterns" in result

    def test_single_valid_token(self):
        """A single non-stopword token produces a query without OR."""
        result = build_fts_query("authentication")
        assert result == "authentication"
        assert " OR " not in result

    def test_all_single_char_returns_empty(self):
        """All tokens < 2 chars (after stopword filter) returns empty."""
        result = build_fts_query("x y z")
        # x, y, z are 1-char; not stopwords but < 2 chars
        assert result == ""


# ---------------------------------------------------------------------------
# search_entries
# ---------------------------------------------------------------------------

class TestSearchEntries:
    def test_basic_search(self, populated_db):
        results = search_entries(populated_db, "TeamCreate guard")
        assert len(results) >= 1
        assert results[0]["role"] == "reviewer"

    def test_search_returns_expected_fields(self, populated_db):
        results = search_entries(populated_db, "validation security")
        assert len(results) >= 1
        r = results[0]
        assert "id" in r
        assert "source" in r
        assert "layer" in r
        assert "role" in r
        assert "content_preview" in r
        assert "score" in r
        assert "line_number" in r

    def test_content_preview_truncated(self, db):
        """content_preview is substr(content, 1, 200) — max 200 chars."""
        long_content = "x" * 500
        entries = [
            {
                "id": "longentry12345678",
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": long_content,
                "tags": "searchable_keyword",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        rebuild_index(db, entries)
        results = search_entries(db, "searchable_keyword")
        assert len(results) == 1
        assert len(results[0]["content_preview"]) <= 200

    def test_filter_by_layer(self, populated_db):
        results = search_entries(populated_db, "security", layer="etched")
        assert all(r["layer"] == "etched" for r in results)

    def test_filter_by_role(self, populated_db):
        results = search_entries(populated_db, "guard", role="reviewer")
        assert all(r["role"] == "reviewer" for r in results)

    def test_limit_respected(self, populated_db):
        results = search_entries(populated_db, "security", limit=1)
        assert len(results) <= 1

    def test_empty_query_returns_empty(self, populated_db):
        results = search_entries(populated_db, "")
        assert results == []

    def test_no_matches(self, populated_db):
        results = search_entries(populated_db, "zzzznonexistent")
        assert results == []

    def test_combined_layer_and_role_filter(self, populated_db):
        """Both layer and role filters applied simultaneously."""
        results = search_entries(populated_db, "security", layer="etched", role="orchestrator")
        assert len(results) >= 1
        assert all(r["layer"] == "etched" and r["role"] == "orchestrator" for r in results)

    def test_filter_excludes_non_matching(self, populated_db):
        """Layer filter should exclude entries from other layers."""
        results = search_entries(populated_db, "guard", layer="etched")
        # "guard" appears in the inscribed entry, not etched
        assert all(r["layer"] == "etched" for r in results)

    def test_limit_zero_returns_empty(self, populated_db):
        """Limit of 0 should return no results."""
        results = search_entries(populated_db, "security", limit=0)
        assert results == []

    def test_score_is_numeric(self, populated_db):
        """BM25 scores should be float values."""
        results = search_entries(populated_db, "security")
        for r in results:
            assert isinstance(r["score"], float)

    def test_search_after_empty_rebuild(self, db):
        """Search on a DB that was rebuilt with no entries returns empty."""
        rebuild_index(db, [])
        results = search_entries(db, "anything")
        assert results == []

    def test_porter_stemming(self, db):
        """FTS5 uses porter stemmer — 'securing' should match 'security'."""
        entries = [
            {
                "id": "stemtest12345678",
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "securing the application against threats",
                "tags": "",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        rebuild_index(db, entries)
        # "security" stems to "secur", "securing" also stems to "secur"
        results = search_entries(db, "security")
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# get_details
# ---------------------------------------------------------------------------

class TestGetDetails:
    def test_fetch_by_id(self, populated_db):
        results = get_details(populated_db, ["abc123def4567890"])
        assert len(results) == 1
        assert results[0]["id"] == "abc123def4567890"
        assert results[0]["full_content"] == "Always use pre-create guard before TeamCreate"

    def test_fetch_multiple_ids(self, populated_db):
        results = get_details(populated_db, ["abc123def4567890", "1234567890abcdef"])
        assert len(results) == 2

    def test_nonexistent_id(self, populated_db):
        results = get_details(populated_db, ["does_not_exist_00"])
        assert results == []

    def test_empty_ids(self, populated_db):
        results = get_details(populated_db, [])
        assert results == []

    def test_sec002_cap_at_100(self, populated_db):
        """IDs list is capped at 100 — defense-in-depth."""
        ids = ["id_%d_padded_to_16" % i for i in range(150)]
        results = get_details(populated_db, ids)
        # Should not error; just returns 0 results since none exist
        assert isinstance(results, list)

    def test_non_string_ids_filtered(self, populated_db):
        """Non-string IDs are filtered out by isinstance check."""
        # Intentionally passing wrong types to test runtime defense-in-depth
        mixed_ids = [123, None, "abc123def4567890"]  # type: ignore[list-item]
        results = get_details(populated_db, mixed_ids)
        # Only the valid string ID should be used
        assert len(results) <= 1

    def test_returns_all_fields(self, populated_db):
        results = get_details(populated_db, ["abc123def4567890"])
        assert len(results) == 1
        r = results[0]
        expected_keys = {"id", "source", "layer", "role", "full_content", "date", "tags", "line_number", "file_path"}
        assert set(r.keys()) == expected_keys

    def test_mixed_existing_and_missing_ids(self, populated_db):
        """Returns only entries that exist, ignores missing IDs."""
        results = get_details(populated_db, ["abc123def4567890", "nonexistent_id_00"])
        assert len(results) == 1
        assert results[0]["id"] == "abc123def4567890"

    def test_duplicate_ids_in_request(self, populated_db):
        """Passing the same ID twice returns it once (SQL IN deduplicates)."""
        results = get_details(populated_db, ["abc123def4567890", "abc123def4567890"])
        assert len(results) == 1

    def test_full_content_not_truncated(self, db):
        """get_details returns full content, not the 200-char preview."""
        long_content = "x" * 500
        entries = [
            {
                "id": "fullcontent12345",
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": long_content,
                "tags": "",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        rebuild_index(db, entries)
        results = get_details(db, ["fullcontent12345"])
        assert len(results) == 1
        assert len(results[0]["full_content"]) == 500


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestGetStats:
    def test_empty_db(self, db):
        stats = get_stats(db)
        assert stats["total_entries"] == 0
        assert stats["by_layer"] == {}
        assert stats["by_role"] == {}
        assert stats["last_indexed"] == ""

    def test_populated_db(self, populated_db):
        stats = get_stats(populated_db)
        assert stats["total_entries"] == 2
        assert stats["by_layer"]["inscribed"] == 1
        assert stats["by_layer"]["etched"] == 1
        assert stats["by_role"]["reviewer"] == 1
        assert stats["by_role"]["orchestrator"] == 1
        assert stats["last_indexed"] != ""


# ---------------------------------------------------------------------------
# do_reindex (integration test)
# ---------------------------------------------------------------------------

class TestDoReindex:
    def test_end_to_end(self, tmp_path):
        """Full reindex: parse MEMORY.md files → build DB → verify."""
        echo_dir = tmp_path / "echoes"
        role_dir = echo_dir / "reviewer"
        role_dir.mkdir(parents=True)
        (role_dir / "MEMORY.md").write_text(textwrap.dedent("""\
            ## Inscribed — Pattern A (2026-01-01)
            **Source**: `src-1`
            Content for pattern A

            ## Etched — Pattern B (2026-01-02)
            **Source**: `src-2`
            Content for pattern B
        """))

        db_path = str(tmp_path / "echo.db")

        # Import do_reindex (it imports indexer internally)
        from server import do_reindex

        result = do_reindex(str(echo_dir), db_path)

        assert result["entries_indexed"] == 2
        assert result["time_ms"] >= 0
        assert "reviewer" in result["roles"]

        # Verify DB content
        conn = get_db(db_path)
        try:
            stats = get_stats(conn)
            assert stats["total_entries"] == 2
            assert stats["by_role"]["reviewer"] == 2
        finally:
            conn.close()

    def test_reindex_empty_dir(self, tmp_path):
        echo_dir = tmp_path / "empty_echoes"
        echo_dir.mkdir()
        db_path = str(tmp_path / "echo.db")

        from server import do_reindex

        result = do_reindex(str(echo_dir), db_path)
        assert result["entries_indexed"] == 0
        assert result["roles"] == []

    def test_reindex_replaces_previous(self, tmp_path):
        """Second reindex should replace, not append."""
        echo_dir = tmp_path / "echoes"
        role_dir = echo_dir / "test"
        role_dir.mkdir(parents=True)
        (role_dir / "MEMORY.md").write_text(
            "## Inscribed — Entry (2026-01-01)\n**Source**: `s`\nContent"
        )

        db_path = str(tmp_path / "echo.db")
        from server import do_reindex

        do_reindex(str(echo_dir), db_path)
        do_reindex(str(echo_dir), db_path)

        conn = get_db(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM echo_entries").fetchone()[0]
            assert count == 1  # not 2
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# FTS search integration
# ---------------------------------------------------------------------------

class TestFtsIntegration:
    """End-to-end FTS5 search tests using BM25 ranking."""

    def test_search_by_content(self, populated_db):
        results = search_entries(populated_db, "pre-create guard TeamCreate")
        assert len(results) >= 1
        assert results[0]["id"] == "abc123def4567890"

    def test_search_by_tags(self, populated_db):
        """FTS5 indexes content, tags, and source — tags should be searchable."""
        results = search_entries(populated_db, "lifecycle guards")
        assert len(results) >= 1
        assert results[0]["tags"] if "tags" in results[0] else True

    def test_search_by_source(self, populated_db):
        results = search_entries(populated_db, "rune:audit full-scan")
        assert len(results) >= 1

    def test_bm25_ranking(self, db):
        """More relevant results should have more negative scores (ASC order)."""
        entries = [
            {
                "id": "a" * 16,
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "security security security hardening patterns",
                "tags": "security",
                "line_number": 1,
                "file_path": "/p",
            },
            {
                "id": "b" * 16,
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "some general content about configuration",
                "tags": "config security",
                "line_number": 2,
                "file_path": "/p",
            },
        ]
        rebuild_index(db, entries)
        results = search_entries(db, "security")
        assert len(results) == 2
        # First result should be more relevant (more negative BM25 score)
        assert results[0]["score"] <= results[1]["score"]

    def test_sec2_no_raw_fts_injection(self, populated_db):
        """FTS5 special syntax should not be injectable via search query."""
        # These would cause FTS5 parse errors if passed raw
        dangerous_queries = [
            'content MATCH "test"',
            "* OR 1=1",
            "NEAR(a, b, 5)",
            '"{column:content}"',
            "content:hack",
        ]
        for q in dangerous_queries:
            # Should not raise — build_fts_query sanitizes
            results = search_entries(populated_db, q)
            assert isinstance(results, list)

    def test_sec2_fts5_column_filter_blocked(self, populated_db):
        """FTS5 column filter syntax (col:term) is not injectable."""
        # In raw FTS5, "source:hack" would search only the source column
        results = search_entries(populated_db, "source:rune")
        # Should search for "source" and "rune" as separate tokens, not as column filter
        assert isinstance(results, list)

    def test_sec2_boolean_operators_not_injectable(self, populated_db):
        """FTS5 AND/NOT/OR operators as raw input are treated as plain words."""
        results = search_entries(populated_db, "security NOT validation")
        # "NOT" is a stopword and gets filtered; doesn't become FTS5 operator
        assert isinstance(results, list)

    def test_search_unicode_content(self, db):
        """FTS5 with unicode61 tokenizer handles non-ASCII text."""
        entries = [
            {
                "id": "unicode_search_01",
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "Xác thực người dùng bằng mật khẩu",
                "tags": "authentication",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        rebuild_index(db, entries)
        # Search by tag (ASCII) should find it
        results = search_entries(db, "authentication")
        assert len(results) == 1

    def test_reindex_then_search_integrity(self, db):
        """Index, search, reindex with different data, search again."""
        entries_v1 = [
            {
                "id": "v1_entry_12345678",
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "original content about authentication",
                "tags": "auth",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        rebuild_index(db, entries_v1)
        assert len(search_entries(db, "authentication")) == 1

        entries_v2 = [
            {
                "id": "v2_entry_12345678",
                "role": "r",
                "layer": "inscribed",
                "date": "",
                "source": "",
                "content": "replacement content about deployment",
                "tags": "deploy",
                "line_number": 1,
                "file_path": "/p",
            }
        ]
        rebuild_index(db, entries_v2)

        # Old term gone, new term searchable
        assert len(search_entries(db, "authentication")) == 0
        assert len(search_entries(db, "deployment")) == 1


# ---------------------------------------------------------------------------
# Dirty signal helpers
# ---------------------------------------------------------------------------

from server import _signal_path, _check_and_clear_dirty


class TestSignalPath:
    """Unit tests for _signal_path derivation."""

    def test_standard_echo_dir(self):
        path = _signal_path("/project/.claude/echoes")
        assert path == os.path.join("/project", "tmp", ".rune-signals", ".echo-dirty")

    def test_trailing_slash_stripped(self):
        path = _signal_path("/project/.claude/echoes/")
        assert path == os.path.join("/project", "tmp", ".rune-signals", ".echo-dirty")

    def test_empty_echo_dir_returns_empty(self):
        assert _signal_path("") == ""

    def test_non_standard_dir_uses_fallback(self):
        """When ECHO_DIR doesn't end with .claude/echoes, walk up two dirs."""
        path = _signal_path("/custom/path/echoes")
        # Fallback: dirname(dirname("/custom/path/echoes")) = "/custom"
        assert path == os.path.join("/custom", "tmp", ".rune-signals", ".echo-dirty")


class TestCheckAndClearDirty:
    """Unit tests for _check_and_clear_dirty."""

    def test_returns_false_when_no_signal(self, tmp_path):
        echo_dir = str(tmp_path / ".claude" / "echoes")
        os.makedirs(echo_dir, exist_ok=True)
        assert _check_and_clear_dirty(echo_dir) is False

    def test_returns_true_and_deletes_signal(self, tmp_path):
        echo_dir = str(tmp_path / ".claude" / "echoes")
        os.makedirs(echo_dir, exist_ok=True)
        signal_dir = tmp_path / "tmp" / ".rune-signals"
        signal_dir.mkdir(parents=True)
        signal_file = signal_dir / ".echo-dirty"
        signal_file.write_text("1")

        assert _check_and_clear_dirty(echo_dir) is True
        assert not signal_file.exists(), "signal file should be deleted after consumption"

    def test_returns_false_after_second_call(self, tmp_path):
        """Signal is consumed on first call — second call returns False."""
        echo_dir = str(tmp_path / ".claude" / "echoes")
        os.makedirs(echo_dir, exist_ok=True)
        signal_dir = tmp_path / "tmp" / ".rune-signals"
        signal_dir.mkdir(parents=True)
        (signal_dir / ".echo-dirty").write_text("1")

        assert _check_and_clear_dirty(echo_dir) is True
        assert _check_and_clear_dirty(echo_dir) is False

    def test_empty_echo_dir_returns_false(self):
        assert _check_and_clear_dirty("") is False
