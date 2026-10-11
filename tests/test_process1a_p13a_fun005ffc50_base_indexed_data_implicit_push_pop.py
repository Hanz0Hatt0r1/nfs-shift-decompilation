import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_implicit_push_pop.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_base_indexed_data_implicit_push_pop.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_baseidx_pushpop',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_push_pop_to_call_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'push','eax'),(0x1008,'xor','eax,eax'),(0x100a,'pop','ecx'),(0x100b,'call','ecx')]);assert r['tainted_push_event_count']==1 and r['tainted_pop_reload_event_count']==1 and r['pop_derived_indirect_transfer_count']==1
def test_nested_unknown_push_blocks_pop_taint():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'push','eax'),(0x1008,'push','edx'),(0x1009,'pop','ecx')]);assert r['tainted_push_event_count']==1 and r['tainted_pop_reload_event_count']==0
def test_esp_write_stops_path():
 m=mod();r=m.scan_rows([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'push','eax'),(0x1008,'add','esp,4'),(0x100b,'pop','ecx')]);assert r['termination_reason_counts']=={'unmodelled_esp_write':1}
def test_unknown_base_not_seeded():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,DWORD PTR [esi+4]'),(0x1004,'push','eax')]);assert r['base_indexed_data_load_count']==0 and r['tainted_push_event_count']==0
def test_retail_inventory():
 i=data()['inventory'];assert i['base_indexed_data_load_count']==63 and i['unique_effective_address_count']==51;assert i['tainted_push_event_count']==5 and i['pushed_load_count']==5;assert i['push_count_by_register']=={'eax':3,'ecx':2} and i['transformed_tainted_push_count']==0;assert i['tainted_pop_reload_event_count']==0 and i['pop_derived_indirect_transfer_count']==0 and i['tainted_register_indirect_transfer_count']==0;assert i['termination_reason_counts']=={'all_taint_dead':2,'other_control_transfer':61}
def test_global_gates_stay_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_base_indexed_data_implicit_push_pop_subset_complete'] is True;assert a['base_indexed_data_implicit_pop_indirect_transfer_found'] is False
 for k in ['base_indexed_esp_normalization_ruled_out','base_indexed_inter_block_carry_ruled_out','base_indexed_writable_sources_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
