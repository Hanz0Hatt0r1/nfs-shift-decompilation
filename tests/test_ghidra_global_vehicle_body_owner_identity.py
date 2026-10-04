from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_global_vehicle_body_owner_identity.py"


def _module():
    spec = importlib.util.spec_from_file_location("global_vehicle_body_owner_identity", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _global(m, tmp_path: Path) -> Path:
    return _write(
        tmp_path / "global.json",
        {
            "format": m.GLOBAL_FORMAT,
            "identity_join": {
                "outer_update_receiver_address": "0x00c13700",
                "runtime_component_vehicle_base_address": "0x00c13700",
                "same_numeric_address": True,
                "global_outer_receiver_is_vehicle_component_base": True,
            },
            "handoff": {
                "global_vehicle_component_base_identity_ready": True,
                "update_child_to_vehicle_base_equality_required": False,
                "update_child_to_vehicle_base_equality_proven": False,
                "outer_receiver_to_BODY_owner_continuity_proven": False,
                "vehicle_BODY_selection_ready": False,
                "phase698_positive_selection_admissible": False,
            },
            "scope": {"BODY_array_owner_equals_global_vehicle_base_proven": False},
        },
    )


def _chassis(m, tmp_path: Path) -> Path:
    return _write(
        tmp_path / "chassis.json",
        {
            "format": m.CHASSIS_FORMAT,
            "selection": {
                "main_chassis_BODY_selected": True,
                "selected_BODY_name": "body",
                "selected_BODY_index": 0,
            },
            "handoff": {
                "main_chassis_BODY_selected": True,
                "main_chassis_BODY_index": 0,
                "vehicle_BODY_selection_ready": False,
                "phase698_positive_selection_admissible": False,
            },
        },
    )


def _receiver(m, tmp_path: Path, *, positive: bool) -> Path:
    origins = ["entry:ECX"] if positive else ["unknown:ECX@0x007657b2:call-clobber"]
    blockers = [] if positive else [{"id": "body-loop-receiver-provenance", "evidence_state": "ambiguous"}]
    return _write(
        tmp_path / "receiver.json",
        {
            "format": m.RECEIVER_FORMAT,
            "analysis": {
                "receiver_origins_before_body_loop_call": origins,
                "receiver_origin_cardinality": 1,
                "receiver_equals_half_step_entry_ECX_on_all_reachable_paths": positive,
                "receiver_provenance_ambiguous": not positive,
            },
            "handoff": {
                "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven": positive,
                "global_vehicle_to_BODY_owner_composition_ready": positive,
                "phase703_gate_rewrite_ready": positive,
                "phase698_positive_selection_admissible_by_this_artifact_alone": False,
            },
            "blockers": blockers,
        },
    )


def _field(m, tmp_path: Path) -> Path:
    return _write(
        tmp_path / "field.json",
        {
            "format": m.FIELD_FORMAT,
            "machine_edge": {
                "entry_receiver_to_BODY_owner_pointer_field_edge_proven": True,
                "entry_receiver_equals_call_receiver_pointer": False,
                "BODY_owner_pointer_field_offset": m.BODY_OWNER_FIELD_OFFSET,
                "BODY_owner_pointer_expression": "dword ptr [entry:ECX + 0x339c]",
            },
            "handoff": {
                "half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven": True,
                "BODY_array_owner_pointer_field_offset": m.BODY_OWNER_FIELD_OFFSET,
                "global_vehicle_to_BODY_owner_composition_ready": True,
                "phase703_gate_rewrite_ready": True,
                "phase698_positive_selection_admissible_by_this_artifact_alone": False,
            },
            "blockers": [],
        },
    )


def test_positive_receiver_composes_global_vehicle_to_chassis_body_zero(tmp_path: Path):
    m = _module()
    report = m.build_global_vehicle_body_owner_identity(
        _global(m, tmp_path), _receiver(m, tmp_path, positive=True), _chassis(m, tmp_path)
    )
    join = report["identity_join"]
    assert report["format"] == "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
    assert join["global_vehicle_address"] == "0x00c13700"
    assert join["BODY_array_owner_is_global_vehicle_base"] is True
    assert join["BODY_array_owner_pointer_loaded_from_global_vehicle_base"] is False
    assert join["main_chassis_BODY_index"] == 0
    assert join["global_vehicle_BODY_owner_identity_ready"] is True
    assert report["handoff"]["selected_BODY_index"] == 0
    assert report["handoff"]["phase700_runtime_handoff_admissible"] is True
    assert report["blockers"] == []


def test_retail_field_edge_composes_without_pointer_equality(tmp_path: Path):
    m = _module()
    report = m.build_global_vehicle_body_owner_identity(
        _global(m, tmp_path), _field(m, tmp_path), _chassis(m, tmp_path)
    )
    join = report["identity_join"]
    assert join["half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven"] is False
    assert join["half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven"] is True
    assert join["BODY_array_owner_is_global_vehicle_base"] is False
    assert join["BODY_array_owner_pointer_loaded_from_global_vehicle_base"] is True
    assert join["BODY_array_owner_pointer_field_offset"] == "0x339c"
    assert join["global_vehicle_BODY_owner_identity_ready"] is True
    assert join["evidence_state"] == "proven-composed-static-field"
    handoff = report["handoff"]
    assert handoff["outer_receiver_to_BODY_owner_continuity_proven"] is True
    assert handoff["vehicle_BODY_selection_ready"] is True
    assert handoff["selected_BODY_index"] == 0
    assert handoff["phase698_positive_selection_admissible"] is True
    assert handoff["phase700_runtime_handoff_admissible"] is True
    assert handoff["phase703_update_child_equality_gate_required"] is False
    assert report["scope"]["BODY_array_owner_pointer_equals_global_vehicle_base_proven"] is False
    assert report["scope"]["BODY_array_owner_pointer_field_edge_proven"] is True
    assert report["blockers"] == []


def test_negative_receiver_keeps_phase698_fail_closed(tmp_path: Path):
    m = _module()
    report = m.build_global_vehicle_body_owner_identity(
        _global(m, tmp_path), _receiver(m, tmp_path, positive=False), _chassis(m, tmp_path)
    )
    assert report["identity_join"]["global_vehicle_BODY_owner_identity_ready"] is False
    assert report["handoff"]["vehicle_BODY_selection_ready"] is False
    assert report["handoff"]["selected_BODY_index"] is None
    assert report["handoff"]["phase698_positive_selection_admissible"] is False
    assert [row["id"] for row in report["blockers"]] == ["half-step-entry-receiver-to-BODY-array-owner"]


def test_inconsistent_positive_receiver_flags_are_rejected(tmp_path: Path):
    m = _module()
    receiver = _receiver(m, tmp_path, positive=True)
    value = json.loads(receiver.read_text(encoding="utf-8"))
    value["handoff"]["phase703_gate_rewrite_ready"] = False
    receiver.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="handoff flags disagree"):
        m.build_global_vehicle_body_owner_identity(_global(m, tmp_path), receiver, _chassis(m, tmp_path))


def test_field_edge_rejects_pointer_equality_or_offset_drift(tmp_path: Path):
    m = _module()
    field = _field(m, tmp_path)
    value = json.loads(field.read_text(encoding="utf-8"))
    value["machine_edge"]["entry_receiver_equals_call_receiver_pointer"] = True
    field.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="incorrectly claims pointer equality"):
        m.build_global_vehicle_body_owner_identity(_global(m, tmp_path), field, _chassis(m, tmp_path))

    field = _field(m, tmp_path)
    value = json.loads(field.read_text(encoding="utf-8"))
    value["machine_edge"]["BODY_owner_pointer_field_offset"] = "0x33a0"
    field.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="field offset drift"):
        m.build_global_vehicle_body_owner_identity(_global(m, tmp_path), field, _chassis(m, tmp_path))


def test_global_or_chassis_preclaim_drift_fails_closed(tmp_path: Path):
    m = _module()
    global_path = _global(m, tmp_path)
    value = json.loads(global_path.read_text(encoding="utf-8"))
    value["handoff"]["outer_receiver_to_BODY_owner_continuity_proven"] = True
    global_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="preclaims BODY-owner continuity"):
        m.build_global_vehicle_body_owner_identity(global_path, _field(m, tmp_path), _chassis(m, tmp_path))

    global_path = _global(m, tmp_path)
    chassis_path = _chassis(m, tmp_path)
    value = json.loads(chassis_path.read_text(encoding="utf-8"))
    value["selection"]["selected_BODY_index"] = 9
    chassis_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="chassis BODY index drift"):
        m.build_global_vehicle_body_owner_identity(global_path, _field(m, tmp_path), chassis_path)


def test_local_provenance_artifact_cannot_admit_phase698_by_itself(tmp_path: Path):
    m = _module()
    receiver = _receiver(m, tmp_path, positive=True)
    value = json.loads(receiver.read_text(encoding="utf-8"))
    value["handoff"]["phase698_positive_selection_admissible_by_this_artifact_alone"] = True
    receiver.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="claims Phase 698 admission alone"):
        m.build_global_vehicle_body_owner_identity(_global(m, tmp_path), receiver, _chassis(m, tmp_path))

    field = _field(m, tmp_path)
    value = json.loads(field.read_text(encoding="utf-8"))
    value["handoff"]["phase698_positive_selection_admissible_by_this_artifact_alone"] = True
    field.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="incorrectly admits Phase 698 alone"):
        m.build_global_vehicle_body_owner_identity(_global(m, tmp_path), field, _chassis(m, tmp_path))
