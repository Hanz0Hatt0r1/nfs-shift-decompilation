import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'tools'/'ghidra'/'build_p1b_hdvehicle_4330_indirect_entry_coverage_v16.py'
SURFACE=ROOT/'evidence'/'p1b_hdvehicle_4330_source_slot_exact_address_surface.json'
EVIDENCE=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v16.json'
def data(path): return json.loads(path.read_text(encoding='utf-8'))
def module():
 spec=importlib.util.spec_from_file_location('p1b_4330_indirect_v16',BUILDER); assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def test_exact_slot_address_surface_is_bounded_and_complete():
 d=data(SURFACE);s=d['surface'];a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330SourceSlotExactAddressSurface/1'
 assert s['total_exact_source_slot_address_dword_occurrence_count']==6
 slots={x['address']:x for x in s['source_slots']}
 assert slots['0x00b83dc0']['raw_dword_occurrence_count']==4
 assert slots['0x00b83ec0']['raw_dword_occurrence_count']==2
 assert a['exact_source_slot_address_literal_surface_complete'] is True
 assert a['computed_or_runtime_alias_surface_complete'] is False
def test_static_alias_getter_entry_surface_is_direct_only():
 s=data(SURFACE)['surface']; getters={x['address']:x for x in s['alias_getters']}
 assert getters['0x00552f50']['direct_call_sites']==['0x008df2cf','0x008dfc06']
 assert getters['0x00553640']['direct_call_sites']==['0x008df037']
 assert s['total_static_alias_getter_direct_call_site_count']==3
 assert s['total_static_alias_getter_function_address_dword_occurrence_count']==0
 assert data(SURFACE)['adjudication']['source_slot_alias_getter_function_address_taken_found'] is False
def test_v16_advances_one_bounded_class_only():
 d=data(EVIDENCE);s=d['surface'];a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/16'
 assert (s['previous_bounded_coverage_class_count'],s['composed_coverage_class_count'])==(19,20)
 assert s['source_slot_exact_address_dword_occurrence_count']==6
 assert s['source_slot_static_alias_getter_direct_call_site_count']==3
 assert a['computed_or_runtime_alias_surface_complete'] is False
 assert a['runtime_or_alias_writer_provenance_complete'] is False
 assert a['memory_derived_indirect_call_target_identity_complete'] is False
 assert a['indirect_entry_into_carriers_ruled_out'] is False
 assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
 assert a['last_literal_0x004b86cf_rejected'] is False
 assert a['p1_3_control_producer_complete'] is False
 assert a['external_provider_count']==7
def test_builder_reproduces_committed_v16(): assert module().build()==data(EVIDENCE)
