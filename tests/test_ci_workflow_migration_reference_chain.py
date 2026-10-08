import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "coordination/ci_migrations/native_physics_reference_chain_747_748.json"
STABLE = ROOT / ".github/workflows/native-physics-reference-chain.yml"
OLD_747 = ROOT / ".github/workflows/native-physics-phase747.yml"
OLD_748 = ROOT / ".github/workflows/native-physics-phase748.yml"


def test_reference_chain_migration_is_superset_and_complete():
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


def test_superseded_reference_chain_phase_workflows_are_removed():
    assert STABLE.exists()
    assert not OLD_747.exists()
    assert not OLD_748.exists()
