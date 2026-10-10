import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_fun00765c40_wheel_register_alias_pe.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00765c40_wheel_register_alias_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_765c40_wheel_register_alias", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_upstreams(tmp_path, module):
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
                    "fun00765c40_exact_hdvehicle_carrier_handoff_complete": True,
                },
            }
        ),
        encoding="utf-8",
    )
    wheel = tmp_path / "wheel.json"
    wheel.write_text(
        json.dumps(
            {
                "format": module.WHEEL_PROOF_FORMAT,
                "ready": True,
                "authority": {
                    "retail_executable_sha256": module.PE_SHA256,
                    "callee_entry": "0x00752fa0",
                },
                "caller_join": {
                    "caller": "FUN_00765c40",
                    "call_site": "0x00765ec1",
                    "receiver_first": "HDVehicle+0x400",
                    "receiver_count": 4,
                    "receiver_stride": "0x0a80",
                },
                "callee_side_effect_surface_closed": True,
            }
        ),
        encoding="utf-8",
    )
    return handoff, wheel


def test_pinned_four_wheel_alias_reaches_slot3_without_escape():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00765c40WheelRegisterAliasClosure/1"
    assert data["root_capture"] == {
        "alias": "ESI=HDVehicle",
        "input_receiver": "HDVehicle",
        "instruction": "mov esi,ecx",
        "site": "0x00765c5f",
    }
    loop = data["wheel_loop"]
    assert loop["receiver_offsets"] == ["+0x400", "+0x0e80", "+0x1900", "+0x2380"]
    assert loop["selected_slot3_iteration"] == 3
    assert loop["selected_slot3_receiver"] == "HDVehicle+0x2380"
    assert loop["exact_receiver_pointer_store_found"] is False
    assert loop["exact_receiver_pointer_push_found"] is False
    callee = data["callee"]
    assert callee["leaf"] is True
    assert callee["direct_call_count"] == 0
    assert callee["selected_slot3_vehicle_relative_writes"] == [
        "+0x2d78 dword",
        "+0x2d80 qword",
    ]
    assert callee["selected_target_overlap"] is False


def test_global_alias_and_writer_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["fun00765c40_four_wheel_register_alias_subset_complete"] is True
    assert gates["fun00765c40_selected_slot3_register_alias_reached"] is True
    assert gates["fun00765c40_selected_slot3_pointer_escape_found"] is False
    assert gates["fun00752fa0_selected_slot3_writer_found"] is False
    assert gates["other_fun00765c40_derived_aliases_ruled_out"] is False
    assert gates["machine_register_alias_storage_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_synthetic_exact_machine_surfaces_reproduce_pinned_contract(monkeypatch, tmp_path):
    module = load_module()
    handoff, wheel = write_upstreams(tmp_path, module)
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"synthetic")

    surfaces = {
        module.CAPTURE_START: dict(module.CAPTURE_ANCHORS),
        module.LOOP_START: dict(module.LOOP_ANCHORS),
        module.CALLEE_START: dict(module.CALLEE_ANCHORS),
    }
    monkeypatch.setattr(module, "sha256", lambda path: module.PE_SHA256)
    monkeypatch.setattr(
        module,
        "disassemble",
        lambda executable, start, stop, objdump: dict(surfaces[start]),
    )

    got = module.analyze(executable, handoff, wheel)
    expected = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert got == expected


def test_new_instruction_in_wheel_alias_window_fails_closed(monkeypatch, tmp_path):
    module = load_module()
    handoff, wheel = write_upstreams(tmp_path, module)
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"synthetic")

    capture = dict(module.CAPTURE_ANCHORS)
    loop = dict(module.LOOP_ANCHORS)
    loop[0x00765EC4] = "mov DWORD PTR [eax],ecx"
    callee = dict(module.CALLEE_ANCHORS)
    monkeypatch.setattr(module, "sha256", lambda path: module.PE_SHA256)
    monkeypatch.setattr(
        module,
        "disassemble",
        lambda executable, start, stop, objdump: (
            capture if start == module.CAPTURE_START else loop if start == module.LOOP_START else callee
        ),
    )

    with pytest.raises(ValueError, match="instruction-address surface drift"):
        module.analyze(executable, handoff, wheel)
