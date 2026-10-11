import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_stack_spill_reload.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_base_indexed_data_stack_spill_reload.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_baseidx_stack',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_exact_spill_reload_to_call_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'mov','DWORD PTR [ebp-0x4],eax'),(0x100a,'xor','eax,eax'),(0x100c,'mov','ecx,DWORD PTR [ebp-0x4]'),(0x1010,'call','ecx')]);assert r['stack_spill_event_count']==1 and r['stack_reload_event_count']==1 and r['reload_derived_indirect_transfer_count']==1
def test_esp_base_invalidation_blocks_reload():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'mov','DWORD PTR [esp+0x8],eax'),(0x100b,'push','ecx'),(0x100c,'mov','edx,DWORD PTR [esp+0x8]'),(0x1010,'call','edx')]);assert r['stack_spill_event_count']==1 and r['stack_reload_event_count']==0 and r['reload_derived_indirect_transfer_count']==0
def test_transformed_spill_is_marked():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'and','eax,0xff'),(0x100a,'mov','DWORD PTR [ebp-0x8],eax')]);assert r['stack_spill_event_count']==1 and r['transformed_stack_spill_count']==1
def test_unknown_base_is_not_seeded():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,DWORD PTR [esi+0x4]'),(0x1004,'mov','DWORD PTR [ebp-0x4],eax')]);assert r['base_indexed_data_load_count']==0 and r['stack_spill_event_count']==0
def test_retail_inventory():
 i=data()['inventory'];assert i['base_indexed_data_load_count']==63 and i['unique_effective_address_count']==51;assert i['stack_spill_event_count']==2 and i['spilled_load_count']==2;assert i['stack_spill_count_by_base']=={'ebp':1,'esp':1} and i['transformed_stack_spill_count']==1;assert i['stack_reload_event_count']==0 and i['reloaded_load_count']==0 and i['reload_derived_indirect_transfer_count']==0;assert i['tainted_register_indirect_transfer_count']==0;assert i['termination_reason_counts']=={'all_taint_dead':4,'other_control_transfer':59}
def test_global_gates_stay_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_base_indexed_data_stack_spill_reload_subset_complete'] is True;assert a['base_indexed_data_stack_reload_indirect_transfer_found'] is False
 for k in ['base_indexed_inter_block_carry_ruled_out','base_indexed_writable_sources_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
