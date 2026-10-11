import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_nvapi_writable_table.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_nvapi_writable_table.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_nvapi',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_nvapi_table_shape_and_unique_ids():
 p=data();n=p['nvapi_table'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50NvapiWritableDispatchTable/1'
 assert n['module_name']=='nvapi.dll' and n['query_symbol']=='nvapi_QueryInterface'
 assert n['record_count']==255 and n['record_stride']==8 and n['initial_pointer_count']==255
 assert n['unique_function_id_count']==255 and n['zero_function_id_count']==0
 assert n['terminator_id_address']=='0x00bbc504' and n['terminator_id_value']==0
def test_nvapi_thunk_surface_and_anchor_id():
 n=data()['nvapi_table'];assert n['direct_thunk_count']==255 and n['direct_table_indirect_transfer_count']==255
 assert n['first_thunk']=='0x00a61ae8' and n['last_thunk']=='0x00a620dc'
 assert n['known_anchor_function_id']=='0xe5ac921f' and n['known_anchor_index']==5
def test_resolver_machine_anchors_pin_external_provider_loop():
 a=data()['machine_anchors']
 assert a['load_library_name']=='0x00a61a5b push 0xb66b10'
 assert a['get_proc_address_call']=='0x00a61a7c call DWORD PTR ds:0xaa62fc'
 assert a['query_entry']=='0x00a61abb call ebp'
 assert a['store_resolved_pointer']=='0x00a61ac2 mov DWORD PTR [esi],eax'
 assert a['next_record']=='0x00a61ac4 add esi,0x8'
def test_narrow_nvapi_gate_keeps_global_runtime_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_nvapi_writable_dispatch_table_subset_complete'] is True
 assert a['nvapi_writable_table_internal_fun005ffc50_static_provider_found'] is False
 assert a['nvapi_writable_table_values_are_stub_or_external_queryinterface_results'] is True
 for k in ['writable_memory_or_runtime_fun005ffc50_entry_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
