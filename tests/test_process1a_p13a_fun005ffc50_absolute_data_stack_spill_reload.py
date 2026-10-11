import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_absolute_data_stack_spill_reload.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_absolute_data_stack_spill_reload.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_abs_stack',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_ebp_spill_reload_then_call_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'mov','DWORD PTR [ebp-0x10],eax'),(0x1008,'xor','eax,eax'),(0x100a,'mov','ecx,DWORD PTR [ebp-0x10]'),(0x100d,'call','ecx')])
 assert r['stack_spill_event_count']==1 and r['stack_reload_event_count']==1
 assert r['reload_derived_indirect_transfer_count']==1 and r['reload_derived_indirect_transfers'][0]['transfer_register']=='ecx'
def test_synthetic_transformed_spill_is_marked():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'add','eax,4'),(0x1008,'mov','DWORD PTR [ebp-0x8],eax')])
 assert r['stack_spill_event_count']==1 and r['transformed_stack_spill_count']==1
def test_esp_base_change_invalidates_spilled_slot():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'mov','DWORD PTR [esp+0x4],eax'),(0x1009,'push','ebx'),(0x100a,'mov','ecx,DWORD PTR [esp+0x4]'),(0x100e,'call','ecx')])
 assert r['stack_spill_event_count']==1 and r['stack_reload_event_count']==0 and r['reload_derived_indirect_transfer_count']==0
def test_exact_stack_overwrite_kills_saved_taint():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'mov','DWORD PTR [ebp-0x4],eax'),(0x1009,'mov','DWORD PTR [ebp-0x4],ebx'),(0x100d,'mov','ecx,DWORD PTR [ebp-0x4]'),(0x1010,'call','ecx')])
 assert r['stack_spill_event_count']==1 and r['stack_reload_event_count']==0 and r['reload_derived_indirect_transfer_count']==0
def test_retail_stack_inventory_is_exact_and_negative():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50AbsoluteDataStackSpillReload/1'
 assert i['decoded_instruction_count']==2847850 and i['absolute_data_load_count']==1786 and i['unique_absolute_data_slot_count']==434
 assert i['stack_spill_event_count']==109 and i['spilled_load_count']==108 and i['stack_spill_count_by_base']=={'ebp':91,'esp':18}
 assert i['transformed_stack_spill_count']==82
 assert i['stack_reload_event_count']==8 and i['reloaded_load_count']==8 and i['stack_reload_count_by_base']=={'ebp':8}
 assert i['transformed_stack_reload_count']==0
 assert i['tainted_register_indirect_transfer_count']==0 and i['reload_derived_indirect_transfer_count']==0
 assert i['termination_reason_counts']=={'all_taint_dead':282,'other_control_transfer':1466,'window_exhausted':38}
def test_stack_subset_gate_keeps_global_frontiers_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_absolute_data_stack_spill_reload_subset_complete'] is True
 assert a['absolute_data_stack_reload_indirect_transfer_found'] is False
 for k in ['register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
