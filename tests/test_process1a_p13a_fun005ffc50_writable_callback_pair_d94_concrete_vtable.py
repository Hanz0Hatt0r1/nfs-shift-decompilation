import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_concrete_vtable.json'
def data():return json.loads(EV.read_text())
def test_vtable_targets():
 p=data()['proof']; assert p['concrete_vtable']=='0x00b18d38'; assert p['registration_slot_e0_target']=='0x008313b0'; assert p['lookup_slot_ec_target']=='0x0082da60'
def test_singleton_writes_exact():assert data()['proof']['direct_singleton_write_sites']==['0x00823d1a','0x00823d50']
def test_constructor_contract():
 p=data()['proof']; assert p['singleton_allocation_size']=='0x3970'; assert p['singleton_constructor']=='0x008323d0'; assert p['singleton_store']=='0x00823d1a'
def test_registration_is_index():assert data()['proof']['registration_target_writes_handle_index'] is True
def test_lookup_dispatch_shape():
 p=data()['proof']; assert p['lookup_target_dispatch_table_offset']=='0x1ac8'; assert p['lookup_target_null_entry_returns_zero'] is True; assert p['lookup_target_nonnull_entry_dispatches_entry_vtable_slot0'] is True
def test_fail_closed():
 a=data()['adjudication']; assert a['p13a_fun005ffc50_writable_callback_pair_d94_concrete_vtable_subset_complete'] is True; assert a['writable_callback_pair_d94_vtable_ec_concrete_target_proven'] is True; assert a['writable_callback_pair_d94_vtable_ec_target']=='0x0082da60'; assert a['writable_callback_pair_d94_value_range_proven'] is False; assert a['p1_3_control_producer_complete'] is False; assert a['external_provider_count']==7
