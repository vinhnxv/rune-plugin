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

from cli import _extract_component_name, _mask_token, _supports_color, build_parser, main  # noqa: E402


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

    def test_react_code_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "react", "https://figma.com/design/ABC/Title", "--code"
        ])
        assert args.code is True

    def test_react_write_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "react", "https://figma.com/design/ABC/Title", "--write", "/tmp/out/"
        ])
        assert args.write == "/tmp/out/"

    def test_react_aria_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "react", "https://figma.com/design/ABC/Title", "--aria"
        ])
        assert args.aria is True

    def test_react_aria_default_off(self):
        parser = build_parser()
        args = parser.parse_args([
            "react", "https://figma.com/design/ABC/Title"
        ])
        assert args.aria is False

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

    def test_code_flag_outputs_raw_tsx(self, monkeypatch):
        """--code prints raw React code, not JSON."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")

        mock_result = {
            "content": json.dumps({
                "file_key": "ABC",
                "main_component": "export default function SignUp() {\n  return <div/>;\n}",
            }),
        }

        with patch("core.to_react", new_callable=AsyncMock, return_value=mock_result):
            captured = StringIO()
            monkeypatch.setattr("sys.stdout", captured)

            main([
                "react",
                "https://www.figma.com/design/ABC123XYZabcdef789012/Title?node-id=1-3",
                "--code",
            ])

            output = captured.getvalue().strip()
            assert output.startswith("export default function")
            # Should NOT be JSON-wrapped
            assert not output.startswith("{")

    def test_write_flag_creates_file(self, monkeypatch, tmp_path):
        """--write writes a .tsx file."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")

        code = "export default function MyCard() {\n  return <div/>;\n}"
        mock_result = {
            "content": json.dumps({"file_key": "ABC", "main_component": code}),
        }

        with patch("core.to_react", new_callable=AsyncMock, return_value=mock_result):
            main([
                "react",
                "https://www.figma.com/design/ABC123XYZabcdef789012/Title?node-id=1-3",
                "--write", str(tmp_path / "MyCard.tsx"),
            ])

        out_file = tmp_path / "MyCard.tsx"
        assert out_file.exists()
        content = out_file.read_text()
        assert "export default function MyCard" in content

    def test_write_flag_auto_names_from_component(self, monkeypatch, tmp_path):
        """--write to a directory auto-names the .tsx file from the component."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")

        code = "export default function LoginForm() {\n  return <div/>;\n}"
        mock_result = {
            "content": json.dumps({"file_key": "ABC", "main_component": code}),
        }

        with patch("core.to_react", new_callable=AsyncMock, return_value=mock_result):
            main([
                "react",
                "https://www.figma.com/design/ABC123XYZabcdef789012/Title?node-id=1-3",
                "--write", str(tmp_path),
            ])

        out_file = tmp_path / "LoginForm.tsx"
        assert out_file.exists()

    def test_code_and_write_mutually_exclusive(self, monkeypatch):
        """--code and --write together should error."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")
        with pytest.raises(SystemExit) as exc_info:
            main([
                "react",
                "https://figma.com/design/ABC/Title",
                "--code", "--write", "/tmp/out.tsx",
            ])
        assert exc_info.value.code == 2  # argparse error

    def test_code_and_output_conflict(self, monkeypatch):
        """--code and --output together should error."""
        monkeypatch.setenv("FIGMA_TOKEN", "figd_test_token_value")
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--output", "/tmp/out.json",
                "react",
                "https://figma.com/design/ABC/Title",
                "--code",
            ])
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# _extract_component_name
# ---------------------------------------------------------------------------


class TestExtractComponentName:
    """Test component name extraction from generated React code."""

    def test_standard_export(self):
        code = "export default function MyCard() {\n  return <div/>;\n}"
        assert _extract_component_name(code) == "MyCard"

    def test_multiline_code(self):
        code = "import React from 'react';\n\nexport default function SignUpForm() {"
        assert _extract_component_name(code) == "SignUpForm"

    def test_no_match_returns_default(self):
        code = "const x = 42;"
        assert _extract_component_name(code) == "Component"

    def test_empty_string(self):
        assert _extract_component_name("") == "Component"
