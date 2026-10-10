import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_residual_indexed_wheel_root_lifetimes.py'
E=ROOT/'evidence'/'p1a_p13a_residual_indexed_wheel_root_lifetimes.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_residual_indexed',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_selected_hdvehicle_entries_are_literal_proven():
 p=data();assert p['format']=='SHIFT.P1A.P13AResidualIndexedWheelRootLifetimes/1'
 assert p['selected_hdvehicle_entry']['FUN_00765850']==[{'call':'0x0074d988','literal':'0x00c13700'},{'call':'0x00713b0b','literal':'0x00c13700'}]
 assert p['selected_hdvehicle_entry']['FUN_00765aa0']==[{'call':'0x00713ac7','literal':'0x00c13700'}]
def test_exact_root_lifetimes_have_only_stack_spills():
 p=data();rows={x['function']:x for x in p['indexed_materializers']}
 assert rows['FUN_00765850']['exact_root_events']=={'stack_spills':[{'site':'0x0076589a','dst':'DWORD PTR [ebp-0x24]'}],'nonstack_stores':[],'register_copies':[],'pushes':[],'exact_receiver_calls':[]}
 assert rows['FUN_00765aa0']['exact_root_events']=={'stack_spills':[{'site':'0x00765ad2','dst':'DWORD PTR [ebp-0x1c]'}],'nonstack_stores':[],'register_copies':[],'pushes':[],'exact_receiver_calls':[]}
 assert all(x['persistent_exact_root_escape_found'] is False for x in rows.values())
def test_range_hashes_match_tool_constants():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.RETAIL_SHA
 for n,(s,e,h) in m.RANGES.items():
  assert p['authority']['ranges'][n]=={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
def test_narrow_gate_only():
 a=data()['adjudication'];assert a['p13a_residual_indexed_wheel_root_lifetime_subset_complete'] is True
 for k in ['fun00765850_exact_root_persistent_escape_found','fun00765aa0_exact_root_persistent_escape_found','residual_indexed_exact_root_nonstack_store_found','residual_indexed_exact_root_push_found','residual_indexed_exact_root_direct_callee_forward_found']:
  assert a[k] is False
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','reconstructed_wheel_pointers_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
