import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_wpair',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_writable_pair_exact_direct_surfaces():
 p=data();w=p['writable_callback_pair'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1'
 assert w['direct_setter_callsites']==['0x0060adde','0x0061ccbe']
 assert w['direct_config_callsites']==['0x005f3b7f','0x005f47b7']
 assert w['slot_A_direct_absolute_writers']==['0x00616602','0x006166c5']
 assert w['slot_B_direct_absolute_writers']==['0x0061660d','0x006166d8']
 assert w['slot_A_direct_indirect_transfer_count']==26 and w['slot_B_direct_indirect_transfer_count']==51
def test_direct_static_candidate_values_exclude_target():
 w=data()['writable_callback_pair']
 assert w['initial_slot_A']=='0x006165b6' and w['initial_slot_B']=='0x006165c0'
 assert w['direct_static_slot_A_candidate_values']==['0x005f46f0','0x006165b6','0x0061cb43']
 assert w['direct_static_slot_B_candidate_values']==['0x005f4760','0x006165c0','0x0061cbff']
 assert w['direct_static_candidate_values_include_FUN_005ffc50'] is False
def test_startup_snapshots_and_entry_address_literals():
 p=data();w=p['writable_callback_pair'];s=p['static_entry_address_literals']
 assert w['startup_snapshot_table_entries']=={'0x00aa77b8':'0x00a7fa5c','0x00aa77bc':'0x00a7fa67'}
 assert all(v==0 for v in s.values())
 a=p['machine_anchors'];assert a['slot_A_default_load']=='0x006166c0 mov eax,ds:0xbe87dc';assert a['slot_B_default_load']=='0x006166d1 mov eax,ds:0xbe87e0'
def test_narrow_gate_keeps_alias_and_runtime_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_direct_static_provenance_subset_complete'] is True
 assert a['writable_callback_pair_direct_static_fun005ffc50_value_found'] is False
 for k in ['writable_callback_pair_indirect_or_alias_writers_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
