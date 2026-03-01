"""Integration tests using captured Figma API responses.

These tests exercise the full pipeline (fetch → parse → generate)
against real API data without hitting the network. The fixture
``signup_12_749_nodes.json`` was captured from node 12-749 of:
https://www.figma.com/design/VszzNQxbig1xYxHTrfxeIY/50-Web-Sign-up-log-in-designs--Community-

To recapture the fixture (requires FIGMA_TOKEN):
    python3 -c "
    import asyncio, json
    from figma_client import FigmaClient
    async def go():
        async with FigmaClient() as c:
            d = await c.get_nodes('VszzNQxbig1xYxHTrfxeIY', ['12-749'])
            with open('tests/fixtures/signup_12_749_nodes.json', 'w') as f:
                json.dump(d, f, indent=2)
    asyncio.run(go())
    "
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import extract_react_code, fetch_design, to_react  # noqa: E402
from node_parser import parse_node, walk_tree  # noqa: E402
from tests.mock_figma_client import MockFigmaClient, FIXTURES_DIR  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIGNUP_FILE_KEY = "VszzNQxbig1xYxHTrfxeIY"
SIGNUP_NODE_ID = "12:749"
SIGNUP_URL = (
    "https://www.figma.com/design/VszzNQxbig1xYxHTrfxeIY/"
    "50-Web-Sign-up-log-in-designs--Community-?node-id=12-749"
)
SIGNUP_FIXTURE = FIXTURES_DIR / "signup_12_749_nodes.json"


@pytest.fixture()
def mock_client() -> MockFigmaClient:
    """Create a MockFigmaClient with the signup fixture registered."""
    client = MockFigmaClient()
    client.register_nodes_fixture(
        SIGNUP_FILE_KEY,
        SIGNUP_NODE_ID,
        SIGNUP_FIXTURE,
    )
    return client


@pytest.fixture()
def signup_raw_doc() -> dict:
    """Load the raw document dict for the signup node (12:749)."""
    with open(SIGNUP_FIXTURE) as f:
        data = json.load(f)
    return data["nodes"][SIGNUP_NODE_ID]["document"]


# ---------------------------------------------------------------------------
# Data preservation — raw dict has all fields
# ---------------------------------------------------------------------------


class TestRawDataPreservation:
    """Verify captured fixture contains the fields that Pydantic used to strip."""

    def test_fixture_has_text_characters(self, signup_raw_doc):
        """At least one TEXT node has 'characters' field."""
        texts = _find_nodes_by_type(signup_raw_doc, "TEXT")
        assert len(texts) > 0
        chars_found = [n.get("characters", "") for n in texts if n.get("characters")]
        assert len(chars_found) > 0, "No TEXT node has characters field"

    def test_fixture_has_layout_mode(self, signup_raw_doc):
        """At least one FRAME has layoutMode set."""
        frames = _find_nodes_by_type(signup_raw_doc, "FRAME")
        layouts = [f for f in frames if f.get("layoutMode") and f["layoutMode"] != "NONE"]
        assert len(layouts) > 0, "No FRAME has layoutMode set"

    def test_fixture_has_fill_geometry(self, signup_raw_doc):
        """At least one VECTOR node has fillGeometry."""
        vectors = _find_nodes_by_type(signup_raw_doc, "VECTOR")
        with_geo = [v for v in vectors if v.get("fillGeometry")]
        assert len(with_geo) > 0, "No VECTOR has fillGeometry"


# ---------------------------------------------------------------------------
# IR parsing from real data
# ---------------------------------------------------------------------------


class TestIRParsingFromFixture:
    """Verify parse_node() produces correct IR from captured fixture data."""

    def test_parses_root_frame(self, signup_raw_doc):
        ir = parse_node(signup_raw_doc)
        assert ir is not None
        assert ir.name == "Sign up"
        assert ir.node_type.value == "FRAME"

    def test_text_content_parsed(self, signup_raw_doc):
        """All TEXT nodes should have text_content populated."""
        ir = parse_node(signup_raw_doc)
        assert ir is not None
        all_nodes = walk_tree(ir)
        text_nodes = [n for n in all_nodes if n.text_content]
        assert len(text_nodes) >= 5, f"Expected >=5 text nodes, got {len(text_nodes)}"

        # Specific text values from the design
        all_text = " ".join(n.text_content for n in text_nodes)
        assert "Facebook" in all_text
        assert "Google" in all_text
        assert "Twitter" in all_text

    def test_auto_layout_detected(self, signup_raw_doc):
        """Frames with layoutMode should have has_auto_layout=True."""
        ir = parse_node(signup_raw_doc)
        assert ir is not None
        all_nodes = walk_tree(ir)
        auto_layout_nodes = [n for n in all_nodes if n.has_auto_layout]
        assert len(auto_layout_nodes) >= 3, (
            f"Expected >=3 auto-layout nodes, got {len(auto_layout_nodes)}"
        )

    def test_fill_geometry_on_vectors(self, signup_raw_doc):
        """Vector nodes should have fill_geometry populated."""
        ir = parse_node(signup_raw_doc)
        assert ir is not None
        all_nodes = walk_tree(ir)
        with_geo = [n for n in all_nodes if n.fill_geometry]
        assert len(with_geo) >= 3, (
            f"Expected >=3 nodes with fill_geometry, got {len(with_geo)}"
        )


# ---------------------------------------------------------------------------
# Full pipeline: to_react() via MockFigmaClient
# ---------------------------------------------------------------------------


class TestToReactPipeline:
    """Test the full to_react() pipeline with mock client."""

    @pytest.mark.asyncio
    async def test_generates_component(self, mock_client):
        result = await to_react(mock_client, SIGNUP_URL)
        code = extract_react_code(result)
        assert "export default function" in code
        assert "import React" in code

    @pytest.mark.asyncio
    async def test_text_content_in_output(self, mock_client):
        """Generated JSX should contain actual text from the design."""
        result = await to_react(mock_client, SIGNUP_URL)
        code = extract_react_code(result)
        assert "Facebook" in code
        assert "Google" in code

    @pytest.mark.asyncio
    async def test_flex_layout_in_output(self, mock_client):
        """Generated JSX should contain Tailwind flex classes."""
        result = await to_react(mock_client, SIGNUP_URL)
        code = extract_react_code(result)
        assert "flex" in code

    @pytest.mark.asyncio
    async def test_semantic_html_in_output(self, mock_client):
        """Generated JSX should use semantic HTML tags."""
        result = await to_react(mock_client, SIGNUP_URL)
        code = extract_react_code(result)
        # The design has text fields and labels — at least some should map
        # to semantic tags based on font size (h1/h2/h3) or name (button)
        has_semantic = any(
            tag in code for tag in ("<h1", "<h2", "<h3", "<button", "<nav", "<p")
        )
        assert has_semantic, "No semantic HTML tags found in generated code"

    @pytest.mark.asyncio
    async def test_svg_paths_in_output(self, mock_client):
        """Generated JSX should contain actual SVG path data."""
        result = await to_react(mock_client, SIGNUP_URL)
        code = extract_react_code(result)
        assert "<path d=" in code, "No SVG path elements found"

    @pytest.mark.asyncio
    async def test_no_empty_text_nodes(self, mock_client):
        """No text node should render as empty content."""
        result = await to_react(mock_client, SIGNUP_URL)
        code = extract_react_code(result)
        # Check there are no empty <p></p> or <h1></h1> tags
        import re
        empty_tags = re.findall(r"<(p|h[1-3])\b[^>]*>\s*</(p|h[1-3])>", code)
        assert len(empty_tags) == 0, f"Found empty text tags: {empty_tags}"


# ---------------------------------------------------------------------------
# fetch_design() pipeline
# ---------------------------------------------------------------------------


class TestFetchDesignPipeline:
    """Test fetch_design() returns valid IR tree."""

    @pytest.mark.asyncio
    async def test_returns_tree_with_nodes(self, mock_client):
        # Use large max_length — 184 nodes produce ~130KB of IR JSON
        result = await fetch_design(
            mock_client, SIGNUP_URL, max_length=500_000
        )
        content = json.loads(result["content"])
        assert content["node_count"] > 10
        assert content["tree"]["name"] == "Sign up"
        assert "children" in content["tree"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_nodes_by_type(raw: dict, node_type: str) -> list[dict]:
    """Recursively find all nodes of a given type in raw Figma data."""
    results: list[dict] = []
    if raw.get("type") == node_type:
        results.append(raw)
    for child in raw.get("children", []):
        results.extend(_find_nodes_by_type(child, node_type))
    return results
