import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_fun00765c40_wheel_interior_alias_pe.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00765c40_wheel_interior_alias_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_765c40_wheel_interior_alias", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_wheel_678_alias_is_stack_local_and_target_disjoint():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00765c40WheelInteriorAliasClosure/1"
    alias = data["wheel_interior_alias"]
    assert alias["per_wheel_offset"] == "+0x678"
    assert alias["vehicle_relative_offsets"] == [
        "+0x0a78",
        "+0x14f8",
        "+0x1f78",
        "+0x29f8",
    ]
    assert alias["selected_slot3_receiver"] == "HDVehicle+0x29f8 = wheel+0x678"
    assert alias["stack_local_slot"] == "[ebp-0xc]"
    assert alias["persistent_or_nonlocal_pointer_store_found"] is False
    assert alias["selected_slot3_write_offsets"] == [
        "HDVehicle+0x29f0 = wheel+0x670 qword",
        "HDVehicle+0x29f8 = wheel+0x678 qword",
    ]
    assert alias["selected_target_overlap"] is False


def test_child_load_and_transient_push_do_not_escape():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    child = data["child_pointer_load"]
    assert child["expression"] == "[wheel+0x678-0x258] = [wheel+0x420]"
    assert child["selected_slot3_child_field"] == "HDVehicle+0x27a0 = wheel+0x420"
    assert child["child_pointer_forward_to_call_found"] is False
    assert child["child_pointer_store_found"] is False

    transient = data["transient_stack_alias"]
    assert transient["site"] == "0x00765da4"
    assert transient["instruction"] == "push ecx"
    assert transient["overwrite_site"] == "0x00765dc9"
    assert transient["overwrite_instruction"] == "fstp DWORD PTR [esp]"
    assert transient["next_call_site"] == "0x00765dcc"
    assert transient["pointer_reaches_callee_stack_argument"] is False
    assert transient["persistent_escape"] is False

    scalar = data["scalar_call_ecx"]
    assert scalar["caller_value"] == "ECX=ESI=HDVehicle"
    assert scalar["callee_incoming_ecx_read_before_overwrite"] is False
    assert scalar["callee_ecx_overwrite_site"] == "0x00758adb"
    assert scalar["hdvehicle_pointer_consumed_as_object_receiver"] is False


def test_global_alias_and_writer_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["fun00765c40_wheel_678_interior_alias_subset_complete"] is True
    assert gates["fun00765c40_selected_slot3_interior_alias_reached"] is True
    assert gates["fun00765c40_selected_slot3_interior_persistent_escape_found"] is False
    assert gates["fun00765c40_selected_slot3_child_pointer_forward_found"] is False
    assert gates["fun00765c40_transient_stack_pointer_copy_found"] is True
    assert gates["fun00765c40_transient_stack_pointer_copy_reaches_callee"] is False
    assert gates["fun00758ad0_consumes_hdvehicle_receiver"] is False
    assert gates["other_fun00765c40_derived_aliases_ruled_out"] is False
    assert gates["machine_register_alias_storage_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_machine_window_drift_fails_closed():
    module = load_module()
    with pytest.raises(ValueError, match="machine-window drift"):
        module.verify_window("branch_a", [])


def test_unproven_handoff_fails_closed(tmp_path):
    module = load_module()
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps(
            {
                "format": module.HANDOFF_FORMAT,
                "ready": True,
                "authority": {"retail_executable_sha256": module.PE_SHA256},
                "carrier": {
                    "function": "FUN_00765c40",
                    "entry": "0x00765c40",
                    "receiver_domain": "HDVehicle",
                },
                "selected_slot3": {"absolute_target": "HDVehicle+0x28b8"},
                "adjudication": {
                    "fun00765c40_exact_hdvehicle_carrier_handoff_complete": False,
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="handoff is not complete"):
        module.load_handoff(handoff)
