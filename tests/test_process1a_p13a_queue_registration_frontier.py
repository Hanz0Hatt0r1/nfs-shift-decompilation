import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_queue_registration_frontier.py'
E=ROOT/'evidence'/'p1a_p13a_queue_registration_frontier.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_queue_frontier',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_direct_queue_registration_surface_is_exact():
 p=data();assert p['format']=='SHIFT.P1A.P13AQueueRegistrationFrontier/1'
 s=p['direct_registration_surface'];assert s['count']==4
 assert s['callsites']==['0x0067b69e','0x00713122','0x007131cc','0x0076e4ff']
 assert s['proven_selected_wheel_registration_count']==1
 assert s['proven_nonwheel_registration_count']==2
 assert s['unresolved_source_registration_count']==1
def test_only_unresolved_direct_source_is_static_callback():
 p=data();rows={x['site']:x for x in p['direct_registration_surface']['classifications']}
 assert rows['0x0076e4ff']['class']=='proven-selected-wheel-root'
 assert rows['0x00713122']['class']==rows['0x007131cc']['class']=='proven-distinct-task-subobject'
 assert rows['0x0067b69e']['class']=='unresolved-callback-source'
 c=p['callback_frontier'];assert c['function']=='FUN_0067b660' and c['direct_transfer_count']==0
 assert c['absolute_pointer_occurrence_count']==1
 assert c['absolute_pointer_occurrences']==[{'file_offset':'0x006f5f48','section':'.rdata','va':'0x00af7548'}]
 assert c['adjacent_static_string']=='AnimationProcessor::mStartEvent'
 assert c['argument_provenance_complete'] is False
def test_range_hashes_match_tool_constants():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.RETAIL_SHA
 s,e,h=m.CALLBACK_RANGE;assert p['authority']['callback_range']=={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 s,e,h=m.CALLBACK_TABLE_RANGE;assert p['authority']['callback_table_range']=={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
def test_frontier_gate_stays_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun00a62f60_direct_registration_surface_complete'] is True
 assert a['fun00a62f60_direct_registration_count']==4 and a['fun00a62f60_unresolved_source_registration_count']==1
 assert a['fun0067b660_static_callback_pointer_found'] is True
 assert a['fun0067b660_callback_argument_provenance_complete'] is False
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
