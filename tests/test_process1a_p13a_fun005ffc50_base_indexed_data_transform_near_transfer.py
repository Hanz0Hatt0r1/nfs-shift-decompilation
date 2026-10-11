import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_transform_near_transfer.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_base_indexed_data_transform_near_transfer.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_baseidx_transform',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_copy_to_indirect_call_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'mov','ecx,eax'),(0x1009,'call','ecx')]);assert r['copy_event_count']==1 and r['tainted_register_indirect_transfer_count']==1
def test_transform_to_indirect_jump_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'add','eax,0x4'),(0x100a,'jmp','eax')]);assert r['transform_event_count']==1 and r['transformed_register_indirect_transfer_count']==1
def test_dependency_erasing_xor_blocks_transfer():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'xor','eax,eax'),(0x1009,'call','eax')]);assert r['tainted_register_indirect_transfer_count']==0 and r['termination_reason_counts']=={'all_tainted_registers_clobbered':1}
def test_unknown_base_is_not_seeded():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,DWORD PTR [esi+0x4]'),(0x1004,'call','eax')]);assert r['base_indexed_data_load_count']==0 and r['tainted_register_indirect_transfer_count']==0
def test_retail_inventory():
 i=data()['inventory'];assert i['base_indexed_data_load_count']==63 and i['unique_effective_address_count']==51;assert i['copy_event_count']==1 and i['copied_load_count']==1 and i['unique_copy_site_count']==1;assert i['transform_event_count']==4 and i['transformed_load_count']==3 and i['unique_transform_site_count']==4;assert i['transform_count_by_mnemonic']=={'add':1,'and':1,'imul':1,'sar':1};assert i['tainted_register_indirect_transfer_count']==0 and i['transformed_register_indirect_transfer_count']==0;assert i['termination_reason_counts']=={'all_tainted_registers_clobbered':4,'other_control_transfer':59}
def test_global_gates_stay_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_base_indexed_data_copy_transform_near_transfer_subset_complete'] is True;assert a['base_indexed_data_copied_or_transformed_register_indirect_transfer_found'] is False
 for k in ['base_indexed_stack_spill_reload_ruled_out','base_indexed_inter_block_carry_ruled_out','base_indexed_writable_sources_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
