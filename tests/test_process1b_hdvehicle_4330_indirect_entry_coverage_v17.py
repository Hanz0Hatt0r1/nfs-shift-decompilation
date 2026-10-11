import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'tools'/'ghidra'/'build_p1b_hdvehicle_4330_indirect_entry_coverage_v17.py'
SURFACE=ROOT/'evidence'/'p1b_hdvehicle_4330_alias_getter_direct_consumer_slot0.json'
EVIDENCE=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v17.json'
def data(path): return json.loads(path.read_text(encoding='utf-8'))
def module():
 spec=importlib.util.spec_from_file_location('p1b_4330_indirect_v17',BUILDER); assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def test_direct_getter_consumers_do_not_write_or_export_slot0():
 d=data(SURFACE);s=d['surface'];a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330AliasGetterDirectConsumerSlot0Writer/1'
 assert s['direct_alias_getter_callsite_count']==3
 assert s['slot0_direct_memory_write_count']==0
 assert s['slot0_pointer_argument_count']==0
 assert s['slot0_write_or_pointer_escape_count']==0
 assert all(x['nonstack_direct_memory_write_count']==0 for x in s['caller_functions'])
 assert a['direct_alias_getter_consumer_slot0_writer_subset_complete'] is True
 assert a['direct_alias_getter_consumer_slot0_write_or_pointer_escape_found'] is False
def test_mutable_pointer_arguments_are_nonzero_fields_only():
 o=data(SURFACE)['surface']['nonzero_field_pointer_argument_offsets']
 assert o['0x00b83dc0_stride_0x40']==['0x0c','0x10','0x38']
 assert o['0x00b83ec0_stride_0x3c']==['0x0c','0x10','0x14','0x18','0x1c','0x38']
 assert '0x00' not in o['0x00b83dc0_stride_0x40'] and '0x00' not in o['0x00b83ec0_stride_0x3c']
def test_v17_keeps_global_alias_and_p13_gates_open():
 d=data(EVIDENCE);s=d['surface'];a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/17'
 assert (s['previous_bounded_coverage_class_count'],s['composed_coverage_class_count'])==(20,21)
 assert s['direct_alias_getter_slot0_write_or_pointer_escape_count']==0
 assert a['computed_or_runtime_alias_surface_complete'] is False
 assert a['runtime_or_alias_writer_provenance_complete'] is False
 assert a['memory_derived_indirect_call_target_identity_complete'] is False
 assert a['indirect_entry_into_carriers_ruled_out'] is False
 assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
 assert a['last_literal_0x004b86cf_rejected'] is False
 assert a['p1_3_control_producer_complete'] is False
 assert a['external_provider_count']==7
def test_builder_reproduces_committed_v17(): assert module().build()==data(EVIDENCE)
