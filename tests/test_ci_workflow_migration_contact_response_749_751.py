import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "coordination/ci_migrations/native_physics_contact_response_749_751.json"
STABLE = ROOT / ".github/workflows/native-physics-contact-response.yml"
OLD_749 = ROOT / ".github/workflows/native-physics-phase749.yml"
OLD_750 = ROOT / ".github/workflows/native-physics-phase750.yml"
OLD_751 = ROOT / ".github/workflows/native-physics-phase751.yml"


def test_contact_response_749_751_migration_is_superset_and_complete():
    payload = json.loads(MIGRATION.read_text(encoding="utf-8"))
    text = STABLE.read_text(encoding="utf-8")

    assert payload["format"] == "SHIFT.CIWorkflowMigration/1"
    assert payload["status"] == "ready"
    assert payload["coverage_policy"] == "superset"
    assert payload["semantic_gate_changes"] is False
    assert payload["provider_count_changes"] is False
    assert payload["trigger_policy"]["mode"] == "union"

    for test in payload["parity"]["python_tests"]:
        assert test in text
    for fmt in payload["parity"]["evidence_formats"]:
        assert fmt in text
    for target in payload["parity"]["native_targets"]:
        assert target in text
    for name in payload["parity"]["ctest_names"]:
        assert name in text
    for fmt in payload["parity"]["native_reports"]:
        assert fmt in text


def test_superseded_749_751_phase_workflows_are_removed_after_parity_transfer():
    assert STABLE.exists()
    assert not OLD_749.exists()
    assert not OLD_750.exists()
    assert not OLD_751.exists()
