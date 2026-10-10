import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_simple_reconstruction.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_simple_reconstruction.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_5ffc50_recon',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_multistep_reconstruction_and_indirect_call():
 m=mod();lines=['  00500000: b8 00 f0 5f 00 mov eax,0x5ff000\n','  00500005: 05 50 0c 00 00 add eax,0xc50\n','  0050000a: ff d0 call eax\n']
 n,mats,calls=m.scan_lines(lines);assert n==3
 assert mats==[{'site':'0x00500005','register':'eax','instruction':'add eax,0xc50'}]
 assert calls==[{'site':'0x0050000a','kind':'call','register':'eax'}]
def test_synthetic_branch_boundary_kills_reconstruction_state():
 m=mod();lines=['  00500000: b8 00 f0 5f 00 mov eax,0x5ff000\n','  00500005: 75 02 jne 0x500009\n','  00500007: 05 50 0c 00 00 add eax,0xc50\n','  0050000c: ff d0 call eax\n']
 assert m.scan_lines(lines)[1:]==([],[])
def test_retail_simple_reconstruction_surface_is_zero():
 p=data();assert p['format']=='SHIFT.P1A.P13AFun005ffc50SimpleImmediateReconstruction/1'
 assert p['scope']['decoded_instruction_count']==2847850
 assert p['inventory']=={'exact_target_indirect_call_or_jump_count':0,'exact_target_materialization_count':0,'indirect_transfers':[],'materializations':[]}
def test_narrow_gate_stays_fail_closed_globally():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_simple_straight_line_immediate_reconstruction_subset_complete'] is True
 assert a['simple_straight_line_fun005ffc50_reconstruction_found'] is False and a['simple_straight_line_fun005ffc50_indirect_transfer_found'] is False
 for k in ['encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
