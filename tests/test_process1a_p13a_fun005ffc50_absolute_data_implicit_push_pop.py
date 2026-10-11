import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_absolute_data_implicit_push_pop.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_absolute_data_implicit_push_pop.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_pushpop',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_push_pop_then_call_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'push','eax'),(0x1006,'xor','eax,eax'),(0x1008,'pop','ecx'),(0x1009,'call','ecx')])
 assert r['tainted_push_event_count']==1 and r['tainted_pop_reload_event_count']==1
 assert r['pop_derived_indirect_transfer_count']==1 and r['pop_derived_indirect_transfers'][0]['transfer_register']=='ecx'
def test_nested_unknown_push_preserves_correct_stack_order():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'push','eax'),(0x1006,'push','ebx'),(0x1007,'pop','ecx'),(0x1008,'pop','edx'),(0x1009,'jmp','edx')])
 assert r['tainted_push_event_count']==1 and r['tainted_pop_reload_event_count']==1
 assert r['pop_derived_indirect_transfer_count']==1 and r['pop_derived_indirect_transfers'][0]['transfer_register']=='edx'
def test_transformed_push_is_marked_and_restored():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'add','eax,4'),(0x1008,'push','eax'),(0x1009,'pop','ecx')])
 assert r['transformed_tainted_push_count']==1 and r['pop_reload_events'][0]['transformed'] is True
def test_unmodelled_esp_write_stops_push_pop_provenance():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'push','eax'),(0x1006,'add','esp,4'),(0x1009,'pop','ecx'),(0x100a,'call','ecx')])
 assert r['tainted_push_event_count']==1 and r['tainted_pop_reload_event_count']==0 and r['pop_derived_indirect_transfer_count']==0
def test_retail_implicit_stack_inventory_is_exact_and_negative():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50AbsoluteDataImplicitPushPop/1'
 assert i['decoded_instruction_count']==2847850 and i['absolute_data_load_count']==1786 and i['unique_absolute_data_slot_count']==434
 assert i['tainted_push_event_count']==208 and i['pushed_load_count']==208
 assert i['push_count_by_register']=={'eax':92,'ecx':71,'edx':44,'esi':1} and i['transformed_tainted_push_count']==12
 assert i['tainted_pop_reload_event_count']==0 and i['pop_derived_indirect_transfer_count']==0 and i['tainted_register_indirect_transfer_count']==0
 assert i['termination_reason_counts']=={'all_taint_dead':259,'other_control_transfer':1482,'unmodelled_esp_write':25,'window_exhausted':20}
def test_narrow_push_pop_gate_keeps_global_frontiers_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_absolute_data_implicit_push_pop_subset_complete'] is True
 assert a['absolute_data_implicit_pop_indirect_transfer_found'] is False
 for k in ['register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
