import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_direct_creg_entry.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_direct_creg_entry_closure.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_5ffc50_creg',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_direct_entry_surface_is_exact_and_has_no_creg():
 p=data();d=p['direct_entry_surface']
 assert p['format']=='SHIFT.P1A.P13AFun005ffc50DirectCregEntryClosure/1'
 assert d['direct_call_count']==13 and d['distinct_direct_caller_count']==3 and d['direct_creg_call_count']==0
 assert d['direct_callers']==['FUN_005b81a0','FUN_005b8210','FUN_005be1b0']
 assert d['command_counts']=={'0x63646563':3,'0x636c6964':1,'0x63726566':1,'0x69646576':1,'0x6d696372':3,'0x6f646576':1,'0x706f7274':1,'0x73657276':1,'0x74696d65':1}
 assert all(r['is_creg'] is False for r in d['rows'])
def test_exact_static_pointer_literals_are_absent():
 s=data()['static_pointer_literal_surface']
 assert s=={'exact_absolute_va':'0x005ffc50','exact_absolute_va_occurrence_count':0,'exact_rva':'0x001ffc50','exact_rva_occurrence_count':0}
def test_machine_range_and_creg_anchors_are_pinned():
 p=data();m=mod();r=p['authority']['fun005ffc50_range'];s,e,h=m.RANGE
 assert p['authority']['retail_executable_sha256']==m.SHA and p['authority']['upstream_contract']==m.UPSTREAM
 assert r=={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 a=p['machine_anchors'];assert a['creg_compare']=='0x005ffc69 cmp eax,0x63726567'
 assert a['creg_registry_call']=='0x005ffc7a call 0x6144f0'
def test_narrow_gate_stays_fail_closed_globally():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_direct_creg_entry_subset_complete'] is True
 assert a['direct_fun005ffc50_creg_registration_found'] is False
 assert a['exact_static_fun005ffc50_absolute_pointer_found'] is False and a['exact_static_fun005ffc50_rva_pointer_found'] is False
 assert a['fun005ffc50_creg_requires_indirect_or_reconstructed_entry'] is True
 for k in ['fun0067b660_callback_argument_provenance_complete','fun0067b660_callback_argument_is_selected_wheel_ruled_out','callbacks_and_indirect_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
