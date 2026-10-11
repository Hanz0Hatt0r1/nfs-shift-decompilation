import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_nonstack_fnstenv_direct_reachability.py';E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_nonstack_fnstenv_direct_reachability.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_nonstack_fnstenv',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_nonstack_rows_and_no_direct_incoming_edges():
 p=data();assert p['format']=='SHIFT.P1A.P13AFun005ffc50NonStackFnstenvDirectReachability/1'
 assert [x['site'] for x in p['non_stack_fnstenv_rows']]==['0x004177e4','0x0050d063']
 assert p['direct_incoming_edges']=={'0x004177e4':[],'0x0050d063':[]}
def test_first_decode_is_ret_followed_aligned_pointer_table():
 c=data()['decode_0x004177e4_context'];assert c['preceded_by']=='0x004177e2 ret' and c['aligned_dword_count']==11 and c['all_dwords_point_into_nearby_text'] is True
 assert c['aligned_dwords'][0]=='0x004177d9' and c['aligned_dwords'][-1]=='0x004177cc'
def test_second_decode_is_inside_int3_padding_window():
 c=data()['decode_0x0050d063_context'];assert c['size']==59 and c['int3_byte_count']==56
 assert c['preceding_transfer']=='0x0050d030 jmp 0x4eb550' and c['following_transfer']=='0x0050d070 jmp 0x40cc70'
 assert c['non_int3_bytes']==[{'site':'0x0050d035','byte':'0x90'},{'site':'0x0050d063','byte':'0xd9'},{'site':'0x0050d064','byte':'0xb3'}]
def test_narrow_gate_keeps_indirect_runtime_entry_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_nonstack_fnstenv_direct_reachability_subset_complete'] is True
 assert a['nonstack_fnstenv_direct_call_or_branch_entry_found'] is False and a['nonstack_fnstenv_fallthrough_from_preceding_code_found'] is False
 for k in ['nonstack_fnstenv_indirect_or_runtime_entry_ruled_out','other_pic_or_fnstenv_entry_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
