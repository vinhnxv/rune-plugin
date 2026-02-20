"""Unit tests for TOME parser and FINDING marker extraction.

Tests the tome_parser module against sample TOME files to verify
regex patterns, nonce validation, severity counting, and sanitization.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers.tome_parser import (
    DEDUP_PRIORITY,
    FINDING_PATTERN,
    SPOT_FINDING_PATTERN,
    Finding,
    count_findings,
    is_spot_clean,
    parse_spot_findings,
    parse_tome,
    sanitize_description,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tome_content() -> str:
    return (FIXTURES_DIR / "tome_sample.md").read_text()


@pytest.fixture
def injected_tome() -> str:
    return (FIXTURES_DIR / "tome_injected.md").read_text()


@pytest.fixture
def spot_content() -> str:
    return (FIXTURES_DIR / "spot_findings.md").read_text()


# ---------------------------------------------------------------------------
# Basic TOME parsing
# ---------------------------------------------------------------------------

class TestParseTome:
    """Tests for the main parse_tome function."""

    def test_total_findings(self, tome_content: str) -> None:
        report = parse_tome(tome_content)
        assert report.total_findings == 9

    def test_severity_counts(self, tome_content: str) -> None:
        report = parse_tome(tome_content)
        assert report.p1_count == 2
        assert report.p2_count == 3
        assert report.p3_count == 4

    def test_files_affected(self, tome_content: str) -> None:
        report = parse_tome(tome_content)
        assert "src/db/query.py" in report.files_affected
        assert "src/config.py" in report.files_affected
        assert "src/transforms.py" in report.files_affected
        assert len(report.files_affected) == 8

    def test_prefixes_seen(self, tome_content: str) -> None:
        report = parse_tome(tome_content)
        assert report.prefixes_seen == {"SEC", "QUAL", "DOC", "BACK"}

    def test_finding_details(self, tome_content: str) -> None:
        report = parse_tome(tome_content)
        sec001 = next(f for f in report.findings if f.id == "SEC-001")
        assert sec001.file == "src/db/query.py"
        assert sec001.line == 42
        assert sec001.severity == "P1"
        assert sec001.prefix == "SEC"

    def test_all_valid_with_correct_nonce(self, tome_content: str) -> None:
        report = parse_tome(tome_content, expected_nonce="a1b2c3d4e5f6")
        assert report.valid_findings == 9
        assert report.invalid_nonce_count == 0

    def test_all_invalid_with_wrong_nonce(self, tome_content: str) -> None:
        report = parse_tome(tome_content, expected_nonce="wrong_nonce_x")
        assert report.invalid_nonce_count == 9
        assert report.valid_findings == 0


# ---------------------------------------------------------------------------
# Nonce injection detection
# ---------------------------------------------------------------------------

class TestNonceValidation:
    """Tests for nonce-based prompt injection detection."""

    def test_injected_nonce_detection(self, injected_tome: str) -> None:
        report = parse_tome(injected_tome, expected_nonce="a1b2c3d4e5f6")
        assert report.total_findings == 5
        assert report.invalid_nonce_count == 2  # INJECTED-001, INJECTED-002

    def test_valid_findings_count_with_injection(self, injected_tome: str) -> None:
        report = parse_tome(injected_tome, expected_nonce="a1b2c3d4e5f6")
        # 2 valid nonce + valid severity (SEC-001 P1, QUAL-001 P3)
        # BAD-001 has valid nonce but invalid severity "CRITICAL"
        assert report.valid_findings == 2

    def test_invalid_severity_count(self, injected_tome: str) -> None:
        report = parse_tome(injected_tome, expected_nonce="a1b2c3d4e5f6")
        assert report.invalid_severity_count == 1  # BAD-001 has "CRITICAL"

    def test_no_nonce_check_when_not_provided(self, injected_tome: str) -> None:
        report = parse_tome(injected_tome)
        # Without expected_nonce, all are "valid nonce"
        assert report.invalid_nonce_count == 0
        # But BAD-001 still has invalid severity
        # valid_findings = those with valid nonce AND valid severity
        assert report.valid_findings == 4  # all except BAD-001


# ---------------------------------------------------------------------------
# SPOT findings
# ---------------------------------------------------------------------------

class TestSpotFindings:
    """Tests for SPOT:FINDING and SPOT:CLEAN markers."""

    def test_parse_spot_findings(self, spot_content: str) -> None:
        findings = parse_spot_findings(spot_content)
        assert len(findings) == 2

    def test_spot_finding_details(self, spot_content: str) -> None:
        findings = parse_spot_findings(spot_content)
        p1 = next(f for f in findings if f.severity == "P1")
        assert p1.file == "src/parser.py"
        assert p1.line == 92

        p2 = next(f for f in findings if f.severity == "P2")
        assert p2.file == "src/config.py"
        assert p2.line == 18

    def test_is_spot_clean(self, spot_content: str) -> None:
        assert is_spot_clean(spot_content) is True

    def test_is_not_spot_clean(self) -> None:
        assert is_spot_clean("no clean marker here") is False

    def test_empty_spot_findings(self) -> None:
        assert parse_spot_findings("nothing here") == []


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

class TestRegexPatterns:
    """Direct tests for the regex patterns."""

    def test_finding_pattern_captures_all_groups(self) -> None:
        marker = '<!-- RUNE:FINDING nonce="abc123def456" id="SEC-001" file="src/app.py" line="42" severity="P1" -->'
        match = FINDING_PATTERN.search(marker)
        assert match is not None
        assert match.group("nonce") == "abc123def456"
        assert match.group("id") == "SEC-001"
        assert match.group("file") == "src/app.py"
        assert match.group("line") == "42"
        assert match.group("severity") == "P1"

    def test_finding_pattern_with_extra_whitespace(self) -> None:
        marker = '<!--  RUNE:FINDING  nonce="abc"  id="X-1"  file="f.py"  line="1"  severity="P3"  -->'
        match = FINDING_PATTERN.search(marker)
        assert match is not None
        assert match.group("id") == "X-1"

    def test_spot_finding_pattern(self) -> None:
        marker = '<!-- SPOT:FINDING file="src/foo.py" line="10" severity="P2" -->'
        match = SPOT_FINDING_PATTERN.search(marker)
        assert match is not None
        assert match.group("file") == "src/foo.py"
        assert match.group("line") == "10"
        assert match.group("severity") == "P2"

    def test_pattern_does_not_match_partial(self) -> None:
        # Missing severity attribute
        marker = '<!-- RUNE:FINDING nonce="abc" id="X-1" file="f.py" line="1" -->'
        match = FINDING_PATTERN.search(marker)
        assert match is None


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------

class TestSanitization:
    """Tests for description sanitization (matches arc.md generateMiniTome)."""

    def test_strips_html_comments(self) -> None:
        desc = "Before <!-- hidden --> After"
        assert sanitize_description(desc) == "Before  After"

    def test_replaces_newlines(self) -> None:
        desc = "Line one\nLine two\r\nLine three"
        assert sanitize_description(desc) == "Line one Line two Line three"

    def test_truncates_to_max_length(self) -> None:
        desc = "A" * 1000
        assert len(sanitize_description(desc)) == 500

    def test_custom_max_length(self) -> None:
        desc = "A" * 100
        assert len(sanitize_description(desc, max_length=50)) == 50

    def test_empty_input(self) -> None:
        assert sanitize_description("") == ""

    def test_strips_multiline_html_comment(self) -> None:
        desc = "Before <!-- multi\nline\ncomment --> After"
        assert sanitize_description(desc) == "Before  After"


# ---------------------------------------------------------------------------
# Quick count
# ---------------------------------------------------------------------------

class TestCountFindings:
    """Tests for the count_findings shortcut."""

    def test_count_matches_parse(self, tome_content: str) -> None:
        assert count_findings(tome_content) == parse_tome(tome_content).total_findings

    def test_count_zero_for_no_markers(self) -> None:
        assert count_findings("Just some text with no markers") == 0


# ---------------------------------------------------------------------------
# Finding priority
# ---------------------------------------------------------------------------

class TestFindingPriority:
    """Tests for the dedup priority system."""

    def test_sec_highest_priority(self) -> None:
        f = Finding(nonce="x", id="SEC-001", file="f.py", line=1, severity="P1", prefix="SEC")
        assert f.priority == 0

    def test_front_lowest_known_priority(self) -> None:
        f = Finding(nonce="x", id="FRONT-001", file="f.py", line=1, severity="P3", prefix="FRONT")
        assert f.priority == 4

    def test_cdx_lowest_known_priority(self) -> None:
        f = Finding(nonce="x", id="CDX-001", file="f.py", line=1, severity="P2", prefix="CDX")
        assert f.priority == 5

    def test_unknown_prefix_gets_99(self) -> None:
        f = Finding(nonce="x", id="CUSTOM-001", file="f.py", line=1, severity="P2", prefix="CUSTOM")
        assert f.priority == 99

    def test_dedup_priority_order(self) -> None:
        assert DEDUP_PRIORITY["SEC"] < DEDUP_PRIORITY["BACK"]
        assert DEDUP_PRIORITY["BACK"] < DEDUP_PRIORITY["DOC"]
        assert DEDUP_PRIORITY["DOC"] < DEDUP_PRIORITY["QUAL"]
        assert DEDUP_PRIORITY["QUAL"] < DEDUP_PRIORITY["FRONT"]
        assert DEDUP_PRIORITY["FRONT"] < DEDUP_PRIORITY["CDX"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case handling."""

    def test_empty_content(self) -> None:
        report = parse_tome("")
        assert report.total_findings == 0
        assert report.findings == []

    def test_non_numeric_line(self) -> None:
        marker = '<!-- RUNE:FINDING nonce="abc" id="X-1" file="f.py" line="notanumber" severity="P1" -->'
        report = parse_tome(marker)
        assert report.findings[0].line == 0  # fallback

    def test_finding_rate_by_severity(self, tome_content: str) -> None:
        report = parse_tome(tome_content)
        rates = report.finding_rate_by_severity
        assert rates == {"P1": 2, "P2": 3, "P3": 4}
