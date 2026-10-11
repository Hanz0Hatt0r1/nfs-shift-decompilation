import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_absolute_data_esp_normalization.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_absolute_data_esp_normalization.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_esp',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data(): return json.loads(E.read_text())
def test_add_esp_preserves_deeper_cell_then_pop_call():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'push','eax'),(0x1006,'sub','esp,0x8'),(0x1009,'add','esp,0x8'),(0x100c,'pop','ecx'),(0x100d,'call','ecx')])
 assert r['esp_normalization_event_count']==2
 assert r['tainted_pop_reload_event_count']==1
 assert r['pop_derived_indirect_transfer_count']==1
def test_add_esp_discards_popped_tainted_cell():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'push','eax'),(0x1006,'add','esp,0x4'),(0x1009,'pop','ecx'),(0x100a,'call','ecx')])
 assert r['tainted_pop_reload_event_count']==0
 assert r['pop_derived_indirect_transfer_count']==0
def test_lea_esp_zero_delta_is_modeled():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'lea','esp,[esp+0x0]'),(0x1009,'call','eax')])
 assert r['esp_normalization_by_mnemonic']=={'lea':1}
 assert r['tainted_register_indirect_transfer_count']==1
def test_complex_esp_write_stays_fail_closed():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'mov','esp,ecx'),(0x1007,'call','eax')])
 assert r['termination_reason_counts']=={'unmodelled_esp_write':1}
 assert r['tainted_register_indirect_transfer_count']==0
def test_retail_inventory():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50AbsoluteDataEspNormalization/1'
 assert i['esp_normalization_event_count']==25 and i['esp_normalization_load_count']==25
 assert i['esp_normalization_by_mnemonic']=={'add':23,'lea':2}
 assert i['tainted_push_event_count']==209 and i['tainted_pop_reload_event_count']==0
 assert i['tainted_register_indirect_transfer_count']==0 and i['pop_derived_indirect_transfer_count']==0
 assert i['termination_reason_counts']=={'all_taint_dead':259,'other_control_transfer':1507,'window_exhausted':20}
def test_global_gates_stay_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_absolute_data_esp_normalization_subset_complete'] is True
 assert a['absolute_data_esp_normalized_indirect_transfer_found'] is False
 for k in ['base_indexed_writable_sources_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','callbacks_and_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
