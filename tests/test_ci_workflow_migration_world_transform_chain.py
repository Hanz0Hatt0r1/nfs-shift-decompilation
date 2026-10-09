import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "coordination/ci_migrations/native_physics_world_transform_chain_698_707.json"
STABLE = ROOT / ".github/workflows/native-physics-world-transform-chain.yml"


def test_world_transform_chain_migration_is_superset_and_complete():
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
    for target in payload["parity"]["native_targets"]:
        assert target in text
    for name in payload["parity"]["ctest_names"]:
        assert name in text
    for contract in payload["parity"]["evidence_contracts"]:
        assert contract in text
    for fmt in payload["parity"]["native_reports"]:
        assert fmt in text
    for marker in payload["parity"]["semantic_gate_markers"]:
        assert marker in text

    assert "workflow_dispatch:" in text
    assert "cancel-in-progress: true" in text


def test_superseded_world_transform_phase_workflows_are_removed():
    payload = json.loads(MIGRATION.read_text(encoding="utf-8"))

    assert STABLE.exists()
    for row in payload["superseded_workflows"]:
        assert not (ROOT / row["path"]).exists()
