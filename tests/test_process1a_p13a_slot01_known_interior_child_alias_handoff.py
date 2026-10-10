import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1a_slot01_known_interior_child_alias_handoff.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_slot01_known_interior_child_alias_handoff.json"
INPUTS = [
    ROOT / "evidence/p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json",
    ROOT / "evidence/p1d_slot3_primary_alias_escape.json",
    ROOT / "evidence/p1d_slot3_fun007555b0_interior_alias_closure.json",
    ROOT / "evidence/p1d_slot3_exact_wheel_direct_carrier_closure.json",
    ROOT / "evidence/p1d_slot3_fun00755a60_register_alias_closure.json",
    ROOT / "evidence/p1d_slot3_wheel420_child_callee_machine_closure.json",
]


def load_tool():
    spec = importlib.util.spec_from_file_location("p1a_known_alias_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_handoff():
    module = load_tool()
    assert module.build(*[load(path) for path in INPUTS]) == load(EVIDENCE)


def test_slot0_slot1_alias_normalization_is_exact():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13ASlot01KnownInteriorChildAliasHandoff/1"
    assert data["slot01"] == [
        {
            "absolute_target": "HDVehicle+0x938..+0x93f",
            "slot": 0,
            "wheel_7c8_receiver": "HDVehicle+0xbc8",
            "wheel_80_receiver": "HDVehicle+0x480",
            "wheel_receiver": "HDVehicle+0x400",
        },
        {
            "absolute_target": "HDVehicle+0x13b8..+0x13bf",
            "slot": 1,
            "wheel_7c8_receiver": "HDVehicle+0x1648",
            "wheel_80_receiver": "HDVehicle+0xf00",
            "wheel_receiver": "HDVehicle+0xe80",
        },
    ]


def test_wheel_80_and_7c8_paths_are_negative_for_target_and_escape():
    data = load(EVIDENCE)
    w80 = data["wheel_80_alias"]
    assert w80["target_relative_to_callee"] == "+0x4b8"
    assert w80["callee_receiver_write_offsets"] == ["+0x248", "+0x250", "+0x258", "+0x260"]
    assert w80["wheel_relative_write_offsets"] == ["+0x2c8", "+0x2d0", "+0x2d8", "+0x2e0"]
    assert w80["target_writer_found"] is False
    assert w80["reconstructs_wheel_root"] is False
    assert w80["forwards_to_direct_callee"] is False

    w7 = data["wheel_7c8_alias"]
    assert w7["materialization"] == "0x00755c04 ECX=wheel+0x7c8"
    assert w7["callee_call"] == "0x00755dae -> FUN_00753620"
    assert w7["callee_write_offsets"] == ["+0x0"]
    assert w7["wheel_relative_write_offsets"] == ["+0x7c8"]
    assert w7["callee_direct_call_count"] == 0
    assert w7["target_writer_found"] is False


def test_wheel_420_child_chain_does_not_recover_or_persist_wheel_root():
    child = load(EVIDENCE)["wheel_420_child_alias"]
    assert child["source"] == "child=[wheel+0x420]"
    assert child["bounded_callers"] == ["FUN_00760b50", "FUN_00755f80"]
    assert child["back_pointer_or_wheel_root_recovery_found"] is False
    assert child["child_pointer_persistence_found"] is False
    assert child["selected_target_writer_found"] is False
    assert child["persistent_child_scalar_writes"] == [
        "child+0x128 f32",
        "child+0x12c f32",
        "child+0x130 f32",
        "child+0x138 f64",
        "child+0x140 f64",
        "child+0x148 f64",
    ]


def test_only_known_alias_subset_closes():
    adj = load(EVIDENCE)["adjudication"]
    assert adj["p13a_slot01_wheel_80_interior_alias_subset_complete"] is True
    assert adj["p13a_slot01_wheel_7c8_interior_alias_subset_complete"] is True
    assert adj["p13a_slot01_wheel_420_child_alias_subset_complete"] is True
    assert adj["p13a_slot01_known_interior_child_alias_target_writer_found"] is False
    assert adj["p13a_slot01_known_interior_child_alias_root_reconstruction_found"] is False
    assert adj["p13a_slot01_known_interior_child_alias_pointer_persistence_found"] is False
    assert adj["other_derived_or_child_aliases_ruled_out"] is False
    assert adj["reconstructed_wheel_pointers_ruled_out"] is False
    assert adj["runtime_generated_or_copied_pointer_stores_ruled_out"] is False
    assert adj["callbacks_and_indirect_entry_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
