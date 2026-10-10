import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun0067b660_static_vtable_object.py'
E=ROOT/'evidence'/'p1a_p13a_fun0067b660_static_vtable_object.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_67b660_vtable',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_exact_object_vtable_and_slot4_identity():
 p=data();assert p['format']=='SHIFT.P1A.P13AFun0067b660StaticVtableObject/1'
 v=p['object_vtable'];assert v['address']=='0x00af7544' and v['fun0067b660_is_exact_slot_4'] is True
 assert [(x['slot'],x['target']) for x in v['entries']]==[('+0x0','0x0067b8c0'),('+0x4','0x0067b660'),('+0x8','0x0067b330')]
def test_constructor_layout_and_entry_surface_are_exact():
 c=data()['constructor_layout'];assert c['direct_call_count']==3
 assert c['direct_calls']==['0x00489171','0x0067b180','0x00d4b54e']
 assert c['embedded_instance_offsets']==['parent+0x8a0','parent+0x2c0','parent+0x320']
 assert c['source_record_base']=='+0x130' and c['source_record_stride']=='0x30' and c['source_record_count']==7
 assert c['source_record_vtable']=='0x00af74f4' and c['source_record_vtable_entries']==['0x0067b300','0x0067b730']
 assert c['queue_manager_offset']=='+0x2b0'
def test_machine_ranges_match_tool_constants():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.RETAIL_SHA
 for n,(s,e,h) in m.RANGES.items():
  assert p['authority']['ranges'][n]=={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
def test_argument_provenance_remains_fail_closed():
 p=data();b=p['callback_argument_boundary'];assert b['slot4_method_uses_ecx_receiver'] is False
 assert b['param1_equals_vtable_object_this_proven'] is False and b['param1_object_identity_complete'] is False
 a=p['adjudication'];assert a['p13a_fun0067b660_static_vtable_object_identity_complete'] is True
 assert a['fun0067b660_exact_vtable_slot_4_proven'] is True and a['fun0067b660_constructor_layout_complete'] is True
 assert a['fun0067b660_source_record_layout_complete'] is True
 assert a['fun0067b660_callback_argument_provenance_complete'] is False
 assert a['fun0067b660_callback_argument_is_selected_wheel_ruled_out'] is False
 for k in ['callbacks_and_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
