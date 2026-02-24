"""Tests for react_generator.py — React JSX code generation from Figma IR."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from react_generator import (
    generate_component,
    generate_component_with_props,
    _to_component_name,
    _escape_jsx,
)
from node_parser import FigmaIRNode, StyledTextSegment
from figma_types import LayoutMode, NodeType, TypeStyle


# ---------------------------------------------------------------------------
# Helper to build minimal IR nodes
# ---------------------------------------------------------------------------

def _make_node(**overrides) -> FigmaIRNode:
    defaults = dict(
        node_id="1:1",
        name="TestFrame",
        node_type=NodeType.FRAME,
        is_frame_like=True,
        width=400.0,
        height=300.0,
    )
    defaults.update(overrides)
    return FigmaIRNode(**defaults)


def _make_text_node(**overrides) -> FigmaIRNode:
    defaults = dict(
        node_id="2:1",
        name="Title",
        node_type=NodeType.TEXT,
        text_content="Hello World",
        width=200.0,
        height=24.0,
    )
    defaults.update(overrides)
    return FigmaIRNode(**defaults)


# ---------------------------------------------------------------------------
# _to_component_name
# ---------------------------------------------------------------------------

class TestComponentName:
    """Test Figma name to React component name conversion."""

    def test_simple_name(self):
        assert _to_component_name("HeroCard") == "Herocard"

    def test_spaces_to_pascal(self):
        assert _to_component_name("hero card") == "HeroCard"

    def test_hyphens_to_pascal(self):
        assert _to_component_name("nav-bar") == "NavBar"

    def test_slashes_to_pascal(self):
        assert _to_component_name("icons/close") == "IconsClose"

    def test_number_prefix_gets_component(self):
        # capitalize() lowercases all but first char: "3dButton" -> "3dbutton"
        assert _to_component_name("3dButton") == "Component3dbutton"

    def test_empty_returns_component(self):
        assert _to_component_name("") == "Component"

    def test_special_chars_only(self):
        assert _to_component_name("---") == "Component"


# ---------------------------------------------------------------------------
# _escape_jsx
# ---------------------------------------------------------------------------

class TestEscapeJsx:
    """Test JSX text escaping."""

    def test_plain_text_unchanged(self):
        assert _escape_jsx("Hello World") == "Hello World"

    def test_curly_braces_escaped(self):
        result = _escape_jsx("{value}")
        assert "&#123;" in result
        assert "&#125;" in result

    def test_angle_brackets_escaped(self):
        result = _escape_jsx("<script>alert(1)</script>")
        assert "&lt;" in result
        assert "&gt;" in result


# ---------------------------------------------------------------------------
# generate_component — basic structure
# ---------------------------------------------------------------------------

class TestGenerateComponentStructure:
    """Test generated component structure and boilerplate."""

    def test_has_import(self):
        root = _make_node()
        code = generate_component(root)
        assert "import React from 'react'" in code

    def test_has_export_default(self):
        root = _make_node()
        code = generate_component(root)
        assert "export default function" in code

    def test_uses_node_name(self):
        root = _make_node(name="HeroSection")
        code = generate_component(root)
        assert "Herosection" in code

    def test_custom_name_override(self):
        root = _make_node(name="SomeFrame")
        code = generate_component(root, component_name="MyCard")
        assert "MyCard" in code
        assert "Someframe" not in code

    def test_has_return_statement(self):
        root = _make_node()
        code = generate_component(root)
        assert "return (" in code

    def test_ends_with_closing_brace(self):
        root = _make_node()
        code = generate_component(root)
        lines = code.strip().split("\n")
        assert any(line.strip() == "}" for line in lines)


# ---------------------------------------------------------------------------
# generate_component — empty/leaf nodes
# ---------------------------------------------------------------------------

class TestLeafNodes:
    """Test code generation for leaf and empty nodes."""

    def test_empty_frame_self_closing_div(self):
        root = _make_node(children=[])
        code = generate_component(root)
        assert "<div" in code
        assert "/>" in code

    def test_invisible_child_skipped(self):
        child = _make_node(node_id="2:1", visible=False)
        root = _make_node(children=[child])
        code = generate_component(root)
        assert "<div" in code


# ---------------------------------------------------------------------------
# generate_component — text nodes
# ---------------------------------------------------------------------------

class TestTextNodeGeneration:
    """Test code generation for text nodes."""

    def test_simple_text_generates_p_tag(self):
        text = _make_text_node()
        root = _make_node(children=[text])
        code = generate_component(root)
        assert "<p" in code
        assert "Hello World" in code

    def test_text_with_jsx_special_chars(self):
        text = _make_text_node(text_content="Price: {$10}")
        root = _make_node(children=[text])
        code = generate_component(root)
        assert "&#123;" in code

    def test_rich_text_with_segments(self):
        """Text with multiple styled segments should use span wrappers."""
        # TypeStyle uses Pydantic aliases — must use model_validate with alias keys
        style_bold = TypeStyle.model_validate({"fontSize": 16.0, "fontWeight": 700.0})
        style_normal = TypeStyle.model_validate({"fontSize": 16.0, "fontWeight": 400.0})
        segments = [
            StyledTextSegment(text="Bold ", style=style_bold),
            StyledTextSegment(text="and normal", style=style_normal),
        ]
        text = _make_text_node(
            text_content="Bold and normal",
            text_segments=segments,
        )
        root = _make_node(children=[text])
        code = generate_component(root)
        assert "<span" in code
        assert "Bold " in code


# ---------------------------------------------------------------------------
# generate_component — image nodes
# ---------------------------------------------------------------------------

class TestImageNodeGeneration:
    """Test code generation for image and SVG nodes."""

    def test_image_fill_generates_img(self):
        img = _make_node(
            node_id="2:1",
            name="CardImage",
            node_type=NodeType.RECTANGLE,
            has_image_fill=True,
            image_ref="hash123",
            width=300.0,
            height=200.0,
        )
        root = _make_node(children=[img])
        code = generate_component(root, image_urls={"hash123": "https://cdn.example.com/img.png"})
        assert "<img" in code
        assert "https://cdn.example.com/img.png" in code

    def test_unresolved_image_adds_todo(self):
        img = _make_node(
            node_id="2:1",
            node_type=NodeType.RECTANGLE,
            has_image_fill=True,
            image_ref="unresolved_hash",
        )
        root = _make_node(children=[img])
        code = generate_component(root)
        assert "TODO" in code
        assert "unresolved_hash" in code

    def test_svg_candidate_generates_svg(self):
        icon = _make_node(
            node_id="2:1",
            name="CloseIcon",
            is_svg_candidate=True,
            width=24.0,
            height=24.0,
        )
        root = _make_node(children=[icon])
        code = generate_component(root)
        assert "<svg" in code
        assert "CloseIcon" in code


# ---------------------------------------------------------------------------
# generate_component — nested structure
# ---------------------------------------------------------------------------

class TestNestedGeneration:
    """Test code generation for nested node trees."""

    def test_nested_divs(self):
        inner = _make_node(node_id="3:1", name="Inner", children=[])
        middle = _make_node(node_id="2:1", name="Middle", children=[inner])
        root = _make_node(children=[middle])
        code = generate_component(root)
        assert code.count("<div") >= 2

    def test_layout_classes_on_container(self):
        child = _make_node(node_id="2:1", name="Child")
        root = _make_node(
            has_auto_layout=True,
            layout_mode=LayoutMode.HORIZONTAL,
            item_spacing=8.0,
            children=[child],
        )
        code = generate_component(root)
        assert "flex" in code
        assert "flex-row" in code
        assert "gap-2" in code


# ---------------------------------------------------------------------------
# generate_component_with_props
# ---------------------------------------------------------------------------

class TestGenerateComponentWithProps:
    """Test component generation with TypeScript props interface."""

    def test_generates_interface(self):
        root = _make_node()
        code = generate_component_with_props(
            root,
            component_name="Card",
            prop_names=["title", "subtitle"],
        )
        assert "interface CardProps" in code
        assert "title?: string" in code
        assert "subtitle?: string" in code

    def test_destructures_props(self):
        root = _make_node()
        code = generate_component_with_props(
            root,
            component_name="Card",
            prop_names=["title"],
        )
        assert "{ title }: CardProps" in code

    def test_no_props_same_as_generate_component(self):
        root = _make_node()
        code = generate_component_with_props(root, component_name="Card")
        assert "interface" not in code
        assert "export default function Card()" in code

    def test_custom_name(self):
        root = _make_node()
        code = generate_component_with_props(
            root,
            component_name="MyWidget",
            prop_names=["size"],
        )
        assert "MyWidgetProps" in code
        assert "function MyWidget" in code
