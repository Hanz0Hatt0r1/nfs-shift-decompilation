import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_delayed_receiver_alias.py'
E=ROOT/'evidence'/'p1a_p13a_delayed_receiver_alias_closure.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_delayed',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_local_event_scanner_tracks_exact_alias_and_subregister_kill():
 m=mod()
 rows=[
  (0x1000,'call','0x886980',''),(0x1005,'mov','DWORD PTR [ebp-0x10],eax',''),(0x1008,'mov','al,0x1',''),(0x100a,'ret','',''),
  (0x2000,'call','0x886980',''),(0x2005,'push','eax',''),(0x2006,'call','0x123456',''),
 ]
 calls,ev=m.local_events(rows)
 assert calls==[0x1000,0x2000]
 assert [e['kind'] for e in ev]==['stack_spill','call_argument_escape']
def test_retail_delayed_event_inventory_is_exact():
 p=data(); e=p['local_exact_receiver_events']
 assert p['format']=='SHIFT.P1A.P13ADelayedReceiverAliasClosure/1'
 assert p['scope']['direct_singleton_getter_call_count']==203
 assert e['stack_spill_count']==1 and e['stack_spills'][0]['site']=='0x00832aa2'
 assert e['raw_return_count']==1 and e['raw_returns'][0]['site']=='0x005f51a1'
 assert e['non_stack_store_count']==0 and e['call_argument_escape_count']==0
def test_nvapi_overwrite_closes_the_only_stack_spill():
 p=data()['stack_spill_closure']
 assert p['pre_overwrite_receiver_dispatch_slots']==['+0x50','+0x58']
 assert p['module_base_getter_slots_seen_before_overwrite']==[]
 assert p['dynamic_nvapi_slot']=='0x00bbbd34'
 assert p['dynamic_nvapi_interface_id']=='0xe5ac921f'
 assert p['dynamic_nvapi_symbol']=='NvAPI_EnumPhysicalGPUs'
 assert p['post_call_store_is_receiver_escape'] is False
def test_raw_return_is_unconsumed_and_global_gates_stay_fail_closed():
 p=data(); r=p['raw_return_closure']; a=p['adjudication']
 assert r['escaped_receiver_return_consumed'] is False
 assert [x['site'] for x in r['wrapper_direct_transfer_surface']]==['0x005f79d7','0x005f7b85','0x005f8aff']
 assert a['p13a_direct_getter_delayed_spill_return_subset_complete'] is True
 assert a['direct_singleton_getter_delayed_or_stored_alias_dispatch_ruled_out'] is True
 for k in ['delayed_or_stored_receiver_alias_dispatch_ruled_out','module_base_getter_consumer_paths_complete','runtime_callback_registration_ruled_out','incoming_indirect_entry_ruled_out','encoded_or_reconstructed_carrier_pointers_ruled_out','runtime_generated_or_copied_carrier_pointers_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
