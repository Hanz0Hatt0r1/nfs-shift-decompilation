import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'tools'/'ghidra'/'build_p1b_hdvehicle_4330_indirect_entry_coverage_v15.py'
TARGETS=ROOT/'evidence'/'p1b_hdvehicle_4330_memory_derived_call_target_provenance.json'
EVIDENCE=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v15.json'
def data(path): return json.loads(path.read_text(encoding='utf-8'))
def module():
 spec=importlib.util.spec_from_file_location('p1b_4330_indirect_v15',BUILDER); assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def test_bounded_target_provenance_has_no_exact_carrier_hit():
 d=data(TARGETS); s=d['surface']; a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330BaseIndexedMemoryDerivedCallTargetProvenance/1'
 assert s['target_derived_call_count']==2
 assert s['bounded_target_table_pointer_values']==['0x00acdd68','0x00acdd70']
 assert s['bounded_callable_target_values']==['0x00553260','0x00553a90']
 assert s['bounded_callable_target_exact_carrier_hit_count']==0
 assert s['canonical_p1b_carrier_count']==15
 assert a['bounded_static_initializer_target_provenance_complete'] is True
 assert a['bounded_static_initializer_target_can_hit_exact_p1b_carrier'] is False
 assert a['runtime_or_alias_writer_provenance_complete'] is False
 assert a['memory_derived_indirect_call_target_identity_complete'] is False
def test_selected_call_candidate_sets_are_exact():
 calls={x['call_site']:x for x in data(TARGETS)['surface']['calls']}
 assert calls['0x00553247']['source_slot']=='0x00b83dc0'
 assert calls['0x00553247']['table_pointer_values']==['0x00acdd68','0x00acdd70']
 assert calls['0x00553247']['callable_target_values']==['0x00553260','0x00553a90']
 assert calls['0x005539ac']['source_slot']=='0x00b83ec0'
 assert calls['0x005539ac']['table_pointer_values']==['0x00acdd68']
 assert calls['0x005539ac']['callable_target_values']==['0x00553a90']
def test_v15_advances_one_bounded_class_without_global_promotion():
 d=data(EVIDENCE); s=d['surface']; a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/15'
 assert (s['previous_bounded_coverage_class_count'],s['composed_coverage_class_count'])==(18,19)
 assert s['bounded_static_initializer_callable_target_exact_carrier_hit_count']==0
 assert a['runtime_or_alias_writer_provenance_complete'] is False
 assert a['memory_derived_indirect_call_target_identity_complete'] is False
 assert a['indirect_entry_into_carriers_ruled_out'] is False
 assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
 assert a['last_literal_0x004b86cf_rejected'] is False
 assert a['p1_3_control_producer_complete'] is False
 assert a['external_provider_count']==7
def test_builder_reproduces_committed_v15(): assert module().build()==data(EVIDENCE)
