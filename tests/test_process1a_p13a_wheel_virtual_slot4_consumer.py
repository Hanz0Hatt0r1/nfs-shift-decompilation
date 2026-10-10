import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_wheel_virtual_slot4_consumer.py'
E=ROOT/'evidence'/'p1a_p13a_wheel_virtual_slot4_consumer_closure.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_slot4',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_selected_target_range_and_virtual_consumer_are_exact():
 p=data();assert p['format']=='SHIFT.P1A.P13AWheelVirtualSlot4ConsumerClosure/1'
 assert p['selected_target']=={'wheel_relative_range':'+0x538..+0x53f','slot0_absolute':'HDVehicle+0x938..+0x93f','slot1_absolute':'HDVehicle+0x13b8..+0x13bf'}
 v=p['virtual_consumer'];assert v['target']=='0x0075cfb0' and v['instruction_count']==3841
 assert v['direct_selected_target_overlap_count']==0 and v['direct_selected_target_overlaps']==[]
 assert v['exact_root_forward']=={'prep':'0x007606f4','call':'0x00760705','callee':'FUN_00755790'}
def test_root_pointer_surface_has_only_one_transient_copy():
 p=data();v=p['virtual_consumer']['exact_root_surface']
 assert v=={'register_copies':[{'site':'0x007606f4','dst':'ecx'}],'nonstack_pointer_stores':[],'pushes':[],'writes_to_root_register':[]}
 c=p['forward_callee'];assert c['pointer_persistence_found'] is False and c['selected_target_write_found'] is False
 assert c['direct_selected_target_overlap_count']==0
 assert c['exact_root_surface']=={'register_copies':[],'nonstack_pointer_stores':[],'pushes':[],'writes_to_root_register':[]}
def test_range_hashes_match_tool_constants():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.RETAIL_SHA
 assert p['authority']['ranges']['wheel_virtual_slot4_target']=={'start':'0x0075cfb0','end_exclusive':'0x00760b48','size':m.TARGET_END-m.TARGET_START,'sha256':m.TARGET_SHA}
 assert p['authority']['ranges']['FUN_00755790']=={'start':'0x00755790','end_exclusive':'0x0075594a','size':m.CALLEE_END-m.CALLEE_START,'sha256':m.CALLEE_SHA}
def test_narrow_consumer_gate_only():
 a=data()['adjudication'];assert a['p13a_persisted_wheel_virtual_slot4_consumer_subset_complete'] is True
 assert a['persisted_wheel_virtual_slot4_selected_target_write_found'] is False
 assert a['persisted_wheel_virtual_slot4_exact_root_pointer_persistence_found'] is False
 assert a['persisted_wheel_virtual_slot4_only_exact_root_forward_closed'] is True
 assert a['runtime_generated_selected_wheel_pointer_store_found'] is True
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
