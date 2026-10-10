import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fixed_wheel_root_leaf_handoffs.py'
E=ROOT/'evidence'/'p1a_p13a_fixed_wheel_root_leaf_handoffs.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_leaf_handoffs',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_global_vehicle_receiver_and_slot_geometry_are_exact():
 p=data();assert p['format']=='SHIFT.P1A.P13AFixedWheelRootLeafHandoffs/1'
 assert p['authority']['global_vehicle_receiver']=='0x00c13700'
 s=p['wheel_layout']['slots'];assert p['wheel_layout']['count']==4 and p['wheel_layout']['stride']=='+0xa80'
 assert s[0]=={'slot':0,'wheel_root':'HDVehicle+0x400','selected_target':'HDVehicle+0x938..+0x93f'}
 assert s[1]=={'slot':1,'wheel_root':'HDVehicle+0xe80','selected_target':'HDVehicle+0x13b8..+0x13bf'}
def test_two_four_wheel_handoff_families_are_complete_leafs():
 h=data()['handoffs'];a=h['FUN_007582f0_to_FUN_00756010'];b=h['FUN_0076ed60_to_FUN_00753020']
 assert a['count']==b['count']==4
 assert [r['slot'] for r in a['rows']]==[0,1,2,3]
 assert [r['slot'] for r in b['rows']]==[0,1,2,3]
 assert a['callee_complete_leaf'] and b['callee_complete_leaf']
 assert a['callee_root_value_store_or_copy_found'] is False
 assert b['callee_root_value_store_or_copy_found'] is False
def test_narrow_gate_only_and_global_gates_fail_closed():
 a=data()['adjudication'];assert a['p13a_fixed_four_wheel_leaf_handoff_subset_complete'] is True
 assert a['fixed_four_wheel_leaf_handoff_count']==8
 assert a['fixed_four_wheel_leaf_root_persistence_found'] is False
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','reconstructed_wheel_pointers_ruled_out','stored_or_escaped_aliases_ruled_out','callbacks_and_indirect_entry_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
def test_machine_ranges_are_hash_pinned_to_tool_constants():
 p=data();m=module()
 assert p['authority']['retail_executable_sha256']==m.SHA
 for name,(s,e,h) in m.RANGES.items():
  r=p['authority']['ranges'][name];assert r['start']==f'0x{s:08x}' and r['end_exclusive']==f'0x{e:08x}' and r['size']==e-s and r['sha256']==h
