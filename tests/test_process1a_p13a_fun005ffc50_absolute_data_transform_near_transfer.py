import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_absolute_data_transform_near_transfer.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_absolute_data_transform_near_transfer.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_abs_transform',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_arithmetic_transform_then_call_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'add','eax,0x20'),(0x1008,'call','eax')])
 assert r['transform_event_count']==1 and r['transformed_register_indirect_transfer_count']==1
 assert r['transformed_register_indirect_transfers'][0]['transformed'] is True
def test_synthetic_copy_then_transform_survives_origin_clobber():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'mov','ecx,eax'),(0x1007,'add','ecx,4'),(0x100a,'xor','eax,eax'),(0x100c,'jmp','ecx')])
 assert r['transform_event_count']==1 and r['transformed_register_indirect_transfer_count']==1
 assert r['transformed_register_indirect_transfers'][0]['transfer_register']=='ecx'
def test_dependency_erasing_self_xor_is_not_carried():
 m=mod();r=m.scan_rows([(0x1000,'mov','edx,ds:0xb81004'),(0x1006,'xor','edx,edx'),(0x1008,'call','edx')])
 assert r['transform_event_count']==0 and r['tainted_register_indirect_transfer_count']==0
def test_synthetic_lea_from_tainted_source_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,ds:0xb81008'),(0x1006,'lea','edi,[esi+0x10]'),(0x1009,'call','edi')])
 assert r['transform_count_by_mnemonic']=={'lea':1} and r['transformed_register_indirect_transfer_count']==1
def test_retail_transform_inventory_is_exact_and_negative():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50AbsoluteDataTransformNearTransfer/1'
 assert i['decoded_instruction_count']==2847850 and i['absolute_data_load_count']==1786 and i['unique_absolute_data_slot_count']==434
 assert i['transform_event_count']==179 and i['transformed_load_count']==160 and i['unique_transform_site_count']==164
 assert i['transform_count_by_mnemonic']=={'add':26,'and':9,'dec':4,'imul':1,'inc':4,'lea':45,'or':2,'shl':1,'sub':3,'xor':84}
 assert i['tainted_register_indirect_transfer_count']==0 and i['transformed_register_indirect_transfer_count']==0
 assert i['termination_reason_counts']=={'all_tainted_registers_clobbered':336,'other_control_transfer':1430,'window_exhausted':20}
def test_narrow_transform_gate_keeps_global_frontiers_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_absolute_data_transform_near_transfer_subset_complete'] is True
 assert a['absolute_data_transformed_register_indirect_transfer_found'] is False
 for k in ['register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
