"""Unit tests for the Markdown report generator.

Tests the report_generator module to verify report structure,
verdict logic, and section rendering with various input combinations.
"""

from __future__ import annotations

import pytest

from helpers.checkpoint_validator import CheckpointReport, PHASE_ORDER
from helpers.code_evaluator import DimensionScore, QualityReport
from helpers.report_generator import (
    PHASE_DISPLAY,
    _compute_verdict,
    _status_icon,
    generate_report,
)
from helpers.tome_parser import TomeReport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def passing_checkpoint() -> CheckpointReport:
    """A fully valid checkpoint report."""
    report = CheckpointReport()
    report.schema_version = 4
    report.completed_phases = 9
    report.phase_statuses = {p: "completed" for p in PHASE_ORDER}
    report.phase_statuses["plan_refine"] = "skipped"
    return report


@pytest.fixture
def failing_checkpoint() -> CheckpointReport:
    """A checkpoint with validation errors."""
    report = CheckpointReport()
    report.schema_version = 4
    report.completed_phases = 6
    report.phase_statuses = {p: "completed" for p in PHASE_ORDER[:6]}
    report.phase_statuses["code_review"] = "failed"
    report.phase_statuses["mend"] = "pending"
    report.phase_statuses["verify_mend"] = "pending"
    report.phase_statuses["audit"] = "pending"
    report.add_error("code_review", "Phase failed with timeout")
    return report


@pytest.fixture
def passing_quality() -> QualityReport:
    report = QualityReport()
    report.dimensions = [
        DimensionScore("functional", 9.0, 0.30, "9/10 tests passed"),
        DimensionScore("linting", 8.0, 0.10, "2 violations"),
    ]
    report.total_score = 8.4
    return report


@pytest.fixture
def failing_quality() -> QualityReport:
    report = QualityReport()
    report.dimensions = [
        DimensionScore("functional", 4.0, 0.30, "4/10 tests passed"),
    ]
    report.total_score = 4.0
    return report


@pytest.fixture
def sample_tome_report() -> TomeReport:
    report = TomeReport()
    report.total_findings = 9
    report.p1_count = 2
    report.p2_count = 3
    report.p3_count = 4
    report.valid_findings = 9
    report.files_affected = {"src/a.py", "src/b.py"}
    report.prefixes_seen = {"SEC", "QUAL"}
    return report


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

class TestComputeVerdict:
    """Tests for the _compute_verdict function."""

    def test_pass_when_all_good(self, passing_checkpoint: CheckpointReport, passing_quality: QualityReport) -> None:
        assert _compute_verdict(passing_checkpoint, passing_quality) == "PASS"

    def test_fail_on_checkpoint_invalid(self, failing_checkpoint: CheckpointReport, passing_quality: QualityReport) -> None:
        verdict = _compute_verdict(failing_checkpoint, passing_quality)
        assert verdict.startswith("FAIL")
        assert "checkpoint" in verdict.lower()

    def test_fail_on_quality_score(self, passing_checkpoint: CheckpointReport, failing_quality: QualityReport) -> None:
        verdict = _compute_verdict(passing_checkpoint, failing_quality)
        assert verdict.startswith("FAIL")
        assert "quality" in verdict.lower()

    def test_fail_on_failed_phase(self, failing_checkpoint: CheckpointReport, failing_quality: QualityReport) -> None:
        verdict = _compute_verdict(failing_checkpoint, failing_quality)
        assert verdict.startswith("FAIL")
        assert "code_review" in verdict

    def test_pass_with_none_inputs(self) -> None:
        assert _compute_verdict(None, None) == "PASS"

    def test_pass_with_skipped_phases(self, passing_checkpoint: CheckpointReport) -> None:
        # Skipped phases should not trigger failure
        passing_checkpoint.phase_statuses["plan_refine"] = "skipped"
        verdict = _compute_verdict(passing_checkpoint, None)
        assert verdict == "PASS"


# ---------------------------------------------------------------------------
# Status icons
# ---------------------------------------------------------------------------

class TestStatusIcon:
    """Tests for status icon mapping."""

    def test_completed_icon(self) -> None:
        assert _status_icon("completed") == "[x]"

    def test_skipped_icon(self) -> None:
        assert _status_icon("skipped") == "[-]"

    def test_pending_icon(self) -> None:
        assert _status_icon("pending") == "[ ]"

    def test_failed_icon(self) -> None:
        assert _status_icon("failed") == "[!]"

    def test_unknown_icon(self) -> None:
        assert _status_icon("unknown") == "[?]"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

class TestGenerateReport:
    """Tests for the full report generation."""

    def test_report_has_header(self) -> None:
        report = generate_report(challenge_name="dataweaver")
        assert "# Rune Arc Test Report" in report

    def test_report_includes_challenge_name(self) -> None:
        report = generate_report(challenge_name="dataweaver")
        assert "dataweaver" in report

    def test_report_includes_duration(self) -> None:
        report = generate_report(arc_duration_seconds=600.0)
        assert "10.0 minutes" in report

    def test_report_includes_pipeline_table(self, passing_checkpoint: CheckpointReport) -> None:
        report = generate_report(checkpoint_report=passing_checkpoint)
        assert "Pipeline Status" in report
        assert "| Phase | Status |" in report
        for phase in PHASE_ORDER:
            display = PHASE_DISPLAY.get(phase, phase)
            assert display in report

    def test_report_includes_checkpoint_integrity(self, passing_checkpoint: CheckpointReport) -> None:
        report = generate_report(checkpoint_report=passing_checkpoint)
        assert "Checkpoint Integrity" in report
        assert "Schema version: 4" in report
        assert "Valid: Yes" in report

    def test_report_includes_quality(self, passing_quality: QualityReport) -> None:
        report = generate_report(quality_report=passing_quality)
        assert "Code Quality" in report
        assert "8.4" in report

    def test_report_includes_tome(self, sample_tome_report: TomeReport) -> None:
        report = generate_report(tome_report=sample_tome_report)
        assert "TOME Analysis" in report
        assert "P1 (Critical): 2" in report
        assert "P2 (High): 3" in report

    def test_report_includes_convergence(self) -> None:
        conv = {
            "round": 1,
            "max_rounds": 2,
            "history": [
                {"round": 0, "findings_before": 10, "findings_after": 3, "verdict": "retry"},
                {"round": 1, "findings_before": 3, "findings_after": 0, "verdict": "converged"},
            ],
        }
        report = generate_report(convergence_info=conv)
        assert "Convergence Gate" in report
        assert "2 mend pass(es)" in report
        assert "converged" in report

    def test_report_includes_raw_output(self) -> None:
        report = generate_report(run_output="Claude did stuff\nMore stuff")
        assert "Arc Output" in report
        assert "Claude did stuff" in report

    def test_report_no_data_graceful(self) -> None:
        """Report should render gracefully with all None inputs."""
        report = generate_report()
        assert "# Rune Arc Test Report" in report
        assert "No checkpoint data available" in report
        assert "No quality evaluation available" in report
        assert "No TOME data available" in report

    def test_report_gap_analysis_section(self) -> None:
        gap = "# Implementation Gap Analysis\n\n## Summary\n\n| Status | Count |\n|--------|-------|\n| ADDRESSED | 10 |\n| MISSING | 2 |\n\n## Details"
        report = generate_report(gap_analysis_text=gap)
        assert "Gap Analysis" in report
        assert "ADDRESSED" in report

    def test_full_report_with_all_sections(
        self,
        passing_checkpoint: CheckpointReport,
        passing_quality: QualityReport,
        sample_tome_report: TomeReport,
    ) -> None:
        """Full report with all data should include all sections."""
        report = generate_report(
            challenge_name="dataweaver",
            arc_duration_seconds=1200.0,
            checkpoint_report=passing_checkpoint,
            tome_report=sample_tome_report,
            quality_report=passing_quality,
            convergence_info={"round": 0, "max_rounds": 2, "history": []},
            run_output="Done",
        )
        assert "Verdict: PASS" in report
        assert "Pipeline Status" in report
        assert "Checkpoint Integrity" in report
        assert "Code Quality" in report
        assert "TOME Analysis" in report
        assert "Convergence Gate" in report
        assert "Arc Output" in report


# ---------------------------------------------------------------------------
# Phase display map
# ---------------------------------------------------------------------------

class TestPhaseDisplay:
    """Verify the display map covers all phases."""

    def test_all_phases_have_display(self) -> None:
        for phase in PHASE_ORDER:
            assert phase in PHASE_DISPLAY, f"Phase '{phase}' missing from PHASE_DISPLAY"

    def test_gap_analysis_display(self) -> None:
        assert "GAP ANALYSIS" in PHASE_DISPLAY["gap_analysis"]

    def test_display_includes_phase_number(self) -> None:
        assert "5.5" in PHASE_DISPLAY["gap_analysis"]
        assert "7.5" in PHASE_DISPLAY["verify_mend"]
