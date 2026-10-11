import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_literal_producer_inventory.json'
def data():return json.loads(EV.read_text())
def test_literal_surface_counts():
 r=data()['inventory'];assert r['decoded_instruction_count']==2847850;assert r['literal_reference_count']==12;assert r['read_or_compare_count']==8;assert r['direct_write_count']==3;assert r['address_taken_count']==1
def test_direct_writes_exact():
 r=data()['inventory'];assert r['direct_write_sites']==['0x0045b2ae','0x0045ecd3','0x0045f43f'];assert r['direct_zero_write_sites']==['0x0045b2ae','0x0045f43f'];assert r['direct_runtime_value_write_sites']==['0x0045ecd3']
def test_runtime_source_exact():
 x=data()['inventory']['runtime_value_source'];assert x['write_site']=='0x0045ecd3';assert x['value_register']=='eax';assert 'vtable + 0xec' in x['source'];assert '0x0045ecca' in x['source']
def test_address_escape_exact():
 x=data()['inventory']['escaped_address_helper'];assert x=={'helper_call_site':'0x00872257','helper_target':'0x0041a560','lea_site':'0x00872247'}
def test_modulus1_frontier_preserved():assert data()['inventory']['remaining_modulus1_sites']==['0x00503328','0x0050334b']
def test_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_d94_literal_producer_inventory_subset_complete'] is True;assert a['writable_callback_pair_d94_literal_surface_has_runtime_or_helper_producers'] is True;assert a['writable_callback_pair_d94_value_range_proven'] is False;assert a['writable_callback_pair_target_compatible_frontier_empty'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['external_provider_count']==7
