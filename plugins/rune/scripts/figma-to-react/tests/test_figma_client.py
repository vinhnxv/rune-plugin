"""Tests for figma_client.py — Figma REST API client, cache, and error handling."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from figma_client import (  # noqa: E402
    FigmaAPIError,
    FigmaAuthError,
    FigmaBadRequestError,
    FigmaClient,
    FigmaNotFoundError,
    FigmaRateLimitError,
    ResponseCache,
    _handle_error_response,
)


# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------

class TestResponseCache:
    """Test the two-tier response cache."""

    def test_set_and_get(self):
        """Cache should store and retrieve values."""
        cache = ResponseCache(file_ttl=60, image_ttl=3600)
        cache.set("key1", {"data": "test"})
        assert cache.get("key1") == {"data": "test"}

    def test_get_missing_key(self):
        """Missing key should return None."""
        cache = ResponseCache()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        """Expired entries should return None and be cleaned up."""
        cache = ResponseCache(file_ttl=0, image_ttl=0)
        cache.set("key1", "value1")
        # TTL of 0 means it expires immediately
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_image_ttl_longer(self):
        """Image entries should use the longer image TTL."""
        cache = ResponseCache(file_ttl=0, image_ttl=3600)
        cache.set("img1", "url", is_image=True)
        # File TTL is 0 but image TTL is 3600 — should still be alive
        time.sleep(0.01)
        assert cache.get("img1") == "url"

    def test_invalidate(self):
        """Invalidate should remove a specific key."""
        cache = ResponseCache()
        cache.set("key1", "value1")
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_invalidate_missing_key(self):
        """Invalidating a missing key should not raise."""
        cache = ResponseCache()
        cache.invalidate("nonexistent")  # Should not raise

    def test_clear(self):
        """Clear should remove all entries."""
        cache = ResponseCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite_existing_key(self):
        """Setting the same key again should overwrite."""
        cache = ResponseCache(file_ttl=3600)
        cache.set("key1", "old")
        cache.set("key1", "new")
        assert cache.get("key1") == "new"


# ---------------------------------------------------------------------------
# Error handling (_handle_error_response)
# ---------------------------------------------------------------------------

class TestHandleErrorResponse:
    """Test HTTP response error handling."""

    def _mock_response(self, status_code: int, text: str = "", headers: dict | None = None):
        """Create a mock httpx.Response."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.text = text
        resp.headers = headers or {}
        return resp

    def test_200_no_error(self):
        """2xx responses should not raise."""
        resp = self._mock_response(200)
        _handle_error_response(resp)  # Should not raise

    def test_201_no_error(self):
        """201 Created should not raise."""
        resp = self._mock_response(201)
        _handle_error_response(resp)

    def test_400_bad_request(self):
        """400 should raise FigmaBadRequestError."""
        resp = self._mock_response(400, text="Invalid node ID format")
        with pytest.raises(FigmaBadRequestError) as exc_info:
            _handle_error_response(resp)
        assert exc_info.value.status_code == 400

    def test_403_auth_error(self):
        """403 should raise FigmaAuthError."""
        resp = self._mock_response(403)
        with pytest.raises(FigmaAuthError) as exc_info:
            _handle_error_response(resp)
        assert exc_info.value.status_code == 403
        assert "denied" in str(exc_info.value).lower() or "403" in str(exc_info.value)

    def test_404_not_found(self):
        """404 should raise FigmaNotFoundError."""
        resp = self._mock_response(404)
        with pytest.raises(FigmaNotFoundError) as exc_info:
            _handle_error_response(resp)
        assert exc_info.value.status_code == 404

    def test_429_rate_limit(self):
        """429 should raise FigmaRateLimitError with parsed headers."""
        headers = {
            "Retry-After": "60",
            "X-Figma-Rate-Limit-Type": "low",
            "X-Figma-Plan-Tier": "starter",
        }
        resp = self._mock_response(429, headers=headers)
        with pytest.raises(FigmaRateLimitError) as exc_info:
            _handle_error_response(resp)
        err = exc_info.value
        assert err.status_code == 429
        assert err.retry_after == 60.0
        assert err.rate_limit_type == "low"
        assert err.plan_tier == "starter"

    def test_429_without_headers(self):
        """429 without rate limit headers should still raise with defaults."""
        resp = self._mock_response(429, headers={})
        with pytest.raises(FigmaRateLimitError) as exc_info:
            _handle_error_response(resp)
        err = exc_info.value
        assert err.status_code == 429
        assert err.retry_after is None

    def test_500_server_error(self):
        """500 should raise generic FigmaAPIError."""
        resp = self._mock_response(500, text="Internal Server Error")
        with pytest.raises(FigmaAPIError) as exc_info:
            _handle_error_response(resp)
        assert exc_info.value.status_code == 500

    def test_error_message_truncated(self):
        """Long error text should be truncated to prevent DoS."""
        long_text = "x" * 10000
        resp = self._mock_response(503, text=long_text)
        with pytest.raises(FigmaAPIError) as exc_info:
            _handle_error_response(resp)
        # Message should be reasonable length (500 char cap from impl)
        assert len(str(exc_info.value)) <= 600


# ---------------------------------------------------------------------------
# FigmaClient initialization
# ---------------------------------------------------------------------------

class TestFigmaClientInit:
    """Test FigmaClient initialization and configuration."""

    def test_default_init(self):
        """Client should initialize with default values."""
        client = FigmaClient()
        assert client._timeout == 30.0
        assert client._client is None

    def test_custom_ttl(self):
        """Custom cache TTLs should be stored."""
        client = FigmaClient(file_cache_ttl=100, image_cache_ttl=200)
        assert client._cache.file_ttl == 100
        assert client._cache.image_ttl == 200

    def test_custom_timeout(self):
        """Custom timeout should be stored."""
        client = FigmaClient(timeout=60.0)
        assert client._timeout == 60.0


# ---------------------------------------------------------------------------
# FigmaClient async context manager
# ---------------------------------------------------------------------------

class TestFigmaClientContextManager:
    """Test async context manager lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client should be usable as async context manager."""
        async with FigmaClient() as client:
            assert client is not None

    @pytest.mark.asyncio
    async def test_close_clears_cache(self):
        """Closing client should clear the cache."""
        client = FigmaClient()
        client._cache.set("test", "value")
        await client.close()
        assert client._cache.get("test") is None


# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------

class TestTokenResolution:
    """Test FIGMA_TOKEN environment variable resolution."""

    @pytest.mark.asyncio
    async def test_missing_token_raises(self):
        """Missing FIGMA_TOKEN should raise FigmaAPIError on API call."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove FIGMA_TOKEN if set
            import os
            os.environ.pop("FIGMA_TOKEN", None)
            os.environ.pop("FIGMA_PERSONAL_ACCESS_TOKEN", None)

            client = FigmaClient()
            with pytest.raises(FigmaAPIError, match="FIGMA_TOKEN"):
                await client._ensure_client()
            await client.close()

    @pytest.mark.asyncio
    async def test_token_set_creates_client(self):
        """With FIGMA_TOKEN set, client should be created."""
        with patch.dict("os.environ", {"FIGMA_TOKEN": "figd_test_token"}):
            client = FigmaClient()
            http_client = await client._ensure_client()
            assert http_client is not None
            assert "X-Figma-Token" in http_client.headers
            await client.close()


# ---------------------------------------------------------------------------
# Caching in API methods
# ---------------------------------------------------------------------------

class TestClientCaching:
    """Test that API methods use the response cache correctly."""

    @pytest.mark.asyncio
    async def test_get_file_caches_response(self):
        """get_file should cache the response and return cached data on repeat."""
        with patch.dict("os.environ", {"FIGMA_TOKEN": "figd_test"}):
            client = FigmaClient()
            mock_data = {"name": "TestFile", "document": {}}

            # Mock the _request method
            client._request = AsyncMock(return_value=mock_data)

            result1 = await client.get_file("abc123", depth=2)
            result2 = await client.get_file("abc123", depth=2)

            assert result1 == mock_data
            assert result2 == mock_data
            # Should only call _request once (second call hits cache)
            assert client._request.call_count == 1
            await client.close()

    @pytest.mark.asyncio
    async def test_get_nodes_caches_response(self):
        """get_nodes should cache by file_key + node_ids."""
        with patch.dict("os.environ", {"FIGMA_TOKEN": "figd_test"}):
            client = FigmaClient()
            mock_data = {"nodes": {"1:3": {"document": {}}}}

            client._request = AsyncMock(return_value=mock_data)

            result1 = await client.get_nodes("abc123", ["1:3"])
            result2 = await client.get_nodes("abc123", ["1:3"])

            assert client._request.call_count == 1
            await client.close()

    @pytest.mark.asyncio
    async def test_get_images_uses_image_ttl(self):
        """get_images should cache with is_image=True (longer TTL)."""
        with patch.dict("os.environ", {"FIGMA_TOKEN": "figd_test"}):
            client = FigmaClient(file_cache_ttl=0, image_cache_ttl=3600)
            mock_data = {"images": {"1:3": "https://cdn.figma.com/img/..."}}

            client._request = AsyncMock(return_value=mock_data)

            result1 = await client.get_images("abc123", ["1:3"])
            time.sleep(0.01)
            result2 = await client.get_images("abc123", ["1:3"])

            # Image TTL is 3600, so should still be cached
            assert client._request.call_count == 1
            await client.close()

    @pytest.mark.asyncio
    async def test_different_depth_different_cache(self):
        """Different depth values should use different cache keys."""
        with patch.dict("os.environ", {"FIGMA_TOKEN": "figd_test"}):
            client = FigmaClient()
            mock_data = {"name": "TestFile", "document": {}}

            client._request = AsyncMock(return_value=mock_data)

            await client.get_file("abc123", depth=1)
            await client.get_file("abc123", depth=2)

            # Different depths = different cache keys = 2 requests
            assert client._request.call_count == 2
            await client.close()
