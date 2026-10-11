import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_absolute_data_load_near_transfer.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_absolute_data_load_near_transfer.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_absload',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_absolute_data_load_then_same_register_call_is_detected():
 m=mod();rows=[(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'nop',''),(0x1006,'call','eax')]
 r=m.scan_rows(rows);assert r['absolute_data_load_count']==1 and r['unique_absolute_data_slot_count']==1
 assert r['near_loaded_register_indirect_transfers']==[{'load_site':'0x00001000','slot':'0x00b81000','register':'eax','transfer_site':'0x00001006','kind':'call','distance':2}]
def test_synthetic_clobber_blocks_same_register_transfer_provenance():
 m=mod();rows=[(0x1000,'mov','ecx,DWORD PTR ds:0xb81004'),(0x1006,'xor','ecx,ecx'),(0x1008,'call','ecx')]
 r=m.scan_rows(rows);assert r['near_loaded_register_indirect_transfers']==[] and r['termination_reason_counts']=={'register_clobber':1}
def test_retail_absolute_data_load_inventory_is_zero_for_near_transfer():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50AbsoluteDataLoadNearTransfer/1'
 assert p['scope']['decoded_instruction_count']==2847850 and p['scope']['forward_window_decoded_instructions']==16
 assert i['absolute_data_load_count']==1786 and i['unique_absolute_data_slot_count']==434
 assert i['load_count_by_register']=={'eax':1125,'ebp':1,'ebx':25,'ecx':326,'edi':72,'edx':186,'esi':51}
 assert i['load_count_by_encoding_form']=={'modrm_absolute':661,'moffs_absolute':1125}
 assert i['termination_reason_counts']=={'other_control_transfer':1355,'register_clobber':413,'window_exhausted':18}
 assert i['near_loaded_register_indirect_transfer_count']==0 and i['near_loaded_register_indirect_transfers']==[]
def test_narrow_gate_keeps_copies_aliases_and_runtime_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_absolute_data_load_near_register_transfer_subset_complete'] is True
 assert a['absolute_data_load_near_register_indirect_transfer_found'] is False
 for k in ['register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
