import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_loop_receiver_provenance.json'
def data():return json.loads(EV.read_text())
def test_contract_identity():
 r=data();assert r['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LoopReceiverProvenance/1';assert r['ready'] is True
def test_loop_owner_identity():
 p=data()['proof'];assert p['loop_function']=='0x005031e0';assert p['loop_owner_vtable']=='0x00ac4a58';assert p['loop_owner_vtable_slot1']=='0x005031e0';assert p['loop_function_pointer_occurrences_in_image']==1
def test_source_and_derived_containers():
 p=data()['proof'];assert p['source_container']=='loop_owner+0x4';assert p['source_container_element_stride']=='0x0d98';assert p['derived_container']=='loop_owner+0x38';assert p['derived_record_first_dword_source']=='source_record+0x0'
def test_loop_receiver_chain():
 p=data()['proof'];assert p['loop_receiver_expression']=='DWORD PTR [derived_record+0x0]';assert p['loop_receiver_load_site']=='0x005032e6';assert p['loop_bound_sites']==['0x005032ea','0x0050337a']
def test_writer_identity_stays_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_d94_loop_receiver_provenance_subset_complete'] is True;assert a['writable_callback_pair_d94_loop_receiver_source_chain_proven'] is True;assert a['writable_callback_pair_d94_writer_consumer_receiver_identity_proven'] is False;assert a['writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven'] is False;assert a['writable_callback_pair_d94_value_range_proven'] is False
def test_aggregate_gates_fail_closed():
 a=data()['adjudication'];assert a['p13a_slot0_complete'] is False;assert a['p13a_slot1_complete'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['callbacks_and_indirect_entry_ruled_out'] is False;assert a['external_provider_count']==7
