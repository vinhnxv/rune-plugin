"""TOME and FINDING marker parser.

Extracts structured findings from TOME markdown files by parsing
<!-- RUNE:FINDING ... --> markers. Validates nonces, severities,
and file references.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Regex for RUNE:FINDING markers
FINDING_PATTERN = re.compile(
    r'<!--\s*RUNE:FINDING\s+'
    r'nonce="(?P<nonce>[^"]+)"\s+'
    r'id="(?P<id>[^"]+)"\s+'
    r'file="(?P<file>[^"]+)"\s+'
    r'line="(?P<line>[^"]+)"\s+'
    r'severity="(?P<severity>[^"]+)"\s*'
    r'-->'
)

# Regex for SPOT:FINDING markers (Phase 7.5 verify_mend)
SPOT_FINDING_PATTERN = re.compile(
    r'<!--\s*SPOT:FINDING\s+'
    r'file="(?P<file>[^"]+)"\s+'
    r'line="(?P<line>[^"]+)"\s+'
    r'severity="(?P<severity>[^"]+)"\s*'
    r'-->'
)

SPOT_CLEAN_PATTERN = re.compile(r'<!--\s*SPOT:CLEAN\s*-->')

VALID_SEVERITIES = {"P1", "P2", "P3"}

# Dedup priority (lower = higher priority)
DEDUP_PRIORITY = {"SEC": 0, "BACK": 1, "DOM": 2, "DOC": 3, "QUAL": 4, "FRONT": 5}


@dataclass
class Finding:
    """A parsed RUNE:FINDING from a TOME."""

    nonce: str
    id: str
    file: str
    line: int
    severity: str
    prefix: str = ""
    description: str = ""
    valid_nonce: bool = True

    @property
    def priority(self) -> int:
        return DEDUP_PRIORITY.get(self.prefix, 99)


@dataclass
class SpotFinding:
    """A parsed SPOT:FINDING from a verify_mend spot-check."""

    file: str
    line: int
    severity: str
    description: str = ""


@dataclass
class TomeReport:
    """Analysis of a TOME file."""

    total_findings: int = 0
    p1_count: int = 0
    p2_count: int = 0
    p3_count: int = 0
    valid_findings: int = 0
    invalid_nonce_count: int = 0
    invalid_severity_count: int = 0
    findings: list[Finding] = field(default_factory=list)
    files_affected: set[str] = field(default_factory=set)
    prefixes_seen: set[str] = field(default_factory=set)

    @property
    def finding_rate_by_severity(self) -> dict[str, int]:
        return {"P1": self.p1_count, "P2": self.p2_count, "P3": self.p3_count}


def parse_tome(content: str, expected_nonce: str | None = None) -> TomeReport:
    """Parse a TOME markdown file and extract all RUNE:FINDING markers.

    Args:
        content: Full TOME markdown content.
        expected_nonce: If provided, findings with mismatched nonces are flagged.
    """
    report = TomeReport()

    for match in FINDING_PATTERN.finditer(content):
        nonce = match.group("nonce")
        finding_id = match.group("id")
        file = match.group("file")
        severity = match.group("severity")

        try:
            line = int(match.group("line"))
        except ValueError:
            line = 0

        # Extract prefix from finding ID (e.g., "SEC-001" → "SEC")
        prefix = finding_id.split("-")[0] if "-" in finding_id else ""

        valid_nonce = True
        if expected_nonce and nonce != expected_nonce:
            valid_nonce = False
            report.invalid_nonce_count += 1

        if severity not in VALID_SEVERITIES:
            report.invalid_severity_count += 1

        finding = Finding(
            nonce=nonce,
            id=finding_id,
            file=file,
            line=line,
            severity=severity,
            prefix=prefix,
            valid_nonce=valid_nonce,
        )

        report.findings.append(finding)
        report.total_findings += 1
        report.files_affected.add(file)
        if prefix:
            report.prefixes_seen.add(prefix)

        if valid_nonce and severity in VALID_SEVERITIES:
            report.valid_findings += 1

        if severity == "P1":
            report.p1_count += 1
        elif severity == "P2":
            report.p2_count += 1
        elif severity == "P3":
            report.p3_count += 1

    return report


def parse_spot_findings(content: str) -> list[SpotFinding]:
    """Parse SPOT:FINDING markers from a verify_mend spot-check output."""
    findings = []
    for match in SPOT_FINDING_PATTERN.finditer(content):
        try:
            line = int(match.group("line"))
        except ValueError:
            line = 0

        findings.append(SpotFinding(
            file=match.group("file"),
            line=line,
            severity=match.group("severity"),
        ))
    return findings


def is_spot_clean(content: str) -> bool:
    """Check if spot-check output contains SPOT:CLEAN marker."""
    return bool(SPOT_CLEAN_PATTERN.search(content))


def sanitize_description(desc: str, max_length: int = 500) -> str:
    """Sanitize a finding description (matches arc.md generateMiniTome logic).

    Strips HTML comments, replaces newlines, truncates.
    """
    sanitized = re.sub(r"<!--[\s\S]*?-->", "", desc)
    sanitized = re.sub(r"[\r\n]+", " ", sanitized)
    return sanitized[:max_length]


def count_findings(content: str) -> int:
    """Count total RUNE:FINDING markers in content (quick count without full parse)."""
    return len(FINDING_PATTERN.findall(content))
