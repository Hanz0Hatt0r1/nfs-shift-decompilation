import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "tools" / "ghidra" / "build_global_vehicle_component_base_identity.py"
    spec = importlib.util.spec_from_file_location("global_vehicle_component_base_identity", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _outer(m):
    return {
        "format": m.OUTER_FORMAT,
        "source": {"sha256": m.SOURCE_SHA256},
        "ghidra": {"executable_md5": m.PE_MD5},
        "outer_update": {
            "function": m.OUTER_UPDATE,
            "receiver_at_callsites": "DAT_00c13700",
        },
    }


def _frontier(m):
    return {
        "format": m.VEHICLE_FRONTIER_FORMAT,
        "pointer_domains": {
            "update_child_receiver": {"source_rule": "*record + 0x340"},
            "outer_physics_receiver": {"source_expression": "&DAT_00c13700"},
        },
        "scope": {
            "normal_outer_call_forwards_vehicle_receiver_pointer": False,
            "outer_receiver_to_BODY_owner_pointer_continuity_proven": False,
        },
    }


def _callsite(m):
    return {
        "format": m.CALLSITE_FORMAT,
        "source_snapshot_sha256": m.SOURCE_SHA256,
        "executable_md5": m.PE_MD5,
        "runtime_component_callsite": {
            "caller": "0x0079a050",
            "caller_name": m.RUNTIME_CALLER,
            "call_address": f"0x{m.RUNTIME_CALL:08x}",
            "return_address": f"0x{m.RUNTIME_RETURN:08x}",
            "callee_wrapper": "0x00757d20",
            "callee_core": f"0x{m.MUTATION_CORE:08x}",
            "caller_class": "runtime-threshold-slot",
            "vehicle_pointer_register_at_core_entry": "ECX",
            "component_offset_register_at_core_entry": "EAX",
            "vehicle_base_address": f"0x{m.GLOBAL_VEHICLE_ADDRESS:08x}",
            "component_base_offset": "0x400",
            "component_stride": "0xa80",
            "component_count": 4,
            "component_offset_rule": "slot * 0xa80",
        },
        "vehicle_layout_join": {
            "solver_setup_function": m.SOLVER_SETUP,
            "component_fields_same_layout_proven": True,
        },
        "scope": {
            "global_vehicle_component_base_address_proven": True,
            "update_child_pointer_equals_global_vehicle_base_proven": False,
            "body_array_owner_equals_global_vehicle_base_proven": False,
        },
    }


def _fixture(tmp_path: Path, m):
    outer = tmp_path / "outer.json"
    frontier = tmp_path / "frontier.json"
    callsite = tmp_path / "callsite.json"
    _write(outer, _outer(m))
    _write(frontier, _frontier(m))
    _write(callsite, _callsite(m))
    return outer, frontier, callsite


def test_same_global_address_proves_vehicle_component_base_without_update_child_relabel(tmp_path):
    m = _module()
    outer, frontier, callsite = _fixture(tmp_path, m)
    report = m.build_global_vehicle_component_base_identity(outer, frontier, callsite)

    assert report["format"] == "SHIFT.GlobalVehicleComponentBaseIdentity/1"
    join = report["identity_join"]
    assert join["outer_update_receiver_address"] == "0x00c13700"
    assert join["runtime_component_vehicle_base_address"] == "0x00c13700"
    assert join["same_numeric_address"] is True
    assert join["global_outer_receiver_is_vehicle_component_base"] is True
    assert join["evidence_state"] == "proven-composed-static"

    child = report["update_child_role"]
    assert child["pointer_forwarded_to_outer_update"] is False
    assert child["pointer_identity_with_global_vehicle_base"] == "unknown"
    assert child["pointer_identity_required_to_prove_global_vehicle_base"] is False

    assert report["next_instruction_targets"] == [m.HALF_STEP, m.BODY_ARRAY_LOOP]
    assert report["handoff"]["global_vehicle_component_base_identity_ready"] is True
    assert report["handoff"]["outer_receiver_to_BODY_owner_continuity_proven"] is False
    assert report["handoff"]["vehicle_BODY_selection_ready"] is False
    assert report["handoff"]["phase698_positive_selection_admissible"] is False


def test_outer_receiver_address_drift_fails_closed(tmp_path):
    m = _module()
    outer, frontier, callsite = _fixture(tmp_path, m)
    value = json.loads(outer.read_text())
    value["outer_update"]["receiver_at_callsites"] = "DAT_00c13710"
    _write(outer, value)
    with pytest.raises(ValueError, match="outer receiver address drift"):
        m.build_global_vehicle_component_base_identity(outer, frontier, callsite)


def test_phase633_global_vehicle_address_drift_fails_closed(tmp_path):
    m = _module()
    outer, frontier, callsite = _fixture(tmp_path, m)
    value = json.loads(callsite.read_text())
    value["runtime_component_callsite"]["vehicle_base_address"] = "0x00c14700"
    _write(callsite, value)
    with pytest.raises(ValueError, match="global vehicle base address drift"):
        m.build_global_vehicle_component_base_identity(outer, frontier, callsite)


def test_update_child_equality_preclaim_is_rejected(tmp_path):
    m = _module()
    outer, frontier, callsite = _fixture(tmp_path, m)
    value = json.loads(callsite.read_text())
    value["scope"]["update_child_pointer_equals_global_vehicle_base_proven"] = True
    _write(callsite, value)
    with pytest.raises(ValueError, match="preclaims update-child equality"):
        m.build_global_vehicle_component_base_identity(outer, frontier, callsite)


def test_committed_phase633_callsite_evidence_keeps_body_owner_open(tmp_path):
    m = _module()
    evidence = json.loads(
        (ROOT / "evidence" / "global_vehicle_component_callsite_phase633.json").read_text()
    )
    assert evidence["format"] == m.CALLSITE_FORMAT
    assert evidence["runtime_component_callsite"]["vehicle_base_address"] == "0x00c13700"
    assert evidence["scope"]["global_vehicle_component_base_address_proven"] is True
    assert evidence["scope"]["update_child_pointer_equals_global_vehicle_base_proven"] is False
    assert evidence["scope"]["body_array_owner_equals_global_vehicle_base_proven"] is False
