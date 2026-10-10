import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1a_slot01_fun00765c40_derived_alias_handoff.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_slot01_fun00765c40_derived_alias_handoff.json"
INPUTS = [
    ROOT / "evidence/p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json",
    ROOT / "evidence/p1d_slot3_fun00765c40_wheel_interior_alias_closure.json",
    ROOT / "evidence/p1d_slot3_fun00765c40_wheel_7a8_alias_closure.json",
    ROOT / "evidence/p1d_slot3_fun00765c40_post_derived_inventory.json",
]


def load_tool():
    spec = importlib.util.spec_from_file_location("p1a_fun00765c40_alias", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_handoff():
    module = load_tool()
    assert module.build(*[load(path) for path in INPUTS]) == load(EVIDENCE)


def test_slot0_slot1_four_wheel_alias_geometry_is_exact():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13ASlot01Fun00765c40DerivedAliasHandoff/1"
    assert data["slot01"] == [
        {
            "absolute_target": "HDVehicle+0x938..+0x93f",
            "slot": 0,
            "wheel_678_receiver": "HDVehicle+0xa78",
            "wheel_678_writes": ["HDVehicle+0xa70 qword", "HDVehicle+0xa78 qword"],
            "wheel_7a8_receiver": "HDVehicle+0xba8",
            "wheel_7a8_writes": ["HDVehicle+0xba0 qword", "HDVehicle+0xba8 qword"],
            "wheel_receiver": "HDVehicle+0x400",
        },
        {
            "absolute_target": "HDVehicle+0x13b8..+0x13bf",
            "slot": 1,
            "wheel_678_receiver": "HDVehicle+0x14f8",
            "wheel_678_writes": ["HDVehicle+0x14f0 qword", "HDVehicle+0x14f8 qword"],
            "wheel_7a8_receiver": "HDVehicle+0x1628",
            "wheel_7a8_writes": ["HDVehicle+0x1620 qword", "HDVehicle+0x1628 qword"],
            "wheel_receiver": "HDVehicle+0xe80",
        },
    ]


def test_wheel_678_and_7a8_aliases_are_bounded_negative():
    data = load(EVIDENCE)
    a678 = data["wheel_678_alias"]
    assert a678["per_wheel_offset"] == "+0x678"
    assert a678["write_offsets"] == ["+0x670 qword", "+0x678 qword"]
    assert a678["persistent_or_nonlocal_pointer_store_found"] is False
    assert a678["child_source"] == "[wheel+0x420]"
    assert a678["child_pointer_forward_or_store_found"] is False
    assert a678["transient_stack_pointer_site"] == "0x00765da4"
    assert a678["transient_stack_pointer_overwrite_site"] == "0x00765dc9"
    assert a678["transient_stack_pointer_reaches_callee"] is False
    assert a678["target_overlap"] is False

    a7 = data["wheel_7a8_alias"]
    assert a7["per_wheel_offset"] == "+0x7a8"
    assert a7["write_offsets"] == ["+0x7a0 qword", "+0x7a8 qword"]
    assert a7["pointer_store_found"] is False
    assert a7["pointer_push_found"] is False
    assert a7["direct_call_count"] == 0
    assert a7["target_overlap"] is False


def test_post_derived_inventory_preserves_positive_nonwheel_backpointer():
    inv = load(EVIDENCE)["post_derived_identity_inventory"]
    assert inv["selected_wheel_alias_found"] is False
    assert inv["nonwheel_runtime_backpointer_family"] == "HDVehicle+0x6730"
    assert inv["nonwheel_runtime_backpointer_stores"] == [
        "0x00a62a20 [node+0x24]=HDVehicle+0x6730",
        "0x00a62a63 [node+0x34]=HDVehicle+0x6730",
    ]
    assert inv["hdvehicle_local_array_bases"] == [
        "HDVehicle+0x3430",
        "HDVehicle+0x35c8",
        "HDVehicle+0x35f8",
        "HDVehicle+0x36e0",
    ]
    assert inv["local_array_callee_lifetimes_complete"] is False


def test_global_alias_and_slot_gates_stay_fail_closed():
    adj = load(EVIDENCE)["adjudication"]
    assert adj["p13a_fun00765c40_wheel_678_alias_subset_complete"] is True
    assert adj["p13a_fun00765c40_wheel_7a8_alias_subset_complete"] is True
    assert adj["p13a_fun00765c40_post_derived_identity_inventory_complete"] is True
    assert adj["p13a_fun00765c40_known_wheel_alias_target_writer_found"] is False
    assert adj["p13a_fun00765c40_known_wheel_alias_persistent_escape_found"] is False
    assert adj["p13a_fun00765c40_post_derived_selected_wheel_alias_found"] is False
    assert adj["p13a_fun00765c40_nonwheel_runtime_backpointer_store_found"] is True
    assert adj["p13a_fun00765c40_local_array_callee_lifetimes_complete"] is False
    assert adj["other_derived_aliases_ruled_out"] is False
    assert adj["reconstructed_wheel_pointers_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["callbacks_and_indirect_entry_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
