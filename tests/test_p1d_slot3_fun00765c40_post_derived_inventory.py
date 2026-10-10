import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_fun00765c40_post_derived_inventory_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_fun00765c40_post_derived_inventory.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_post_derived_inventory", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_machine_windows_are_pinned():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00765c40PostDerivedInventory/1"
    assert set(data["scope"]) == {"manager_6730", "local_12", "local_4", "a62940", "a628a0"}
    for row in data["scope"].values():
        assert row["instruction_count"] > 0
        assert row["decoded_byte_count"] > 0
        assert len(row["machine_bytes_sha256"]) == 64


def test_6730_runtime_backpointer_is_distinct_from_slot3():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    manager = data["families"]["hdvehicle_6730"]
    gates = data["adjudication"]
    assert manager["selected_slot3_pointer_identity"] is False
    assert manager["runtime_created_node_backpointer_stores"] == [
        "0x00a62a20 [node+0x24]=HDVehicle+0x6730",
        "0x00a62a63 [node+0x34]=HDVehicle+0x6730",
    ]
    assert manager["fun00a628a0_receiver_value_store_or_push_found"] is False
    assert gates["fun00765c40_hdvehicle_6730_runtime_backpointer_store_found"] is True
    assert gates["fun00765c40_hdvehicle_6730_is_selected_slot3_alias"] is False


def test_post_derived_array_families_remain_fail_closed_at_callees():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    arrays12 = data["families"]["hdvehicle_local_arrays_12"]
    arrays4 = data["families"]["hdvehicle_local_array_4"]
    assert arrays12["iteration_count"] == 12
    assert arrays12["selected_slot3_pointer_identity"] is False
    assert arrays12["callee_lifetime_fully_closed"] is False
    assert arrays4["iteration_count"] == 4
    assert arrays4["selected_slot3_pointer_identity"] is False
    assert arrays4["callee_lifetime_fully_closed"] is False


def test_global_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["fun00765c40_post_derived_family_inventory_complete"] is True
    assert gates["fun00765c40_post_derived_selected_slot3_alias_found"] is False
    assert gates["other_fun00765c40_derived_aliases_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_tool_contract_matches_evidence_shape():
    module = load_module()
    assert module.FORMAT == "SHIFT.P1D.Slot3Fun00765c40PostDerivedInventory/1"
    assert len(module.WINDOWS) == 5
    assert 0x00A62A20 in module.ANCHORS
    assert 0x00A62A63 in module.ANCHORS
