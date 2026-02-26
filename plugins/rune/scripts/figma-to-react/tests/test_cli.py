"""Tests for cli.py — CLI argument parsing and integration."""
from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add parent directory to path so we can import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli import _mask_token, _supports_color, build_parser, main  # noqa: E402


# ---------------------------------------------------------------------------
# Token masking
# ---------------------------------------------------------------------------


class TestMaskToken:
    """Test token masking for safe display."""

    def test_short_token_fully_masked(self):
        assert _mask_token("abc") == "****"
        assert _mask_token("123456789012") == "****"

    def test_long_token_shows_prefix_suffix(self):
        token = "figd_abcdefghijklmnop"
        masked = _mask_token(token)
        assert masked.startswith("figd_")
        assert masked.endswith("mnop")
        assert "****" in masked

    def test_empty_token(self):
        assert _mask_token("") == "****"


# ---------------------------------------------------------------------------
# Color support detection
# ---------------------------------------------------------------------------


class TestSupportsColor:
    """Test terminal color detection."""

    def test_no_color_env(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        assert _supports_color() is False

    def test_force_color_env(self, monkeypatch):
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert _supports_color() is True


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    """Test CLI argument parser construction."""

    def test_fetch_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["fetch", "https://figma.com/design/ABC/Title"])
        assert args.command == "fetch"
        assert args.url == "https://figma.com/design/ABC/Title"
        assert args.depth == 2  # default

    def test_fetch_with_depth(self):
        parser = build_parser()
        args = parser.parse_args([
            "fetch", "https://figma.com/design/ABC/Title", "--depth", "5"
        ])
        assert args.depth == 5

    def test_inspect_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "inspect", "https://figma.com/design/ABC/Title?node-id=1-3"
        ])
        assert args.command == "inspect"

    def test_list_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["list", "https://figma.com/design/ABC/Title"])
        assert args.command == "list"

    def test_react_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "react", "https://figma.com/design/ABC/Title?node-id=1-3",
            "--name", "MyCard",
        ])
        assert args.command == "react"
        assert args.name == "MyCard"

    def test_react_no_tailwind(self):
        parser = build_parser()
        args = parser.parse_args([
            "react", "https://figma.com/design/ABC/Title", "--no-tailwind"
        ])
        assert args.no_tailwind is True

    def test_react_extract(self):
        parser = build_parser()
        args = parser.parse_args([
            "react", "https://figma.com/design/ABC/Title", "--extract"
        ])
        assert args.extract is True

    def test_global_options(self):
        parser = build_parser()
        args = parser.parse_args([
            "--token", "figd_xxx", "--pretty", "--verbose",
            "fetch", "https://figma.com/design/ABC/Title",
        ])
        assert args.token == "figd_xxx"
        assert args.pretty is True
        assert args.verbose is True

    def test_output_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "/tmp/out.json",
            "fetch", "https://figma.com/design/ABC/Title",
        ])
        assert args.output == "/tmp/out.json"

    def test_missing_command_exits(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


class TestMain:
    """Test main() entry point with mocked API calls."""

    def test_missing_token_exits(self, monkeypatch):
        """Exit code 1 when no token is provided."""
        monkeypatch.delenv("FIGMA_TOKEN", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            main(["fetch", "https://figma.com/design/ABC/Title"])
        assert exc_info.value.code == 1

    def test_invalid_url_exits(self, monkeypatch):
        """Exit code 1 for invalid Figma URLs."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")
        with pytest.raises(SystemExit) as exc_info:
            main(["fetch", "https://example.com/not-figma"])
        assert exc_info.value.code == 1

    def test_fetch_success(self, monkeypatch):
        """Successful fetch writes JSON to stdout."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")

        mock_result = {
            "content": '{"file_key": "ABC", "node_count": 5, "tree": {}}',
        }

        with patch("core.fetch_design", new_callable=AsyncMock, return_value=mock_result):
            captured = StringIO()
            monkeypatch.setattr("sys.stdout", captured)

            main(["fetch", "https://www.figma.com/design/ABC123XYZabcdef789012/Title"])

            output = captured.getvalue()
            parsed = json.loads(output)
            assert parsed["content"] is not None

    def test_output_to_file(self, monkeypatch, tmp_path):
        """--output writes result to file instead of stdout."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")
        out_file = tmp_path / "result.json"

        mock_result = {"content": "test"}

        with patch("core.fetch_design", new_callable=AsyncMock, return_value=mock_result):
            main([
                "--output", str(out_file),
                "fetch", "https://www.figma.com/design/ABC123XYZabcdef789012/Title",
            ])

        assert out_file.exists()
        parsed = json.loads(out_file.read_text())
        assert parsed["content"] == "test"

    def test_pretty_output(self, monkeypatch):
        """--pretty produces indented JSON."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")

        mock_result = {"content": "test", "count": 1}

        with patch("core.fetch_design", new_callable=AsyncMock, return_value=mock_result):
            captured = StringIO()
            monkeypatch.setattr("sys.stdout", captured)

            main([
                "--pretty",
                "fetch", "https://www.figma.com/design/ABC123XYZabcdef789012/Title",
            ])

            output = captured.getvalue()
            assert "\n" in output  # indented output has newlines
            assert "  " in output  # 2-space indentation
