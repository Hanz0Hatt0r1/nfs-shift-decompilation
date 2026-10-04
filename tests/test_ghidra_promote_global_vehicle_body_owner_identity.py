from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools" / "ghidra" / "promote_global_vehicle_body_owner_identity.py"
    )
    spec = importlib.util.spec_from_file_location(
        "promote_global_vehicle_body_owner_identity", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _blocked(m):
    return {
        "format": m.FORMAT,
        "inputs": {},
        "identity_join": {
            "global_vehicle_address": m.GLOBAL_VEHICLE_ADDRESS,
            "global_vehicle_component_base_identity_ready": True,
            "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven": False,
            "BODY_array_owner_is_global_vehicle_base": False,
            "main_chassis_BODY_selected": True,
            "main_chassis_BODY_name": "body",
            "main_chassis_BODY_index": 0,
            "global_vehicle_BODY_owner_identity_ready": False,
            "evidence_state": "blocked",
        },
        "handoff": {
            "outer_receiver_to_BODY_owner_continuity_proven": False,
            "vehicle_BODY_selection_ready": False,
            "selected_BODY_index": None,
            "phase698_positive_selection_admissible": False,
            "phase700_runtime_handoff_admissible": False,
            "phase703_update_child_equality_gate_required": False,
            "phase703_gate_rewrite_ready": False,
            "vehicle_world_transform_ready": False,
            "critical_next_join": "FUN_00765470 entry ECX -> FUN_007b2270 BODY-array owner ECX",
        },
        "blockers": [{"id": "half-step-entry-receiver-to-BODY-array-owner"}],
        "scope": {
            "update_child_pointer_equals_global_vehicle_base_proven": False,
            "update_child_pointer_equality_required": False,
            "BODY_array_owner_pointer_equals_global_vehicle_base_proven": False,
            "dynamic_BODY_pose_to_VHF_composition_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def _field(m):
    return {
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
    }


def test_promotes_field_edge_to_positive_body_zero_handoff(tmp_path: Path):
    m = _module()
    blocked = _write(tmp_path / "blocked.json", _blocked(m))
    field = _write(tmp_path / "field.json", _field(m))

    report = m.promote_global_vehicle_body_owner_identity(blocked, field)

    assert report["format"] == "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
    join = report["identity_join"]
    assert join["global_vehicle_address"] == "0x00c13700"
    assert join["half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven"] is False
    assert join["half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven"] is True
    assert join["BODY_array_owner_is_global_vehicle_base"] is False
    assert join["BODY_array_owner_pointer_loaded_from_global_vehicle_base"] is True
    assert join["BODY_array_owner_pointer_field_offset"] == "0x339c"
    assert join["global_vehicle_BODY_owner_identity_ready"] is True
    handoff = report["handoff"]
    assert handoff["outer_receiver_to_BODY_owner_continuity_proven"] is True
    assert handoff["vehicle_BODY_selection_ready"] is True
    assert handoff["selected_BODY_index"] == 0
    assert handoff["phase698_positive_selection_admissible"] is True
    assert handoff["phase700_runtime_handoff_admissible"] is True
    assert handoff["phase703_update_child_equality_gate_required"] is False
    assert handoff["phase703_gate_rewrite_ready"] is True
    assert report["blockers"] == []


def test_rejects_field_proof_that_reintroduces_pointer_equality(tmp_path: Path):
    m = _module()
    field_value = _field(m)
    field_value["machine_edge"]["entry_receiver_equals_call_receiver_pointer"] = True
    with pytest.raises(ValueError, match="incorrectly claims pointer equality"):
        m.promote_global_vehicle_body_owner_identity(
            _write(tmp_path / "blocked.json", _blocked(m)),
            _write(tmp_path / "field.json", field_value),
        )


def test_rejects_wrong_owner_field_offset(tmp_path: Path):
    m = _module()
    field_value = _field(m)
    field_value["machine_edge"]["BODY_owner_pointer_field_offset"] = "0x33a0"
    with pytest.raises(ValueError, match="field offset drift"):
        m.promote_global_vehicle_body_owner_identity(
            _write(tmp_path / "blocked.json", _blocked(m)),
            _write(tmp_path / "field.json", field_value),
        )


def test_rejects_blocked_identity_that_preclaims_selection(tmp_path: Path):
    m = _module()
    blocked_value = _blocked(m)
    blocked_value["handoff"]["selected_BODY_index"] = 0
    with pytest.raises(ValueError, match="preclaims BODY index"):
        m.promote_global_vehicle_body_owner_identity(
            _write(tmp_path / "blocked.json", blocked_value),
            _write(tmp_path / "field.json", _field(m)),
        )
