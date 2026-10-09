import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "coordination/ci_migrations/native_physics_fun007afdd0_680_692.json"
STABLE = ROOT / ".github/workflows/native-physics-fun007afdd0-analysis.yml"
OLD_680 = ROOT / ".github/workflows/native-physics-phase680.yml"
OLD_692 = ROOT / ".github/workflows/native-physics-phase692.yml"


def test_fun007afdd0_workflow_migration_is_superset_and_complete():
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
    for runner in payload["parity"]["shell_syntax_checks"]:
        assert f"bash -n {runner}" in text
    for guard in payload["parity"]["static_guards"]:
        assert guard in text

    # Preserve the union of the old path filters so either analyzer family
    # continues to trigger the complete stable gate.
    for required_path in (
        "tools/ghidra/ShiftFunctionInstructionExporter.java",
        "tools/ghidra/analyze_fun_007afdd0_basis_rotation.py",
        "tools/ghidra/run_fun_007afdd0_basis_rotation.sh",
        "tools/ghidra/analyze_fun_007afdd0_scalar_provenance.py",
        "tools/ghidra/run_fun_007afdd0_scalar_provenance.sh",
        "docs/PHASE680_FUN_007AFDD0_STATIC_FREEZE.md",
        "docs/PHASE692_FUN_007AFDD0_SCALAR_PROVENANCE.md",
    ):
        assert required_path in text


def test_superseded_fun007afdd0_phase_workflows_are_removed():
    assert STABLE.exists()
    assert not OLD_680.exists()
    assert not OLD_692.exists()
