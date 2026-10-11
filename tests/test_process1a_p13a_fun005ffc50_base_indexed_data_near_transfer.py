import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_near_transfer.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_base_indexed_data_near_transfer.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_baseidx',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_exact_effective_address_uses_known_constants():
 m=mod(); assert m.eval_expr('esi*4+0xb81618',{'esi':2})==0xb81620
 assert m.eval_expr('edi-0xc',{'edi':0xb83ed0})==0xb83ec4
 st={'esi':(0,0),'eax':(1,0)};st=m.update_state('call','0x123456',st);assert 'esi' in st and 'eax' not in st
 st={'edi':(0xbac6d4,16)};st=m.update_state('nop','',st);assert st=={}
def test_synthetic_same_register_call_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'nop',''),(0x1008,'call','eax')]);assert r['base_indexed_data_load_count']==1 and r['same_register_indirect_transfer_count']==1
def test_clobber_blocks_transfer():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'mov','eax,0x1'),(0x100c,'call','eax')]);assert r['same_register_indirect_transfer_count']==0 and r['termination_reason_counts']=={'register_clobber':1}
def test_unknown_index_is_not_claimed():
 m=mod();r=m.scan_rows([(0x1000,'mov','ecx,DWORD PTR [esi*4+0xb81618]')]);assert r['base_indexed_data_load_count']==0
def test_retail_inventory():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataNearTransfer/1';assert i['decoded_instruction_count']==2847850;assert i['base_indexed_data_load_count']==63 and i['unique_effective_address_count']==51;assert i['destination_register_counts']=={'eax':37,'ebx':4,'ecx':10,'edi':2,'edx':5,'esi':5};assert i['same_register_indirect_transfer_count']==0;assert i['termination_reason_counts']=={'other_control_transfer':58,'register_clobber':5}
def test_global_gates_stay_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_base_indexed_data_same_register_near_transfer_subset_complete'] is True;assert a['base_indexed_data_same_register_indirect_transfer_found'] is False
 for k in ['register_copy_or_transform_after_base_indexed_load_ruled_out','base_indexed_stack_spill_reload_ruled_out','base_indexed_inter_block_carry_ruled_out','base_indexed_writable_sources_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
