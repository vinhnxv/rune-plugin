"""Markdown report generator for Rune Arc test results.

Combines checkpoint validation, TOME analysis, code quality scores,
and pipeline timing into a comprehensive evaluation report.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .checkpoint_validator import CheckpointReport, PHASE_ORDER
from .code_evaluator import QualityReport
from .tome_parser import TomeReport


# Display names for phases
PHASE_DISPLAY = {
    "forge": "1.   FORGE",
    "plan_review": "2.   PLAN REVIEW",
    "plan_refine": "2.5  PLAN REFINEMENT",
    "verification": "2.7  VERIFICATION",
    "work": "5.   WORK",
    "gap_analysis": "5.5  GAP ANALYSIS",
    "code_review": "6.   CODE REVIEW",
    "mend": "7.   MEND",
    "verify_mend": "7.5  VERIFY MEND",
    "audit": "8.   AUDIT",
}


def generate_report(
    *,
    challenge_name: str = "unknown",
    arc_duration_seconds: float = 0.0,
    checkpoint_report: CheckpointReport | None = None,
    tome_report: TomeReport | None = None,
    quality_report: QualityReport | None = None,
    gap_analysis_text: str | None = None,
    convergence_info: dict | None = None,
    run_output: str | None = None,
) -> str:
    """Generate a comprehensive Markdown evaluation report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    duration_min = arc_duration_seconds / 60

    lines: list[str] = []
    lines.append("# Rune Arc Test Report\n")
    lines.append(f"**Date**: {now}")
    lines.append(f"**Challenge**: {challenge_name}")
    lines.append(f"**Arc Duration**: {duration_min:.1f} minutes")
    lines.append("")

    # --- Overall Verdict ---
    verdict = _compute_verdict(checkpoint_report, quality_report)
    lines.append(f"## Verdict: {verdict}")
    lines.append("")

    # --- Pipeline Status ---
    lines.append("## Pipeline Status\n")
    if checkpoint_report:
        lines.append("| Phase | Status |")
        lines.append("|-------|--------|")
        for phase in PHASE_ORDER:
            display = PHASE_DISPLAY.get(phase, phase)
            status = checkpoint_report.phase_statuses.get(phase, "MISSING")
            icon = _status_icon(status)
            lines.append(f"| {display} | {icon} {status} |")
        lines.append("")
        lines.append(f"**Completed**: {checkpoint_report.completed_phases}/{checkpoint_report.total_phases} phases")
        lines.append("")
    else:
        lines.append("*No checkpoint data available*\n")

    # --- Checkpoint Integrity ---
    lines.append("## Checkpoint Integrity\n")
    if checkpoint_report:
        lines.append(f"- Schema version: {checkpoint_report.schema_version}")
        lines.append(f"- Valid: {'Yes' if checkpoint_report.valid else 'No'}")

        if checkpoint_report.artifact_checks:
            all_exist = all(checkpoint_report.artifact_checks.values())
            lines.append(f"- All artifacts exist: {'Yes' if all_exist else 'No'}")

        if checkpoint_report.hash_checks:
            all_match = all(checkpoint_report.hash_checks.values())
            lines.append(f"- All hashes match: {'Yes' if all_match else 'No'}")

        if checkpoint_report.issues:
            lines.append("")
            lines.append("### Issues\n")
            for issue in checkpoint_report.issues:
                icon = "!!!" if issue.severity == "error" else "?"
                phase_str = f" [{issue.phase}]" if issue.phase else ""
                lines.append(f"- {icon}{phase_str} {issue.message}")
        lines.append("")
    else:
        lines.append("*No checkpoint data available*\n")

    # --- Code Quality ---
    lines.append("## Code Quality\n")
    if quality_report:
        lines.append(f"**Score: {quality_report.total_score:.1f}/{quality_report.max_score:.1f}**")
        lines.append(f"**Threshold: {quality_report.pass_threshold}**")
        lines.append(f"**Result: {'PASS' if quality_report.passed else 'FAIL'}**\n")

        lines.append("| Dimension | Score | Weight | Weighted | Details |")
        lines.append("|-----------|-------|--------|----------|---------|")
        for d in quality_report.dimensions:
            lines.append(f"| {d.name} | {d.score:.1f}/10 | {d.weight:.0%} | {d.weighted:.2f} | {d.details} |")
        lines.append("")
    else:
        lines.append("*No quality evaluation available*\n")

    # --- TOME Analysis ---
    lines.append("## TOME Analysis\n")
    if tome_report:
        lines.append(f"- Total findings: {tome_report.total_findings}")
        lines.append(f"  - P1 (Critical): {tome_report.p1_count}")
        lines.append(f"  - P2 (High): {tome_report.p2_count}")
        lines.append(f"  - P3 (Medium): {tome_report.p3_count}")
        lines.append(f"- Valid findings: {tome_report.valid_findings}")
        lines.append(f"- Invalid nonce: {tome_report.invalid_nonce_count}")
        lines.append(f"- Files affected: {len(tome_report.files_affected)}")
        lines.append(f"- Ash prefixes: {', '.join(sorted(tome_report.prefixes_seen)) or 'none'}")
        lines.append("")
    else:
        lines.append("*No TOME data available*\n")

    # --- Gap Analysis ---
    if gap_analysis_text:
        lines.append("## Gap Analysis\n")
        # Extract summary table from gap analysis markdown
        in_summary = False
        for line in gap_analysis_text.split("\n"):
            if "## Summary" in line:
                in_summary = True
                continue
            if in_summary:
                if line.startswith("##"):
                    break
                if line.strip():
                    lines.append(line)
        lines.append("")

    # --- Convergence ---
    if convergence_info:
        lines.append("## Convergence Gate\n")
        lines.append(f"- Rounds: {convergence_info.get('round', 0) + 1} mend pass(es)")
        lines.append(f"- Max rounds: {convergence_info.get('max_rounds', 2)}")
        history = convergence_info.get("history", [])
        if history:
            lines.append("")
            lines.append("| Round | Findings Before | Findings After | Verdict |")
            lines.append("|-------|-----------------|----------------|---------|")
            for entry in history:
                lines.append(
                    f"| {entry.get('round', '?')} | {entry.get('findings_before', '?')} "
                    f"| {entry.get('findings_after', '?')} | {entry.get('verdict', '?')} |"
                )
        lines.append("")

    # --- Raw output snippet ---
    if run_output:
        lines.append("## Arc Output (last 2000 chars)\n")
        snippet = run_output[-2000:]
        # Generate a dynamic fence that is longer than any backtick run in the content
        max_backtick_run = 0
        current_run = 0
        for ch in snippet:
            if ch == "`":
                current_run += 1
                if current_run > max_backtick_run:
                    max_backtick_run = current_run
            else:
                current_run = 0
        fence = "`" * max(3, max_backtick_run + 1)
        lines.append(fence)
        lines.append(snippet)
        lines.append(fence + "\n")

    return "\n".join(lines)


def _status_icon(status: str) -> str:
    return {
        "completed": "[x]",
        "skipped": "[-]",
        "pending": "[ ]",
        "failed": "[!]",
        "cancelled": "[~]",
        "timeout": "[!]",
    }.get(status, "[?]")


def _compute_verdict(
    checkpoint_report: CheckpointReport | None,
    quality_report: QualityReport | None,
) -> str:
    issues = []

    if checkpoint_report and not checkpoint_report.valid:
        issues.append("checkpoint integrity failed")
    if checkpoint_report and checkpoint_report.completed_phases < checkpoint_report.total_phases:
        incomplete = [
            p for p, s in checkpoint_report.phase_statuses.items()
            if s in ("failed", "cancelled", "timeout", "pending", "in_progress")
        ]
        if incomplete:
            issues.append(f"phases incomplete: {', '.join(incomplete)}")

    if quality_report and not quality_report.passed:
        issues.append(f"quality score {quality_report.total_score:.1f} < {quality_report.pass_threshold}")

    if not issues:
        return "PASS"
    return f"FAIL ({'; '.join(issues)})"


def write_report(report_text: str, output_path: Path) -> Path:
    """Write report to a file and return the path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text)
    return output_path
