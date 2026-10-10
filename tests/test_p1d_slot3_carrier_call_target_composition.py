import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1d_slot3_carrier_call_target_composition.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_carrier_call_target_composition.json"
DIRECT = ROOT / "evidence/p1d_slot3_direct_callee_bulk_opcode_closure.json"
IMPORTED = ROOT / "evidence/p1d_slot3_static_indirect_aa60b4_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_carrier_call_target_composition", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_composed_carrier_call_surface_is_complete():
    data = load_evidence()
    surface = data["surface"]
    assert data["format"] == "SHIFT.P1D.Slot3CarrierCallTargetComposition/2"
    assert data["supersedes"] == "SHIFT.P1D.Slot3CarrierCallTargetComposition/1"
    assert data["upstream_contracts"] == [
        "SHIFT.P1D.Slot3DirectCalleeBulkOpcodeClosure/1",
        "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/2",
    ]
    assert surface["carrier_count"] == 16
    assert surface["total_machine_callsite_count"] == 216
    assert surface["immediate_direct_callsite_count"] == 214
    assert surface["call_through_memory_site_count"] == 2
    assert surface["runtime_unknown_call_target_count_within_16_carrier_bodies"] == 0
    assert surface["on_disk_import_name_rva_misclassified_as_code_target"] is False


def test_two_non_immediate_sites_are_import_resolved():
    rows = load_evidence()["surface"]["resolved_call_through_memory_sites"]
    assert rows == [
        {
            "operation": "InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 1)",
            "resolution_kind": "PE import/IAT",
            "runtime_import": "KERNEL32!InterlockedExchange",
            "site": "0x00770ec4",
            "slot": "0x00aa60b4",
            "target_argument": "HDVehicle+0x4020",
            "value_argument": 1,
        },
        {
            "operation": "InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 2)",
            "resolution_kind": "PE import/IAT",
            "runtime_import": "KERNEL32!InterlockedExchange",
            "site": "0x00770f41",
            "slot": "0x00aa60b4",
            "target_argument": "HDVehicle+0x4020",
            "value_argument": 2,
        },
    ]


def test_global_indirect_gates_remain_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["sixteen_carrier_machine_call_target_surface_complete"] is True
    assert gates["sixteen_carrier_runtime_unknown_call_target_found"] is False
    assert gates["sixteen_carrier_runtime_unknown_call_target_count"] == 0
    assert gates["sixteen_carrier_import_resolved_callsite_count"] == 2
    assert gates["sixteen_carrier_static_game_code_target_count_for_aa60b4"] == 0
    assert gates["other_indirect_entry_ruled_out"] is False
    assert gates["callbacks_registered_outside_carriers_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_builder_reproduces_committed_evidence():
    module = load_module()
    built = module.build(DIRECT, IMPORTED)
    assert built == load_evidence()
    assert module.FORMAT == "SHIFT.P1D.Slot3CarrierCallTargetComposition/2"
    assert module.IMPORT_FORMAT == "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/2"
    assert module.EXPECTED_IMPORT == "KERNEL32!InterlockedExchange"
