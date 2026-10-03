from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_chassis_body_identity_frontier.py"


def _module():
    spec = importlib.util.spec_from_file_location("bmw_chassis_identity", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _copy_json(source: Path, target: Path):
    value = json.loads(source.read_text(encoding="utf-8"))
    target.write_text(json.dumps(value), encoding="utf-8")
    return value


def test_retained_retail_topology_selects_body_zero_but_keeps_runtime_join_closed():
    m = _module()
    report = m.build_bmw_chassis_body_identity_frontier()
    assert report["format"] == "SHIFT.BMWChassisBodyIdentityFrontier/1"
    assert report["selection"] == {
        "role": "main-suspension/chassis BODY",
        "selected_BODY_name": "body",
        "selected_BODY_index": 0,
        "evidence_state": "proven-by-retail-constraint-topology",
        "main_chassis_BODY_selected": True,
    }
    proof = report["topology_proof"]
    assert proof["bar_count"] == 20
    assert proof["unique_BODY_incident_to_all_BARs"] == "body"
    assert proof["bar_endpoint_degrees"]["body"] == 20
    assert proof["bar_endpoint_degrees"]["fl_spindle"] == 5
    assert proof["bar_endpoint_degrees"]["fuel_tank"] == 0
    assert proof["body_name_plausibility_used_as_proof"] is False
    handoff = report["handoff"]
    assert handoff["main_chassis_BODY_selected"] is True
    assert handoff["main_chassis_BODY_index"] == 0
    assert handoff["rear_axle_BODY_index_required_for_chassis_selection"] is False
    assert handoff["update_child_to_vehicle_solver_base_continuity_proven"] is False
    assert handoff["vehicle_BODY_selection_ready"] is False
    assert handoff["phase698_positive_selection_admissible"] is False
    assert [row["id"] for row in report["blockers"]] == [
        "update-child-to-vehicle-solver-base-continuity"
    ]


def test_phase405_ordering_signature_drift_fails_closed(tmp_path: Path):
    m = _module()
    phase405 = tmp_path / "phase405.json"
    value = _copy_json(ROOT / m.DEFAULT_PHASE405, phase405)
    value["ordering"]["final_cost"] += 1
    phase405.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="ordering signature drift: final_cost"):
        m.build_bmw_chassis_body_identity_frontier(phase405_path=phase405)


def test_bar_topology_cannot_promote_nonunique_or_partial_central_body(tmp_path: Path):
    m = _module()
    topology = tmp_path / "topology.json"
    value = _copy_json(ROOT / m.DEFAULT_TOPOLOGY, topology)
    value["bar_topology"]["target_counts"]["fl_spindle"] = 4
    topology.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="BAR target count sum drift"):
        m.build_bmw_chassis_body_identity_frontier(topology_path=topology)


def test_selected_index_must_match_exact_phase404_body_order(tmp_path: Path):
    m = _module()
    topology = tmp_path / "topology.json"
    value = _copy_json(ROOT / m.DEFAULT_TOPOLOGY, topology)
    value["semantic_selection"]["body_index"] = 9
    topology.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="selected BODY index/order mismatch"):
        m.build_bmw_chassis_body_identity_frontier(topology_path=topology)


def test_cli_emits_machine_readable_fail_closed_frontier(tmp_path: Path):
    output = tmp_path / "frontier.json"
    completed = subprocess.run(
        [sys.executable, str(TOOL), "--json-out", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["selection"]["selected_BODY_index"] == 0
    assert report["handoff"]["vehicle_BODY_selection_ready"] is False
    assert "main chassis BODY: 0 (body)" in completed.stdout
