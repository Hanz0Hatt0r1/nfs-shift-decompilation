import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_callnext_pic.py';E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_callnext_pic.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_callnext',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_callnext_detector_positive_and_negative():
 m=mod();rs=[(0x1000,'call','0x1005'),(0x1005,'pop','eax'),(0x1006,'call','0x2000'),(0x100b,'nop','')]
 assert m.find_callnext(rs)==[{'call':'0x00001000','return':'0x00001005','next_instruction':'pop eax'}]
def test_retail_has_one_callnext_and_it_is_secu_base_capture():
 p=data();assert p['format']=='SHIFT.P1A.P13AFun005ffc50CallNextPic/1'
 s=p['call_next_surface'];assert s['decoded_instruction_count']==2847850 and s['call_next_count']==1
 assert s['rows']==[{'call':'0x00d31404','return':'0x00d31409','next_instruction':'pop ebp'}]
 c=p['pic_candidate'];assert c['derived_value']=='0x00d31000' and c['derived_value_is_fun005ffc50'] is False and c['first_control_boundary']=='0x00d31420'
def test_machine_range_and_anchors_are_pinned():
 p=data();m=mod();r=p['authority']['machine_range'];assert p['authority']['retail_executable_sha256']==m.SHA and p['authority']['upstream_contract']==m.UPSTREAM
 assert r=={'start':'0x00d31400','end_exclusive':'0x00d31422','size':34,'sha256':'e1890a43eb24c8e35b25f6847e8d343902d22d0a7adb08395c3fcf67d105e112'}
 assert p['machine_anchors']['capture_return']=='0x00d31409 pop ebp' and p['machine_anchors']['subtract_delta']=='0x00d3140a sub ebp,0x409'
def test_narrow_gate_keeps_other_pic_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_call_next_pop_pic_subset_complete'] is True
 assert a['call_next_pop_fun005ffc50_reconstruction_found'] is False and a['call_next_pop_fun005ffc50_indirect_entry_found'] is False
 for k in ['other_pic_or_fnstenv_entry_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
