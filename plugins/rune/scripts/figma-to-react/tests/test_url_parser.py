"""Tests for url_parser.py — Figma URL parsing and validation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add parent directory to path so we can import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from url_parser import FigmaURLError, parse_figma_url  # noqa: E402


# ---------------------------------------------------------------------------
# Standard URL formats (7 types)
# ---------------------------------------------------------------------------

class TestStandardUrls:
    """Test parsing of all 7 supported Figma URL formats."""

    def test_design_url(self):
        """Parse /design/ URL (current canonical format)."""
        result = parse_figma_url(
            "https://www.figma.com/design/ABC123XYZabcdef789012/MyFile?node-id=1-3"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["type"] == "design"
        assert result["node_id"] == "1:3"

    def test_file_url(self):
        """Parse legacy /file/ URL."""
        result = parse_figma_url(
            "https://www.figma.com/file/ABC123XYZabcdef789012/MyFile"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["type"] == "file"

    def test_dev_url(self):
        """Parse /dev/ URL (Dev Mode)."""
        result = parse_figma_url(
            "https://figma.com/dev/ABC123XYZabcdef789012/MyFile?node-id=5-10"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["type"] == "dev"
        assert result["node_id"] == "5:10"

    def test_proto_url(self):
        """Parse /proto/ URL (Prototype)."""
        result = parse_figma_url(
            "https://www.figma.com/proto/ABC123XYZabcdef789012/MyProto"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["type"] == "proto"

    def test_board_url(self):
        """Parse /board/ URL (FigJam)."""
        result = parse_figma_url(
            "https://www.figma.com/board/ABC123XYZabcdef789012/MyBoard"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["type"] == "board"

    def test_slides_url(self):
        """Parse /slides/ URL."""
        result = parse_figma_url(
            "https://www.figma.com/slides/ABC123XYZabcdef789012/MySlides"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["type"] == "slides"

    def test_make_url(self):
        """Parse /make/ URL."""
        result = parse_figma_url(
            "https://www.figma.com/make/ABC123XYZabcdef789012/MyMake"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["type"] == "make"


# ---------------------------------------------------------------------------
# Branch URLs
# ---------------------------------------------------------------------------

class TestBranchUrls:
    """Test parsing of branch URLs."""

    def test_branch_url(self):
        """Parse URL with branch key."""
        result = parse_figma_url(
            "https://www.figma.com/design/ABC123XYZabcdef789012/branch/BR456def/MyFile?node-id=2-5"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["branch_key"] == "BR456def"
        assert result["node_id"] == "2:5"

    def test_branch_without_node_id(self):
        """Parse branch URL without node-id parameter."""
        result = parse_figma_url(
            "https://www.figma.com/design/ABC123XYZabcdef789012/branch/BR456/MyFile"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"
        assert result["branch_key"] == "BR456"
        assert result.get("node_id") is None or result.get("node_id") == ""


# ---------------------------------------------------------------------------
# Node ID conversion (hyphen to colon)
# ---------------------------------------------------------------------------

class TestNodeIdConversion:
    """Test hyphen-to-colon conversion for node IDs."""

    def test_hyphen_to_colon(self):
        """Node IDs in URLs use hyphens; API uses colons."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/File?node-id=1-3"
        )
        assert result["node_id"] == "1:3"

    def test_url_encoded_colon(self):
        """Handle %3A URL encoding for colons."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/File?node-id=1%3A3"
        )
        # After URL decoding, 1:3 should remain 1:3 (colon already present)
        assert result["node_id"] == "1:3"

    def test_complex_node_id(self):
        """Handle multi-level node IDs like 100-200."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/File?node-id=100-200"
        )
        assert result["node_id"] == "100:200"

    def test_no_node_id(self):
        """URL without node-id should have None or empty node_id."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/MyFile"
        )
        assert result.get("node_id") is None or result.get("node_id") == ""

    def test_multiple_query_params(self):
        """Extract node-id from URL with multiple query parameters."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/File?t=abc&node-id=3-7&mode=dev"
        )
        assert result["node_id"] == "3:7"


# ---------------------------------------------------------------------------
# Invalid URLs
# ---------------------------------------------------------------------------

class TestInvalidUrls:
    """Test rejection of invalid Figma URLs."""

    def test_empty_string(self):
        """Empty string should raise ValueError."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("")

    def test_non_figma_domain(self):
        """Non-Figma URLs should be rejected."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("https://example.com/design/ABC123/File")

    def test_random_string(self):
        """Random non-URL string should be rejected."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("not-a-url-at-all")

    def test_missing_file_key(self):
        """URL without file key should be rejected."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("https://figma.com/design/")

    def test_unsupported_path(self):
        """URL with unsupported path segment should be rejected."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("https://figma.com/unknown/ABC123/File")


# ---------------------------------------------------------------------------
# SSRF Prevention
# ---------------------------------------------------------------------------

class TestSsrfPrevention:
    """Test that non-Figma hostnames are blocked."""

    def test_localhost_blocked(self):
        """Localhost URLs must be blocked."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("https://localhost/design/ABC123XYZabcdef789012/File")

    def test_ip_address_blocked(self):
        """IP address URLs must be blocked."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("https://127.0.0.1/design/ABC123XYZabcdef789012/File")

    def test_internal_domain_blocked(self):
        """Internal/private domain URLs must be blocked."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("https://internal.corp/design/ABC123XYZabcdef789012/File")

    def test_figma_subdomain_spoofing_blocked(self):
        """Subdomains that aren't www.figma.com or figma.com should be blocked."""
        with pytest.raises(FigmaURLError):
            parse_figma_url("https://evil.figma.com.attacker.com/design/ABC123/File")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and unusual but valid inputs."""

    def test_url_without_www(self):
        """figma.com without www prefix should work."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/MyFile"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"

    def test_url_with_www(self):
        """www.figma.com should work."""
        result = parse_figma_url(
            "https://www.figma.com/design/ABC123XYZabcdef789012/MyFile"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"

    def test_url_with_trailing_slash(self):
        """URL with trailing slash should still parse."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/MyFile/"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"

    def test_url_with_special_chars_in_name(self):
        """File name with special characters should parse."""
        result = parse_figma_url(
            "https://figma.com/design/ABC123XYZabcdef789012/My%20File%20(v2)"
        )
        assert result["file_key"] == "ABC123XYZabcdef789012"

    def test_http_rejected(self):
        """HTTP URLs must be rejected — only HTTPS is allowed (SEC-001)."""
        with pytest.raises(FigmaURLError):
            parse_figma_url(
                "http://figma.com/design/ABC123XYZabcdef789012/MyFile"
            )
