"""Tests for decomposer.py — query decomposition module."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from decomposer import (
    STOPWORDS,
    _TTLCache,
    _count_nonstop_tokens,
    _normalize_query,
    _validate_facets,
    cache_size,
    clear_cache,
    decompose_query,
    merge_results_by_best_score,
    should_decompose,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(entry_id: str, score: float, content: str = "test") -> Dict[str, Any]:
    """Create a minimal search result entry for merge testing."""
    return {"id": entry_id, "score": score, "content": content}


# ---------------------------------------------------------------------------
# _normalize_query tests
# ---------------------------------------------------------------------------

class TestNormalizeQuery:
    def test_lowercases(self) -> None:
        assert _normalize_query("Hello World") == "hello world"

    def test_strips_whitespace(self) -> None:
        assert _normalize_query("  hello  ") == "hello"

    def test_collapses_spaces(self) -> None:
        assert _normalize_query("hello   world   test") == "hello world test"

    def test_empty_string(self) -> None:
        assert _normalize_query("") == ""


# ---------------------------------------------------------------------------
# _count_nonstop_tokens tests
# ---------------------------------------------------------------------------

class TestCountNonstopTokens:
    def test_all_stopwords(self) -> None:
        assert _count_nonstop_tokens("the and or but") == 0

    def test_mixed(self) -> None:
        # "how" (not stopword, 3 chars), "to" (stopword), "debug" (not stopword)
        assert _count_nonstop_tokens("how to debug") == 2

    def test_complex_query(self) -> None:
        # "team" "lifecycle" "cleanup" "sessions" "expire" are non-stop
        result = _count_nonstop_tokens(
            "how to handle team lifecycle cleanup when sessions expire"
        )
        assert result >= 5

    def test_short_tokens_excluded(self) -> None:
        # Single-char tokens are excluded (len < 2)
        assert _count_nonstop_tokens("a b c") == 0

    def test_empty_string(self) -> None:
        assert _count_nonstop_tokens("") == 0


# ---------------------------------------------------------------------------
# should_decompose tests
# ---------------------------------------------------------------------------

class TestShouldDecompose:
    def test_simple_query_bypasses(self) -> None:
        """Queries with <=3 non-stopword tokens bypass decomposition (EDGE-012)."""
        assert not should_decompose("debug error")
        assert not should_decompose("how to debug")  # "how" + "debug" = 2 non-stop
        assert not should_decompose("the and or")  # 0 non-stop

    def test_complex_query_decomposes(self) -> None:
        """Queries with >=4 non-stopword tokens trigger decomposition."""
        assert should_decompose(
            "team lifecycle cleanup guard pattern stale detection"
        )

    def test_boundary_three_nonstop(self) -> None:
        """Exactly 3 non-stopword tokens should NOT decompose."""
        # "debug", "error", "handling" = 3 non-stop tokens
        assert not should_decompose("debug error handling")

    def test_boundary_four_nonstop(self) -> None:
        """Exactly 4 non-stopword tokens SHOULD decompose."""
        # "debug", "error", "handling", "pattern" = 4 non-stop tokens
        assert should_decompose("debug error handling pattern")

    def test_empty_query(self) -> None:
        assert not should_decompose("")


# ---------------------------------------------------------------------------
# _validate_facets tests
# ---------------------------------------------------------------------------

class TestValidateFacets:
    def test_valid_array(self) -> None:
        result = _validate_facets('["team lifecycle", "session cleanup"]')
        assert result == ["team lifecycle", "session cleanup"]

    def test_extracts_from_surrounding_text(self) -> None:
        result = _validate_facets('Here are the facets: ["alpha", "beta"] Done.')
        assert result == ["alpha", "beta"]

    def test_rejects_non_array(self) -> None:
        assert _validate_facets('{"key": "value"}') is None

    def test_rejects_empty_array(self) -> None:
        assert _validate_facets("[]") is None

    def test_rejects_too_many_facets(self) -> None:
        assert _validate_facets('["a","b","c","d","e"]') is None

    def test_rejects_non_string_items(self) -> None:
        assert _validate_facets("[1, 2, 3]") is None

    def test_filters_empty_strings(self) -> None:
        result = _validate_facets('["valid", "", "also valid"]')
        assert result == ["valid", "also valid"]

    def test_filters_overlong_strings(self) -> None:
        long_str = "x" * 101
        result = _validate_facets(f'["short", "{long_str}"]')
        assert result == ["short"]

    def test_rejects_no_json(self) -> None:
        assert _validate_facets("no json here") is None

    def test_rejects_invalid_json(self) -> None:
        assert _validate_facets("[not, valid, json]") is None

    def test_single_facet(self) -> None:
        result = _validate_facets('["single facet"]')
        assert result == ["single facet"]

    def test_four_facets_max(self) -> None:
        result = _validate_facets('["a", "b", "c", "d"]')
        assert result == ["a", "b", "c", "d"]


# ---------------------------------------------------------------------------
# _TTLCache tests
# ---------------------------------------------------------------------------

class TestTTLCache:
    def test_put_and_get(self) -> None:
        cache = _TTLCache(max_size=10, ttl=60.0)
        cache.put("key1", ["facet1", "facet2"])
        assert cache.get("key1") == ["facet1", "facet2"]

    def test_cache_miss(self) -> None:
        cache = _TTLCache(max_size=10, ttl=60.0)
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self) -> None:
        cache = _TTLCache(max_size=10, ttl=0.1)  # 100ms TTL
        cache.put("key1", ["facet1"])
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_lru_eviction(self) -> None:
        cache = _TTLCache(max_size=2, ttl=60.0)
        cache.put("key1", ["a"])
        cache.put("key2", ["b"])
        cache.put("key3", ["c"])  # Evicts key1
        assert cache.get("key1") is None
        assert cache.get("key2") == ["b"]
        assert cache.get("key3") == ["c"]

    def test_access_refreshes_lru(self) -> None:
        cache = _TTLCache(max_size=2, ttl=60.0)
        cache.put("key1", ["a"])
        cache.put("key2", ["b"])
        cache.get("key1")  # Access key1, making key2 the LRU
        cache.put("key3", ["c"])  # Evicts key2
        assert cache.get("key1") == ["a"]
        assert cache.get("key2") is None

    def test_clear(self) -> None:
        cache = _TTLCache(max_size=10, ttl=60.0)
        cache.put("key1", ["a"])
        cache.put("key2", ["b"])
        cache.clear()
        assert len(cache) == 0

    def test_overwrite_existing_key(self) -> None:
        cache = _TTLCache(max_size=10, ttl=60.0)
        cache.put("key1", ["old"])
        cache.put("key1", ["new"])
        assert cache.get("key1") == ["new"]
        assert len(cache) == 1


# ---------------------------------------------------------------------------
# merge_results_by_best_score tests
# ---------------------------------------------------------------------------

class TestMergeResultsByBestScore:
    def test_no_overlap(self) -> None:
        """Entries from different facets with no overlap are all included."""
        facets = [
            [_make_entry("a", -5.0)],
            [_make_entry("b", -3.0)],
        ]
        merged = merge_results_by_best_score(facets)
        assert len(merged) == 2
        ids = [e["id"] for e in merged]
        assert "a" in ids
        assert "b" in ids

    def test_overlap_keeps_best_score(self) -> None:
        """Same entry in two facets keeps most-negative score (EDGE-013)."""
        facets = [
            [_make_entry("a", -3.0)],
            [_make_entry("a", -7.0)],  # Better score (more negative)
        ]
        merged = merge_results_by_best_score(facets)
        assert len(merged) == 1
        assert merged[0]["id"] == "a"
        assert merged[0]["score"] == -7.0  # min() = most negative = best

    def test_overlap_does_not_use_max(self) -> None:
        """Verify merge does NOT use max() which would pick wrong score."""
        facets = [
            [_make_entry("a", -1.0)],  # Worse score
            [_make_entry("a", -10.0)],  # Better score
        ]
        merged = merge_results_by_best_score(facets)
        assert merged[0]["score"] == -10.0  # NOT -1.0

    def test_sorted_by_score_ascending(self) -> None:
        """Results are sorted by score ASC (most negative first = best first)."""
        facets = [
            [_make_entry("a", -2.0), _make_entry("b", -8.0)],
            [_make_entry("c", -5.0)],
        ]
        merged = merge_results_by_best_score(facets)
        scores = [e["score"] for e in merged]
        assert scores == sorted(scores)

    def test_all_empty_facets(self) -> None:
        """All empty facet results return empty list (EDGE-014)."""
        facets = [[], [], []]
        merged = merge_results_by_best_score(facets)
        assert merged == []

    def test_empty_input(self) -> None:
        """No facets at all returns empty list."""
        assert merge_results_by_best_score([]) == []

    def test_entries_without_id_skipped(self) -> None:
        """Entries missing 'id' field are skipped."""
        facets = [
            [{"score": -5.0, "content": "no id"}],
            [_make_entry("a", -3.0)],
        ]
        merged = merge_results_by_best_score(facets)
        assert len(merged) == 1
        assert merged[0]["id"] == "a"

    def test_entries_with_empty_id_skipped(self) -> None:
        """Entries with empty string id are skipped."""
        facets = [[_make_entry("", -5.0)]]
        merged = merge_results_by_best_score(facets)
        assert merged == []

    def test_multiple_overlapping_facets(self) -> None:
        """Entry appearing in 3 facets keeps the best score from any."""
        facets = [
            [_make_entry("a", -2.0)],
            [_make_entry("a", -5.0)],
            [_make_entry("a", -3.0)],
        ]
        merged = merge_results_by_best_score(facets)
        assert len(merged) == 1
        assert merged[0]["score"] == -5.0


# ---------------------------------------------------------------------------
# decompose_query tests (async, with mocked subprocess)
# ---------------------------------------------------------------------------

class TestDecomposeQuery:
    """Tests for the async decompose_query function."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.asyncio
    async def test_simple_query_bypasses(self) -> None:
        """Simple query returns normalized original without subprocess call."""
        result = await decompose_query("debug error")
        # <=3 non-stop tokens, should bypass
        assert len(result) == 1
        assert result[0] == "debug error"

    @pytest.mark.asyncio
    async def test_empty_query(self) -> None:
        result = await decompose_query("")
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_query(self) -> None:
        result = await decompose_query("   ")
        assert result == []  # whitespace-only treated same as empty

    @pytest.mark.asyncio
    async def test_complex_query_with_successful_decomposition(self) -> None:
        """Complex query calls subprocess and returns facets."""
        facets_json = json.dumps(["team lifecycle", "cleanup pattern", "stale detection"])
        envelope = json.dumps({"type": "result", "result": facets_json})

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(envelope.encode(), b"")
        )
        mock_proc.returncode = 0

        with patch("decomposer.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await decompose_query(
                "team lifecycle cleanup guard pattern stale detection"
            )
        assert result == ["team lifecycle", "cleanup pattern", "stale detection"]

    @pytest.mark.asyncio
    async def test_subprocess_timeout_fallback(self) -> None:
        """Timeout falls back to original query (EDGE-004)."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch("decomposer.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await decompose_query(
                "team lifecycle cleanup guard pattern stale detection"
            )
        # Falls back to single normalized query
        assert len(result) == 1
        assert "team" in result[0]
        # Verify kill was called (EDGE-004)
        mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_subprocess_error_fallback(self) -> None:
        """Non-zero exit code falls back to original query."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
        mock_proc.returncode = 1

        with patch("decomposer.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await decompose_query(
                "team lifecycle cleanup guard pattern stale detection"
            )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_subprocess_oserror_fallback(self) -> None:
        """OSError (e.g., claude not found) falls back to original query."""
        with patch(
            "decomposer.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("claude not found"),
        ):
            result = await decompose_query(
                "team lifecycle cleanup guard pattern stale detection"
            )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Second call for same query uses cache, not subprocess."""
        facets_json = json.dumps(["alpha", "beta"])
        envelope = json.dumps({"type": "result", "result": facets_json})

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(envelope.encode(), b"")
        )
        mock_proc.returncode = 0

        with patch("decomposer.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            query = "team lifecycle cleanup guard pattern stale detection"
            result1 = await decompose_query(query)
            result2 = await decompose_query(query)

        assert result1 == ["alpha", "beta"]
        assert result2 == ["alpha", "beta"]
        # Subprocess called only once (second was cache hit)
        assert mock_exec.call_count == 1
        assert cache_size() == 1

    @pytest.mark.asyncio
    async def test_invalid_facets_fallback(self) -> None:
        """Invalid subprocess output falls back to original query."""
        envelope = json.dumps({"type": "result", "result": "not valid json array"})

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(envelope.encode(), b"")
        )
        mock_proc.returncode = 0

        with patch("decomposer.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await decompose_query(
                "team lifecycle cleanup guard pattern stale detection"
            )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_all_empty_facets_returns_original(self) -> None:
        """When decomposition returns empty facets, falls back (EDGE-014)."""
        # _validate_facets rejects empty array, so subprocess returns None -> fallback
        envelope = json.dumps({"type": "result", "result": "[]"})

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(envelope.encode(), b"")
        )
        mock_proc.returncode = 0

        with patch("decomposer.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await decompose_query(
                "team lifecycle cleanup guard pattern stale detection"
            )
        assert len(result) == 1  # Falls back to original


# ---------------------------------------------------------------------------
# clear_cache / cache_size tests
# ---------------------------------------------------------------------------

class TestCacheHelpers:
    def test_clear_cache(self) -> None:
        _cache = _TTLCache()
        _cache.put("test", ["a"])
        _cache.clear()
        assert len(_cache) == 0

    def test_cache_size(self) -> None:
        clear_cache()
        assert cache_size() == 0
