"""Tests for core.py — business logic extracted from server.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add parent directory to path so we can import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import ir_to_dict, paginate_output  # noqa: E402
from node_parser import parse_node  # noqa: E402


# ---------------------------------------------------------------------------
# ir_to_dict
# ---------------------------------------------------------------------------


class TestIrToDict:
    """Test IR node tree serialization."""

    def test_basic_frame(self, hero_card_node):
        """Convert a parsed frame to dict."""
        ir = parse_node(hero_card_node)
        assert ir is not None
        result = ir_to_dict(ir)
        assert result["node_id"] == "1:2"
        assert result["name"] == "HeroCard"
        assert "children" in result

    def test_max_depth_truncation(self, hero_card_node):
        """Nodes beyond max_depth are truncated."""
        ir = parse_node(hero_card_node)
        assert ir is not None
        result = ir_to_dict(ir, max_depth=1)
        if "children" in result:
            for child in result["children"]:
                assert child.get("truncated") is True

    def test_text_content_included(self, text_node):
        """Text nodes include content and font info."""
        ir = parse_node(text_node)
        assert ir is not None
        result = ir_to_dict(ir)
        assert "text_content" in result
        assert result["text_content"] == "Welcome to Rune"


# ---------------------------------------------------------------------------
# paginate_output
# ---------------------------------------------------------------------------


class TestPaginateOutput:
    """Test output pagination logic."""

    def test_small_content_no_pagination(self):
        content = "hello world"
        result = paginate_output(content)
        assert result["content"] == "hello world"
        assert "has_more" not in result

    def test_large_content_paginated(self):
        content = "x" * 100
        result = paginate_output(content, max_length=30)
        assert len(result["content"]) == 30
        assert result["has_more"] is True
        assert result["next_start_index"] == 30
        assert result["total_length"] == 100

    def test_start_index_offset(self):
        content = "abcdefghij"
        result = paginate_output(content, max_length=3, start_index=5)
        assert result["content"] == "fgh"
        assert result["start_index"] == 5
        assert result["end_index"] == 8

    def test_last_page_no_has_more(self):
        content = "abcdefghij"
        result = paginate_output(content, max_length=5, start_index=5)
        assert result["content"] == "fghij"
        assert "has_more" not in result
