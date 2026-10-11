import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_runtime_writer_singleton_provenance.json'
def data():return json.loads(EV.read_text())
def test_contract_identity():
 r=data();assert r['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94RuntimeWriterSingletonProvenance/1';assert r['ready'] is True
def test_singleton_construction():
 p=data()['proof'];assert p['runtime_writer_singleton_storage']=='0x00bc185c';assert p['singleton_allocation_size']=='0x46e0';assert p['singleton_constructor']=='0x0045ef50';assert p['constructor_primary_vtable']=='0x00ab5644'
def test_singleton_write_surface():
 p=data()['proof'];assert p['singleton_direct_reference_count']==115;assert p['singleton_direct_write_count']==2;assert p['singleton_direct_write_sites']==['0x00d362ec','0x00d362f3']
def test_writer_direct_entry_surface():
 p=data()['proof'];assert p['writer_body']=='0x0045ec60';assert p['writer_guard_wrapper']=='0x00462d10';assert p['writer_body_direct_branch_sites']==['0x00462d1e'];assert p['writer_wrapper_direct_call_sites']==['0x004694fb'];assert p['writer_d94_store']=='0x0045ecd3'
def test_bounded_gates_only():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_d94_runtime_writer_singleton_provenance_subset_complete'] is True;assert a['writable_callback_pair_d94_runtime_writer_singleton_constructor_proven'] is True;assert a['writable_callback_pair_d94_runtime_writer_direct_entry_surface_bounded'] is True;assert a['writable_callback_pair_d94_writer_consumer_receiver_identity_proven'] is False;assert a['writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven'] is False
def test_aggregate_gates_fail_closed():
 a=data()['adjudication'];assert a['writable_callback_pair_d94_value_range_proven'] is False;assert a['p13a_slot0_complete'] is False;assert a['p13a_slot1_complete'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['callbacks_and_indirect_entry_ruled_out'] is False;assert a['external_provider_count']==7
