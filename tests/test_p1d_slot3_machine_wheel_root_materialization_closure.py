import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_machine_wheel_root_materialization_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_machine_wheel_root_materialization_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_wheel_root_materialization", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_four_wheel_layout_is_pinned():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3MachineWheelRootMaterializationClosure/1"
    assert data["wheel_layout"] == {
        "count": 4,
        "root_offsets": ["+0x400", "+0xe80", "+0x1900", "+0x2380"],
        "stride": "+0xa80",
    }


def test_fun00763570_loop_is_stack_local_and_four_wide():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["fun00763570_loop"]
    assert row["cursor_storage"] == "stack-local [EBP-0x4]"
    assert row["materialized_receivers"] == [
        "HDVehicle+0x400",
        "HDVehicle+0xe80",
        "HDVehicle+0x1900",
        "HDVehicle+0x2380",
    ]
    assert row["nonstack_wheel_root_store_found"] is False
    assert row["window"]["instruction_count"] == 12
    assert row["window"]["decoded_byte_count"] == 54
    assert row["window"]["machine_bytes_sha256"] == "30ae593298ee11283898a0397b527583fc232d3db7ac4f0db7a8578e6bf00333"


def test_fun00770e80_explicit_slot3_receiver_is_exact():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["fun00770e80_explicit"]
    assert [x["receiver"] for x in row["materializations"]] == [
        "HDVehicle+0x400",
        "HDVehicle+0xe80",
        "HDVehicle+0x1900",
        "HDVehicle+0x2380",
    ]
    slot3 = row["materializations"][-1]
    assert slot3["site"] == "0x00771177"
    assert slot3["calls"] == ["0x00771180"]
    assert slot3["selected_slot3"] is True
    assert row["wheel_root_push_count"] == 0
    assert row["wheel_root_nonstack_store_count"] == 0
    assert row["window"]["machine_bytes_sha256"] == "9007ea4422621778fa979ae4ca105faa85f1f03b792803da7f6d3b34d38c6534"


def test_global_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["known_hdvehicle_to_four_wheel_root_materialization_machine_subset_complete"] is True
    assert gates["selected_slot3_wheel_root_materialization_proven"] is True
    assert gates["selected_slot3_wheel_root_nonstack_persistence_found"] is False
    assert gates["selected_slot3_wheel_root_new_forward_beyond_closed_consumers_found"] is False
    assert gates["other_derived_alias_storage_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_tool_contract_matches_evidence():
    module = load_module()
    assert module.FORMAT == "SHIFT.P1D.Slot3MachineWheelRootMaterializationClosure/1"
    assert module.WHEEL_OFFSETS == [0x400, 0xE80, 0x1900, 0x2380]
