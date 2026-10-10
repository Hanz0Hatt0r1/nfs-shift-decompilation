import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1d_slot3_carrier_call_target_composition.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_carrier_call_target_composition.json"
DIRECT = ROOT / "evidence/p1d_slot3_direct_callee_bulk_opcode_closure.json"
STATIC = ROOT / "evidence/p1d_slot3_static_indirect_aa60b4_closure.json"


def load_module():
    spec=importlib.util.spec_from_file_location("p1d_carrier_call_target_composition",TOOL)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def test_composed_carrier_call_surface_is_complete():
    data=json.loads(EVIDENCE.read_text(encoding="utf-8")); surface=data["surface"]
    assert data["format"]=="SHIFT.P1D.Slot3CarrierCallTargetComposition/1"
    assert surface["carrier_count"]==16
    assert surface["total_machine_callsite_count"]==216
    assert surface["immediate_direct_callsite_count"]==214
    assert surface["call_through_memory_site_count"]==2
    assert surface["runtime_unknown_call_target_count_within_16_carrier_bodies"]==0


def test_two_non_immediate_sites_are_statically_resolved():
    rows=json.loads(EVIDENCE.read_text(encoding="utf-8"))["surface"]["resolved_call_through_memory_sites"]
    assert [r["site"] for r in rows]==["0x00770ec4","0x00770f41"]
    assert all(r["slot"]=="0x00aa60b4" and r["static_image_target"]=="0x00778052" for r in rows)


def test_global_indirect_gates_remain_fail_closed():
    gates=json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["sixteen_carrier_machine_call_target_surface_complete"] is True
    assert gates["sixteen_carrier_runtime_unknown_call_target_found"] is False
    assert gates["sixteen_carrier_runtime_unknown_call_target_count"]==0
    assert gates["other_indirect_entry_ruled_out"] is False
    assert gates["callbacks_registered_outside_carriers_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"]==7


def test_builder_reproduces_committed_evidence():
    module=load_module(); built=module.build(DIRECT,STATIC); committed=json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert built==committed
