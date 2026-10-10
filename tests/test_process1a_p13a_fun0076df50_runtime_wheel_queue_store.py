import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun0076df50_runtime_wheel_queue_store.py'
E=ROOT/'evidence'/'p1a_p13a_fun0076df50_runtime_wheel_queue_store.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_76df50_queue',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data(): return json.loads(E.read_text(encoding='utf-8'))
def test_four_wheel_selected_root_store_surface_is_positive():
 p=data(); assert p['format']=='SHIFT.P1A.P13AFun0076df50RuntimeWheelQueueStore/1'
 w=p['four_wheel_loop']; assert w['slot_count']==4 and w['slots']==[0,1,2,3]
 assert w['roots']==['HDVehicle+0x400','HDVehicle+0xe80','HDVehicle+0x1900','HDVehicle+0x2380']
 s=p['runtime_pointer_store']; assert s['store_site']=='0x00a62fc0'
 assert s['stores_per_fun0076df50_wheel_loop']==4 and s['slot0_store_found'] and s['slot1_store_found']
def test_runtime_store_reaches_exact_virtual_consumer():
 c=data()['consumer_path']; assert c['runtime_node_task_pointer_reloaded'] is True
 assert c['consumer_receiver_is_exact_stored_wheel_root'] is True
 assert c['wheel_vptr']=='0x00b09a68' and c['wheel_vtable_slot_4']=='0x0075cfb0'
 assert c['resolved_slot_4_target']=='0x0075cfb0'
def test_hash_locked_machine_ranges_match_tool_constants():
 p=data();m=module();assert p['authority']['retail_executable_sha256']==m.RETAIL_SHA
 for n,(s,e,h) in m.RANGES.items():
  r=p['authority']['ranges'][n]; assert r=={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
def test_positive_store_keeps_global_gates_fail_closed():
 a=data()['adjudication']; assert a['p13a_fun0076df50_runtime_wheel_queue_store_subset_complete'] is True
 assert a['runtime_generated_selected_wheel_pointer_store_found'] is True
 assert a['slot0_runtime_wheel_pointer_store_found'] is True and a['slot1_runtime_wheel_pointer_store_found'] is True
 assert a['stored_wheel_pointer_indirect_virtual_consumer_found'] is True
 assert a['stored_wheel_pointer_virtual_slot_4_target_resolved'] is True
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','reconstructed_wheel_pointers_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
