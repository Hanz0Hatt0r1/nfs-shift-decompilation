import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
FROZEN_MAX_NATIVE_PHYSICS_PHASE_WORKFLOW = 753
PATTERN = re.compile(r"native-physics-phase(\d+)\.yml$")


def _phase_workflows():
    rows = []
    for path in sorted(WORKFLOWS.glob("native-physics-phase*.yml")):
        match = PATTERN.fullmatch(path.name)
        assert match, f"unexpected phase workflow name: {path.name}"
        rows.append((int(match.group(1)), path.name))
    return rows


def test_historical_phase_workflow_set_is_frozen():
    rows = _phase_workflows()
    assert rows, "expected historical native-physics phase workflows"
    newest_phase, newest_name = max(rows)
    assert newest_phase <= FROZEN_MAX_NATIVE_PHYSICS_PHASE_WORKFLOW, (
        f"new phase-numbered workflow {newest_name} detected; add coverage to an existing "
        "stable workflow, pytest/CTest target, or matrix instead of creating another phase YAML"
    )


def test_new_stable_workflows_must_not_use_phase_numbering():
    for path in sorted(WORKFLOWS.glob("*.yml")):
        if path.name.startswith("native-physics-phase"):
            continue
        assert not re.search(r"phase\d+", path.name, re.IGNORECASE), (
            f"new stable workflow should describe a subsystem/gate, not a phase: {path.name}"
        )
