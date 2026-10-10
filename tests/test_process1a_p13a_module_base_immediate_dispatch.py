import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_module_base_immediate_dispatch.py'; E=ROOT/'evidence'/'p1a_p13a_module_base_immediate_dispatch_closure.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_dispatch',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_getter_dispatch_and_intervening_call_boundary():
 m=mod(); lines=[
 '  00500000: e8 7b 69 38 00 call   0x886980\n','  00500005: 8b f0 mov esi,eax\n','  00500007: 8b 06 mov eax,DWORD PTR [esi]\n','  00500009: 8b 80 84 00 00 00 mov eax,DWORD PTR [eax+0x84]\n','  0050000f: 8b ce mov ecx,esi\n','  00500011: ff d0 call eax\n']
 c,d,h=m.scan_lines(lines);assert len(c)==1 and d==[] and h[0]['slot']=='+0x84'
 blocked=[lines[0],'  00500005: e8 00 00 00 00 call 0x0050000a\n']+lines[1:]
 assert m.scan_lines(blocked)[2]==[]
def test_retail_immediate_surface_is_exact():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AModuleBaseImmediateDispatchClosure/1'
 assert i['direct_singleton_getter_call_count']==203
 assert i['direct_field_getter_transfer_count']==0
 assert i['immediate_virtual_dispatch_count']==14
 assert i['slot_counts']=={'+0x3c':3,'+0x48':4,'+0x58':5,'+0x5c':1,'+0x80':1}
 assert i['module_base_getter_slot_0x84_count']==0 and i['module_base_getter_slot_0xa4_count']==0
 assert p['immediate_virtual_dispatches'][-1]=={'dispatch_site':'0x00a691b2','form':'call-register','singleton_getter_call':'0x00a69197','slot':'+0x80'}
def test_bounded_negative_result_stays_fail_closed():
 a=data()['adjudication'];assert a['p13a_module_base_immediate_dispatch_subset_complete'] is True
 assert a['direct_module_base_field_getter_transfer_found'] is False
 assert a['immediate_module_base_getter_dispatch_found'] is False
 assert a['module_base_getter_consumer_paths_complete'] is False
 for k in ['delayed_or_stored_receiver_alias_dispatch_ruled_out','runtime_callback_registration_ruled_out','incoming_indirect_entry_ruled_out','encoded_or_reconstructed_carrier_pointers_ruled_out','runtime_generated_or_copied_carrier_pointers_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
