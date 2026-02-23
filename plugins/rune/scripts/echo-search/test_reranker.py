"""Tests for reranker.py — Haiku-powered semantic reranking.

Covers all edge cases from the enriched plan (EDGE-001 through EDGE-024)
using mocked subprocess responses. No actual CLI invocations.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reranker import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_THRESHOLD,
    DEFAULT_TIMEOUT,
    _validate_scores,
    build_rerank_prompt,
    claude_cli_available,
    parse_cli_output,
    rerank_results,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_results() -> List[Dict[str, Any]]:
    """Generate sample BM25 search results for testing."""
    return [
        {
            "id": f"entry-{i:03d}",
            "content_preview": f"Sample content for entry {i} about testing",
            "score": -10.0 + i * 0.3,  # BM25: more negative = better
            "layer": "inscribed",
            "role": "reviewer",
        }
        for i in range(30)
    ]


@pytest.fixture
def small_results() -> List[Dict[str, Any]]:
    """Results below the default reranking threshold."""
    return [
        {
            "id": f"entry-{i:03d}",
            "content_preview": f"Small result {i}",
            "score": -5.0 + i * 0.1,
            "layer": "inscribed",
            "role": "reviewer",
        }
        for i in range(10)
    ]


@pytest.fixture
def enabled_config() -> Dict[str, Any]:
    """Reranking config with feature enabled."""
    return {
        "enabled": True,
        "threshold": 25,
        "max_candidates": 40,
        "timeout": 4,
    }


@pytest.fixture
def mock_haiku_response() -> Dict[str, Any]:
    """A valid claude CLI JSON envelope with rerank scores."""
    scores = [
        {"id": f"entry-{i:03d}", "score": round(1.0 - i * 0.03, 2)}
        for i in range(30)
    ]
    return {
        "type": "result",
        "result": json.dumps(scores),
    }


# ---------------------------------------------------------------------------
# Tests: claude_cli_available
# ---------------------------------------------------------------------------

class TestClaudeCliAvailable:
    """Tests for the CLI availability check (EDGE-001)."""

    def test_cli_found(self) -> None:
        with patch("reranker.shutil.which", return_value="/usr/local/bin/claude"):
            assert claude_cli_available() is True

    def test_cli_not_found(self) -> None:
        with patch("reranker.shutil.which", return_value=None):
            assert claude_cli_available() is False


# ---------------------------------------------------------------------------
# Tests: build_rerank_prompt
# ---------------------------------------------------------------------------

class TestBuildRerankPrompt:
    """Tests for prompt construction."""

    def test_basic_prompt(self) -> None:
        entries = [
            {"id": "abc", "content_preview": "Hello world"},
            {"id": "def", "content_preview": "Goodbye world"},
        ]
        prompt = build_rerank_prompt("test query", entries)
        assert "test query" in prompt
        assert "[abc]: Hello world" in prompt
        assert "[def]: Goodbye world" in prompt

    def test_missing_content_preview_falls_back_to_content(self) -> None:
        entries = [{"id": "abc", "content": "Fallback content"}]
        prompt = build_rerank_prompt("query", entries)
        assert "[abc]: Fallback content" in prompt

    def test_missing_id_uses_unknown(self) -> None:
        entries = [{"content_preview": "No ID entry"}]
        prompt = build_rerank_prompt("query", entries)
        assert "[unknown]: No ID entry" in prompt

    def test_empty_entries(self) -> None:
        prompt = build_rerank_prompt("query", [])
        assert "query" in prompt
        assert "Entries:\n" in prompt


# ---------------------------------------------------------------------------
# Tests: parse_cli_output
# ---------------------------------------------------------------------------

class TestParseCliOutput:
    """Tests for JSON envelope parsing with all EDGE cases."""

    def test_normal_json_envelope(self) -> None:
        """Standard claude --output-format json response."""
        scores = [{"id": "a", "score": 0.9}, {"id": "b", "score": 0.5}]
        envelope = {"type": "result", "result": json.dumps(scores)}
        result = parse_cli_output(json.dumps(envelope))
        assert len(result) == 2
        assert result[0]["id"] == "a"
        assert result[0]["score"] == 0.9

    def test_result_already_dict(self) -> None:
        """EDGE-022: result field is already a dict/list, not a string."""
        scores = [{"id": "a", "score": 0.8}]
        envelope = {"type": "result", "result": scores}
        result = parse_cli_output(json.dumps(envelope))
        assert len(result) == 1
        assert result[0]["score"] == 0.8

    def test_empty_stdout_raises(self) -> None:
        """Empty CLI output should raise ValueError."""
        with pytest.raises(ValueError, match="Empty CLI output"):
            parse_cli_output("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="Empty CLI output"):
            parse_cli_output("   \n  ")

    def test_empty_result_field(self) -> None:
        """EDGE-024: Empty result string."""
        envelope = {"type": "result", "result": ""}
        with pytest.raises(ValueError, match="Empty result"):
            parse_cli_output(json.dumps(envelope))

    def test_none_result_field(self) -> None:
        """EDGE-024: None result."""
        envelope = {"type": "result", "result": None}
        with pytest.raises(ValueError, match="Empty result"):
            parse_cli_output(json.dumps(envelope))

    def test_non_json_with_embedded_array(self) -> None:
        """EDGE-023: Plain text with embedded JSON array."""
        text = 'Some preamble text\n[{"id": "x", "score": 0.7}]\nmore text'
        result = parse_cli_output(text)
        assert len(result) == 1
        assert result[0]["id"] == "x"

    def test_non_json_garbage_raises(self) -> None:
        """Complete garbage text raises ValueError."""
        with pytest.raises(ValueError, match="Cannot extract scores"):
            parse_cli_output("This is just random text with no JSON at all")

    def test_multiline_last_line_json(self) -> None:
        """EDGE-002: Non-JSON lines before valid JSON on last line."""
        scores = [{"id": "a", "score": 0.5}]
        envelope = {"type": "result", "result": json.dumps(scores)}
        # The full text does end with } since the envelope JSON is the last line
        text = "Warning: deprecated flag\nSome other noise\n" + json.dumps(envelope)
        assert text.rstrip().endswith("}")
        result = parse_cli_output(text)
        assert len(result) == 1

    def test_raw_json_array_no_envelope(self) -> None:
        """Direct JSON array output (no envelope wrapper)."""
        scores = [{"id": "a", "score": 0.6}]
        result = parse_cli_output(json.dumps(scores))
        assert len(result) == 1

    def test_nested_result_invalid_json_raises(self) -> None:
        """EDGE-022: result is a string but not valid JSON."""
        envelope = {"type": "result", "result": "not valid json {["}
        with pytest.raises(ValueError, match="Cannot parse nested result"):
            parse_cli_output(json.dumps(envelope))


# ---------------------------------------------------------------------------
# Tests: _validate_scores
# ---------------------------------------------------------------------------

class TestValidateScores:
    """Tests for score validation and normalization."""

    def test_valid_scores(self) -> None:
        data = [{"id": "a", "score": 0.9}, {"id": "b", "score": 0.1}]
        result = _validate_scores(data)
        assert len(result) == 2

    def test_clamps_score_above_one(self) -> None:
        data = [{"id": "a", "score": 1.5}]
        result = _validate_scores(data)
        assert result[0]["score"] == 1.0

    def test_clamps_score_below_zero(self) -> None:
        data = [{"id": "a", "score": -0.5}]
        result = _validate_scores(data)
        assert result[0]["score"] == 0.0

    def test_score_as_string_converted(self) -> None:
        data = [{"id": "a", "score": "0.75"}]
        result = _validate_scores(data)
        assert result[0]["score"] == 0.75

    def test_skips_non_dict_items(self) -> None:
        data = [{"id": "a", "score": 0.9}, "garbage", 42, None]
        result = _validate_scores(data)
        assert len(result) == 1

    def test_skips_missing_id(self) -> None:
        """Single item with missing id: skipped, then raises (no valid entries)."""
        data = [{"score": 0.9}]
        with pytest.raises(ValueError, match="No valid score entries"):
            _validate_scores(data)

    def test_skips_missing_id_with_valid_sibling(self) -> None:
        """Missing-id item skipped but valid sibling survives."""
        data = [{"score": 0.9}, {"id": "b", "score": 0.5}]
        result = _validate_scores(data)
        assert len(result) == 1
        assert result[0]["id"] == "b"

    def test_skips_missing_score(self) -> None:
        """Single item with missing score: skipped, then raises."""
        data = [{"id": "a"}]
        with pytest.raises(ValueError, match="No valid score entries"):
            _validate_scores(data)

    def test_skips_missing_score_with_valid_sibling(self) -> None:
        """Missing-score item skipped but valid sibling survives."""
        data = [{"id": "a"}, {"id": "b", "score": 0.5}]
        result = _validate_scores(data)
        assert len(result) == 1
        assert result[0]["id"] == "b"

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError, match="No valid score entries"):
            _validate_scores([])

    def test_all_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="No valid score entries"):
            _validate_scores([{"bad": "data"}, {"also": "bad"}])

    def test_not_a_list_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected list"):
            _validate_scores({"id": "a", "score": 0.5})

    def test_id_coerced_to_string(self) -> None:
        data = [{"id": 123, "score": 0.5}]
        result = _validate_scores(data)
        assert result[0]["id"] == "123"

    def test_invalid_score_type_skipped(self) -> None:
        """Single item with unconvertible score: skipped, then raises."""
        data = [{"id": "a", "score": "not-a-number"}]
        with pytest.raises(ValueError, match="No valid score entries"):
            _validate_scores(data)

    def test_invalid_score_type_with_valid_sibling(self) -> None:
        """Bad score type skipped but valid sibling survives."""
        data = [{"id": "a", "score": "not-a-number"}, {"id": "b", "score": 0.5}]
        result = _validate_scores(data)
        assert len(result) == 1
        assert result[0]["id"] == "b"


# ---------------------------------------------------------------------------
# Tests: rerank_results (async integration)
# ---------------------------------------------------------------------------

class TestRerankResults:
    """Tests for the main reranking entrypoint."""

    @pytest.mark.asyncio
    async def test_disabled_config_returns_unchanged(
        self, sample_results: List[Dict[str, Any]]
    ) -> None:
        """When reranking is disabled, results pass through unchanged."""
        result = await rerank_results("query", sample_results, {"enabled": False})
        assert result is sample_results

    @pytest.mark.asyncio
    async def test_none_config_returns_unchanged(
        self, sample_results: List[Dict[str, Any]]
    ) -> None:
        """None config defaults to disabled."""
        result = await rerank_results("query", sample_results, None)
        assert result is sample_results

    @pytest.mark.asyncio
    async def test_below_threshold_returns_unchanged(
        self,
        small_results: List[Dict[str, Any]],
        enabled_config: Dict[str, Any],
    ) -> None:
        """Below threshold, skip reranking even if enabled."""
        result = await rerank_results("query", small_results, enabled_config)
        assert result is small_results

    @pytest.mark.asyncio
    async def test_cli_not_available_returns_unchanged(
        self,
        sample_results: List[Dict[str, Any]],
        enabled_config: Dict[str, Any],
    ) -> None:
        """EDGE-001: Missing CLI falls back gracefully."""
        with patch("reranker.claude_cli_available", return_value=False):
            result = await rerank_results("query", sample_results, enabled_config)
            assert result is sample_results

    @pytest.mark.asyncio
    async def test_successful_reranking(
        self,
        sample_results: List[Dict[str, Any]],
        enabled_config: Dict[str, Any],
        mock_haiku_response: Dict[str, Any],
    ) -> None:
        """Happy path: successful reranking with score merging."""
        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch(
                "reranker._invoke_haiku",
                new_callable=AsyncMock,
                return_value=json.dumps(mock_haiku_response),
            ),
        ):
            result = await rerank_results("query", sample_results, enabled_config)
            # Should have rerank_score on each result
            for entry in result:
                assert "rerank_score" in entry
            # First result should have highest rerank_score
            assert result[0]["rerank_score"] >= result[1]["rerank_score"]

    @pytest.mark.asyncio
    async def test_timeout_falls_back(
        self,
        sample_results: List[Dict[str, Any]],
        enabled_config: Dict[str, Any],
    ) -> None:
        """Timeout from CLI should fall back to BM25 results."""
        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch(
                "reranker._invoke_haiku",
                new_callable=AsyncMock,
                side_effect=asyncio.TimeoutError(),
            ),
        ):
            result = await rerank_results("query", sample_results, enabled_config)
            assert result is sample_results

    @pytest.mark.asyncio
    async def test_runtime_error_falls_back(
        self,
        sample_results: List[Dict[str, Any]],
        enabled_config: Dict[str, Any],
    ) -> None:
        """Non-zero exit code from CLI falls back gracefully."""
        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch(
                "reranker._invoke_haiku",
                new_callable=AsyncMock,
                side_effect=RuntimeError("claude CLI exited with code 1"),
            ),
        ):
            result = await rerank_results("query", sample_results, enabled_config)
            assert result is sample_results

    @pytest.mark.asyncio
    async def test_os_error_falls_back(
        self,
        sample_results: List[Dict[str, Any]],
        enabled_config: Dict[str, Any],
    ) -> None:
        """EDGE-001: FileNotFoundError (subclass of OSError) falls back."""
        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch(
                "reranker._invoke_haiku",
                new_callable=AsyncMock,
                side_effect=FileNotFoundError("claude not found"),
            ),
        ):
            result = await rerank_results("query", sample_results, enabled_config)
            assert result is sample_results

    @pytest.mark.asyncio
    async def test_value_error_falls_back(
        self,
        sample_results: List[Dict[str, Any]],
        enabled_config: Dict[str, Any],
    ) -> None:
        """Parse error falls back gracefully."""
        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch(
                "reranker._invoke_haiku",
                new_callable=AsyncMock,
                return_value="not json at all",
            ),
        ):
            result = await rerank_results("query", sample_results, enabled_config)
            assert result is sample_results

    @pytest.mark.asyncio
    async def test_max_candidates_cap(
        self,
        enabled_config: Dict[str, Any],
        mock_haiku_response: Dict[str, Any],
    ) -> None:
        """Only max_candidates entries are sent for reranking."""
        enabled_config["max_candidates"] = 5
        enabled_config["threshold"] = 2  # Lower threshold so it triggers
        big_results = [
            {
                "id": f"entry-{i:03d}",
                "content_preview": f"Content {i}",
                "score": -10.0 + i,
            }
            for i in range(20)
        ]

        captured_prompt = {}

        async def capture_invoke(prompt: str, timeout: float) -> str:
            captured_prompt["text"] = prompt
            # Return scores for first 5 only
            scores = [{"id": f"entry-{i:03d}", "score": 0.9 - i * 0.1} for i in range(5)]
            return json.dumps({"type": "result", "result": json.dumps(scores)})

        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch("reranker._invoke_haiku", side_effect=capture_invoke),
        ):
            result = await rerank_results("query", big_results, enabled_config)
            # Should have all 20 results (5 reranked + 15 appended)
            assert len(result) == 20
            # First 5 should have rerank_score
            for entry in result[:5]:
                assert "rerank_score" in entry
            # Remaining 15 should NOT have rerank_score (appended unchanged)
            for entry in result[5:]:
                assert "rerank_score" not in entry

    @pytest.mark.asyncio
    async def test_reranked_results_sorted_by_score(
        self,
        enabled_config: Dict[str, Any],
    ) -> None:
        """Reranked results should be sorted by rerank_score descending."""
        enabled_config["threshold"] = 2
        results = [
            {"id": "a", "content_preview": "First", "score": -10.0},
            {"id": "b", "content_preview": "Second", "score": -9.0},
            {"id": "c", "content_preview": "Third", "score": -8.0},
        ]

        async def mock_invoke(prompt: str, timeout: float) -> str:
            # Reverse the BM25 order: c is best, then a, then b
            scores = [
                {"id": "c", "score": 0.95},
                {"id": "a", "score": 0.7},
                {"id": "b", "score": 0.3},
            ]
            return json.dumps({"type": "result", "result": json.dumps(scores)})

        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch("reranker._invoke_haiku", side_effect=mock_invoke),
        ):
            result = await rerank_results("query", results, enabled_config)
            assert result[0]["id"] == "c"
            assert result[1]["id"] == "a"
            assert result[2]["id"] == "b"

    @pytest.mark.asyncio
    async def test_missing_scores_default_to_zero(
        self,
        enabled_config: Dict[str, Any],
    ) -> None:
        """Entries not scored by Haiku get rerank_score 0.0."""
        enabled_config["threshold"] = 2
        results = [
            {"id": "a", "content_preview": "Found", "score": -10.0},
            {"id": "b", "content_preview": "Missing", "score": -9.0},
            {"id": "c", "content_preview": "Also found", "score": -8.0},
        ]

        async def mock_invoke(prompt: str, timeout: float) -> str:
            # Only score a and c, skip b
            scores = [
                {"id": "a", "score": 0.8},
                {"id": "c", "score": 0.6},
            ]
            return json.dumps({"type": "result", "result": json.dumps(scores)})

        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch("reranker._invoke_haiku", side_effect=mock_invoke),
        ):
            result = await rerank_results("query", results, enabled_config)
            b_entry = next(r for r in result if r["id"] == "b")
            assert b_entry["rerank_score"] == 0.0

    @pytest.mark.asyncio
    async def test_custom_config_values(self) -> None:
        """Custom threshold and max_candidates are respected."""
        config = {
            "enabled": True,
            "threshold": 5,
            "max_candidates": 10,
            "timeout": 2.0,
        }
        results = [
            {"id": f"e{i}", "content_preview": f"Entry {i}", "score": -5.0 + i}
            for i in range(6)
        ]

        captured_timeout = {}

        async def mock_invoke(prompt: str, timeout: float) -> str:
            captured_timeout["value"] = timeout
            scores = [{"id": f"e{i}", "score": 0.5} for i in range(6)]
            return json.dumps({"type": "result", "result": json.dumps(scores)})

        with (
            patch("reranker.claude_cli_available", return_value=True),
            patch("reranker._invoke_haiku", side_effect=mock_invoke),
        ):
            await rerank_results("query", results, config)
            assert captured_timeout["value"] == 2.0


# ---------------------------------------------------------------------------
# Tests: _invoke_haiku (subprocess behavior)
# ---------------------------------------------------------------------------

class TestInvokeHaiku:
    """Tests for the async subprocess invocation."""

    @pytest.mark.asyncio
    async def test_successful_invocation(self) -> None:
        """Mocked successful subprocess."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(b'{"type":"result","result":"[]"}', b"")
        )
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            from reranker import _invoke_haiku

            result = await _invoke_haiku("test prompt", 4.0)
            assert "result" in result

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self) -> None:
        """EDGE-004: Timeout must kill and wait for the subprocess."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = AsyncMock()
        mock_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            from reranker import _invoke_haiku

            with pytest.raises(asyncio.TimeoutError):
                await _invoke_haiku("test prompt", 4.0)

            # Verify orphan prevention
            mock_proc.kill.assert_called_once()
            mock_proc.wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_nonzero_exit_code_raises(self) -> None:
        """EDGE-006: Non-zero exit code raises RuntimeError."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"Error: auth failed")
        )
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            from reranker import _invoke_haiku

            with pytest.raises(RuntimeError, match="exited with code 1"):
                await _invoke_haiku("test prompt", 4.0)

    @pytest.mark.asyncio
    async def test_empty_stdout_raises(self) -> None:
        """Empty stdout from successful exit raises RuntimeError."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            from reranker import _invoke_haiku

            with pytest.raises(RuntimeError, match="empty stdout"):
                await _invoke_haiku("test prompt", 4.0)

    @pytest.mark.asyncio
    async def test_stderr_logged_on_failure(self) -> None:
        """EDGE-005: stderr is included in error message."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"Permission denied: no API key")
        )
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            from reranker import _invoke_haiku

            with pytest.raises(RuntimeError, match="Permission denied"):
                await _invoke_haiku("test prompt", 4.0)


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Verify default constant values match the plan."""

    def test_default_timeout(self) -> None:
        assert DEFAULT_TIMEOUT == 4.0

    def test_default_threshold(self) -> None:
        assert DEFAULT_THRESHOLD == 25

    def test_default_max_candidates(self) -> None:
        assert DEFAULT_MAX_CANDIDATES == 40
