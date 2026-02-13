"""Unit tests for checkpoint validation and migration.

Tests the checkpoint_validator module against v1, v3, and v4 fixtures
to verify schema validation, migration logic, and artifact integrity checks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from helpers.checkpoint_validator import (
    ORCHESTRATOR_ONLY,
    PHASE_ORDER,
    VALID_STATUSES,
    migrate_checkpoint,
    validate_checkpoint,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def v1_checkpoint() -> dict:
    return json.loads((FIXTURES_DIR / "checkpoint_v1.json").read_text())


@pytest.fixture
def v3_checkpoint() -> dict:
    return json.loads((FIXTURES_DIR / "checkpoint_v3.json").read_text())


@pytest.fixture
def v4_checkpoint() -> dict:
    return json.loads((FIXTURES_DIR / "checkpoint_v4.json").read_text())


# ---------------------------------------------------------------------------
# Schema validation — v4
# ---------------------------------------------------------------------------

class TestValidateV4:
    """Tests for a valid v4 checkpoint."""

    def test_valid_checkpoint_passes(self, v4_checkpoint: dict) -> None:
        report = validate_checkpoint(v4_checkpoint)
        assert report.valid is True
        assert report.schema_version == 4

    def test_all_phases_present(self, v4_checkpoint: dict) -> None:
        report = validate_checkpoint(v4_checkpoint)
        for phase in PHASE_ORDER:
            assert phase in report.phase_statuses

    def test_completed_phase_count(self, v4_checkpoint: dict) -> None:
        report = validate_checkpoint(v4_checkpoint)
        # v4 fixture has all phases completed except plan_refine (skipped)
        completed = sum(1 for s in report.phase_statuses.values() if s == "completed")
        assert completed >= 8

    def test_no_errors(self, v4_checkpoint: dict) -> None:
        report = validate_checkpoint(v4_checkpoint)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_convergence_valid(self, v4_checkpoint: dict) -> None:
        report = validate_checkpoint(v4_checkpoint)
        # Should not flag convergence errors for valid v4
        conv_errors = [i for i in report.issues if "convergence" in i.message.lower()]
        assert len(conv_errors) == 0


# ---------------------------------------------------------------------------
# Schema validation — errors
# ---------------------------------------------------------------------------

class TestValidateErrors:
    """Tests for various validation error conditions."""

    def test_wrong_schema_version(self) -> None:
        cp = {
            "id": "arc-123",
            "schema_version": 2,
            "session_nonce": "aabbccddeeff",
            "phases": {},
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        assert report.valid is False
        assert any("schema_version" in i.message for i in report.issues)

    def test_missing_id(self) -> None:
        cp = {
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER},
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        assert report.valid is False
        assert any("id" in i.message.lower() for i in report.issues)

    def test_bad_nonce_length(self) -> None:
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "short",
            "phases": {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER},
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        assert report.valid is False
        assert any("nonce" in i.message.lower() for i in report.issues)

    def test_arc_style_nonce_accepted(self) -> None:
        """Arc generates nonces like 'arc1770998459' (arc + timestamp)."""
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "arc1770998459",
            "phases": {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER},
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        nonce_issues = [i for i in report.issues if "nonce" in i.message.lower()]
        assert len(nonce_issues) == 0, f"Arc-style nonce should be accepted: {nonce_issues}"

    def test_missing_phase(self) -> None:
        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        del phases["gap_analysis"]
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        assert report.valid is False
        assert any("gap_analysis" in i.message for i in report.issues)

    def test_invalid_status(self) -> None:
        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["work"]["status"] = "running"  # invalid
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        assert report.valid is False
        assert any("running" in i.message for i in report.issues)

    def test_missing_convergence(self) -> None:
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER},
        }
        report = validate_checkpoint(cp)
        assert report.valid is False
        assert any("convergence" in i.message.lower() for i in report.issues)

    def test_missing_phase_fields(self) -> None:
        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["forge"] = {"status": "completed"}  # missing artifact, artifact_hash, team_name
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        assert report.valid is False
        assert any("Missing fields" in i.message for i in report.issues)


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------

class TestValidateWarnings:
    """Tests for non-fatal warning conditions."""

    def test_orchestrator_phase_with_team(self) -> None:
        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["gap_analysis"]["team_name"] = "arc-gap-team"
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert any("orchestrator" in w.message.lower() for w in warnings)

    def test_max_rounds_exceeds_limit(self) -> None:
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER},
            "convergence": {"round": 0, "max_rounds": 5, "history": []},
        }
        report = validate_checkpoint(cp)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert any("max_rounds" in w.message for w in warnings)

    def test_unexpected_extra_phase(self) -> None:
        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["unknown_phase"] = {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None}
        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }
        report = validate_checkpoint(cp)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert any("unexpected" in w.message.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Artifact integrity
# ---------------------------------------------------------------------------

class TestArtifactChecks:
    """Tests for artifact file existence and hash verification."""

    def test_artifact_exists_check(self, tmp_path: Path) -> None:
        # Create a fake workspace with an artifact
        artifact_dir = tmp_path / "tmp" / "arc" / "arc-123"
        artifact_dir.mkdir(parents=True)
        artifact = artifact_dir / "enriched-plan.md"
        artifact.write_text("# Plan content")

        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["forge"] = {
            "status": "completed",
            "artifact": "tmp/arc/arc-123/enriched-plan.md",
            "artifact_hash": None,
            "team_name": "arc-forge-team",
        }

        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }

        report = validate_checkpoint(cp, workspace=tmp_path)
        assert report.artifact_checks.get("forge") is True

    def test_artifact_missing_check(self, tmp_path: Path) -> None:
        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["forge"] = {
            "status": "completed",
            "artifact": "tmp/arc/arc-123/nonexistent.md",
            "artifact_hash": None,
            "team_name": "arc-forge-team",
        }

        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }

        report = validate_checkpoint(cp, workspace=tmp_path)
        assert report.artifact_checks.get("forge") is False
        assert report.valid is False

    def test_hash_with_sha256_prefix(self, tmp_path: Path) -> None:
        """Arc stores hashes as 'sha256:<hex>' — validator must strip prefix."""
        artifact_dir = tmp_path / "tmp" / "arc" / "arc-123"
        artifact_dir.mkdir(parents=True)
        artifact = artifact_dir / "enriched-plan.md"
        content = "# Plan content with hash test"
        artifact.write_text(content)
        expected_hex = hashlib.sha256(content.encode()).hexdigest()

        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["forge"] = {
            "status": "completed",
            "artifact": "tmp/arc/arc-123/enriched-plan.md",
            "artifact_hash": f"sha256:{expected_hex}",
            "team_name": "arc-forge-team",
        }

        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }

        report = validate_checkpoint(cp, workspace=tmp_path)
        assert report.hash_checks.get("forge") is True
        assert report.valid is True

    def test_hash_without_prefix_still_works(self, tmp_path: Path) -> None:
        """Bare hex hashes (no prefix) should also match."""
        artifact_dir = tmp_path / "tmp" / "arc" / "arc-123"
        artifact_dir.mkdir(parents=True)
        artifact = artifact_dir / "enriched-plan.md"
        content = "# Bare hash test"
        artifact.write_text(content)
        expected_hex = hashlib.sha256(content.encode()).hexdigest()

        phases = {p: {"status": "pending", "artifact": None, "artifact_hash": None, "team_name": None} for p in PHASE_ORDER}
        phases["forge"] = {
            "status": "completed",
            "artifact": "tmp/arc/arc-123/enriched-plan.md",
            "artifact_hash": expected_hex,
            "team_name": "arc-forge-team",
        }

        cp = {
            "id": "arc-123",
            "schema_version": 4,
            "session_nonce": "aabbccddeeff",
            "phases": phases,
            "convergence": {"round": 0, "max_rounds": 2, "history": []},
        }

        report = validate_checkpoint(cp, workspace=tmp_path)
        assert report.hash_checks.get("forge") is True
        assert report.valid is True


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

class TestMigration:
    """Tests for checkpoint schema migration."""

    def test_v1_to_v4(self, v1_checkpoint: dict) -> None:
        migrated = migrate_checkpoint(v1_checkpoint)
        assert migrated["schema_version"] == 4
        # Should have all 10 phases
        for phase in PHASE_ORDER:
            assert phase in migrated["phases"], f"Missing phase after migration: {phase}"

    def test_v1_adds_missing_phases(self, v1_checkpoint: dict) -> None:
        migrated = migrate_checkpoint(v1_checkpoint)
        # These phases should be added with "skipped" status
        assert migrated["phases"]["plan_refine"]["status"] == "skipped"
        assert migrated["phases"]["verification"]["status"] == "skipped"
        assert migrated["phases"]["verify_mend"]["status"] == "skipped"
        assert migrated["phases"]["gap_analysis"]["status"] == "skipped"

    def test_v1_adds_convergence(self, v1_checkpoint: dict) -> None:
        migrated = migrate_checkpoint(v1_checkpoint)
        assert "convergence" in migrated
        assert migrated["convergence"]["round"] == 0
        assert migrated["convergence"]["max_rounds"] == 2
        assert migrated["convergence"]["history"] == []

    def test_v3_to_v4(self, v3_checkpoint: dict) -> None:
        migrated = migrate_checkpoint(v3_checkpoint)
        assert migrated["schema_version"] == 4
        assert "gap_analysis" in migrated["phases"]
        assert migrated["phases"]["gap_analysis"]["status"] == "skipped"

    def test_v3_preserves_existing_phases(self, v3_checkpoint: dict) -> None:
        migrated = migrate_checkpoint(v3_checkpoint)
        # Original phases should be preserved
        assert migrated["phases"]["forge"]["status"] == "completed"
        assert migrated["phases"]["plan_review"]["status"] == "completed"
        assert migrated["phases"]["work"]["status"] == "pending"

    def test_v4_no_change(self, v4_checkpoint: dict) -> None:
        migrated = migrate_checkpoint(v4_checkpoint)
        assert migrated["schema_version"] == 4
        # Should be identical (deep copy)
        assert migrated == v4_checkpoint

    def test_migration_does_not_mutate_input(self, v1_checkpoint: dict) -> None:
        original = json.dumps(v1_checkpoint)
        migrate_checkpoint(v1_checkpoint)
        assert json.dumps(v1_checkpoint) == original

    def test_migrated_v1_validates(self, v1_checkpoint: dict) -> None:
        """After migration, the checkpoint should pass v4 validation."""
        migrated = migrate_checkpoint(v1_checkpoint)
        report = validate_checkpoint(migrated)
        assert report.valid is True


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Verify that module constants match arc.md expectations."""

    def test_phase_order_has_10_phases(self) -> None:
        assert len(PHASE_ORDER) == 10

    def test_phase_order_sequence(self) -> None:
        assert PHASE_ORDER[0] == "forge"
        assert PHASE_ORDER[4] == "work"
        assert PHASE_ORDER[5] == "gap_analysis"
        assert PHASE_ORDER[6] == "code_review"
        assert PHASE_ORDER[9] == "audit"

    def test_orchestrator_only_phases(self) -> None:
        assert ORCHESTRATOR_ONLY == {"plan_refine", "verification", "gap_analysis", "verify_mend"}

    def test_valid_statuses(self) -> None:
        expected = {"pending", "in_progress", "completed", "failed", "skipped", "timeout", "cancelled"}
        assert VALID_STATUSES == expected
