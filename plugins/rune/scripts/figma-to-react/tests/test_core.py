"""Tests for core.py — business logic extracted from server.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add parent directory to path so we can import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import extract_react_code, ir_to_dict, paginate_output  # noqa: E402
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


# ---------------------------------------------------------------------------
# extract_react_code
# ---------------------------------------------------------------------------


class TestExtractReactCode:
    """Test extracting raw React code from paginated to_react() results."""

    def test_extracts_from_paginated_result(self):
        """Standard paginated result with JSON content string."""
        import json
        inner = {"file_key": "ABC", "main_component": "export default function Foo() {}"}
        result = {"content": json.dumps(inner)}
        assert extract_react_code(result) == "export default function Foo() {}"

    def test_extracts_from_plain_dict(self):
        """Unpaginated dict (content is not a string)."""
        result = {"main_component": "const Bar = () => <div/>"}
        assert extract_react_code(result) == "const Bar = () => <div/>"

    def test_missing_main_component_returns_empty(self):
        """Returns empty string when main_component is absent."""
        import json
        result = {"content": json.dumps({"file_key": "X"})}
        assert extract_react_code(result) == ""

    def test_empty_result_returns_empty(self):
        """Gracefully handles empty dict."""
        assert extract_react_code({}) == ""


# ---------------------------------------------------------------------------
# Data preservation (P0 — validates the Pydantic bypass fix)
# ---------------------------------------------------------------------------


class TestDataPreservation:
    """Verify raw dict bypass preserves type-specific Figma fields.

    These tests simulate what _fetch_node_or_file() now returns:
    raw dicts with characters, layoutMode, fillGeometry, etc.
    """

    def test_text_characters_preserved(self):
        """TEXT node's characters field survives the roundtrip."""
        raw = {
            "id": "100:1",
            "name": "SignUp",
            "type": "TEXT",
            "characters": "Sign up with Facebook",
            "style": {"fontFamily": "Inter", "fontSize": 16.0, "fontWeight": 400.0},
            "fills": [],
            "strokes": [],
            "effects": [],
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 24},
        }
        ir = parse_node(raw)
        assert ir is not None
        assert ir.text_content == "Sign up with Facebook"

    def test_layout_mode_preserved(self):
        """FRAME node's layoutMode field survives the roundtrip."""
        raw = {
            "id": "100:2",
            "name": "Container",
            "type": "FRAME",
            "layoutMode": "VERTICAL",
            "itemSpacing": 48,
            "paddingTop": 16, "paddingRight": 16,
            "paddingBottom": 16, "paddingLeft": 16,
            "fills": [], "strokes": [], "effects": [],
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 600},
            "children": [],
        }
        ir = parse_node(raw)
        assert ir is not None
        assert ir.has_auto_layout is True
        assert ir.layout_mode.value == "VERTICAL"
        assert ir.item_spacing == 48

    def test_fill_geometry_preserved(self):
        """VECTOR node's fillGeometry field survives the roundtrip."""
        raw = {
            "id": "100:3",
            "name": "ArrowIcon",
            "type": "VECTOR",
            "fillGeometry": [
                {"path": "M10 20L20 10L30 20", "windingRule": "NONZERO"}
            ],
            "fills": [], "strokes": [], "effects": [],
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 30, "height": 20},
        }
        ir = parse_node(raw)
        assert ir is not None
        assert len(ir.fill_geometry) == 1
        assert ir.fill_geometry[0]["path"] == "M10 20L20 10L30 20"

    def test_nested_text_in_frame(self):
        """Text content survives when nested inside auto-layout frames."""
        raw = {
            "id": "100:4",
            "name": "Card",
            "type": "FRAME",
            "layoutMode": "VERTICAL",
            "itemSpacing": 16,
            "fills": [], "strokes": [], "effects": [],
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 400},
            "children": [
                {
                    "id": "100:5",
                    "name": "Title",
                    "type": "TEXT",
                    "characters": "Welcome",
                    "style": {"fontFamily": "Inter", "fontSize": 24.0, "fontWeight": 700.0},
                    "fills": [], "strokes": [], "effects": [],
                    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30},
                },
                {
                    "id": "100:6",
                    "name": "Body",
                    "type": "TEXT",
                    "characters": "Hello world",
                    "style": {"fontFamily": "Inter", "fontSize": 14.0, "fontWeight": 400.0},
                    "fills": [], "strokes": [], "effects": [],
                    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 20},
                },
            ],
        }
        ir = parse_node(raw)
        assert ir is not None
        assert len(ir.children) == 2
        assert ir.children[0].text_content == "Welcome"
        assert ir.children[1].text_content == "Hello world"
        assert ir.has_auto_layout is True
