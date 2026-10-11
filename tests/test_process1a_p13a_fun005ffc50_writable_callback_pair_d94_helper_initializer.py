import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_helper_initializer.json'
def data(): return json.loads(EV.read_text())
def test_contract_and_authority():
 r=data(); assert r['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94HelperInitializer/1'; assert r['authority']['platform']=='PC retail 1.02'; assert r['authority']['retail_executable_sha256']=='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
def test_helper_chain_exact():
 p=data()['proof']; assert p['direct_helper_chain']==['0x0041a560','0x0062ffd0','0x0062fde0','0x0062f520']; assert p['cross_section_trampoline']=='0x00457f31'
def test_initializer_argument_and_flags_exact():
 p=data()['proof']; assert p['forwarded_initializer_arg1']==4; assert p['forced_low_flag_bits']=='0x1f'; assert p['field_object_register']=='esi'
def test_base_write_exact():
 p=data()['proof']; assert p['base_dword_write_site']=='0x0062f5e2'; assert p['base_dword_written_value']==4
def test_helper_source_closed_but_runtime_source_open():
 a=data()['adjudication']; assert a['p13a_fun005ffc50_writable_callback_pair_d94_helper_initializer_subset_complete'] is True; assert a['writable_callback_pair_d94_helper_base_dword_value_proven'] is True; assert a['writable_callback_pair_d94_helper_base_dword_value']==4; assert a['writable_callback_pair_d94_helper_is_unbounded_value_source'] is False; assert a['writable_callback_pair_d94_runtime_vtable_producer_value_range_proven'] is False
def test_fail_closed():
 a=data()['adjudication']; assert a['writable_callback_pair_d94_value_range_proven'] is False; assert a['writable_callback_pair_target_compatible_frontier_empty'] is False; assert a['writable_callback_pair_indirect_or_alias_writers_ruled_out'] is False; assert a['p13a_slot0_complete'] is False; assert a['p13a_slot1_complete'] is False; assert a['p1_3_control_producer_complete'] is False; assert a['external_provider_count']==7
