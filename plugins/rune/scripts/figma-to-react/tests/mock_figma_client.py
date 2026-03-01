"""Mock FigmaClient for integration tests.

Loads captured Figma API responses from fixture files instead of
hitting the real API. Implements the same async interface as
``FigmaClient`` so it can be used as a drop-in replacement.

Usage::

    from tests.mock_figma_client import MockFigmaClient

    async with MockFigmaClient() as client:
        result = await to_react(client, url)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockFigmaClient:
    """Drop-in replacement for FigmaClient that reads from fixture files.

    Fixture file naming convention:
    - ``{name}_nodes.json`` — captured ``get_nodes()`` responses
    - ``{name}_file.json``  — captured ``get_file()`` responses

    The mock matches file_key + node_id to the right fixture.
    """

    def __init__(self, fixtures: Optional[dict[str, Path]] = None) -> None:
        self._fixtures: dict[str, Path] = fixtures or {}
        self._loaded: dict[str, Any] = {}

    def register_nodes_fixture(
        self,
        file_key: str,
        node_id: str,
        fixture_path: Path,
    ) -> None:
        """Register a fixture file for a get_nodes() call."""
        key = f"nodes:{file_key}:{node_id}"
        self._fixtures[key] = fixture_path

    def register_file_fixture(
        self,
        file_key: str,
        fixture_path: Path,
    ) -> None:
        """Register a fixture file for a get_file() call."""
        key = f"file:{file_key}"
        self._fixtures[key] = fixture_path

    def _load_fixture(self, key: str) -> Any:
        if key in self._loaded:
            return self._loaded[key]
        path = self._fixtures.get(key)
        if path is None:
            raise FileNotFoundError(
                f"No fixture registered for key '{key}'. "
                f"Available: {list(self._fixtures.keys())}"
            )
        with open(path) as f:
            data = json.load(f)
        self._loaded[key] = data
        return data

    async def get_nodes(
        self,
        file_key: str,
        node_ids: list[str],
        *,
        branch_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return cached fixture data for get_nodes()."""
        # Try each node_id to find a matching fixture
        for nid in node_ids:
            key = f"nodes:{file_key}:{nid}"
            if key in self._fixtures:
                return self._load_fixture(key)
        # Fallback: try first node_id
        key = f"nodes:{file_key}:{node_ids[0]}"
        return self._load_fixture(key)

    async def get_file(
        self,
        file_key: str,
        *,
        depth: int = 2,
        branch_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return cached fixture data for get_file()."""
        key = f"file:{file_key}"
        return self._load_fixture(key)

    async def get_images(
        self,
        file_key: str,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,
    ) -> dict[str, Optional[str]]:
        """Return empty image URLs (no image export in mock)."""
        return {}

    async def __aenter__(self) -> MockFigmaClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        pass
