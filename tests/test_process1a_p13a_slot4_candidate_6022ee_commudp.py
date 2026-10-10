import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_slot4_candidate_6022ee_commudp.py'
E=ROOT/'evidence'/'p1a_p13a_slot4_candidate_6022ee_commudp_resolution.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_6022ee_commudp',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_upstream_candidate_and_network_vtable_identity():
 p=data();assert p['format']=='SHIFT.P1A.P13ASlot4Candidate6022eeCommUdpResolution/1'
 assert p['upstream_candidate']['call']=='0x006022ee' and p['upstream_candidate']['slot4_load']=='0x006022ea'
 n=p['network_object'];assert n['vtable']=='0x00adccb8' and n['slot_0x20']=='0x005c4a90'
 assert n['animation_vtable']=='0x00af7544' and n['vtable_is_animation_vtable'] is False
def test_commudp_table_resolves_bounded_indirect_targets():
 c=data()['commudp_table']
 assert c['returned_object_slot_0x4']=='0x00600f60' and c['returned_object_slot_0x20']=='0x00601030'
 assert c['candidate_0x006022ee_exact_slot4_target_on_bounded_paths']=='FUN_00600f60'
 assert c['candidate_0x006022dd_exact_slot20_target_on_bounded_paths']=='FUN_00601030'
def test_direct_surfaces_and_static_pointer_absence_are_exact():
 p=data();s=p['direct_call_surfaces']
 assert s['FUN_006021a0']==['0x005c34bd','0x005c367b']
 assert s['FUN_006022d0']==['0x005bcc0d','0x005c319e','0x005c31dd']
 assert s['FUN_005bcc00']==['0x005c4a6a','0x005c4a72']
 assert s['FUN_00601960']==['0x005b998a','0x005b99b4','0x005bfdad','0x005bfdf2','0x005bff3f']
 q=p['secondary_static_pointer_literals'];assert q['absolute_va_occurrence_count']==0 and q['rva_occurrence_count']==0
def test_machine_ranges_match_tool_constants():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.SHA and p['authority']['upstream_contract']==m.UPSTREAM
 for n,(s,e,sec,h) in m.RANGES.items():
  r=p['authority']['machine_ranges'][n];assert r['start']==f'0x{s:08x}' and r['end_exclusive']==f'0x{e:08x}' and r['size']==e-s and r['sha256']==h and len(h)==64
def test_narrow_gate_does_not_promote_global_callback_closure():
 a=data()['adjudication'];assert a['p13a_slot4_candidate_006022ee_direct_static_commudp_subset_complete'] is True
 assert a['slot4_candidate_006022ee_direct_static_target_resolved'] is True
 assert a['slot4_candidate_006022ee_direct_static_targets_fun0067b660'] is False
 assert a['slot4_candidate_006022ee_direct_static_exact_target_fun00600f60'] is True
 assert a['slot20_candidate_006022dd_direct_static_exact_target_fun00601030'] is True
 for k in ['fun0067b660_callback_argument_provenance_complete','callbacks_and_indirect_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
