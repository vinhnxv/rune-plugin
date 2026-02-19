"""Tests for indexer.py — MEMORY.md parser for Echo Search MCP."""

import textwrap

from indexer import discover_and_parse, generate_id, parse_memory_file


# ---------------------------------------------------------------------------
# generate_id
# ---------------------------------------------------------------------------

class TestGenerateId:
    def test_deterministic(self):
        """Same inputs always produce the same ID."""
        id1 = generate_id("reviewer", 10, "/path/MEMORY.md")
        id2 = generate_id("reviewer", 10, "/path/MEMORY.md")
        assert id1 == id2

    def test_different_roles_produce_different_ids(self):
        id1 = generate_id("reviewer", 1, "/p")
        id2 = generate_id("planner", 1, "/p")
        assert id1 != id2

    def test_different_lines_produce_different_ids(self):
        id1 = generate_id("reviewer", 1, "/p")
        id2 = generate_id("reviewer", 2, "/p")
        assert id1 != id2

    def test_different_paths_produce_different_ids(self):
        id1 = generate_id("reviewer", 1, "/a/MEMORY.md")
        id2 = generate_id("reviewer", 1, "/b/MEMORY.md")
        assert id1 != id2

    def test_returns_16_char_hex(self):
        result = generate_id("role", 1, "/path")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_unicode_path(self):
        """Non-ASCII file paths should still produce a valid hex ID."""
        result = generate_id("role", 1, "/đường/dẫn/MEMORY.md")
        assert len(result) == 16


# ---------------------------------------------------------------------------
# parse_memory_file
# ---------------------------------------------------------------------------

class TestParseMemoryFile:
    def test_nonexistent_file(self, tmp_path):
        """Missing file returns empty list."""
        result = parse_memory_file(str(tmp_path / "missing.md"), "role")
        assert result == []

    def test_single_inscribed_entry(self, tmp_path):
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            # Memory

            ## Inscribed — Team lifecycle guards (2026-01-15)
            **Source**: `rune:review session-abc`
            **Confidence**: HIGH (verified across 3 sessions)
            ### Pattern
            - Always use pre-create guard before TeamCreate
            - TeamDelete often fails with active members
        """))

        entries = parse_memory_file(str(md), "orchestrator")
        assert len(entries) == 1

        e = entries[0]
        assert e["role"] == "orchestrator"
        assert e["layer"] == "inscribed"
        assert e["date"] == "2026-01-15"
        assert e["source"] == "rune:review session-abc"
        assert e["tags"] == "Team lifecycle guards"
        assert "pre-create guard" in e["content"]
        assert "id" in e
        assert len(e["id"]) == 16

    def test_multiple_layers(self, tmp_path):
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Etched — Security hardening (2026-02-01)
            **Source**: `rune:audit full-scan`
            - Input validation is essential

            ## Traced — Quick note (2026-02-10)
            **Source**: `rune:work task-42`
            - This was a minor observation
        """))

        entries = parse_memory_file(str(md), "reviewer")
        assert len(entries) == 2
        assert entries[0]["layer"] == "etched"
        assert entries[1]["layer"] == "traced"

    def test_em_dash_separator(self, tmp_path):
        """Parser supports em dash (—), en dash (–), and hyphen (-) separators."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed \u2014 Em dash title (2026-01-01)
            Content for em dash

            ## Etched \u2013 En dash title (2026-01-02)
            Content for en dash

            ## Traced - Hyphen title (2026-01-03)
            Content for hyphen
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 3
        assert entries[0]["tags"] == "Em dash title"
        assert entries[1]["tags"] == "En dash title"
        assert entries[2]["tags"] == "Hyphen title"

    def test_empty_entry_skipped(self, tmp_path):
        """Entry with header but no content body is skipped."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Empty one (2026-01-01)

            ## Inscribed — Has content (2026-01-02)
            Actual content here
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["tags"] == "Has content"

    def test_source_without_backticks(self, tmp_path):
        """Source line without backtick quoting is still parsed."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Title (2026-01-01)
            **Source**: rune:review abc
            Content body here
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["source"] == "rune:review abc"

    def test_content_excludes_source_line(self, tmp_path):
        """Source line should not appear in the content field."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Title (2026-01-01)
            **Source**: `rune:review`
            The actual content
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert "**Source**" not in entries[0]["content"]
        assert "The actual content" in entries[0]["content"]

    def test_multiline_content(self, tmp_path):
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Multi-line (2026-01-01)
            **Source**: `src`
            Line one
            Line two
            Line three
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert "Line one" in entries[0]["content"]
        assert "Line three" in entries[0]["content"]

    def test_line_number_is_one_indexed(self, tmp_path):
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            # Header
            Some preamble

            ## Inscribed — Entry (2026-01-01)
            Content
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["line_number"] == 4  # ## is on line 4

    def test_ids_are_unique_per_entry(self, tmp_path):
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — First (2026-01-01)
            Content A

            ## Inscribed — Second (2026-01-02)
            Content B
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 2
        assert entries[0]["id"] != entries[1]["id"]

    def test_only_first_source_line_captured(self, tmp_path):
        """If multiple **Source** lines appear, only the first is used."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Title (2026-01-01)
            **Source**: `first-source`
            **Source**: `second-source`
            Body content
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["source"] == "first-source"
        # Second source line becomes part of content
        assert "second-source" in entries[0]["content"]

    def test_header_at_last_line(self, tmp_path):
        """Header on the very last line with no following content is skipped."""
        md = tmp_path / "MEMORY.md"
        md.write_text("## Inscribed — Orphan header (2026-01-01)")

        entries = parse_memory_file(str(md), "test")
        assert entries == []

    def test_preamble_text_ignored(self, tmp_path):
        """Text before the first ## header is not captured."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            # Rune Echoes
            This preamble should not create an entry.
            Some more preamble.

            ## Inscribed — Actual entry (2026-01-01)
            Real content
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert "preamble" not in entries[0]["content"]

    def test_consecutive_headers_skip_empty(self, tmp_path):
        """Three headers in a row — first two have no content, only third does."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Empty A (2026-01-01)
            ## Etched — Empty B (2026-01-02)
            ## Traced — Has content (2026-01-03)
            Real content here
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["layer"] == "traced"

    def test_whitespace_only_content_skipped(self, tmp_path):
        """Entry whose body is only whitespace/blank lines is skipped."""
        md = tmp_path / "MEMORY.md"
        md.write_text(
            "## Inscribed — Blank body (2026-01-01)\n"
            "   \n"
            "  \n"
            "\n"
            "## Inscribed — Real body (2026-01-02)\n"
            "Actual content\n"
        )

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["tags"] == "Real body"

    def test_layer_case_normalized_to_lower(self, tmp_path):
        """Layer name from header (e.g. 'Inscribed') is stored as lowercase."""
        md = tmp_path / "MEMORY.md"
        md.write_text("## Inscribed — Title (2026-01-01)\nContent\n")

        entries = parse_memory_file(str(md), "test")
        assert entries[0]["layer"] == "inscribed"

    def test_invalid_layer_name_not_matched(self, tmp_path):
        """Only Inscribed/Etched/Traced are valid layers. Others are ignored."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Custom — Not a valid layer (2026-01-01)
            This should not match

            ## Inscribed — Valid (2026-01-01)
            This should match
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["layer"] == "inscribed"

    def test_title_whitespace_trimmed(self, tmp_path):
        """Extra whitespace around the title is trimmed."""
        md = tmp_path / "MEMORY.md"
        md.write_text("## Inscribed —   Padded title   (2026-01-01)\nContent\n")

        entries = parse_memory_file(str(md), "test")
        assert entries[0]["tags"] == "Padded title"

    def test_date_format_strict(self, tmp_path):
        """Date must match YYYY-MM-DD format. Invalid dates don't match the header."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Bad date (01-2026-01)
            Content for bad date

            ## Inscribed — Good date (2026-01-15)
            Content for good date
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert entries[0]["date"] == "2026-01-15"

    def test_file_path_stored_in_entry(self, tmp_path):
        """Each entry stores the absolute file_path it was parsed from."""
        md = tmp_path / "MEMORY.md"
        md.write_text("## Inscribed — Title (2026-01-01)\nContent\n")

        entries = parse_memory_file(str(md), "test")
        assert entries[0]["file_path"] == str(md)

    def test_empty_file(self, tmp_path):
        """Completely empty file returns no entries."""
        md = tmp_path / "MEMORY.md"
        md.write_text("")

        entries = parse_memory_file(str(md), "test")
        assert entries == []

    def test_content_with_markdown_formatting(self, tmp_path):
        """Content can contain markdown headings, lists, code blocks."""
        md = tmp_path / "MEMORY.md"
        md.write_text(textwrap.dedent("""\
            ## Inscribed — Rich content (2026-01-01)
            **Source**: `src`
            ### Subsection
            - Bullet one
            - Bullet two
            ```python
            code_here()
            ```
            More text
        """))

        entries = parse_memory_file(str(md), "test")
        assert len(entries) == 1
        assert "### Subsection" in entries[0]["content"]
        assert "code_here()" in entries[0]["content"]


# ---------------------------------------------------------------------------
# discover_and_parse
# ---------------------------------------------------------------------------

class TestDiscoverAndParse:
    def test_nonexistent_dir(self, tmp_path):
        result = discover_and_parse(str(tmp_path / "nonexistent"))
        assert result == []

    def test_empty_dir(self, tmp_path):
        echo_dir = tmp_path / "echoes"
        echo_dir.mkdir()
        result = discover_and_parse(str(echo_dir))
        assert result == []

    def test_single_role(self, tmp_path):
        echo_dir = tmp_path / "echoes"
        role_dir = echo_dir / "reviewer"
        role_dir.mkdir(parents=True)
        (role_dir / "MEMORY.md").write_text(textwrap.dedent("""\
            ## Inscribed — Pattern (2026-01-01)
            **Source**: `src`
            Content here
        """))

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 1
        assert entries[0]["role"] == "reviewer"

    def test_multiple_roles_sorted(self, tmp_path):
        echo_dir = tmp_path / "echoes"
        for role in ["worker", "orchestrator", "reviewer"]:
            d = echo_dir / role
            d.mkdir(parents=True)
            (d / "MEMORY.md").write_text(
                "## Inscribed — %s note (2026-01-01)\nContent for %s" % (role, role)
            )

        entries = discover_and_parse(str(echo_dir))
        roles = [e["role"] for e in entries]
        # sorted() in discover_and_parse means orchestrator < reviewer < worker
        assert roles == ["orchestrator", "reviewer", "worker"]

    def test_invalid_role_name_skipped(self, tmp_path):
        """SEC-5: Role dirs with invalid characters are skipped."""
        echo_dir = tmp_path / "echoes"
        (echo_dir / "valid-role").mkdir(parents=True)
        (echo_dir / "valid-role" / "MEMORY.md").write_text(
            "## Inscribed — Entry (2026-01-01)\nContent"
        )
        # These should be skipped
        (echo_dir / "bad role").mkdir(parents=True)  # space
        (echo_dir / "bad role" / "MEMORY.md").write_text(
            "## Inscribed — Skip (2026-01-01)\nContent"
        )
        (echo_dir / "../../escape").mkdir(parents=True, exist_ok=True)

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 1
        assert entries[0]["role"] == "valid-role"

    def test_role_dir_without_memory_file(self, tmp_path):
        """Role dir exists but has no MEMORY.md — skip without error."""
        echo_dir = tmp_path / "echoes"
        (echo_dir / "empty-role").mkdir(parents=True)
        (echo_dir / "has-content").mkdir(parents=True)
        (echo_dir / "has-content" / "MEMORY.md").write_text(
            "## Inscribed — Entry (2026-01-01)\nContent"
        )

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 1
        assert entries[0]["role"] == "has-content"

    def test_file_in_echo_dir_not_treated_as_role(self, tmp_path):
        """Regular files in echo_dir root are not treated as role dirs."""
        echo_dir = tmp_path / "echoes"
        echo_dir.mkdir()
        (echo_dir / "README.md").write_text("not a role")
        (echo_dir / "role1").mkdir()
        (echo_dir / "role1" / "MEMORY.md").write_text(
            "## Inscribed — Entry (2026-01-01)\nContent"
        )

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 1

    def test_role_with_underscore_and_hyphen(self, tmp_path):
        """Valid role name chars: alphanumeric, underscore, hyphen."""
        echo_dir = tmp_path / "echoes"
        (echo_dir / "my_role-2").mkdir(parents=True)
        (echo_dir / "my_role-2" / "MEMORY.md").write_text(
            "## Inscribed — Entry (2026-01-01)\nContent"
        )

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 1
        assert entries[0]["role"] == "my_role-2"

    def test_dot_prefixed_dir_skipped(self, tmp_path):
        """SEC-5: Hidden dirs like .git or .hidden fail the role name regex."""
        echo_dir = tmp_path / "echoes"
        (echo_dir / ".hidden").mkdir(parents=True)
        (echo_dir / ".hidden" / "MEMORY.md").write_text(
            "## Inscribed — Hidden (2026-01-01)\nContent"
        )
        (echo_dir / "visible").mkdir(parents=True)
        (echo_dir / "visible" / "MEMORY.md").write_text(
            "## Inscribed — Visible (2026-01-01)\nContent"
        )

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 1
        assert entries[0]["role"] == "visible"

    def test_nested_subdirectories_not_traversed(self, tmp_path):
        """Only top-level role dirs are scanned, not nested subdirs."""
        echo_dir = tmp_path / "echoes"
        (echo_dir / "role1" / "subdir").mkdir(parents=True)
        (echo_dir / "role1" / "MEMORY.md").write_text(
            "## Inscribed — Top level (2026-01-01)\nContent"
        )
        (echo_dir / "role1" / "subdir" / "MEMORY.md").write_text(
            "## Inscribed — Nested (2026-01-01)\nShould be ignored"
        )

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 1
        assert entries[0]["tags"] == "Top level"

    def test_multiple_entries_per_role(self, tmp_path):
        """A single role's MEMORY.md can contain multiple entries."""
        echo_dir = tmp_path / "echoes"
        (echo_dir / "reviewer").mkdir(parents=True)
        (echo_dir / "reviewer" / "MEMORY.md").write_text(textwrap.dedent("""\
            ## Inscribed — First (2026-01-01)
            Content A

            ## Etched — Second (2026-01-02)
            Content B

            ## Traced — Third (2026-01-03)
            Content C
        """))

        entries = discover_and_parse(str(echo_dir))
        assert len(entries) == 3
        assert all(e["role"] == "reviewer" for e in entries)
