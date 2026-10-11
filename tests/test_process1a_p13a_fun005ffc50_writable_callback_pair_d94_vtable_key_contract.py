import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_vtable_key_contract.json'
def data(): return json.loads(EV.read_text())
def test_authority_and_instruction_count():
 r=data(); assert r['authority']['retail_executable_sha256']=='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'; assert r['inventory']['decoded_instruction_count']==2847850
def test_registration_pair():
 r=data()['inventory']; assert [x['handle_storage'] for x in r['registrations']]==['0x00bbf2d4','0x00bbf2d0']; assert all(x['slot_load'] in ('0x0040db24','0x0040db3c') for x in r['registrations'])
def test_descriptor_contract():
 r=data()['inventory']; assert r['descriptor_initial_dword']==1; assert r['descriptor_zero_dwords']==2; assert r['descriptor_flag_mutation_between_registrations']=={'offset':'0x0c','site':'0x0040db36','value':1}
def test_lookup_pair():
 r=data()['inventory']; assert [x['handle_storage'] for x in r['lookups']]==['0x00bbf2d0','0x00bbf2d4']; assert r['lookups'][1]['result_field_offset']=='0x0d94'; assert r['lookups'][1]['call']=='0x0045ecca'
def test_same_singleton_proven(): assert data()['inventory']['same_singleton_registers_and_consumes_handles'] is True
def test_fail_closed():
 a=data()['adjudication']; assert a['p13a_fun005ffc50_writable_callback_pair_d94_vtable_key_contract_subset_complete'] is True; assert a['writable_callback_pair_d94_runtime_value_is_registered_singleton_key_lookup'] is True; assert a['writable_callback_pair_d94_vtable_ec_concrete_target_proven'] is False; assert a['writable_callback_pair_d94_value_range_proven'] is False; assert a['p1_3_control_producer_complete'] is False; assert a['external_provider_count']==7
