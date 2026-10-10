import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1a_slot01_carrier_surface_composition.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_slot01_carrier_surface_composition.json"
DERIVED = ROOT / "evidence/p1a_p13a_slot01_fun00765c40_derived_alias_handoff.json"
LOCAL_ARRAYS = ROOT / "evidence/p1a_p13a_fun00765c40_local_array_callee_machine_closure.json"
CARRIER_BULK = ROOT / "evidence/p1d_slot3_16carrier_bulk_opcode_closure.json"
CALLEE_BULK = ROOT / "evidence/p1d_slot3_direct_callee_bulk_opcode_closure.json"
CALL_TARGETS = ROOT / "evidence/p1d_slot3_carrier_call_target_composition.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_carrier_surface", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_evidence():
    module = load_module()
    actual = module.build(
        load(DERIVED),
        load(LOCAL_ARRAYS),
        load(CARRIER_BULK),
        load(CALLEE_BULK),
        load(CALL_TARGETS),
    )
    assert actual == load(EVIDENCE)


def test_bounded_carrier_and_callee_surface_is_exact():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13ASlot01CarrierSurfaceComposition/1"
    surface = data["carrier_surface"]
    assert surface["carrier_count"] == 16
    assert surface["carrier_instruction_count"] == 5178
    assert surface["carrier_bulk_opcode_hit_count"] == 0
    assert surface["immediate_direct_callsite_count"] == 214
    assert surface["unique_immediate_direct_callee_count"] == 82
    assert surface["direct_callee_instruction_count"] == 9159
    assert surface["direct_callee_bulk_opcode_hit_count"] == 0
    assert surface["call_through_memory_site_count"] == 2
    assert surface["total_machine_callsite_count"] == 216
    assert surface["runtime_unknown_call_target_count"] == 0


def test_fun00770e80_memory_calls_are_imports_not_game_callbacks():
    rows = load(EVIDENCE)["carrier_surface"]["resolved_call_through_memory_sites"]
    assert [(r["site"], r["runtime_import"], r["target_argument"], r["value_argument"]) for r in rows] == [
        ("0x00770ec4", "KERNEL32!InterlockedExchange", "HDVehicle+0x4020", 1),
        ("0x00770f41", "KERNEL32!InterlockedExchange", "HDVehicle+0x4020", 2),
    ]
    assert all(r["resolution_kind"] == "PE import/IAT" for r in rows)


def test_fun00765c40_local_arrays_close_without_promoting_global_alias_gates():
    data = load(EVIDENCE)
    local = data["fun00765c40"]
    assert local["known_wheel_derived_aliases_complete"] is True
    assert local["known_wheel_alias_target_writer_found"] is False
    assert local["known_wheel_alias_persistent_escape_found"] is False
    assert local["local_array_callee_lifetimes_complete"] is True
    assert local["local_array_pointer_escape_found"] is False
    assert local["local_array_wheel_root_reconstruction_found"] is False
    assert local["nonwheel_runtime_backpointer_store_found"] is True

    adj = data["adjudication"]
    assert adj["p13a_fun00765c40_known_derived_and_local_array_subset_complete"] is True
    assert adj["p13a_sixteen_carrier_direct_bulk_opcode_subset_complete"] is True
    assert adj["p13a_sixteen_carrier_direct_callee_bulk_opcode_subset_complete"] is True
    assert adj["p13a_sixteen_carrier_call_target_surface_complete"] is True
    assert adj["p13a_fun00770e80_aa60b4_import_indirect_subset_complete"] is True
    assert adj["aggregate_or_bulk_alias_stores_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["callbacks_and_indirect_entry_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
