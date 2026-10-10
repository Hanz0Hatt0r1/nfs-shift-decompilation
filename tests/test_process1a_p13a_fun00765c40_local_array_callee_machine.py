import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1a_fun00765c40_local_array_callee_machine.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_fun00765c40_local_array_callee_machine_closure.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1a_local_array_machine", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_machine_verifier_pins_bodies_calls_and_cursor_sites():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.BODY_SPECS == {
        "FUN_007afd20": (0x007AFD20, 49, "2e93cc7574546ce67474eac98cfb1b41aad12ff83b23738ae69754b2f7d021cf"),
        "FUN_007baa70": (0x007BAA70, 121, "eed5416afe216f33c24d437e8ed50a7773c2fee316a4f1c841ef0e6bbd5e817e"),
        "FUN_00747b90": (0x00747B90, 36, "e2c7ab1cffe9f74b40aa5706acf142958fcb2fc37c5427550f9266960410155d"),
        "FUN_007aefb0": (0x007AEFB0, 83, "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29"),
    }
    assert module.EXPECTED_CALL_TARGETS == {
        0x007660BE: 0x007AFD20,
        0x00766365: 0x007BAA70,
        0x007663F6: 0x007AEFB0,
        0x0076646A: 0x00747B90,
        0x007664F2: 0x007BAA70,
        0x007AFD2C: 0x007AEFB0,
    }
    assert module.EXPECTED_BYTES[0x00766081] == "8dbec8350000"
    assert module.EXPECTED_BYTES[0x007663CD] == "8d8ee0360000"
    assert module.EXPECTED_BYTES[0x007663EA] == "0550fdffff"
    assert module.EXPECTED_BYTES[0x00766188] == "8b55ecdd12"


def test_all_four_local_array_lifetimes_are_bounded():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13AFun00765c40LocalArrayCalleeMachineClosure/1"

    a3430 = data["array_3430"]
    assert a3430["identity"] == "HDVehicle+0x3430 + iteration*0x18, 12 iterations"
    assert a3430["callee_path"] == ["FUN_007afd20", "FUN_007aefb0"]
    assert a3430["pointer_store_or_back_reference_found"] is False
    assert a3430["wheel_root_reconstruction_found"] is False

    a35c8 = data["array_35c8"]
    assert a35c8["identity"] == "HDVehicle+0x35c8 + iteration*0x4, 12 iterations"
    assert a35c8["callee"] == "FUN_007baa70"
    assert a35c8["receiver_relative_writes"] == ["+0x48", "+0x50", "+0x58", "+0x60", "+0x68", "+0x70"]
    assert a35c8["absolute_write_span_over_iterations"] == "HDVehicle+0x3610..+0x3664"
    assert a35c8["direct_call_count"] == 0

    a35f8 = data["array_35f8"]
    assert a35f8["identity"] == "HDVehicle+0x35f8 + iteration*0x8, 12 iterations"
    assert a35f8["callee_receives_cursor"] is False

    a36e0 = data["array_36e0"]
    assert a36e0["identity"] == "HDVehicle+0x36e0 + iteration*0x18, 4 iterations"
    assert a36e0["derived_data_source"] == "cursor-0x2b0 => HDVehicle+0x3430 + iteration*0x18"
    assert a36e0["derived_data_callee"] == "FUN_007aefb0"
    assert a36e0["cursor_data_callee"] == "FUN_00747b90"
    assert a36e0["later_FUN_007baa70_receiver"] == "chassis BODY [HDVehicle+0x33a0], not +0x36e0 cursor"


def test_local_arrays_do_not_promote_global_alias_gates():
    adj = load_evidence()["adjudication"]
    assert adj["p13a_fun00765c40_local_array_callee_lifetimes_complete"] is True
    assert adj["p13a_fun00765c40_local_array_pointer_escape_found"] is False
    assert adj["p13a_fun00765c40_local_array_wheel_root_reconstruction_found"] is False
    assert adj["p13a_fun00765c40_local_array_selected_slot_writer_found"] is False
    assert adj["other_derived_aliases_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["callbacks_and_indirect_entry_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
