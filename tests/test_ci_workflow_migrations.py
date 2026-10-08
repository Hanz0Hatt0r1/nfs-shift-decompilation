import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_PATH = ROOT / "coordination" / "ci_workflow_migrations.json"


def _migrations():
    payload = json.loads(MIGRATIONS_PATH.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CIWorkflowMigrations/1"
    assert payload["version"] == 1
    return payload["migrations"]


def test_retired_workflows_are_replaced_with_stable_coverage():
    migrations = _migrations()
    assert migrations, "at least one workflow migration must be recorded"

    for migration in migrations:
        assert migration["status"] == "active"
        replacement = ROOT / migration["replacement"]
        assert replacement.is_file(), f"missing replacement workflow: {replacement}"
        workflow_text = replacement.read_text(encoding="utf-8")

        for retired in migration["retired_workflows"]:
            assert not (ROOT / retired).exists(), f"retired workflow still exists: {retired}"

        for regression in migration["python_regressions"]:
            assert regression in workflow_text, f"missing Python regression parity: {regression}"

        for target in migration["cmake_targets"]:
            assert target in workflow_text, f"missing native target parity: {target}"

        for ctest_name in migration["ctest_names"]:
            assert ctest_name in workflow_text, f"missing CTest parity: {ctest_name}"

        for report_format in migration["native_reports"]:
            assert report_format in workflow_text, f"missing native report parity: {report_format}"
